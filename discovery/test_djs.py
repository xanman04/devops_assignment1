# Copyright © 2026 Xander Chen. All rights reserved.
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from discovery.models import DJMediaLink, DJProfile, GenreCategory, GenreTag
from discovery.management.commands._dj_media import MEDIA
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
        link = DJMediaLink.objects.filter(dj=edited, kind="set").first()
        link.title = "Curator edit"
        link.save(update_fields=["title"])
        call_command("seed_djs", stdout=StringIO())
        self.assertEqual(DJProfile.objects.count(), len(PROFILES))
        self.assertEqual(DJMediaLink.objects.count(), sum(len(links) for links in MEDIA.values()))
        edited.refresh_from_db()
        self.assertEqual(edited.description, "Admin edit")
        link.refresh_from_db()
        self.assertEqual(link.title, "Curator edit")
        self.assertEqual(GenreCategory.objects.count(), len({n for p in PROFILES for n in p[-1]}))
        for dj in DJProfile.objects.all():
            self.assertTrue((Path(__file__).resolve().parents[1] / "static" / dj.photo).is_file())
            self.assertContains(self.client.get(f"/djs/{dj.pk}/"), dj.photo_credit)
        profile_page = self.client.get(f"/djs/{edited.pk}/")
        self.assertContains(profile_page, "Top songs")
        self.assertContains(profile_page, "Past sets & mixes")
        self.assertContains(profile_page, "Curator edit")
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

    def test_profile_without_media_uses_its_genres_as_a_sound_guide(self):
        category = GenreCategory.objects.get(name="Drum & Bass")
        dj = DJProfile.objects.create(name="New DJ", description="Fast and rhythmic.")
        dj.categories.add(category)
        response = self.client.get(f"/djs/{dj.pk}/")
        self.assertContains(response, "Explore their sound")
        self.assertNotContains(response, "Top songs")
        self.assertContains(response, "Explore the genre")
        self.assertNotContains(response, "Past sets & mixes")

    def test_seeded_lists_are_ordered_and_djs_without_songs_show_only_sets(self):
        call_command("seed_djs", stdout=StringIO())
        for name, links in MEDIA.items():
            self.assertEqual(len({url for _, _, _, url in links}), len(links), name)
            self.assertTrue(all(platform in {"youtube", "soundcloud"} for _, _, platform, _ in links), name)
            self.assertGreaterEqual(sum(kind == "set" for kind, *_ in links), 6, name)
        self.assertFalse(any(kind == "track" for kind, *_ in MEDIA["Carl Cox"]))
        for name in set(MEDIA) - {"Carl Cox"}:
            self.assertGreaterEqual(sum(kind == "track" for kind, *_ in MEDIA[name]), 8, name)

        skrillex = DJProfile.objects.get(name="Skrillex")
        page = self.client.get(f"/djs/{skrillex.pk}/").content.decode()
        self.assertIn("has-sets", page)
        self.assertLess(page.index("Where Are Ü Now"), page.index("Rumble"))
        self.assertLess(page.index("Ultra Music Festival 2015"), page.index("Tomorrowland 2012"))

        cox = DJProfile.objects.get(name="Carl Cox")
        page = self.client.get(f"/djs/{cox.pk}/").content.decode()
        self.assertNotIn("Top songs", page)
        self.assertNotIn("Explore their sound", page)
        self.assertNotIn("has-sets", page)
        self.assertIn("Past sets & mixes", page)
        self.assertEqual(page.count('class="dj-media-row dj-media-row--'), len(MEDIA["Carl Cox"]))

        # A curator reorder of a seeded link is reset by the seed; other edits are kept.
        first = DJMediaLink.objects.get(dj=skrillex, title="Where Are Ü Now · with Diplo & Justin Bieber")
        first.display_order = 99
        first.save(update_fields=["display_order"])
        call_command("seed_djs", stdout=StringIO())
        first.refresh_from_db()
        self.assertEqual(first.display_order, 0)

    def test_profile_facts_and_social_links_are_seeded_shown_and_not_overwritten(self):
        call_command("seed_djs", stdout=StringIO())
        profile = DJProfile.objects.get(name="Charlotte de Witte")
        self.assertEqual(profile.origin, "Ghent, Belgium")
        self.assertEqual(profile.active_since, 2010)
        self.assertEqual(profile.social_links.count(), 4)
        self.assertTrue(all(link.url.startswith("https://") for link in profile.social_links.all()))
        page = self.client.get(f"/djs/{profile.pk}/")
        for text in ("Ghent, Belgium", "ACTIVE SINCE", "KNTXT", "Official site", "on Instagram", "on Spotify"):
            self.assertContains(page, text)

        profile.origin = "Brussels, Belgium"
        profile.save(update_fields=["origin"])
        link = profile.social_links.get(platform="instagram")
        link.url = "https://www.instagram.com/edited/"
        link.save(update_fields=["url"])
        call_command("seed_djs", stdout=StringIO())
        profile.refresh_from_db()
        link.refresh_from_db()
        self.assertEqual(profile.origin, "Brussels, Belgium")
        self.assertEqual(link.url, "https://www.instagram.com/edited/")
        self.assertEqual(profile.social_links.count(), 4)

    def test_profile_without_facts_or_social_links_shows_neither_block(self):
        dj = DJProfile.objects.create(name="Plain DJ", description="Fast and rhythmic.")
        page = self.client.get(f"/djs/{dj.pk}/")
        self.assertNotContains(page, "dj-facts")
        self.assertNotContains(page, "dj-links")
