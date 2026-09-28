from django.contrib import admin
from config.admin import SchemaReadOnlyAdmin
from .models import Notification

admin.site.register(Notification, SchemaReadOnlyAdmin)
