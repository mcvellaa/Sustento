from django import forms
import datetime
from .models import Reminders

class UserSendForm(forms.Form):
#    def __init__(self, *args, **kwargs):
#        super(UserSendView, self).__init__(*args, **kwargs)
#        self.helper = FormHelper(self)

    text = forms.CharField(label='Text', max_length=100)

class EmailSendForm(forms.Form):
#    def __init__(self, *args, **kwargs):
#        super(UserSendView, self).__init__(*args, **kwargs)
#        self.helper = FormHelper(self)

    email = forms.CharField(label='E-Mail Address', max_length=100)

class JournalEntryForm(forms.Form):
    text = forms.CharField(label='Journal Entry', max_length=1998)

class DateInput(forms.DateInput):
    input_type = 'date'

class RemindersForm(forms.ModelForm):
    class Meta:
        model = Reminders
        fields = ['when', 'text']
        widgets = {
            'when': DateInput(),
        }