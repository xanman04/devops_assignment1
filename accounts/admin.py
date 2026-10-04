# Copyright © 2026 Xander Chen. All rights reserved.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class AccountAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Public identity", {"fields": ("display_name",)}),)
