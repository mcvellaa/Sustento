# MODEL 

# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django.contrib.auth.models import AbstractUser
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class User(AbstractUser):

    # First Name and Last Name do not cover name patterns
    # around the globe.
    name = models.CharField(_('Name of User'), blank=True, max_length=255)
    phone = models.CharField(_('Phone Number'), blank=False, max_length=255)

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse('users:detail', kwargs={'username': self.username})

class Response(models.Model):
    sender = models.ForeignKey(User)
    phone = models.CharField(max_length=15)
    message = models.CharField(max_length=1000)
    date_created = models.DateTimeField(auto_now_add=True, blank=True)

class SentMessage(models.Model):
    recipient = models.ForeignKey(User)
    phone = models.CharField(max_length=15)
    message = models.CharField(max_length=1000)
    date_created = models.DateTimeField(auto_now_add=True, blank=True)

class ContextForWeek(models.Model):
    patient = models.ForeignKey(User)
    context = models.CharField(max_length=1000)
    start_date = models.DateTimeField(blank=False)
    end_date = models.DateTimeField(blank=True)

class PersonalJournal(models.Model):
    patient = models.ForeignKey(User)
    date_created = models.DateTimeField(auto_now_add=True, blank=True)
    entry = models.CharField(max_length=2000)
    emotion_anger = models.CharField(max_length=15)
    emotion_disgust = models.CharField(max_length=15)
    emotion_sadness = models.CharField(max_length=15)
    emotion_fear = models.CharField(max_length=15)
    emotion_joy = models.CharField(max_length=15)