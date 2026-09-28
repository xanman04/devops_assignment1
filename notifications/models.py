from django.conf import settings
from django.db import models
from django.db.models import Q


class Notification(models.Model):
    class Kind(models.TextChoices):
        EVENT_CHANGE = "event_change", "Event change"
        GROUP_OFFER = "group_offer", "Group offer"
        GROUP_REQUEST = "group_request", "New group request"
        GROUP_REJECTED = "group_rejected", "Group request rejected"
        MEMBER_REMOVED = "member_removed", "Removed from group"
        MEMBER_BANNED = "member_banned", "Banned from group"
        OWNER_TRANSFER = "owner_transfer", "Group ownership transferred"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notifications")
    kind = models.CharField(max_length=14, choices=Kind)
    event_change = models.ForeignKey("discovery.EventChange", on_delete=models.PROTECT, null=True, blank=True, related_name="notifications")
    join_request = models.ForeignKey("groups.JoinRequest", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    group = models.ForeignKey("groups.AttendanceGroup", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["recipient", "read_at", "created_at"], name="notification_inbox_idx")]
        constraints = [
            models.CheckConstraint(condition=(
                Q(kind="event_change", event_change__isnull=False, join_request__isnull=True, group__isnull=True) |
                Q(kind__in=["group_offer", "group_request", "group_rejected"], event_change__isnull=True,
                  join_request__isnull=False, group__isnull=True) |
                Q(kind__in=["member_removed", "member_banned", "owner_transfer"], event_change__isnull=True,
                  join_request__isnull=True, group__isnull=False)
            ), name="notification_source_matches_kind"),
            models.UniqueConstraint(fields=["recipient", "event_change"], name="notification_event_once"),
            models.UniqueConstraint(fields=["recipient", "join_request"], name="notification_offer_once"),
        ]
