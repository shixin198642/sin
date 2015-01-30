from django.contrib import admin
from content_store.models import ContentStore, StoreConfig

class ContentStoreAdmin(admin.ModelAdmin):
  pass
class StoreConfigAdmin(admin.ModelAdmin):
  pass
admin.site.register(StoreConfig, StoreConfigAdmin)
admin.site.register(ContentStore, ContentStoreAdmin)
