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
import collections

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
    responses = Response.objects.all().filter(sender=request.user).order_by('-date_created')
    sentMessages = SentMessage.objects.all().filter(recipient=request.user).order_by('-date_created')
    #now put all messages into a dictionary
    messages = dict()
    for r in responses:
        key = "response" + str(r.id)
        messages[key] = dict()
        messages[key]["type"] = "responses"
        messages[key]["date"] = r.date_created
        messages[key]["text"] = r.message
    for s in sentMessages:
        key = "sent" + str(s.id)
        messages[key] = dict()
        messages[key]["type"] = "sent"
        messages[key]["date"] = s.date_created
        messages[key]["text"] = s.message
    context['mes'] = collections.OrderedDict(sorted(messages.items(), key=lambda t: t[1]["date"], reverse=True))

    return render(request, 'users/messages.html', context)

def MainView(request):
    context = {}
    return render(request, 'users/main.html', context)

def JournalView(request):
    if request.user.is_authenticated() == False:
        return HttpResponseRedirect('/accounts/login/')
    from .forms import JournalEntryForm
    context = {}
    context['journal'] = PersonalJournal.objects.all().filter(patient=request.user).order_by('-date_created')
    context['contexts'] = ContextForWeek.objects.all().filter(patient=request.user).order_by('-start_date')
    if request.method == 'POST' and request.user:
        # create a form instance and populate it with data from the request:
        form = JournalEntryForm(request.POST)
        context['form'] = form
        # check whether it's valid:
        if form.is_valid():
            # Get the emotions back
            userid = request.user
            messageBody = request.POST.get('text')
            sentimentAnalysis = alchemy_language.emotion(text=messageBody)
            journalEntry = PersonalJournal(patient=userid, entry=messageBody, context=ContextForWeek.objects.filter(patient=userid).latest('end_date'), emotion_anger=sentimentAnalysis['docEmotions']['anger'], emotion_disgust=sentimentAnalysis['docEmotions']['disgust'], emotion_sadness=sentimentAnalysis['docEmotions']['sadness'], emotion_fear=sentimentAnalysis['docEmotions']['fear'], emotion_joy=sentimentAnalysis['docEmotions']['joy'])
            journalEntry.save()
            # redirect to a new URL:
            return HttpResponseRedirect('/users/~journal/')
    # if a GET (or any other method) we'll create a blank form
    else:
        form = JournalEntryForm()
        context['form'] = form

    return render(request, 'users/journal.html', context)

# Overall Dashboard View for User
def DashboardView(request):
    if request.user.is_authenticated() == False:
        return HttpResponseRedirect('/accounts/login/')
    # Get Contexts in descending order: latest context is first
    context = {}
    context['contexts'] = ContextForWeek.objects.all().filter(patient=request.user).order_by('-start_date')
    # Filter if user has entered any filter params
    if request.method=='GET':
        searchContext = request.GET.get('searchContextBox', None)
        searchDate = request.GET.get('searchDateBox', None)
        if (searchContext != None and searchContext != ''):
            context['contexts'] = context['contexts'].filter(context__icontains=searchContext).order_by('-start_date')
        if (searchDate != None and searchDate != ''):
            context['contexts'] = context['contexts'].filter(start_date__lte = searchDate) & context['contexts'].filter(end_date__gte = searchDate).order_by('-start_date')
    return render(request, 'users/dashboard.html', context)

# Get Data Points for Each Emotion
def getChartData(journalEntries):
    data = {"Time":[], "Anger":[], "Sadness":[], "Joy":[], "Fear":[], "Disgust":[]}
    # get time and emotions for each journal entry
    for j in journalEntries:
        # Time of journal entry
        t = j.date_created.strftime('%H:%M')
        data["Time"].append(t)
        # Emotions of journal entry
        data["Anger"].append(float(j.emotion_anger))
        data["Sadness"].append(float(j.emotion_sadness))
        data["Joy"].append(float(j.emotion_joy))
        data["Fear"].append(float(j.emotion_fear))
        data["Disgust"].append(float(j.emotion_disgust))
    return data

# Daily Dashboard for User
def DailySummaryView(request):
    from datetime import datetime
    # 1. Get Search Date & Search Context: If User enters date
    if request.method=='GET':
        stringDate = request.GET.get('searchStartDateBox', None)
        searchContext = request.GET.get('searchContextBox', None)
    # Default: Search Date is now()
    if stringDate is None or stringDate=='':
        searchStartDate=datetime.now().date()
        # FOR LOCAL TESTING: Search Date is set to 30th Nov
        # searchStartDate = datetime.strptime('20161130', "%Y%m%d").date()
    else:
        # Get Date Object from String entered
        searchStartDate = datetime.strptime(stringDate, "%Y-%m-%d").date()

    # Get Current Day/ Date 
    currentDay = searchStartDate.strftime('%A').upper()
    currentDate = searchStartDate.strftime('%b %d, %y') 

    # 2. Get journal entries for user for a given day
    # Filter Bar: Require only date or require both context and date
    if (searchContext != None and searchContext != '' and stringDate is not None):
        journalEntries = PersonalJournal.objects.all().filter(patient=request.user).filter(date_created__contains=searchStartDate).filter(context__context__icontains=searchContext)
    # if (searchContext != None and searchContext != ''):
    #     journalEntries = PersonalJournal.objects.all().filter(patient=request.user).filter(context__context__icontains=searchContext)
    else:
        journalEntries = PersonalJournal.objects.all().filter(patient=request.user).filter(date_created__contains=searchStartDate)   
    context = {}

    # 3. Get Context & Data For Chart
    if len(journalEntries) < 1:
        con = None
    else:
        con = journalEntries[0].context
        data = getChartData(journalEntries)

        # 4. Chart Attributes
        chartID = "lineChart"
        chart = {"renderTo": chartID, "type": 'line'}  
        # title = {"text": 'Daily Emotion Analysis'}
        title = {"text": ''}
        xAxis = {"title": {"text": 'Time'}, "categories": data['Time']}
        yAxis = {"title": {"text": 'Emotion'}}
        series = [
            {"name": 'Anger', "data": data['Anger'], "color":'#d9534f'},
            {"name": 'Sadness', "data": data['Sadness'], "color":'#5bc0de'},
            {"name": 'Disgust', "data": data['Disgust'], "color":'#5cb85c'},
            {"name": 'Joy', "data": data['Joy'], "color":'#ffd600'},
            {"name": 'Fear', "data": data['Fear'], "color":'#EE82EE'}
        ]

        # 5. Create Context Variables
        context['chartID'] = chartID
        context['chart'] = chart
        context['title'] = title
        context['xAxis'] = xAxis
        context['yAxis'] = yAxis
        context['series'] = series

    context['journalEntries'] = journalEntries
    context["contextForWeek"] = con
    context['currentDay'] = currentDay
    context['currentDate'] = currentDate
    # 6. Render Daily Summary Template
    return render(request, 'users/dailySummary.html', context)

def RemindersView(request):
    if request.user.is_authenticated() == False:
        return HttpResponseRedirect('/accounts/login/')
    from .forms import RemindersForm
    context = {}
    context['reminders'] = Reminders.objects.filter(patient=request.user)
    if request.method == 'POST' and request.user:
    # create a form instance and populate it with data from the request:
        form = RemindersForm(request.POST)
        context['form'] = form
        # check whether it's valid:
        if form.is_valid():
            userid = request.user
            when = request.POST.get('when')
            text = request.POST.get('text')
            remind = Reminders(patient=userid, when=when, text=text)
            remind.save()
            return HttpResponseRedirect('/users/~reminders/')
    # if a GET (or any other method) we'll create a blank form
    else:
        form = RemindersForm()
        context['form'] = form

    return render(request, 'users/reminders.html', context)


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

    #Process Intent + Store Msg + Sentiment Analysis if appropriate
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
        journalEntry = PersonalJournal(patient=user, entry=resp['input']['text'], context=ContextForWeek.objects.filter(patient=user).latest('end_date'), emotion_anger=sentimentAnalysis['docEmotions']['anger'], emotion_disgust=sentimentAnalysis['docEmotions']['disgust'], emotion_sadness=sentimentAnalysis['docEmotions']['sadness'], emotion_fear=sentimentAnalysis['docEmotions']['fear'], emotion_joy=sentimentAnalysis['docEmotions']['joy'])
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
        # End any previous contexts
        previousContexts = ContextForWeek.objects.filter(end_date__gt=datetime.datetime.now())
        for con in previousContexts:
            con.end_date = datetime.datetime.now()
            con.save()
        # Store Context for Week
        con = ContextForWeek(patient=user, context=conForWeek, start_date=datetime.datetime.now(), end_date=(datetime.datetime.now() + datetime.timedelta(days=7)))
        con.save()
        # Store message as Personal Journal as well to display on dashboard
        sentimentAnalysis = alchemy_language.emotion(text=resp['input']['text'])
        journalEntry = PersonalJournal(patient=user, entry=resp['input']['text'], context=con, emotion_anger=sentimentAnalysis['docEmotions']['anger'], emotion_disgust=sentimentAnalysis['docEmotions']['disgust'], emotion_sadness=sentimentAnalysis['docEmotions']['sadness'], emotion_fear=sentimentAnalysis['docEmotions']['fear'], emotion_joy=sentimentAnalysis['docEmotions']['joy'])
        journalEntry.save()
        
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

@csrf_exempt
def UserSchedule(request):
    for r in Reminders.objects.all():
        if r.when.weekday() == datetime.datetime.today().weekday():
            sendUserMessage(r.text, r.patient)
    return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><Response></Response>')

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
