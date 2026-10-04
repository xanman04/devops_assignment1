"""What a tab left open on the old account can and cannot do after another tab signs in as someone else."""
from datetime import timedelta
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from discovery import models as dm, services


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class StaleTabTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.a = User.objects.create_user("alice", password="Test-password-492!")
        self.b = User.objects.create_user("bob", password="Test-password-492!")
        category = dm.GenreCategory.objects.create(name="House", color="#0066ff", description="House", bpm_min=115, bpm_max=130)
        venue = dm.Venue.objects.create(name="Club", latitude=40.4, longitude=-3.7, timezone="Europe/Madrid",
                                        submitted_by=self.a, review_status="approved")
        start = timezone.now() + timedelta(days=3)
        self.event = services.save_event(actor=self.a, data={"venue": venue, "title": "Night", "description": "x",
                                                              "starts_at": start, "ends_at": start + timedelta(hours=5)},
                                         category_ids=[category.pk])

    def login(self, client, username):
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', client.get("/accounts/login/").content.decode()).group(1)
        response = client.post("/accounts/login/", {"username": username, "password": "Test-password-492!", "csrfmiddlewaretoken": token})
        self.assertEqual(response.status_code, 302)

    def form_token(self, client):
        return re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', client.get(f"/events/{self.event.pk}/").content.decode()).group(1)

    def test_a_form_from_the_old_account_cannot_act_as_the_new_one(self):
        browser = Client(enforce_csrf_checks=True)       # one browser: one cookie jar shared by every tab
        self.login(browser, "alice")
        stale_token = self.form_token(browser)           # what the tab left on Alice's page still holds
        self.login(browser, "bob")                       # another tab signs in as Bob
        response = browser.post(f"/events/{self.event.pk}/follow/", {"csrfmiddlewaretoken": stale_token})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(dm.EventFollow.objects.count(), 0)
        # a page loaded after the switch works, and only as Bob
        fresh = self.form_token(browser)
        self.assertEqual(browser.post(f"/events/{self.event.pk}/follow/", {"csrfmiddlewaretoken": fresh}).status_code, 302)
        self.assertEqual(list(dm.EventFollow.objects.values_list("user__username", flat=True)), ["bob"])

    def test_whoami_reports_the_account_the_browser_is_signed_in_as(self):
        anonymous = Client().get("/accounts/whoami/")
        self.assertEqual(anonymous.json(), {"id": None, "name": ""})
        self.assertIn("no-store", anonymous["Cache-Control"])
        client = Client()
        client.force_login(self.a)
        self.assertEqual(client.get("/accounts/whoami/").json(), {"id": self.a.pk, "name": "alice"})
        client.force_login(self.b)
        self.assertEqual(client.get("/accounts/whoami/").json()["id"], self.b.pk)
        self.assertEqual(client.post("/accounts/whoami/").status_code, 405)

    def test_every_page_says_which_account_it_was_built_for_and_loads_the_guard(self):
        client = Client()
        client.force_login(self.a)
        page = client.get("/discover/").content.decode()
        self.assertIn(f'data-account="{self.a.pk}"', page)
        self.assertIn("account-guard.js", page)
        self.assertIn('data-account=""', Client().get("/discover/").content.decode())

    def test_other_local_servers_do_not_share_cookie_names(self):
        from config import settings
        self.assertEqual(settings.cookie_suffix("8000"), "")
        self.assertEqual(settings.cookie_suffix("8011"), "_8011")
        self.assertEqual(settings.cookie_suffix("bad port"), "")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TabSlotTests(TestCase):
    """A tab that signs in gets its own cookies, so another tab's login is not replaced."""

    SLOT_A, SLOT_B = "t0a1b2c3d", "t4e5f6a7b"

    def setUp(self):
        User = get_user_model()
        self.alice = User.objects.create_user("alice", password="Test-password-492!", display_name="Alice")
        self.bob = User.objects.create_user("bob", password="Test-password-492!", display_name="Bob")
        self.client = Client(enforce_csrf_checks=True)

    def sign_in(self, slot, username):
        page = self.client.get(f"/{slot}/accounts/login/")
        self.assertEqual(page.status_code, 200)
        token = page.context["csrf_token"]
        return self.client.post(f"/{slot}/accounts/login/", {"username": username, "password": "Test-password-492!",
                                                              "csrfmiddlewaretoken": str(token)})

    def who(self, prefix):
        return self.client.get(f"{prefix}/accounts/whoami/").json()["name"]

    def test_two_tabs_hold_different_accounts_in_one_browser(self):
        first, second = self.sign_in(self.SLOT_A, "alice"), self.sign_in(self.SLOT_B, "bob")
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(first["Location"], f"/{self.SLOT_A}/accounts/profile/")
        self.assertEqual(self.who(f"/{self.SLOT_A}"), "Alice")
        self.assertEqual(self.who(f"/{self.SLOT_B}"), "Bob")
        self.assertEqual(self.who(""), "")          # an address without a prefix has no login of its own

    def test_cookies_are_named_for_the_slot_and_limited_to_its_path(self):
        response = self.sign_in(self.SLOT_A, "alice")
        for base in (settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME):
            cookie = response.cookies[f"{base}_{self.SLOT_A}"]
            self.assertEqual(cookie["path"], f"/{self.SLOT_A}/")
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)

    def test_the_browser_wide_login_is_never_used_inside_a_slot(self):
        self.client.force_login(self.alice)         # old style login: plain session cookie sent everywhere
        self.assertEqual(self.who(""), "Alice")
        self.assertEqual(self.who(f"/{self.SLOT_B}"), "")

    def test_slot_pages_link_within_the_slot_and_log_out_stays_in_it(self):
        self.sign_in(self.SLOT_A, "alice")
        page = self.client.get(f"/{self.SLOT_A}/groups/")
        self.assertContains(page, f'data-root="/{self.SLOT_A}/"')
        self.assertContains(page, f'href="/{self.SLOT_A}/notifications/"')
        self.assertContains(page, f'data-account="{self.alice.pk}"')
        token = page.context["csrf_token"]
        out = self.client.post(f"/{self.SLOT_A}/accounts/logout/", {"csrfmiddlewaretoken": str(token)})
        self.assertEqual(out.status_code, 302)
        self.assertEqual(out["Location"], f"/{self.SLOT_A}/")
        self.assertEqual(self.who(f"/{self.SLOT_A}"), "")

    def test_a_form_from_another_slot_cannot_act_for_this_one(self):
        self.sign_in(self.SLOT_A, "alice")
        self.sign_in(self.SLOT_B, "bob")
        page = self.client.get(f"/{self.SLOT_B}/accounts/settings/")
        stale = self.client.post(f"/{self.SLOT_A}/accounts/settings/", {"display_name": "Hacked", "csrfmiddlewaretoken": str(page.context["csrf_token"])})
        self.assertEqual(stale.status_code, 403)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.display_name, "Alice")

    def test_pages_carry_the_tab_scripts(self):
        page = self.client.get("/accounts/login/")
        self.assertContains(page, "data-new-session")
        self.assertContains(page, 'data-root="/"')
        self.assertContains(page, "bassline-slot")

    def test_first_sign_in_from_a_page_without_a_prefix_works(self):
        """The form was made on the plain address; the tab then posts it under its new prefix."""
        page = self.client.get("/accounts/login/")
        token = page.context["csrf_token"]
        response = self.client.post(f"/{self.SLOT_A}/accounts/login/", {"username": "alice", "password": "Test-password-492!",
                                                                         "csrfmiddlewaretoken": str(token), "next": f"/{self.SLOT_A}/groups/"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/{self.SLOT_A}/groups/")
        self.assertEqual(self.who(f"/{self.SLOT_A}"), "Alice")
