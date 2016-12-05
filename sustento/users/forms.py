from django import forms
import datetime
from .models import Reminders
from datetimewidget.widgets import DateTimeWidget

class UserSendForm(forms.Form):
#    def __init__(self, *args, **kwargs):
#        super(UserSendView, self).__init__(*args, **kwargs)
#        self.helper = FormHelper(self)

    text = forms.CharField(label='Text', max_length=100)

class JournalEntryForm(forms.Form):
    text = forms.CharField(label='Journal Entry', max_length=1998)

class DateInput(forms.DateInput):
    input_type = 'datetime-local'

class RemindersForm(forms.Form):
    when = DateTimeWidget(attrs={'id':"Day of Week and Time"}, bootstrap_version=3)
    text = forms.CharField(label='Text', max_length=150)
