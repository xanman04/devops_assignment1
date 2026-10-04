# Copyright © 2026 Xander Chen. All rights reserved.
"""Event "Explore the sound", genre-page song lists and the Go together section."""
from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from discovery import models as dm, services
from groups import services as group_services


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class EventSoundTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("owner", password="Test-password-492!")
        self.house = dm.GenreCategory.objects.create(name="House", color="#0066ff", description="House", bpm_min=115, bpm_max=130)
        self.techno = dm.GenreCategory.objects.create(name="Techno", color="#ff3366", description="Techno", bpm_min=125, bpm_max=145)
        self.deep = dm.GenreTag.objects.create(category=self.house, name="Deep House", description="Deep")
        self.tech = dm.GenreTag.objects.create(category=self.house, name="Tech House", description="Tech")
        self.venue = dm.Venue.objects.create(name="Club", latitude=40.4, longitude=-3.7, timezone="Europe/Madrid",
                                             submitted_by=self.owner, review_status="approved")
        self.refs = {}
        order = 0
        for category, tag, title in [(self.house, None, "House one"), (self.house, None, "House two"), (self.house, None, "House three"),
                                     (self.house, self.deep, "Deep one"), (self.house, self.tech, "Tech one"),
                                     (self.techno, None, "Techno one"), (self.techno, None, "Techno two")]:
            ref = dm.GenreListeningReference.objects.create(title=title, artist_credit="Artist", kind="track", display_order=order,
                                                            url=f"https://www.youtube.com/watch?v=id{order}")
            ref.categories.add(category)
            if tag:
                ref.tags.add(tag)
            self.refs[title] = ref
            order += 1

    def make_event(self, categories, tags=(), title="Night"):
        start = timezone.now() + timedelta(days=3)
        return services.save_event(actor=self.owner, data={"venue": self.venue, "title": title, "description": "x",
                                                            "starts_at": start, "ends_at": start + timedelta(hours=5)},
                                   category_ids=[c.pk for c in categories], tag_ids=[t.pk for t in tags])

    def test_samples_lead_with_the_events_subgenre_then_the_broad_genre(self):
        event = self.make_event([self.house], [self.deep])
        titles = [ref.title for ref in services.event_sound_samples(event)]
        self.assertEqual(len(titles), 4)
        self.assertEqual(titles[0], "Deep one")
        self.assertNotIn("Tech one", titles)
        self.assertEqual(titles[1:], ["House one", "House two", "House three"])

    def test_samples_without_subgenres_use_the_broad_genre_and_mixed_nights_interleave(self):
        plain = self.make_event([self.house], title="Plain")
        self.assertEqual([r.title for r in services.event_sound_samples(plain)][:3], ["House one", "House two", "House three"])
        mixed = self.make_event([self.house, self.techno], title="Mixed")
        titles = [r.title for r in services.event_sound_samples(mixed)]
        self.assertEqual(len(titles), 4)
        self.assertIn("Techno one", titles)
        self.assertIn("House one", titles)
        self.assertEqual(len(set(titles)), 4)

    def test_event_without_any_genre_songs_has_no_samples(self):
        dm.GenreListeningReference.objects.all().delete()
        event = self.make_event([self.house])
        self.assertEqual(services.event_sound_samples(event), [])
        self.assertContains(self.client.get(f"/events/{event.pk}/"), "No listening examples yet")

    def test_page_shows_genre_songs_lineup_media_and_organiser_links(self):
        event = self.make_event([self.house], [self.deep])
        known = dm.DJProfile.objects.create(name="Known DJ", description="Plays house.")
        known.categories.add(self.house)
        for order, (kind, title) in enumerate([("track", "Song A"), ("track", "Song B"), ("track", "Song C"), ("set", "Set A"), ("set", "Set B")]):
            dm.DJMediaLink.objects.create(dj=known, title=title, kind=kind, platform="youtube", display_order=order,
                                          url=f"https://www.youtube.com/watch?v=known{order}")
        silent = dm.DJProfile.objects.create(name="Silent DJ", description="No links yet.")
        event.performers.set([known, silent])
        services.save_event_reference(actor=self.owner, event_id=event.pk,
                                      data={"title": "Organiser pick", "artist_credit": "Someone", "url": "https://example.org/x", "kind": "set"})
        page = self.client.get(f"/events/{event.pk}/")
        for text in ("EXPLORE THE SOUND", "The genre", "Deep one", "From the lineup", "Known DJ", "Song A", "Song B", "Set A",
                     "Added by the organiser", "Organiser pick"):
            self.assertContains(page, text)
        sound = page.content.decode().split("EXPLORE THE SOUND")[1].split("GO TOGETHER")[0]
        self.assertNotIn("Song C", sound)
        self.assertNotIn("Silent DJ", sound)
        self.assertContains(page, "has-lineup")

    def test_lineup_media_falls_back_to_sets_when_there_are_no_songs(self):
        event = self.make_event([self.house])
        dj = dm.DJProfile.objects.create(name="Sets only", description="DJ")
        for order in range(4):
            dm.DJMediaLink.objects.create(dj=dj, title=f"Mix {order}", kind="set", platform="youtube", display_order=order,
                                          url=f"https://www.youtube.com/watch?v=mix{order}")
        event.performers.set([dj])
        links = services.lineup_media(event)[0]["links"]
        self.assertEqual([link.title for link in links], ["Mix 0", "Mix 1", "Mix 2"])

    def test_go_together_has_only_the_two_headings_and_a_compact_group_list(self):
        event = self.make_event([self.house])
        page = self.client.get(f"/events/{event.pk}/")
        self.assertContains(page, "GO TOGETHER")
        self.assertContains(page, "Attending alone?")
        self.assertContains(page, "No groups yet")
        self.assertNotContains(page, "Find company if you want it")
        group_services.save_group(actor=self.owner, data={"event": event, "name": "Early crew", "description": "Meet at the door.",
                                                          "capacity": 3, "joining_mode": "public"})
        page = self.client.get(f"/events/{event.pk}/")
        self.assertContains(page, "go-row")
        self.assertContains(page, "Early crew")
        self.assertContains(page, "1 of 3 joined")
        self.assertContains(page, "Open")
        self.assertNotContains(page, "event-group-row")


class GenrePageSongTests(TestCase):
    def setUp(self):
        self.house = dm.GenreCategory.objects.create(name="House", color="#0066ff", description="House", bpm_min=115, bpm_max=130)
        self.trance = dm.GenreCategory.objects.create(name="Trance", color="#aa44ff", description="Trance", bpm_min=125, bpm_max=145)
        self.deep = dm.GenreTag.objects.create(category=self.house, name="Deep House", description="Deep")
        self.acid = dm.GenreTag.objects.create(category=self.house, name="Acid House", description="Acid")
        self.hard = dm.GenreTag.objects.create(category=self.trance, name="Hard Trance", description="Hard")

    def ref(self, title, categories, tags=(), order=0):
        ref = dm.GenreListeningReference.objects.create(title=title, artist_credit="Someone", kind="track", display_order=order,
                                                        url=f"https://www.youtube.com/watch?v={title.replace(' ', '')}")
        ref.categories.add(*categories)
        if tags:
            ref.tags.add(*tags)
        return ref

    def card(self, html, tag):
        """The expanded text of one subgenre card."""
        return html.split(f'id="subgenre-{tag.pk}"')[1].split("</details>")[0]

    def test_general_songs_sit_in_the_header_and_subgenre_songs_inside_their_cards(self):
        self.ref("Deep song", [self.house], [self.deep], order=1)
        self.ref("Acid song", [self.house], [self.acid], order=2)
        self.ref("General song", [self.house], order=9)
        html = self.client.get(f"/genres/{self.house.pk}/").content.decode()
        header = html.split('class="genre-detail-hero"')[1].split("</header>")[0]
        self.assertIn("HEAR THE GENRE", header)
        self.assertIn("General song", header)
        self.assertNotIn("Deep song", header)
        self.assertNotIn("Acid song", header)
        self.assertLess(html.index("General song"), html.index('class="subgenre-grid"'))
        self.assertIn("Deep song", self.card(html, self.deep))
        self.assertNotIn("Acid song", self.card(html, self.deep))
        self.assertIn("Acid song", self.card(html, self.acid))
        self.assertIn("dj-media-row--youtube", self.card(html, self.acid))
        self.assertIn("♪ 1", html)
        self.assertNotIn("genre-listen-heading", html)
        self.assertEqual(html.count("General song"), 1)

    def test_shared_song_appears_in_each_categorys_own_subgenre_card_only(self):
        self.ref("Shared song", [self.house, self.trance], [self.acid, self.hard])
        house_page = self.client.get(f"/genres/{self.house.pk}/").content.decode()
        trance_page = self.client.get(f"/genres/{self.trance.pk}/").content.decode()
        self.assertIn("Shared song", self.card(house_page, self.acid))
        self.assertNotIn("HEAR THE GENRE", house_page)
        self.assertIn("Shared song", self.card(trance_page, self.hard))
        self.assertEqual(house_page.count("Shared song"), 1)
        self.assertEqual(trance_page.count("Shared song"), 1)

    def test_subgenre_without_songs_shows_no_song_block(self):
        html = self.client.get(f"/genres/{self.house.pk}/").content.decode()
        self.assertNotIn("HEAR IT", html)
        self.assertNotIn("♪", html)


class GenreSongSeedTests(TestCase):
    def test_every_category_and_subgenre_gets_representative_songs(self):
        from discovery.management.commands._genre_songs import SONGS
        names = {category for song in SONGS for category, _ in song["where"]}
        for name in names:
            dm.GenreCategory.objects.create(name=name, color="#56789a", description="A sound.", bpm_min=100, bpm_max=140)
        call_command("import_subgenres", stdout=StringIO())
        call_command("seed_genre_songs", stdout=StringIO())
        count = dm.GenreListeningReference.objects.count()
        call_command("seed_genre_songs", stdout=StringIO())
        self.assertEqual(dm.GenreListeningReference.objects.count(), count)

        self.assertEqual(dm.GenreCategory.objects.count(), 22)
        for category in dm.GenreCategory.objects.all():
            general = [ref for ref in category.listening_references.prefetch_related("tags")
                       if not any(tag.category_id == category.pk for tag in ref.tags.all())]
            self.assertGreaterEqual(len(general), 3, category.name)
        for tag in dm.GenreTag.objects.select_related("category"):
            self.assertGreaterEqual(tag.listening_references.count(), 1, f"{tag.category.name} / {tag.name}")
        for ref in dm.GenreListeningReference.objects.prefetch_related("categories", "tags"):
            self.assertTrue(ref.url.startswith("https://"))
            for tag in ref.tags.all():
                self.assertIn(tag.category_id, {c.pk for c in ref.categories.all()})
        self.assertEqual(len({r.url for r in dm.GenreListeningReference.objects.all()}), count)

    def test_sets_in_the_data_are_stored_as_sets(self):
        from discovery.management.commands._genre_songs import SONGS
        for name in {c for song in SONGS for c, _ in song["where"]}:
            dm.GenreCategory.objects.create(name=name, color="#56789a", description="x", bpm_min=100, bpm_max=140)
        call_command("import_subgenres", stdout=StringIO())
        call_command("seed_genre_songs", stdout=StringIO())
        expected = {song["url"] for song in SONGS if song["kind"] == "set"}
        self.assertTrue(expected)
        self.assertEqual({r.url for r in dm.GenreListeningReference.objects.filter(kind="set")}, expected)
        self.assertEqual(dm.GenreTag.objects.get(name="Hard-Bounce").listening_references.filter(kind="track").count(), 1)


class StylesheetTests(TestCase):
    def test_stylesheets_have_balanced_braces(self):
        # An unclosed block silently drops every rule after it, so check the shipped files.
        from pathlib import Path
        for name in ("app.css", "live.css"):
            text = (Path(__file__).resolve().parents[1] / "static" / name).read_text(encoding="utf-8")
            self.assertEqual(text.count("{"), text.count("}"), name)
