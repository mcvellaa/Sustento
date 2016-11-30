from django import forms

class UserSendForm(forms.Form):
#    def __init__(self, *args, **kwargs):
#        super(UserSendView, self).__init__(*args, **kwargs)
#        self.helper = FormHelper(self)

    text = forms.CharField(label='Text', max_length=100)

class JournalEntryForm(forms.Form):
    text = forms.CharField(label='Journal Entry', max_length=1998)

class RemindersForm(forms.Form):
    when = forms.DateTimeField(label='Weekly Reminder Date and Time')
    text = forms.CharField(label='Reminder Text', max_length=150)
