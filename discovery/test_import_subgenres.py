import csv
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase

from discovery.management.commands.import_subgenres import DEFAULT_SOURCE, CATEGORY_ALIASES
from discovery.models import GenreCategory, GenreTag


class SubgenreImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with DEFAULT_SOURCE.open(encoding="utf-8-sig", newline="") as source:
            rows = list(csv.DictReader(source))
        for name in sorted({CATEGORY_ALIASES.get(row["umbrella_genre"], row["umbrella_genre"])
                            for row in rows}):
            GenreCategory.objects.create(name=name, color="#777777", description="Test category")

    def run_import(self, **options):
        output = StringIO()
        call_command("import_subgenres", stdout=output, **options)
        return output.getvalue()

    def test_full_import_is_repeatable_and_preserves_csv_pitch_and_bpm_meaning(self):
        self.assertIn("Would create 251", self.run_import(dry_run=True))
        self.assertFalse(GenreTag.objects.exists())
        self.assertIn("Created 251", self.run_import())
        self.assertEqual(GenreTag.objects.count(), 251)
        self.assertIn("unchanged 251", self.run_import())

        with DEFAULT_SOURCE.open(encoding="utf-8-sig", newline="") as source:
            pitch = next(row["pitch"] for row in csv.DictReader(source)
                         if row["umbrella_genre"] == "House" and row["subgenre"] == "Deep House")
        self.assertEqual(GenreTag.objects.get(category__name="House", name="Deep House").description, pitch)
        self.assertEqual(GenreTag.objects.get(category__name="Industrial / EBM", name="EBM").category.name,
                         "Industrial / EBM")
        self.assertEqual(GenreTag.objects.filter(bpm_max_open=True).count(), 6)
        drone = GenreTag.objects.get(category__name="Ambient / Experimental", name="Drone")
        self.assertIsNone(drone.bpm_min)
        self.assertIsNone(drone.bpm_max)

        admin = get_user_model().objects.create_superuser("curator", password="test-only-password")
        self.client.force_login(admin)
        response = self.client.post(f"/admin/discovery/genretag/{drone.pk}/change/", {
            "category": drone.category_id, "name": "Drone", "description": "Edited Drone pitch",
            "bpm_min": "", "bpm_max": "", "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        drone.refresh_from_db()
        self.assertEqual(drone.description, "Edited Drone pitch")

    def test_conflict_requires_explicit_update(self):
        self.run_import()
        edited = GenreTag.objects.get(category__name="House", name="Deep House")
        original = edited.description
        edited.description = "My edited description"
        edited.save(update_fields=["description"])
        with self.assertRaises(CommandError):
            self.run_import()
        edited.refresh_from_db()
        self.assertEqual(edited.description, "My edited description")
        self.assertIn("updated 1", self.run_import(update=True))
        edited.refresh_from_db()
        self.assertEqual(edited.description, original)
