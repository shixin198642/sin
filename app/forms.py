from django import forms
from django.contrib.auth.forms import UserCreationForm as DJUserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import ugettext, ugettext_lazy as _

class UserCreationForm(DJUserCreationForm):
  email = forms.EmailField(label=_("Email"),
                           max_length=30,
                           widget=forms.TextInput(attrs={'readonly':'readonly'}))

  def clean_email(self):
    email = self.cleaned_data["email"]
    try:
      User.objects.get(email=email)
    except User.DoesNotExist:
      return email
    raise forms.ValidationError(_("A user with that email already exists."))

  def save(self, commit=True):
    user = super(UserCreationForm, self).save(commit=False)
    user.email = self.cleaned_data["email"]

    if commit:
      user.save()

    return user

