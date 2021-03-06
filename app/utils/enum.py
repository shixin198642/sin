# -*- coding: utf-8 -*-
"""
Global enums defined here.
"""
from django.utils.translation import ugettext_lazy as _

def to_choices(d):
  return map(lambda x: (x[1], x[0]), d.items())

INVITE_STATUS_BASE = (
  ('rejected', -10, _(u'Rejected')),
  ('new', 0, _(u'new')),
  ('approved', 10, _(u'Approved')),
)
INVITE_STATUS = dict([(x[0], x[1]) for x in INVITE_STATUS_BASE])
INVITE_STATUS_DISPLAY = dict([(x[1], x[2]) for x in INVITE_STATUS_BASE])

STORE_STATUS_BASE = (
  ('new', 0, _(u'Stopped')),
  ('disabled', 5, _(u'Disabled')),
  ('stopped', 10, _(u'Stopped')),
  ('running', 15, _(u'Running')),
)
STORE_STATUS = dict([(x[0], x[1]) for x in STORE_STATUS_BASE])
STORE_STATUS_DISPLAY = dict([(x[1], x[2]) for x in STORE_STATUS_BASE])

FILE_SRC_TYPES_BASE = (
  ('upload', 0, _(u'Direct Upload')),
  ('url', 5, _(u'From Url')),
  ('mvn', 10, _(u'From Maven')),
)
FILE_SRC_TYPES = dict([(x[0], x[1]) for x in FILE_SRC_TYPES_BASE])
FILE_SRC_TYPES_DISPLAY = dict([(x[1], x[2]) for x in FILE_SRC_TYPES_BASE])

