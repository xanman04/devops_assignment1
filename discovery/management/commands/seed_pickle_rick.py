"""Add five fictional Psy-Trance DJ profiles (Pickle Rick headlines) for the Pickle Rick Portal Rave demo.

The event itself is not created here: list it through the normal form with the poster from
`tools/build_pickle_rick_poster.py`. Repeatable: DJs are matched by name."""
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


class Command(BaseCommand):
    help = "Create the Pickle Rick demo DJs."

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
