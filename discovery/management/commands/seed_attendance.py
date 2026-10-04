"""Give every non-admin account its own set of event cards, stored exactly as check-in will store them, plus a
bio and music links where those are blank so no profile is empty.

The cards are rows of `EventCard` (the table check-in will write to), so the profile collection, achievements and
genre chart treat them as already checked in. Totals are spread so every tier is represented."""
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from discovery.models import Event, EventCard

# How many events each named account has been to; any other account gets a repeatable number from its username.
TARGETS = {"demo_organizer": 22, "demo_alex": 16, "demo_sam": 11, "demo_jo": 6, "demo_morgan": 3,
           "rick_sanchez": 18, "morty_smith": 8}
BIOS = ("Warehouse nights and long drives to festivals.", "Mostly front of the room, always for the bass.",
        "Dancing since before the sun came up. Ask me about my record bag.", "Here for the openers as much as the headliners.",
        "Tries every new venue once.", "Mid-week techno, weekend everything else.")


class Command(BaseCommand):
    help = "Replace the event cards of accounts (all non-admin accounts by default, or those with --prefix)."

    def add_arguments(self, parser):
        parser.add_argument("--prefix", default="")

    def handle(self, *args, prefix, **options):
        events = list(Event.objects.filter(categories__isnull=False).distinct().order_by("id"))
        if not events:
            self.stdout.write("No events to collect.")
            return
        total = 0
        accounts = get_user_model().objects.filter(is_superuser=False, username__startswith=prefix).order_by("username")
        for user in accounts:
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
            changed = []
            if not user.bio:
                user.bio = rng.choice(BIOS)
                changed.append("bio")
            if not user.instagram_url and not user.spotify_url and not user.soundcloud_url and not user.apple_music_url:
                handle = user.username.replace("_", "")
                user.instagram_url = f"https://www.instagram.com/{handle}/"
                user.spotify_url = f"https://open.spotify.com/user/{handle}"
                changed.append("links")
            if changed:
                user.save(update_fields=["bio", "instagram_url", "spotify_url"])
            self.stdout.write(f"{user.username}: {len(picked)} cards" + (f", filled {' and '.join(changed)}" if changed else ""))
        self.stdout.write(f"{total} cards")
