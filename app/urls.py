from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('views',
  # Examples:
  # url(r'^$', 'sinApp.views.home', name='home'),
  # url(r'^sinApp/', include('sinApp.foo.urls')),

  url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
  url(r'^admin/', include(admin.site.urls)),

  url(r'^mydash/?$', 'mydash', name='mydash'),
  url(r'^password_change/?$', 'password_change', name='password_change'),
  url(r'^password_change_done/?$', 'password_change_done', name='password_change_done'),
  url(r'^password_reset/?$', 'password_reset', name='password_reset'),
  url(r'^password_reset_done/?$', 'password_reset_done', name='password_reset_done'),
  url(r'^password_reset_change/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/?$', 'password_reset_change', name='password_reset_change'),
  url(r'^$', 'index', name='index'),
  url(r'^dashboard/?$', 'dashboard', name='dashboard'),
  url(r'^downloads/?$', 'downloads', name='downloads'),
  url(r'^get-started/?$', 'get_started', name='get_started'),
  url(r'^documentation/?$', 'documentation', name='documentation'),
  url(r'^developers/?$', 'developers', name='developers'),
  url(r'^team/?$', 'team', name='team'),

  url(r'^me/?$', 'me', name='me'),
  url(r'^login_api/?$', 'login_api', name='login_api'),
  url(r'^login/?$', 'login', name='login'),
  url(r'^register/?$', 'register', name='register'),
  url(r'^invite_me/?$', 'invite_me', name='invite_me'),
  url(r'^invite_me_done/?$', 'invite_me_done', name='invite_me_done'),
  url(r'^logout_api/?$', 'logout_api', name='logout_api'),
  url(r'^logout/?$', 'logout', name='logout'),

  url(r'^cluster/', include('cluster.urls')),
  url(r'^store/', include('content_store.urls')),
  url(r'^files/', include('files.urls')),
)
