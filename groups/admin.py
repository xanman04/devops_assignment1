# Copyright © 2026 Xander Chen. All rights reserved.
from django.contrib import admin
from config.admin import SchemaReadOnlyAdmin
from .models import AttendanceGroup, GroupNotice, Membership, JoinRequest, GroupBan, Message
from . import services
from django.db import transaction


@admin.register(AttendanceGroup)
class AttendanceGroupAdmin(SchemaReadOnlyAdmin):
    list_display = ("name", "event", "owner", "capacity", "joining_mode")
    actions = None

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("groups.delete_attendancegroup")

    def delete_model(self, request, obj):
        services.delete_group(actor=request.user, group_id=obj.pk)

    def get_deleted_objects(self, objs, request):
        objects, counts, permissions, protected = super().get_deleted_objects(objs, request)
        # Disband permission covers the displayed group dependents, even though
        # their inspection-only admins disallow direct record deletion.
        if self.has_delete_permission(request):
            permissions = set()
        return objects, counts, permissions, protected


@admin.register(Message)
class MessageAdmin(SchemaReadOnlyAdmin):
    list_display = ("author", "group", "created_at", "edited_at", "deleted_at")
    actions = ("remove_content",)

    def has_moderate_permission(self, request):
        return request.user.has_perm("groups.delete_message")

    @admin.action(description="Remove selected message content", permissions=["moderate"])
    @transaction.atomic
    def remove_content(self, request, queryset):
        for message in queryset:
            services.delete_message(actor=request.user, message_id=message.pk)
        self.message_user(request, "Message content removed; deletion markers retained.")


for model in (Membership, JoinRequest, GroupBan, GroupNotice):
    admin.site.register(model, SchemaReadOnlyAdmin)
