# Copyright © 2026 Xander Chen. All rights reserved.
from django.contrib import admin


class SchemaReadOnlyAdmin(admin.ModelAdmin):
    """Inspect records without bypassing services that are not built yet."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
