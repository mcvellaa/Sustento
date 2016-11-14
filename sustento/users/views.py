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
        return reverse('users:detail',
                       kwargs={'username': self.request.user.username})

def UserSendView(request):
    from .forms import UserSendForm
    context = {}
    context['responses'] = Response.objects.all()
    context['sentMessages'] = SentMessage.objects.all()
    context['journal'] = PersonalJournal.objects.all()
    context['contexts'] = ContextForWeek.objects.all()
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = UserSendForm(request.POST)
        context['form'] = form
        # check whether it's valid:
        if form.is_valid():
            # THIS IS WHERE I SEND TO TWILIO
            tclient = TwilioRestClient(os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_API_AUTH'])
            phone_number = re.sub("(,[ ]*!.*-)$", "", request.POST.get('phone'))
            userid = User.objects.get(phone=phone_number)
            messageBody = request.POST.get('text')
            sentM = SentMessage(recipient=userid, phone=phone_number, message=messageBody)
            sentM.save()
            message = tclient.messages.create(body=messageBody, to="+1"+phone_number, from_="+14122010448")
            # 
            # redirect to a new URL:
            return HttpResponseRedirect('/users/~send/')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = UserSendForm()
        context['form'] = form

    return render(request, 'users/send.html', context)

class UserUpdateView(LoginRequiredMixin, UpdateView):

    fields = ['name', 'phone', ]

    # we already imported User in the view code above, remember?
    model = User

    # send the user back to their own page after a successful update
    def get_success_url(self):
        return reverse('users:detail',
                       kwargs={'username': self.request.user.username})

    def get_object(self):
        # Only get the User record for the user making the request
        return User.objects.get(username=self.request.user.username)


class UserListView(LoginRequiredMixin, ListView):
    model = User
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'

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
        sentM = SentMessage(recipient=userid, phone=respPhone, message=respToUser[0])
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
    print(response2)

    #Store Msg + Sentiment Analysis if appropriate
    storeUserMessage(response2, user)

    # Send response to User
    if response2['output']['text']:
        automatedResp = response2['output']['text']
    else:
        automatedResp = "Got it, have a great rest of your day!"
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
    else:
        return