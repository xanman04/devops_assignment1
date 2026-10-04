# Copyright © 2026 Xander Chen. All rights reserved.
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from discovery import models, services
from groups import models as group_models, services as groups
from notifications.models import Notification


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DemoDataTests(TestCase):
    def run_seed(self, **options):
        output = StringIO()
        call_command("seed_demo", stdout=output, **options)
        return output.getvalue()

    def category(self):
        return models.GenreCategory.objects.create(name="Test classification", description="Test-only reference", color="#1188aa")

    def test_base_repeatable_without_genres_and_does_not_grant_admin(self):
        self.assertIn("Events/groups were skipped", self.run_seed())
        self.assertEqual(get_user_model().objects.count(), 5)
        self.assertEqual(models.Venue.objects.count(), 5)
        self.assertEqual(models.Venue.objects.filter(review_status="approved").count(), 3)
        self.assertFalse(models.GenreCategory.objects.exists())
        self.assertFalse(models.GenreTag.objects.exists())
        self.assertFalse(models.Event.objects.exists())
        self.assertFalse(group_models.AttendanceGroup.objects.exists())
        self.assertFalse(get_user_model().objects.filter(is_staff=True).exists())
        self.assertFalse(get_user_model().objects.filter(is_superuser=True).exists())
        self.assertIn("Created 0 accounts, 0 venues", self.run_seed())
        self.assertEqual(models.Venue.objects.count(), 5)

    def test_unmarked_username_collision_preserves_existing_account_and_rolls_back(self):
        user = get_user_model().objects.create_user("demo_alex", password="Existing-password", email="real@example.org")
        password = user.password
        with self.assertRaises(CommandError):
            self.run_seed()
        user.refresh_from_db()
        self.assertEqual(user.password, password)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertFalse(models.Venue.objects.exists())

    def test_invalid_category_or_refresh_without_selection_makes_no_changes(self):
        for options in ({"category": [999]}, {"refresh_dates": True}):
            with self.assertRaises(CommandError):
                self.run_seed(**options)
        self.assertFalse(get_user_model().objects.exists())

    def test_explicit_classification_creates_valid_scenarios_without_editing_genres(self):
        category = self.category()
        snapshot = list(models.GenreCategory.objects.values())
        self.run_seed(category=[category.pk])
        self.assertEqual(list(models.GenreCategory.objects.values()), snapshot)
        self.assertFalse(models.GenreTag.objects.exists())
        self.assertEqual(models.Event.objects.count(), 6)
        self.assertEqual(services.search_events().count(), 4)
        pins = services.map_pins(services.search_events())
        self.assertTrue(any(pin["count"] == 2 for pin in pins))
        self.assertEqual(group_models.AttendanceGroup.objects.count(), 2)
        self.assertEqual(group_models.Membership.objects.count(), 3)
        self.assertEqual(group_models.JoinRequest.objects.filter(status="approved").count(), 1)
        self.assertEqual(group_models.JoinRequest.objects.filter(status="pending").count(), 1)
        self.assertEqual(group_models.Message.objects.count(), 3)
        self.assertTrue(Notification.objects.filter(kind="event_change").exists())
        self.assertIn("Created 0 accounts, 0 venues, 0 events, 0 groups", self.run_seed(category=[category.pk]))
        self.assertEqual(group_models.Message.objects.count(), 3)

    def test_rerun_preserves_profiles_venue_edits_and_membership_switch(self):
        category = self.category()
        self.run_seed(category=[category.pk])
        alex = get_user_model().objects.get(username="demo_alex")
        alex.display_name = "Edited name"
        alex.set_password("A-new-password")
        alex.save()
        venue = models.Venue.objects.get(name="Demo: Canal Room")
        venue.address = "Edited by the user"
        venue.save()
        offer = group_models.JoinRequest.objects.get(applicant=alex, status="approved")
        groups.accept_offer(actor=alex, request_id=offer.pk, confirm_switch=True)
        self.run_seed(category=[category.pk])
        alex.refresh_from_db(); venue.refresh_from_db()
        self.assertEqual(alex.display_name, "Edited name")
        self.assertTrue(alex.check_password("A-new-password"))
        self.assertEqual(venue.address, "Edited by the user")
        self.assertEqual(alex.attendance_memberships.get().group_id, offer.group_id)

    def test_failure_in_optional_scenarios_rolls_back_base_data(self):
        category = self.category()
        with patch("discovery.management.commands.seed_demo.groups.post_message", side_effect=RuntimeError("Failed message")):
            with self.assertRaises(RuntimeError):
                self.run_seed(category=[category.pk])
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(models.Venue.objects.exists())
        self.assertFalse(models.Event.objects.exists())

    def test_date_refresh_uses_normal_notifications_and_preserves_classification(self):
        category = self.category()
        self.run_seed(category=[category.pk])
        event = models.Event.objects.get(title="Demo: Early Session")
        from datetime import timedelta
        event.starts_at -= timedelta(days=1)
        event.ends_at -= timedelta(days=1)
        event.save()
        self.run_seed(category=[category.pk], refresh_dates=True)
        self.assertTrue(event.changes.filter(changes__has_key="starts_at").exists())
        self.assertEqual(list(event.categories.values_list("pk", flat=True)), [category.pk])
