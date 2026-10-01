from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from discovery.models import DJProfile, GenreCategory, GenreTag
from discovery.management.commands.seed_djs import PROFILES


class DJDiscoveryTests(TestCase):
    def setUp(self):
        names = {name for profile in PROFILES for name in profile[-1]}
        for name in names:
            GenreCategory.objects.create(name=name, color="#56789a", description="A sound.", bpm_min=110, bpm_max=130)

    def test_curated_seed_is_repeatable_and_profiles_are_browsable(self):
        call_command("seed_djs", stdout=StringIO())
        edited = DJProfile.objects.get(name="Andy C")
        edited.description = "Admin edit"
        edited.save(update_fields=["description"])
        call_command("seed_djs", stdout=StringIO())
        self.assertEqual(DJProfile.objects.count(), len(PROFILES))
        edited.refresh_from_db()
        self.assertEqual(edited.description, "Admin edit")
        self.assertEqual(GenreCategory.objects.count(), len({n for p in PROFILES for n in p[-1]}))
        for dj in DJProfile.objects.all():
            self.assertTrue((Path(__file__).resolve().parents[1] / "static" / dj.photo).is_file())
            self.assertContains(self.client.get(f"/djs/{dj.pk}/"), dj.photo_credit)
        self.assertContains(self.client.get("/discover/"), "Charlotte de Witte")
        self.assertContains(self.client.get("/discover/?q=drum+and+bass"), "Andy C")

    def test_genre_detail_presents_compact_subgenre_cards_and_relevant_dj(self):
        call_command("seed_djs", stdout=StringIO())
        category = GenreCategory.objects.get(name="Drum & Bass")
        GenreTag.objects.create(category=category, name="Liquid", description="Warm and melodic. Additional detail.", bpm_min=170, bpm_max=175)
        response = self.client.get(f"/genres/{category.pk}/")
        self.assertContains(response, "subgenre-grid")
        self.assertContains(response, "Warm and melodic.")
        self.assertContains(response, "Andy C")
        self.assertNotContains(response, "Peggy Gou")
