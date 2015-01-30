from django.contrib import admin
from account.models import Invitation

from utils import enum

class InvitationAdmin(admin.ModelAdmin):
  actions = ['approve', 'reject']
  list_display = ('email', 'status', 'description')

  def approve(self, request, qs):
    for invitation in qs.filter(status__lt=enum.INVITE_STATUS['approved']):
      invitation.approve()

    self.message_user(request, 'Done')
  approve.short_description = 'Approve selected invitations'

  def reject(self, request, qs):
    qs.update(status=enum.INVITE_STATUS['rejected'])
    self.message_user(request, 'Done')
  reject.short_description = 'Reject selected invitations'

admin.site.register(Invitation, InvitationAdmin)

