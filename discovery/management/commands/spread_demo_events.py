# Copyright © 2026 Xander Chen. All rights reserved.
"""Spread the demo events over the next 30 days so every date shortcut (Tonight, 3 days, two weeks, 30 days) has some.

Keeps each event's local time of day and length; only the date changes. Run it again whenever the dates have drifted
into the past. Events are updated directly, so nobody is notified."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone

from discovery.models import Event

# Days from today for each event in turn: two tonight, a few in the next 3 days, more in two weeks, the rest in 30 days.
OFFSETS = (0, 0, 1, 2, 3, 4, 5, 6, 8, 9, 11, 12, 14, 16, 18, 19, 21, 22, 24, 25, 26, 28, 29, 30)


class Command(BaseCommand):
    help = "Spread the existing events over the next 30 days, starting today."

    def handle(self, *args, **options):
        now = timezone.now()
        events = list(Event.objects.select_related("venue").order_by("id"))
        for index, event in enumerate(events):
            zone = ZoneInfo(event.venue.timezone)
            today = now.astimezone(zone).date()
            offset = OFFSETS[index % len(OFFSETS)]
            local = event.starts_at.astimezone(zone)
            hour, minute = (21 + index % 2, 0) if offset == 0 else (local.hour, local.minute)   # tonight: late enough to still be on
            start = datetime(today.year, today.month, today.day, hour, minute, tzinfo=zone) + timedelta(days=offset)
            length = max(event.ends_at - event.starts_at, timedelta(hours=5) if offset == 0 else timedelta(hours=1))
            Event.objects.filter(pk=event.pk).update(starts_at=start, ends_at=start + length)
        self.stdout.write(f"Spread {len(events)} events from {now.date()} to {now.date() + timedelta(days=30)}.")
