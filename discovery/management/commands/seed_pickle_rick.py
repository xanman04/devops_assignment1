"""Add five fictional Psy-Trance DJ profiles (Pickle Rick headlines) and the Pickle Rick Portal Rave demo event.

The event uses the bundled flyer `static/demo-posters/pickle-rick-portal-rave.webp` (drawn from scratch; the poster
builder is `tools/build_pickle_rick_poster.py`). It needs the Psy-Trance genre, the Madrid demo venue The Bassement and
the `demo_organizer` account, so it is created only once those exist. Repeatable: DJs are matched by name and the event
by title."""
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core.management.base import BaseCommand, CommandError

from discovery import models

DJS = (
    ("Pickle Rick", "Headliner. Turned himself into a pickle to skip the family therapy and has not stopped since. "
                    "Rolling full-on psytrance with acid-green bass and a lot of unexplained science.", "Dimension C-137", 2017),
    ("Squanchy", "Squanches the room with fast, bouncy progressive psytrance and a very loose relationship with the clock.", "Squanch Planet", 2019),
    ("Birdperson", "Calm, precise forest psy built on slow-building layers; every drop arrives exactly when promised.", "Bird World", 2015),
    ("Evil Morty", "Dark, hypnotic night-time psytrance with a patient build and a sudden turn.", "The Citadel", 2020),
    ("Gazorp", "Hi-tech psy from a planet with strict rules and a very loud sound system.", "Gazorpazorp", 2018),
)


EVENT_TITLE = "Pickle Rick's Portal Rave"
EVENT_TAGS = ("Psytrance", "Psychedelic", "Hi-Tech Psy", "Psy-Tech")
EVENT_POSTER = "demo-posters/pickle-rick-portal-rave.webp"


class Command(BaseCommand):
    help = "Create the Pickle Rick demo DJs and the Pickle Rick Portal Rave demo event."

    def handle(self, *args, **options):
        category = models.GenreCategory.objects.filter(name="Psy-Trance").first()
        if category is None:
            raise CommandError("The Psy-Trance genre is missing.")
        for order, (name, description, origin, since) in enumerate(DJS):
            profile, created = models.DJProfile.objects.get_or_create(
                name=name, defaults={"description": description, "origin": origin, "active_since": since, "display_order": 900 + order})
            profile.categories.add(category)
            photo = f"djs/{name.lower().replace(' ', '_')}.webp"          # drop the image here, then run this command again
            if not profile.photo and finders.find(photo):
                profile.photo = photo
                profile.photo_credit = "Character art supplied by the project owner (Rick and Morty); classroom demo only"
                profile.save(update_fields=["photo", "photo_credit"])
            self.stdout.write(f"{'created' if created else 'kept'} DJ {name}" + (" (photo set)" if profile.photo else f" (no photo yet: add static/{photo})"))
        self._event(category)

    def _event(self, category):
        venue = models.Venue.objects.filter(name="The Bassement", review_status="approved").first()
        organizer = get_user_model().objects.filter(username="demo_organizer").first()
        if venue is None or organizer is None:
            self.stdout.write("Event skipped: run seed_demo and seed_madrid_demo first.")
            return
        event = models.Event.objects.filter(title=EVENT_TITLE).first()
        created = event is None
        if created:
            event = models.Event(
                creator=organizer, venue=venue, title=EVENT_TITLE, description="It's intergalactic, broh.",
                starts_at=datetime(2026, 10, 12, 19, 0, tzinfo=timezone.utc), ends_at=datetime(2026, 10, 13, 4, 0, tzinfo=timezone.utc),
                demo_poster=EVENT_POSTER)
            event.full_clean()
            event.save()
            event.categories.set([category])
            event.tags.set(models.GenreTag.objects.filter(category=category, name__in=EVENT_TAGS))
        event.performers.set(models.DJProfile.objects.filter(name__in=[dj[0] for dj in DJS]))
        self.stdout.write(f"{'created' if created else 'kept'} event {EVENT_TITLE}")
