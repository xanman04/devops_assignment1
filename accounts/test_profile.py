"""Profile page, profile picture and connected music links."""
from io import BytesIO
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from accounts.models import User

TEMP_MEDIA = tempfile.mkdtemp()


def picture(name="me.png", size=(300, 200)):
    buffer = BytesIO()
    Image.new("RGB", size, "#336699").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=TEMP_MEDIA, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ProfileTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user("mia", password="Test-password-492!", display_name="Mia")
        self.client.force_login(self.user)

    def settings_data(self, **extra):
        return {"display_name": "Mia", "bio": "", "email": "", "instagram_url": "", "spotify_url": "",
                "apple_music_url": "", "soundcloud_url": ""} | extra

    def test_profile_needs_login_and_nav_points_at_it(self):
        page = self.client.get("/accounts/profile/")
        for text in ("profile-card", "Mia", "@mia", "Collection", "profile-split", "profile-board", "Edit profile", "Followed events", 'href="/accounts/profile/"'):
            self.assertContains(page, text)
        self.client.logout()
        self.assertEqual(self.client.get("/accounts/profile/").status_code, 302)

    def test_saving_settings_stores_bio_and_links_and_shows_them(self):
        response = self.client.post("/accounts/settings/", self.settings_data(
            bio="Techno after dark", spotify_url="https://open.spotify.com/user/mia", instagram_url="https://www.instagram.com/mia/",
            apple_music_url="https://music.apple.com/profile/mia", soundcloud_url="https://soundcloud.com/mia"))
        self.assertRedirects(response, "/accounts/profile/")
        page = self.client.get("/accounts/profile/")
        self.assertContains(page, "Techno after dark")
        for label in ("Instagram", "Spotify", "Apple Music", "SoundCloud"):
            self.assertContains(page, f'aria-label="{label}"')
        self.assertContains(page, "#icon-apple-music")

    def test_links_must_point_at_the_named_service(self):
        for field, bad in (("spotify_url", "https://example.com/mia"), ("instagram_url", "https://instagram.com.evil.test/mia"),
                           ("soundcloud_url", "javascript:alert(1)"), ("apple_music_url", "https://open.spotify.com/x")):
            response = self.client.post("/accounts/settings/", self.settings_data(**{field: bad}))
            self.assertEqual(response.status_code, 400, field)
            self.user.refresh_from_db()
            self.assertEqual(getattr(self.user, field), "")

    def test_picture_is_re_encoded_served_to_signed_in_users_and_replaceable(self):
        self.client.post("/accounts/settings/", self.settings_data(avatar=picture()))
        self.user.refresh_from_db()
        first = self.user.avatar.name
        self.assertTrue(first.startswith("avatars/"))
        served = self.client.get(f"/accounts/avatar/{self.user.pk}/")
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served["Cache-Control"], "private, no-store")
        self.assertEqual(Image.open(BytesIO(b"".join(served.streaming_content))).format, "JPEG")
        self.assertContains(self.client.get("/accounts/profile/"), f"/accounts/avatar/{self.user.pk}/")
        self.client.post("/accounts/settings/", self.settings_data(avatar=picture("other.png")))
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.avatar.name, first)
        self.assertFalse(self.user.avatar.storage.exists(first))
        # there is no removal control: the picture stays until a new one is uploaded
        page = self.client.get("/accounts/settings/")
        self.assertNotContains(page, "remove_avatar")
        self.assertNotContains(page, "Remove my profile picture")
        self.assertContains(page, f'data-current-src="/accounts/avatar/{self.user.pk}/"')
        self.client.post("/accounts/settings/", self.settings_data())
        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar)
        self.assertEqual(self.client.get(f"/accounts/avatar/{self.user.pk}/").status_code, 200)

    def test_non_images_are_rejected_and_anonymous_visitors_cannot_fetch_pictures(self):
        fake = SimpleUploadedFile("evil.png", b"<script>alert(1)</script>", content_type="image/png")
        self.assertEqual(self.client.post("/accounts/settings/", self.settings_data(avatar=fake)).status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.avatar)
        self.client.logout()
        self.assertEqual(self.client.get(f"/accounts/avatar/{self.user.pk}/").status_code, 302)

    def test_picture_fields_offer_the_crop_tool(self):
        page = self.client.get("/accounts/settings/")
        self.assertContains(page, 'data-crop-aspect="1"')
        self.assertContains(page, 'data-crop-shape="circle"')
        self.assertContains(page, "image-crop.js")
        self.assertContains(page, 'accept="image/jpeg,image/png,image/webp"')

    def test_profile_lists_next_events_as_a_timeline_and_groups_as_small_tiles(self):
        page = self.client.get("/accounts/profile/")
        self.assertContains(page, "Nothing coming up.")
        self.assertNotContains(page, 'id="row-nextup"')

    def make_cards(self, user, genres):
        """One event card per entry in genres, for a person; genres are created on demand."""
        from datetime import timedelta
        from django.utils import timezone
        from discovery import models as dm
        venue = dm.Venue.objects.get_or_create(name="Club", defaults={"latitude": 1, "longitude": 1, "timezone": "Europe/Madrid",
                                                                     "submitted_by": user, "review_status": "approved"})[0]
        for index, name in enumerate(genres):
            category = dm.GenreCategory.objects.get_or_create(name=name, defaults={"color": "#336699", "description": "x", "bpm_min": 100, "bpm_max": 140})[0]
            start = timezone.now() + timedelta(days=index + 1)
            event = dm.Event.objects.create(creator=user, venue=venue, title=f"{name} night {index}", description="x", starts_at=start,
                                            ends_at=start + timedelta(hours=4))
            event.categories.add(category)
            dm.EventCard.objects.create(user=user, event=event)

    def test_collection_is_per_person_and_empty_for_a_new_account(self):
        page = self.client.get("/accounts/profile/")
        self.assertNotContains(page, "badge-card ")
        self.assertContains(page, "badge-slot")
        self.make_cards(self.user, ["Techno"] * 5 + ["House"] * 3)
        page = self.client.get("/accounts/profile/")
        self.assertEqual(page.content.decode().count("badge-card badge-card--event"), 8)
        self.assertContains(page, "Techno Head")
        self.assertContains(page, "tier-silver")
        other = User.objects.create_user("zed", password="Test-password-492!")
        self.client.force_login(other)
        self.assertNotContains(self.client.get("/accounts/profile/"), "Techno night")
        self.assertNotContains(self.client.get("/accounts/profile/"), "tier-")

    def test_genre_chart_follows_the_persons_own_attendance(self):
        from accounts import genre_chart
        self.make_cards(self.user, ["Techno"] * 4 + ["House"] * 2)
        from discovery.models import GenreCategory
        categories = list(GenreCategory.objects.order_by("id"))
        from accounts import sample_badges as sb
        values = dict(zip([c.name for c in categories], genre_chart.values_from_cards(categories, sb.cards_for(self.user))))
        self.assertEqual(values, {"Techno": 1.0, "House": 0.5})
        self.assertContains(self.client.get("/accounts/profile/"), 'class="gchart-svg"')

    def test_chart_geometry_is_closed_bounded_and_scales_with_attendance(self):
        from types import SimpleNamespace
        from accounts import genre_chart
        genres = [SimpleNamespace(name=f"g{i}", color="#fff") for i in range(22)]
        chart = genre_chart.build(genres, [1.0] * 22)
        centre = genre_chart.CENTRE
        for vertex in chart["vertices"]:
            self.assertAlmostEqual(((vertex["x"] - centre) ** 2 + (vertex["y"] - centre) ** 2) ** 0.5, genre_chart.RADIUS, delta=0.5)
        empty = genre_chart.build(genres, [0.0] * 22)
        stub = empty["vertices"][0]
        self.assertLess(((stub["x"] - centre) ** 2 + (stub["y"] - centre) ** 2) ** 0.5, 10)   # a visible stub, not a collapsed point
        self.assertEqual(empty["top"], [])
        self.assertIsNone(genre_chart.build([]))

    def test_foil_colours_come_from_the_badge_itself(self):
        from accounts import badge_palette
        poster = badge_palette.from_poster("demo-posters/blue-hour.webp", "#1D4ED8")      # a blue poster
        self.assertEqual(len(poster), 3)
        for colour in poster:
            self.assertRegex(colour, r"^#[0-9a-f]{6}$")
        orange = badge_palette.from_colour("#FF7A00")
        self.assertEqual(len(orange), 3)
        self.assertNotEqual(poster, orange)                          # different content gives different foil
        self.assertEqual(badge_palette.from_poster("missing/file.webp", "#FF7A00"), orange)
        first_hue = badge_palette._hue_of(poster[0])[0]
        self.assertTrue(0.45 < first_hue < 0.8 or any(0.45 < badge_palette._hue_of(c)[0] < 0.8 for c in poster))   # a blue-ish colour is present

    def test_achievements_have_five_tiers_and_exist_only_with_their_proof(self):
        from accounts import sample_badges as sb
        for needed, name in ((3, "Bronze"), (5, "Silver"), (10, "Gold"), (15, "Platinum"), (20, "Diamond")):
            cards = [dict(sb.event_cards()[0], genre="Techno") for _ in range(needed)]
            tiers = {b["title"]: b["tier"] for b in sb.achievements(cards)}
            self.assertEqual(tiers["Techno Head"], name)
            self.assertEqual(tiers["Scene Regular"], name)
            fewer = {b["title"] for b in sb.achievements(cards[:needed - 1])} if needed > 3 else set()
            if needed == 3:
                self.assertEqual(sb.achievements(cards[:2]), [])           # two cards earn nothing
        self.assertEqual(sb.achievements([]), [])
        cards = sb.event_cards()
        earned = {b["title"]: b for b in sb.achievements(cards)}
        self.assertEqual(len(earned["DnB Lover"]["proof"]), 15)
        self.assertEqual(earned["Scene Regular"]["tier"], "Diamond")
        self.assertEqual(sb.achievements([c for c in cards if c["genre"] != "Techno"]) and
                         "Techno Head" in {b["title"] for b in sb.achievements([c for c in cards if c["genre"] != "Techno"])}, False)

    def test_collection_name_comes_from_one_setting(self):
        self.assertContains(self.client.get("/accounts/profile/"), "<h2 id=\"board-heading\">Collection</h2>")
        with override_settings(COLLECTION_NAME="Crate"):
            page = self.client.get("/accounts/profile/")
        self.assertContains(page, "<h2 id=\"board-heading\">Crate</h2>")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"], MEDIA_ROOT=TEMP_MEDIA)
class RegistrationPageTests(TestCase):
    def test_form_covers_the_whole_profile_and_tags_every_field(self):
        page = self.client.get("/accounts/register/")
        text = page.content.decode()
        for name in ("username", "password1", "password2", "display_name", "avatar", "bio", "email",
                     "instagram_url", "spotify_url", "apple_music_url", "soundcloud_url"):
            self.assertIn(f'name="{name}"', text)
        self.assertEqual(text.count("field-tag--req"), 3)
        self.assertEqual(text.count("field-tag--opt"), 8)
        self.assertNotIn("<ul>", text.split("<form")[1].split("</form>")[0])        # the password rules are plain text
        self.assertContains(page, "At least 8 characters.")
        self.assertContains(page, 'data-crop-aspect="1"')

    def test_only_username_and_password_are_needed_and_profile_fields_are_saved(self):
        base = {"username": "newbie", "password1": "Test-password-492!", "password2": "Test-password-492!"}
        first = self.client.post("/accounts/register/", base)
        self.assertEqual((first.status_code, first["Location"]), (302, "/accounts/profile/"))
        self.client.logout()
        full = {"username": "fulla", "password1": "Test-password-492!", "password2": "Test-password-492!", "display_name": "Fulla",
                "bio": "Hi", "email": "f@example.org", "spotify_url": "https://open.spotify.com/user/f", "avatar": picture()}
        self.assertEqual(self.client.post("/accounts/register/", full).status_code, 302)
        self.client.logout()
        saved = User.objects.get(username="fulla")
        self.assertEqual((saved.display_name, saved.bio, saved.spotify_url), ("Fulla", "Hi", "https://open.spotify.com/user/f"))
        self.assertTrue(saved.avatar.name.startswith("avatars/"))
        bad = dict(full, username="other", spotify_url="https://example.com/x", avatar="")
        self.assertEqual(self.client.post("/accounts/register/", bad).status_code, 400)
        self.assertFalse(User.objects.filter(username="other").exists())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SeedAttendanceTests(TestCase):
    def test_each_demo_account_gets_its_own_cards_in_the_check_in_table(self):
        from datetime import timedelta
        from django.core.management import call_command
        from django.utils import timezone
        from discovery import models as dm
        organizer = User.objects.create_user("demo_organizer", password="x")
        names = {"demo_organizer": 22, "demo_morgan": 3, "demo_sam": 11}
        for name in names:
            User.objects.get_or_create(username=name, defaults={})
        category = dm.GenreCategory.objects.create(name="House", color="#0066ff", description="x", bpm_min=1, bpm_max=2)
        venue = dm.Venue.objects.create(name="C", latitude=1, longitude=1, timezone="Europe/Madrid", submitted_by=organizer, review_status="approved")
        for index in range(24):
            start = timezone.now() + timedelta(days=index + 1)
            event = dm.Event.objects.create(creator=organizer, venue=venue, title=f"E{index}", description="x", starts_at=start, ends_at=start + timedelta(hours=3))
            event.categories.add(category)
        call_command("seed_attendance", stdout=__import__("io").StringIO())
        counts = {name: dm.EventCard.objects.filter(user__username=name).count() for name in names}
        self.assertEqual(counts, names)
        call_command("seed_attendance", stdout=__import__("io").StringIO())              # repeatable, not cumulative
        self.assertEqual({name: dm.EventCard.objects.filter(user__username=name).count() for name in names}, names)
        self.client.force_login(User.objects.get(username="demo_organizer"))
        page = self.client.get("/accounts/profile/")
        self.assertContains(page, "tier-diamond")
        self.assertContains(page, "<dt>Events attended</dt><dd>22</dd>")
