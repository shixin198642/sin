from django.db import models
from django.template import loader

from utils import enum
from utils.enum import to_choices

class Invitation(models.Model):
  invite_key = models.CharField(max_length=40)
  email = models.EmailField(max_length=75)
  description = models.TextField(max_length=1024)

  status = models.SmallIntegerField(choices=to_choices(enum.INVITE_STATUS),
                                    default=enum.INVITE_STATUS['new'])

  def __unicode__(self):
    return self.email

  def approve(self):
    if self.status >= enum.INVITE_STATUS['approved']:
      return
    from django.core.mail import send_mail

    send_mail('Your request has been approved',
              loader.render_to_string('email/invitation_email.html', {
                'email': self.email,
                'invite_key': self.invite_key,
              }),
              'Dataganic <no-reply@dataganic.com>',
              [self.email])
    self.status = enum.INVITE_STATUS['approved']
    self.save()

