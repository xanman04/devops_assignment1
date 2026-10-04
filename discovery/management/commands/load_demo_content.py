# Copyright © 2026 Xander Chen. All rights reserved.
"""Fill an empty database with the curated genres and the demo content, in the order the seed commands need.

`app.py` runs this once on startup when the database has no genre categories, so a fresh clone opens with a working
map and Discover page. Set SEED_DEMO_DATA=0 to start with an empty database instead. Every step is repeatable."""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from discovery.models import GenreCategory

STEPS = ("import_subgenres", "seed_demo", "seed_djs", "seed_genre_songs", "seed_madrid_demo", "seed_pickle_rick",
         "spread_demo_events")


class Command(BaseCommand):
    help = "Load the 22 curated genre categories (when none exist) and then every demo seed command."

    def handle(self, *args, **options):
        if not GenreCategory.objects.exists():
            call_command("loaddata", "genre_categories", verbosity=0)
        for step in STEPS:
            call_command(step, stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS("Demo content is loaded."))
