# Copyright © 2026 Xander Chen. All rights reserved.
"""Recipient-scoped inbox access. Never expose EventChange snapshots here."""
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import Notification


def inbox(*, actor, unread_only=False):
    if not actor or not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("An active account is required.")
    records = Notification.objects.filter(recipient=actor)
    return records.filter(read_at__isnull=True) if unread_only else records


def mark_all_read(*, actor):
    """Mark every unread notification of this person as read; returns how many changed."""
    return inbox(actor=actor, unread_only=True).update(read_at=timezone.now())


def mark_read(*, actor, notification_id):
    record = inbox(actor=actor).get(pk=notification_id)
    if record.read_at is None:
        record.read_at = timezone.now()
        record.save(update_fields=["read_at"])
    return record
