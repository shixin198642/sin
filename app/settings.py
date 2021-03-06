# Django settings for sinApp project.
import os
from utils import get_local_pub_ip

LOCAL_PUB_IP = get_local_pub_ip()
SIN_HOME = os.path.normpath(os.path.join(os.path.normpath(__file__), '../..'))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

VERSION = 0.1

STORE_HOME = '/tmp/store/'

SIN_LISTEN     = 8666
SIN_MIN_THREAD = 16
SIN_MAX_THREAD = 512

DISABLE_HOST_CHECK = True

ADMINS = (
  # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
  'default': {
    'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
    'NAME': '/tmp/sin',            # Or path to database file if using sqlite3.
    'USER': '',            # Not used with sqlite3.
    'PASSWORD': '',          # Not used with sqlite3.
    'HOST': '',            # Set to empty string for localhost. Not used with sqlite3.
    'PORT': '',            # Set to empty string for default. Not used with sqlite3.
  }
}

ZOOKEEPER_URL = 'localhost:2181'
ZOOKEEPER_TIMEOUT = 30000
SIN_SERVICE_NAME = 'sin'

SIN_NODES = {
  "nodes": [
    {"node_id": 0, "host": LOCAL_PUB_IP, "port": 6664},
  ],
}

KAFKA_HOST = 'localhost'

KAFKA_PORT = 9092

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

CACHES = {
  'default': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    'LOCATION': 'sin_main'
  }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(SIN_HOME, 'admin/um')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/static/um/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '%sadmin/' % STATIC_URL

# Additional locations of static files
STATICFILES_DIRS = (
  # Put strings here, like "/home/html/static" or "C:/www/django/static".
  # Always use forward slashes, even on Windows.
  # Don't forget to use absolute paths, not relative paths.
  os.path.join(SIN_HOME, 'admin'),
  os.path.join(SIN_HOME, 'demo'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
  'django.contrib.staticfiles.finders.FileSystemFinder',
  'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#  'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '_sxjdd_*$&q)m01vj2$(ja+$ab83s2=*2-pg#=y&01uvl311#p'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
  'django.template.loaders.filesystem.Loader',
  'django.template.loaders.app_directories.Loader',
#   'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
  'django.middleware.common.CommonMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  # 'django.middleware.csrf.CsrfViewMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
  # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
  # Always use forward slashes, even on Windows.
  # Don't forget to use absolute paths, not relative paths.
  os.path.join(SIN_HOME, 'app/templates'),
)

INSTALLED_APPS = (
  'django.contrib.auth',
  'django.contrib.contenttypes',
  'django.contrib.sessions',
  'django.contrib.messages',
  'django.contrib.staticfiles',
  'django.contrib.admin',
  'django.contrib.admindocs',
  'django.contrib.sites',
  'account',
  'content_store',
  'cluster',
  'files',
  'sin_site',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
  'version': 1,
  'disable_existing_loggers': False,
  'formatters': {
    'verbose': {
      'format': '%(levelname)s %(asctime)s [%(module)s] %(message)s'
      },
    'simple': {
      'format': '%(levelname)s %(message)s'
      }
    },
  'handlers': {
    'console':{
      'level':'INFO',
      'class':'logging.StreamHandler',
      'formatter': 'verbose'
      },
    'mail_admins': {
      'level': 'CRITICAL',
      'class': 'django.utils.log.AdminEmailHandler'
      }
    },
  'loggers': {
    'sin_server': {
      'handlers': ['console', 'mail_admins'],
      'level': 'INFO',
      'propagate': False,
      },
    'content_store': {
      'handlers': ['console', 'mail_admins'],
      'level': 'INFO',
      'propagate': False,
      },
    'django.request': {
      'handlers': ['mail_admins'],
      'level': 'ERROR',
      'propagate': True,
      },
    }
  }

#
# Cluster related constants
#
DEFAULT_REPLICAS = 3
DEFAULT_PARTITIONS = 10
MAX_PARTITIONS = 1024
