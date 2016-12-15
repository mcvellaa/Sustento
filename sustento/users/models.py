# MODEL 

# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django.contrib.auth.models import AbstractUser
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from datetime import datetime

@python_2_unicode_compatible
class User(AbstractUser):

    # First Name and Last Name do not cover name patterns
    # around the globe.
    name = models.CharField(_('Name of User'), blank=True, max_length=255)
    phone = models.CharField(_('Phone Number'), blank=False, max_length=255)
    text_active = models.BooleanField(default=True)
    show_emotions = models.BooleanField(default=True)

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

    def get_journal_entries(self):
        return PersonalJournal.objects.filter(context = self.id).order_by('-date_created')

    def print_start_date(self):
        from datetime import datetime
        return self.start_date.strftime('%b %d, %y')
    def print_end_date(self):
        from datetime import datetime
        return self.end_date.strftime('%b %d, %y')

class Reminders(models.Model):
    patient = models.ForeignKey(User)
    when = models.DateField()
    text = models.CharField(max_length = 150)

    def day_of_week(self):
        days = dict()
        days[0], days[1], days[2], days[3], days[4], days[5], days[6] = "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
        return days[self.when.weekday()]

    def day_int(self):
        return Int(self.when.weekday())

class PersonalJournal(models.Model):
    patient = models.ForeignKey(User)
    context = models.ForeignKey(ContextForWeek)
    date_created = models.DateTimeField(auto_now_add=True, blank=True)
    entry = models.CharField(max_length=2000)
    emotion_anger = models.CharField(max_length=15, blank=True)
    emotion_disgust = models.CharField(max_length=15, blank=True)
    emotion_sadness = models.CharField(max_length=15, blank=True)
    emotion_fear = models.CharField(max_length=15, blank=True)
    emotion_joy = models.CharField(max_length=15, blank=True)

    def print_time(self):
        return self.date_created.strftime('%m/%d/%y %H:%M')

    def get_dominant_mood(self):
        emotions = [float(self.emotion_anger), float(self.emotion_disgust), float(self.emotion_sadness), float(self.emotion_fear), float(self.emotion_joy)]
        dominant_emotion_index = emotions.index(max(emotions))
        dominant_emotion = ''
        if dominant_emotion_index == 0:
            dominant_emotion = 'Anger'
        elif dominant_emotion_index == 1:
            dominant_emotion = 'Disgust'
        elif dominant_emotion_index == 2:
            dominant_emotion = 'Sadness'
        elif dominant_emotion_index == 3:
            dominant_emotion = 'Fear'
        else:
            dominant_emotion = 'Joy'
        print('Emotion: ', dominant_emotion)
        return dominant_emotion

class HighRiskLog(models.Model):
    patient = models.ForeignKey(User)
    context = models.ForeignKey(ContextForWeek)
    date_created = models.DateTimeField(auto_now_add=True, blank=True)
    msg = models.CharField(max_length=2000)

    def getHighRiskCountForDay(userid, searchDate = datetime.now().date()):
        highRiskCountPerDay = HighRiskLog.objects.filter(patient = userid).filter(date_created__year=searchDate.year, date_created__month=searchDate.month, date_created__day=searchDate.day).count()
        return highRiskCountPerDay





