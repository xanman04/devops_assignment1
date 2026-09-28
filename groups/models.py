"""Group storage. Use groups.services for membership and authorization rules."""
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q

USER = settings.AUTH_USER_MODEL


def group_photo_path(instance, filename):
    return f"groups/{uuid4().hex}{Path(filename).suffix.lower()}"


def validate_photo_size(value):
    if value.size > 5 * 1024 * 1024:
        raise ValidationError("Group photos must be at most 5 MiB.")


class AttendanceGroup(models.Model):
    class JoiningMode(models.TextChoices):
        PUBLIC = "public", "Public"
        APPROVAL = "approval_required", "Approval required"

    event = models.ForeignKey("discovery.Event", on_delete=models.PROTECT, related_name="attendance_groups")
    owner = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="owned_attendance_groups")
    name = models.CharField(max_length=120)
    description = models.TextField()
    capacity = models.PositiveIntegerField()
    joining_mode = models.CharField(max_length=17, choices=JoiningMode)
    photo = models.ImageField(upload_to=group_photo_path, blank=True, validators=[
        FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), validate_photo_size,
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gt=0), name="group_positive_capacity"),
            models.CheckConstraint(condition=Q(joining_mode__in=["public", "approval_required"]), name="group_valid_joining_mode"),
        ]

    def __str__(self):
        return self.name


class Membership(models.Model):
    group = models.ForeignKey(AttendanceGroup, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="attendance_memberships")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["joined_at", "id"]
        constraints = [models.UniqueConstraint(fields=["group", "user"], name="membership_group_user_unique")]


class JoinRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved offer"
        REJECTED = "rejected", "Rejected"
        ACCEPTED = "accepted", "Accepted"
        CANCELLED = "cancelled", "Cancelled"

    group = models.ForeignKey(AttendanceGroup, on_delete=models.CASCADE, related_name="join_requests")
    applicant = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="join_requests")
    status = models.CharField(max_length=9, choices=Status, default=Status.PENDING, db_index=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(USER, on_delete=models.PROTECT, null=True, blank=True, related_name="reviewed_join_requests")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["group", "applicant"], condition=Q(status__in=["pending", "approved"]), name="request_one_unresolved"),
            models.CheckConstraint(condition=Q(status__in=["pending", "approved", "rejected", "accepted", "cancelled"]), name="request_valid_status"),
        ]


class GroupBan(models.Model):
    group = models.ForeignKey(AttendanceGroup, on_delete=models.CASCADE, related_name="bans")
    user = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="group_bans")
    issued_by = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="issued_group_bans")
    reason = models.TextField(blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    lifted_at = models.DateTimeField(null=True, blank=True)
    lifted_by = models.ForeignKey(USER, on_delete=models.PROTECT, null=True, blank=True, related_name="lifted_group_bans")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "user"], condition=Q(lifted_at__isnull=True), name="ban_one_active")]


class Message(models.Model):
    group = models.ForeignKey(AttendanceGroup, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="group_messages")
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(USER, on_delete=models.PROTECT, null=True, blank=True, related_name="deleted_group_messages")

    def clean(self):
        if self.deleted_at is None and not self.body.strip():
            raise ValidationError({"body": "A live message needs text."})

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["group", "created_at"], name="message_group_created_idx")]
        constraints = [models.CheckConstraint(
            condition=(Q(deleted_at__isnull=True, deleted_by__isnull=True) & ~Q(body="")) |
                      Q(deleted_at__isnull=False, deleted_by__isnull=False, body=""),
            name="message_live_or_tombstone",
        )]
