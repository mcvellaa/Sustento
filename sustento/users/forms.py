from django import forms

class UserSendForm(forms.Form):
#    def __init__(self, *args, **kwargs):
#        super(UserSendView, self).__init__(*args, **kwargs)
#        self.helper = FormHelper(self)

    text = forms.CharField(label='Text', max_length=100)
    phone = forms.CharField(label='Phone (only numbers with area code, no spaces or separators)', max_length=10)
