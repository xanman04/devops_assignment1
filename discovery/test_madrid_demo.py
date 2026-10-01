from io import StringIO
import csv
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase
from django.utils import timezone

from discovery import models, services
from discovery.management.commands.seed_madrid_demo import NIGHTS, USERS, VENUES


class MadridDemoTests(TestCase):
    def seed(self):
        output = StringIO()
        call_command("seed_madrid_demo", stdout=output)
        return output.getvalue()

    def classification(self):
        names = {name for night in NIGHTS for name in night[7]}
        wanted_tags = {tag for night in NIGHTS for tag in night[8]}
        categories = {}
        for name in names:
            categories[name] = models.GenreCategory.objects.create(name=name, color="#456789", description="Test genre")
        with (Path(__file__).parent / "fixtures" / "electronic_subgenres_v1.csv").open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                category = categories.get(row["umbrella_genre"])
                if category and row["subgenre"] in wanted_tags:
                    models.GenreTag.objects.get_or_create(category=category, name=row["subgenre"],
                                                          defaults={"description": "Test tag"})

    def test_missing_demo_accounts_changes_nothing(self):
        with self.assertRaises(CommandError):
            self.seed()
        self.assertFalse(models.Venue.objects.exists())
        self.assertFalse(models.Event.objects.exists())

    def test_repeatable_seed_uses_existing_users_and_genres(self):
        call_command("seed_demo", stdout=StringIO())
        self.classification()
        user_count = get_user_model().objects.count()
        genre_count = models.GenreCategory.objects.count()
        tag_count = models.GenreTag.objects.count()
        self.assertIn(f"{len(NIGHTS)} events created", self.seed())
        self.assertEqual(models.Event.objects.count(), len(NIGHTS))
        self.assertTrue(all(event.performers.count() == 2 for event in models.Event.objects.all()))
        self.assertEqual(models.Venue.objects.filter(name__in=[v[0] for v in VENUES.values()]).count(), len(VENUES))
        self.assertEqual(set(models.Event.objects.values_list("creator__username", flat=True)), set(USERS))
        self.assertTrue(all(event.demo_poster.startswith("demo-posters/") for event in models.Event.objects.all()))
        seeded_window = services.search_events(starts_at=timezone.now(), ends_at=timezone.now() + timedelta(days=22))
        self.assertEqual(sum(pin["count"] for pin in services.map_pins(seeded_window)), len(NIGHTS))
        first = models.Event.objects.order_by("pk").first()
        self.assertEqual(first.performers.count(), 2)
        self.assertNotIn("Lineup:", first.description)
        self.assertNotIn("Fictional classroom demo listing", first.description)
        self.assertNotIn("fictional_demo", services.map_pins(services.search_events())[0]["events"][0])
        first.description = "Old pitch. Fictional classroom demo listing."
        first.save(update_fields=["description"])
        self.assertIn("0 events created", self.seed())
        first.refresh_from_db()
        self.assertNotIn("Fictional classroom demo listing", first.description)
        self.assertEqual(models.Event.objects.count(), len(NIGHTS))
        self.assertEqual(get_user_model().objects.count(), user_count)
        self.assertEqual(models.GenreCategory.objects.count(), genre_count)
        self.assertEqual(models.GenreTag.objects.count(), tag_count)
