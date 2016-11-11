# VIEW CONTROLLER 
# Class or method for every page

# NOTE: Create Env variables for API variables: os.environ
# Environ Variables to be added to Heroku
os.environ['Alchemy_API_Key'] = 'ce6750adb25651986b7343be606710df17f97433'
os.environ['Conversation_Username'] = 'cacc9266-1ddd-4dc3-a50c-2746e5521c84'
os.environ['Conversation_Password'] = '1gUM2kOQ57kd'
os.environ['Conversation_Version'] = '2016-09-20'
os.environ['Bluemix_Workspace_id'] = '4f0a3c6c-d73c-4248-9563-409a5b64f678'

# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.core.urlresolvers import reverse
from django.views.generic import DetailView, ListView, RedirectView, UpdateView

from django.contrib.auth.mixins import LoginRequiredMixin

from .models import *

from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from twilio.rest import TwilioRestClient
import os
import re

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

context = {}

# Workspace (i.e. Sustento) ID
workspace_id = os.environ['Bluemix_Workspace_id']
#------------------------------------------------------

# TO BE FIXED: Global variable right now since it needs to be accessible across methods. Need to redesign such that this is not required
automatedResp = ''

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

# LOGIC HAPPENS WITHIN THIS METHOD: SEND MSG TO USER
def UserSendView(request):
    from .forms import UserSendForm
    context = {}
    context['responses'] = Response.objects.all()
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = UserSendForm(request.POST)
        context['form'] = form
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # 
            # THIS IS WHERE I SEND TO TWILIO
            tclient = TwilioRestClient(os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_API_AUTH'])
            phone_number = re.sub("(,[ ]*!.*-)$", "", request.POST.get('phone'))
            message = tclient.messages.create(body=request.POST.get('text'), to="+1"+phone_number, from_="+14122010448")
            # 
            # redirect to a new URL:
            return HttpResponseRedirect('/users/~send/')
        else if !form.has_changed: # form is blank==> automated response
            # get automated response
            message = tclient.messages.create(body=automatedResp, to="+1"+phone_number, from_="+14122010448")
            # redirect to a new URL:
            return HttpResponseRedirect('/users/~send/')


    # if a GET (or any other method) we'll create a blank form
    else:
        form = UserSendForm()
        context['form'] = form

    return render(request, 'users/send.html', context)

class UserUpdateView(LoginRequiredMixin, UpdateView):

    fields = ['name', ]

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
    
def getResponseForMessage(msg):
    # conversation starter: Hi
    response1 = conversation.message(
      workspace_id=workspace_id,
      message_input={'text': 'Hi'},
      context=context
    )
    # get intent from message sent by user
    response2 = conversation.message(
      workspace_id=workspace_id,
      message_input={'text': msg},
      context=response1['context']
    )
    print("Response 2 Intent: ", response2['intents'])

    #Store Msg + Sentiment Analysis if appropriate
    storeUserMessage(response2)

    # Send response to User
    automatedResp = response2['output']['text']

def storeUserMessage(resp):
    # 1. Store message sent by user
    # 2. Perform analysis if personal journal
    # 3. Store sentiment analysis results
    # If intent = personal journal --> Sentiment Analysis
    if 'PersonalJournal' in resp['intents'][0]['intent']:
        sentimentAnalysis = alchemy_language.emotion(
            text=resp['input']['text'])
        print("Emotion Analysis for Personal Journal")
        print(json.dumps(sentimentAnalysis, indent=2))


#this will come from Twilio, so we won't have the secret token
@csrf_exempt
# MESSAGE SENT BY USER
def UserReceive(request):
    # if this is a POST request from Twilio, we need to process the POST data
    if request.method == 'POST':
        #receive the Twilio post data and create a new response object
        respPhone = request.POST.get('From')[-10:]
        respMessage = request.POST.get('Body')
        # RESP = MESSAGE SENT BY USER
        resp = Response(phone=respPhone, anonymous=False, message=respMessage)
        resp.save()

        # get Response for message using Conversation API
        getResponseForMessage(resp)

        return HttpResponseRedirect('/users/~send/')
    # if a GET or wrong domain, we'll just redirect
    else:
        return HttpResponseRedirect('/users/~send/')