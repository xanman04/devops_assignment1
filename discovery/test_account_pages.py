# Copyright © 2026 Xander Chen. All rights reserved.
"""My events, Notifications, Account activity, log in and status pages share the app's style."""
from datetime import timedelta
from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from discovery import models as dm, services
from notifications import models as nm, services as notices


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AccountPageTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.me = User.objects.create_user("me", password="Test-password-492!", display_name="Mia")
        self.organizer = User.objects.create_user("organizer", password="Test-password-492!")
        category = dm.GenreCategory.objects.create(name="House", color="#0066ff", description="House", bpm_min=115, bpm_max=130)
        self.venue = dm.Venue.objects.create(name="Club", latitude=40.4, longitude=-3.7, timezone="Europe/Madrid",
                                             submitted_by=self.organizer, review_status="approved")
        start = timezone.now() + timedelta(days=3)

        def make(title, creator, **extra):
            return services.save_event(actor=creator, data={"venue": self.venue, "title": title, "description": "x",
                                                            "starts_at": start, "ends_at": start + timedelta(hours=5)},
                                       category_ids=[category.pk], **extra)
        self.followed = make("Followed night", self.organizer)
        self.gone = make("Vanishing night", self.organizer)
        self.mine = make("My own night", self.me)
        services.follow_event(actor=self.me, event_id=self.followed.pk)
        services.follow_event(actor=self.me, event_id=self.gone.pk)
        services.save_event(actor=self.organizer, event_id=self.gone.pk, data={}, category_ids=[category.pk], hidden=None)
        dm.Event.objects.filter(pk=self.gone.pk).update(moderation_hidden=True)

    def get(self, path, user=None):
        self.client.force_login(user or self.me)
        return self.client.get(path)

    def test_my_events_shows_cards_with_art_date_genres_and_status(self):
        page = self.get("/my-events/")
        for text in ("discover-masthead", "<h1>My events</h1>", "Followed events", "Your listings", "grp-card", "Followed night",
                     "Club", "House", "My own night", "List an event +", "View all activity and account history"):
            self.assertContains(page, text)
        self.assertContains(page, "Followed event unavailable")        # hidden by moderation
        self.assertNotContains(page, "Vanishing night")
        self.assertNotContains(page, "Tracked")
        self.assertNotContains(page, "Events you follow")
        self.assertNotContains(page, "Events you have shared")

    def test_my_events_empty_states_invite_the_next_step(self):
        newcomer = get_user_model().objects.create_user("newcomer", password="Test-password-492!")
        page = self.get("/my-events/", newcomer)
        self.assertContains(page, "No followed events yet.")
        self.assertContains(page, "No listings yet.")
        self.assertContains(page, "Explore nearby")

    def test_notifications_have_tabs_unread_state_and_mark_read(self):
        services.save_event(actor=self.organizer, event_id=self.followed.pk, data={},
                            category_ids=[self.followed.categories.first().pk], cancelled=True)
        page = self.get("/notifications/")
        for text in ("discover-masthead", "<h1>Notifications</h1>", "note-tab is-active", "note-count", "is-unread", "Mark read",
                     "An event you follow changed", "View event"):
            self.assertContains(page, text)
        notice = nm.Notification.objects.get(recipient=self.me)
        notices.mark_read(actor=self.me, notification_id=notice.pk)
        read = self.client.get("/notifications/")
        self.assertContains(read, "note-read")
        self.assertNotContains(read, "Mark read")
        self.assertContains(self.client.get("/notifications/?unread=1"), "You're all caught up.")

    def test_old_notification_wording_is_rewritten_by_the_migration(self):
        migration = import_module("notifications.migrations.0003_follow_wording")
        event_change = dm.EventChange.objects.create(event=self.followed, actor=self.organizer, kind="event_edit",
                                                     changes={"cancelled": {"before": False, "after": True}})
        old = nm.Notification.objects.create(recipient=self.me, kind="event_change", event_change=event_change,
                                             summary="A tracked event changed: start time, end time.")
        migration.reword(apps, None)
        old.refresh_from_db()
        self.assertEqual(old.summary, "An event you follow changed: start time, end time.")

    def test_activity_is_one_timeline_with_the_kind_of_activity_on_each_entry(self):
        from groups.models import AttendanceGroup, JoinRequest, Membership
        group = AttendanceGroup.objects.create(event=self.followed, owner=self.organizer, name="Front row", description="x",
                                               capacity=4, joining_mode="approval_required")
        Membership.objects.create(group=group, user=self.organizer)
        JoinRequest.objects.create(group=group, applicant=self.me)
        joined = AttendanceGroup.objects.create(event=self.mine, owner=self.me, name="My crew", description="x", capacity=4,
                                                joining_mode="public")
        Membership.objects.create(group=joined, user=self.me)
        dm.Venue.objects.create(name="Proposed hall", latitude=40.5, longitude=-3.6, timezone="Europe/Madrid", submitted_by=self.me)
        page = self.get("/my-activity/")
        for text in ("<h1>Account activity</h1>", "act-account", "@me", "Account settings", 'class="tl"', "tl-month",
                     "Listed an event", "Followed an event", "Joined a group", "Requested to join a group", "Proposed a venue",
                     "grp-status--approved", "grp-status--pending", "Unfollow", "Edit", "Cancel request/offer", "Proposed hall"):
            self.assertContains(page, text)
        self.assertEqual(page.content.decode().count('class="tl"'), 1)            # one list, not one per category
        for old_heading in ("My listings", "My groups", "Requests and offers", "My proposed venues"):
            self.assertNotContains(page, old_heading)
        self.assertNotContains(page, "Stop tracking")
        times = [entry.split('datetime="')[1].split('"')[0] for entry in page.content.decode().split("<time")[1:]]
        self.assertEqual(times, sorted(times, reverse=True))                       # newest first

    def test_activity_with_nothing_to_show_points_at_discover(self):
        newcomer = get_user_model().objects.create_user("quiet", password="Test-password-492!")
        page = self.get("/my-activity/", newcomer)
        self.assertContains(page, "Nothing here yet.")
        self.assertNotContains(page, 'class="tl"')

    def test_log_in_and_status_pages_use_the_shared_styles(self):
        self.client.logout()
        login = self.client.get("/accounts/login/")
        self.assertContains(login, "form-page")
        self.assertContains(login, 'type="submit"')
        missing = self.get("/events/999999/")
        self.assertEqual(missing.status_code, 404)
        self.assertContains(missing, "status-page", status_code=404)
        self.assertContains(missing, "Back to Discover", status_code=404)
        denied = self.get(f"/events/{self.followed.pk}/edit/")
        self.assertEqual(denied.status_code, 403)
        self.assertContains(denied, "status-page", status_code=403)
