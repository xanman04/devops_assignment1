"""Give every demo account its own set of event cards, stored exactly as check-in will store them.

The cards are rows of `EventCard` (the table check-in will write to), so the profile collection, achievements and
genre chart treat them as already checked in. Totals are spread so every tier is represented."""
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from discovery.models import Event, EventCard

# How many events each demo account has been to; other demo accounts get a repeatable number from their name.
TARGETS = {"demo_organizer": 22, "demo_alex": 16, "demo_sam": 11, "demo_jo": 6, "demo_morgan": 3}


class Command(BaseCommand):
    help = "Replace the event cards of accounts whose username starts with the given prefix (default demo_)."

    def add_arguments(self, parser):
        parser.add_argument("--prefix", default="demo_")

    def handle(self, *args, prefix, **options):
        events = list(Event.objects.filter(categories__isnull=False).distinct().order_by("id"))
        if not events:
            self.stdout.write("No events to collect.")
            return
        total = 0
        for user in get_user_model().objects.filter(username__startswith=prefix).order_by("username"):
            rng = random.Random(user.username)
            target = min(TARGETS.get(user.username, rng.randint(2, len(events))), len(events))
            favourite = rng.choice(events).categories.first()
            liked = [event for event in events if favourite in event.categories.all()]
            rng.shuffle(liked)
            rest = [event for event in events if event not in liked]
            rng.shuffle(rest)
            picked = (liked + rest)[:target]
            EventCard.objects.filter(user=user).delete()
            EventCard.objects.bulk_create([EventCard(user=user, event=event) for event in picked])
            total += len(picked)
            self.stdout.write(f"{user.username}: {len(picked)} cards")
        self.stdout.write(f"{total} cards")
