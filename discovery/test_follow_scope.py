"""Following an event belongs to the one account that pressed Follow."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from discovery import models as dm, services


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class FollowScopeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.a = User.objects.create_user("tracker", password="Test-password-492!")
        self.b = User.objects.create_user("bystander", password="Test-password-492!")
        category = dm.GenreCategory.objects.create(name="House", color="#0066ff", description="House", bpm_min=115, bpm_max=130)
        venue = dm.Venue.objects.create(name="Club", latitude=40.4, longitude=-3.7, timezone="Europe/Madrid",
                                        submitted_by=self.a, review_status="approved")
        start = timezone.now() + timedelta(days=3)
        self.event = services.save_event(actor=self.a, data={"venue": venue, "title": "Followed night", "description": "x",
                                                              "starts_at": start, "ends_at": start + timedelta(hours=5)},
                                         category_ids=[category.pk])
        self.other = services.save_event(actor=self.a, data={"venue": venue, "title": "Unfollowed night", "description": "x",
                                                              "starts_at": start, "ends_at": start + timedelta(hours=5)},
                                         category_ids=[category.pk])

    def test_following_is_stored_for_and_shown_to_only_that_account(self):
        client_a, client_b, anonymous = Client(), Client(), Client()
        client_a.force_login(self.a)
        client_b.force_login(self.b)
        self.assertEqual(client_a.post(f"/events/{self.event.pk}/follow/").status_code, 302)
        self.assertEqual(dm.EventFollow.objects.count(), 1)
        self.assertEqual(dm.EventFollow.objects.get().user, self.a)

        self.assertContains(client_a.get("/my-events/"), "Followed night")
        self.assertContains(client_a.get(f"/events/{self.event.pk}/"), "Unfollow")

        page = client_b.get("/my-events/")
        self.assertNotContains(page, "Followed night")
        self.assertContains(page, "No followed events yet.")
        detail = client_b.get(f"/events/{self.event.pk}/")
        self.assertContains(detail, "Follow event")
        self.assertNotContains(detail, "Unfollow")
        self.assertNotContains(client_b.get("/my-activity/"), "Followed night")
        self.assertNotContains(anonymous.get(f"/events/{self.event.pk}/"), "Unfollow")

        # B's own following and unfollowing never touch A's.
        client_b.post(f"/events/{self.other.pk}/follow/")
        client_b.post(f"/events/{self.other.pk}/unfollow/")
        self.assertEqual(list(dm.EventFollow.objects.values_list("user__username", "event__title")), [("tracker", "Followed night")])

    def test_user_specific_pages_are_not_cacheable_by_a_shared_cache(self):
        client = Client()
        client.force_login(self.a)
        for path in ("/my-events/", f"/events/{self.event.pk}/", "/groups/"):
            response = client.get(path)
            self.assertIn("Cookie", response.get("Vary", ""), path)

    def test_signed_in_pages_forbid_caching_but_public_pages_are_unchanged(self):
        client = Client()
        public = client.get(f"/events/{self.event.pk}/")
        self.assertNotIn("no-store", public.get("Cache-Control", ""))
        client.force_login(self.a)
        for path in ("/my-events/", f"/events/{self.event.pk}/", "/groups/", "/notifications/"):
            self.assertIn("no-store", client.get(path).get("Cache-Control", ""), path)
        self.assertIn("private", client.get("/my-events/").get("Cache-Control", ""))
