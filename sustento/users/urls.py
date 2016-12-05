# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        regex=r'^$',
        view=views.HomeView,
        name='home'
    ),
    url(
        regex=r'^~list$',
        view=views.UserListView.as_view(),
        name='list'
    ),
    url(
        regex=r'^~redirect/$',
        view=views.UserRedirectView.as_view(),
        name='redirect'
    ),
    url(
        regex=r'^~update/$',
        view=views.UserUpdateView.as_view(),
        name='update'
    ),
    url(
        regex=r'^~receive/$',
        view=views.UserReceive,
        name='receive'
    ),
    url(
        regex=r'^~schedule/$',
        view=views.UserSchedule,
        name='schedule'
    ),
    url(
        regex=r'^~messages/$',
        view=views.MessagesView,
        name='messages'
    ),
    url(
        regex=r'^~journal/$',
        view=views.JournalView,
        name='journal'
    ),
    url(
        regex=r'^~dashboard/$',
        view=views.DashboardView,
        name='dashboard'
    ),
    url(
        regex=r'^~reminders/$',
        view=views.RemindersView,
        name='reminders'
    ),
        url(
        regex=r'^~dailySummary/$',
        view=views.DailySummaryView,
        name='dailySummary'
    )
]
