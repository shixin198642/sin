from django import forms
from django.forms import ModelForm

from account.models import Invitation

from utils import generate_api_key

class InvitationForm(ModelForm):
  class Meta:
    model = Invitation
    exclude = ["invite_key", "status"]

  def save(self):
    email = self.cleaned_data["email"]
    try:
      invitation = Invitation.objects.get(email=email)
      invitation.description = self.cleaned_data.get("description")
      invitation.save()
    except Invitation.DoesNotExist:
      invitation = Invitation.objects.create(invite_key  = generate_api_key(),
                                             email       = email,
                                             description = self.cleaned_data.get("description"))
    return invitation

