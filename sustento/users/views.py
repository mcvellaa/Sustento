# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.core.urlresolvers import reverse
from django.views.generic import DetailView, ListView, RedirectView, UpdateView

from django.contrib.auth.mixins import LoginRequiredMixin

from .models import *

from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from twilio.rest import TwilioRestClient
import os
import re
import datetime
#------------------------------------------------------
# For Alchemy and Conversation APIs to work:
import json

# Alchemy API Key
from watson_developer_cloud import AlchemyLanguageV1
alchemy_language = AlchemyLanguageV1(api_key=os.environ['Alchemy_API_Key'])

# Conversation Credentials
from watson_developer_cloud import ConversationV1
conversation = ConversationV1(
    username=os.environ['Conversation_Username'],
    password=os.environ['Conversation_Password'],
    version = os.environ['Conversation_Version'])

# Workspace (i.e. Sustento) ID
workspace_id = os.environ['Bluemix_Workspace_id']
#------------------------------------------------------

class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse('users:home')

class UserListView(LoginRequiredMixin, ListView):
    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'

def MessagesView(request):
    if request.user.is_authenticated() == False:
        return HttpResponseRedirect('/accounts/login/')
    #this is for viewing the raw messages thread
    context = {}
    context['responses'] = Response.objects.all().filter(sender=request.user).order_by('-date_created')
    context['sentMessages'] = SentMessage.objects.all().filter(recipient=request.user).order_by('-date_created')

    return render(request, 'users/messages.html', context)

def JournalView(request):
    if request.user.is_authenticated() == False:
        return HttpResponseRedirect('/accounts/login/')
    context = {}
    context['journal'] = PersonalJournal.objects.all().filter(patient=request.user).order_by('-date_created')
    context['contexts'] = ContextForWeek.objects.all().filter(patient=request.user).order_by('-start_date')

    return render(request, 'users/journal.html', context)

def HomeView(request):
    if request.user.is_authenticated() == False:
        return HttpResponseRedirect('/accounts/login/')
    elif request.user.is_authenticated() and request.user.phone == "":
        return HttpResponseRedirect('/users/~update')
    from .forms import UserSendForm
    context = {}
    # if this is a POST request we need to process the form data
    if request.method == 'POST' and request.user:
        # create a form instance and populate it with data from the request:
        form = UserSendForm(request.POST)
        context['form'] = form
        # check whether it's valid:
        if form.is_valid():
            # THIS IS WHERE I SEND TO TWILIO
            tclient = TwilioRestClient(os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_API_AUTH'])
            phone_number = request.user.phone
            userid = request.user
            messageBody = request.POST.get('text')
            sentM = SentMessage(recipient=userid, phone=phone_number, message=messageBody)
            sentM.save()
            message = tclient.messages.create(body=messageBody, to="+1"+phone_number, from_="+14122010448")
            # 
            # redirect to a new URL:
            return HttpResponseRedirect('/users/')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = UserSendForm()
        context['form'] = form

    return render(request, 'users/home.html', context)

class UserUpdateView(LoginRequiredMixin, UpdateView):

    fields = ['name', 'phone', ]

    # we already imported User in the view code above, remember?
    model = User

    # send the user back to their own page after a successful update
    def get_success_url(self):
        return reverse('users:home')

    def get_object(self):
        # Only get the User record for the user making the request
        return User.objects.get(username=self.request.user.username)

#this will come from Twilio, so we won't have the secret token
@csrf_exempt
def UserReceive(request):
    # if this is a POST request from Twilio, we need to process the POST data
    if request.method == 'POST':
        #receive the Twilio post data and create a new response object
        respPhone = request.POST.get('From')[-10:]
        respMessage = request.POST.get('Body')
        # query the users table to get the user id of the phone number, or just put 1
        userid = User.objects.get(phone=respPhone)
        # now save the response to be shown
        resp = Response(sender=userid, phone=respPhone, message=respMessage)
        resp.save()
        #now get automated response
        respToUser = getResponseForMessage(respMessage, userid)
        # save the sent message in the database
        sentM = SentMessage(recipient=userid, phone=respPhone, message=respToUser)
        sentM.save()
        # send the text to the user through Twilio
        tclient = TwilioRestClient(os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_API_AUTH'])
        message = tclient.messages.create(body=respToUser, to="+1"+respPhone, from_="+14122010448")

        return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>')
    # if a GET or wrong domain, we'll just redirect
    else:
        return HttpResponseRedirect('/users/~send/')

@csrf_exempt
def getResponseForMessage(msg, user):
    # conversation starter: Hi
    response1 = conversation.message(
      workspace_id=workspace_id,
      message_input={'text': 'Hi'},
      context={}
    )
    # get intent from message sent by user
    response2 = conversation.message(
      workspace_id=workspace_id,
      message_input={'text': msg},
      context=response1['context']
    )

    #Store Msg + Sentiment Analysis if appropriate
    storeUserMessage(response2, user)

    # Send response to User
    if response2['output']['text']:
        automatedResp = response2['output']['text'][0]
    else:
        automatedResp = 'Got it, have a great rest of your day!'
    return automatedResp

@csrf_exempt
def getContextForWeek(entities):
    # Entities is a list of dictionaries of different entities identified by Watson Conversation. We want value of entity titled ContextForWeek.
    if len(entities) < 1:
        return ''
    else:
        for d in entities:
            if d['entity'] == 'ContextForWeek':
                return d['value']
        return ''

@csrf_exempt
def getIntentOfMsg(intents):
    # Intents is a list of dictionaries of different intents identified by Watson Conversation. We want to see if intent = PersonalJournal, ContextForWeek or others
    if len(intents) < 1:
        return ''
    else:
        for d in intents:
            if d['intent'] == 'ContextForWeek':
                return 'ContextForWeek'
            elif d['intent'] == 'PersonalJournal':
                return 'PersonalJournal'
            elif d['intent'] == 'HighRisk':
                return 'HighRisk'
            elif d['intent'] == 'Unsubscribe':
                return 'Unsubscribe'
            elif d['intent'] == 'ConversationStarter':
                return 'ConversationStarter'
        return ''

@csrf_exempt
def storeUserMessage(resp, user):
    msgIntent = getIntentOfMsg(resp['intents'])
    # If Personal Journal:
        # 1. Perform analysis
        # 2. Store sentiment analysis results
    if msgIntent == 'PersonalJournal':
        sentimentAnalysis = alchemy_language.emotion(text=resp['input']['text'])
        journalEntry = PersonalJournal(patient=user, entry=resp['input']['text'], emotion_anger=sentimentAnalysis['docEmotions']['anger'], emotion_disgust=sentimentAnalysis['docEmotions']['disgust'], emotion_sadness=sentimentAnalysis['docEmotions']['sadness'], emotion_fear=sentimentAnalysis['docEmotions']['fear'], emotion_joy=sentimentAnalysis['docEmotions']['joy'])
        journalEntry.save()
        return
    # If Context For Week: Store Context For Week
    elif msgIntent == 'ContextForWeek':
        entities = resp['entities']
        # Get value of entity=contextForWeek if exists
        conForWeek = getContextForWeek(entities)
        # Else context = entire message
        if conForWeek == '':
            conForWeek = resp['input']['text']
        # Store Context for Week
        con = ContextForWeek(patient=user, context=conForWeek, start_date=datetime.date.today(), end_date=(datetime.date.today() + datetime.timedelta(days=7)))
        con.save()
        return 
    elif msgIntent == 'Unsubscribe':
        deactivateUser(user)
    else:
        return

def deactivateUser(user):
    user.text_active = False
    user.save()

#------------------------------------------------------------------------
# SCHEDULE TEXT MESSAGES
def sendUserMessage(message, user):
    # send the text to the user through Twilio
    tclient = TwilioRestClient(os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_API_AUTH'])
    phone_number = user.phone
    message = tclient.messages.create(body=message, to="+1"+phone_number, from_="+14122010448")
    return

@csrf_exempt
def UserSchedule(request):
    user = User.objects.filter(phone="2035601401").first
    sendUserMessage(datetime.datetime.now(), user)

#import schedule
#import time
#import threading

#def run_threaded(job_func, *kwargs):
#    job_thread = threading.Thread(target=job_func, args=kwargs)
#    job_thread.start()

#def requestContextForWeekFromUser(user):
#    msg = 'What do you want to work on this week?'
#    schedule.every(0.1).minutes.do(sendUserMessage, msg, user)
#    schedule.run_pending()

#for user in User.objects.all():
#    if user.phone != "":
#        run_threaded(requestContextForWeekFromUser, user)
#------------------------------------------------------------------------