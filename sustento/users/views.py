# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.core.urlresolvers import reverse
from django.views.generic import DetailView, ListView, RedirectView, UpdateView

from django.contrib.auth.mixins import LoginRequiredMixin

from .models import User

from django.shortcuts import render
from django.http import HttpResponseRedirect

from twilio.rest import TwilioRestClient
import os

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
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = UserSendForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # 
            # THIS IS WHERE I SEND TO TWILIO
            tclient = TwilioRestClient(env['TWILIO_ACCOUNT_SID'], env['TWILIO_API_AUTH'])
            message = tclient.messages.create(body=request.POST.get('text'), to="+12035601401", from_="+14122010448")
            # 
            # redirect to a new URL:
            return HttpResponseRedirect('/users/~send/')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = UserSendForm()

    return render(request, 'users/send.html', {'form': form})

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
