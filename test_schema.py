"""Focused migration/constraint checks, not full business-logic coverage."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from discovery.models import (
    Event, EventCategory, EventChange, EventFollow, EventListeningReference,
    EventTag, GenreCategory, GenreTag, Venue,
)
from discovery.validators import validate_changes, validate_timezone
from groups.models import AttendanceGroup, GroupBan, JoinRequest, Membership, Message
from notifications.models import Notification


class SchemaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("owner", password="local-test-password")
        cls.guest = get_user_model().objects.create_user("guest")
        cls.venue = Venue.objects.create(
            name="Example venue", latitude="48.856600", longitude="2.352200",
            timezone="Europe/Paris", submitted_by=cls.owner, review_status="approved",
        )
        cls.event = Event.objects.create(
            creator=cls.owner, venue=cls.venue, title="Example event", description="Music",
            starts_at=timezone.now(), ends_at=timezone.now() + timedelta(hours=4),
        )
        cls.group = AttendanceGroup.objects.create(
            event=cls.event, owner=cls.owner, name="Solo attendees", description="Meet up",
            capacity=4, joining_mode="approval_required",
        )

    def assert_database_rejects(self, operation):
        with self.assertRaises(IntegrityError), transaction.atomic():
            operation()

    def test_user_uses_django_password_hash_and_name_fallback(self):
        self.assertTrue(self.owner.check_password("local-test-password"))
        self.assertNotEqual(self.owner.password, "local-test-password")
        self.assertEqual(self.owner.public_name, "owner")
        self.owner.display_name = "Music fan"
        self.assertEqual(self.owner.public_name, "Music fan")
        self.assertEqual(self.owner.email, "")

    def test_category_bpm_pairs_are_enforced_by_database(self):
        for low, high in [(120, None), (None, 140), (140, 120), (0, 100)]:
            with self.subTest(low=low, high=high):
                self.assert_database_rejects(lambda: GenreCategory.objects.create(
                    name="House", color="#0000ff", description="Example", bpm_min=low, bpm_max=high,
                ))
        GenreCategory.objects.create(name="Unknown", color="#aaaaaa", description="Unknown")

    def test_subgenre_case_uniqueness_within_category(self):
        category = GenreCategory.objects.create(name="House", color="#0000ff", description="House")
        GenreTag.objects.create(category=category, name="Afrohouse", description="Example")
        self.assert_database_rejects(lambda: GenreTag.objects.create(
            category=category, name="afrohouse", description="Duplicate",
        ))

    def test_event_supports_multiple_tags_and_unique_category_links(self):
        category = GenreCategory.objects.create(name="House", color="#0000ff", description="House")
        EventCategory.objects.create(event=self.event, category=category)
        for name in ["Afrohouse", "Deep house"]:
            tag = GenreTag.objects.create(category=category, name=name, description=name)
            EventTag.objects.create(event=self.event, tag=tag)
        self.assertEqual(self.event.tags.count(), 2)
        self.assert_database_rejects(lambda: EventCategory.objects.create(event=self.event, category=category))

    def test_invalid_time_order_and_coordinates_rejected(self):
        self.assert_database_rejects(lambda: Event.objects.filter(pk=self.event.pk).update(ends_at=self.event.starts_at))
        self.assert_database_rejects(lambda: Venue.objects.filter(pk=self.venue.pk).update(latitude=91))
        self.assert_database_rejects(lambda: Venue.objects.filter(pk=self.venue.pk).update(longitude=-181))

    def test_event_venue_reassignment_does_not_move_other_events(self):
        other = Event.objects.create(
            creator=self.owner, venue=self.venue, title="Other", description="Other",
            starts_at=self.event.starts_at, ends_at=self.event.ends_at,
        )
        destination = Venue.objects.create(
            name="New venue", latitude=50, longitude=3, timezone="Europe/Paris", submitted_by=self.owner,
        )
        self.event.venue = destination
        self.event.save(update_fields=["venue"])
        other.refresh_from_db()
        self.assertEqual(other.venue_id, self.venue.pk)
        self.assertEqual(destination.review_status, "pending")

    def test_follow_is_unique_and_requires_no_membership(self):
        EventFollow.objects.create(user=self.guest, event=self.event)
        self.assertFalse(Membership.objects.filter(user=self.guest).exists())
        self.assert_database_rejects(lambda: EventFollow.objects.create(user=self.guest, event=self.event))

    def test_unresolved_request_uniqueness_preserves_attempt_history(self):
        request = JoinRequest.objects.create(group=self.group, applicant=self.guest)
        self.assert_database_rejects(lambda: JoinRequest.objects.create(group=self.group, applicant=self.guest, status="approved"))
        request.status = "rejected"
        request.save(update_fields=["status"])
        JoinRequest.objects.create(group=self.group, applicant=self.guest)
        self.assertEqual(JoinRequest.objects.filter(applicant=self.guest).count(), 2)

    def test_active_ban_uniqueness_allows_lifted_history(self):
        ban = GroupBan.objects.create(group=self.group, user=self.guest, issued_by=self.owner)
        self.assert_database_rejects(lambda: GroupBan.objects.create(group=self.group, user=self.guest, issued_by=self.owner))
        ban.lifted_at = timezone.now()
        ban.lifted_by = self.owner
        ban.save()
        GroupBan.objects.create(group=self.group, user=self.guest, issued_by=self.owner)

    def test_group_capacity_and_duplicate_membership_constraints(self):
        self.assert_database_rejects(lambda: AttendanceGroup.objects.filter(pk=self.group.pk).update(capacity=0))
        Membership.objects.create(group=self.group, user=self.owner)
        self.assert_database_rejects(lambda: Membership.objects.create(group=self.group, user=self.owner))

    def test_notification_source_and_duplicate_constraints(self):
        request = JoinRequest.objects.create(group=self.group, applicant=self.guest, status="approved")
        Notification.objects.create(recipient=self.guest, kind="group_offer", join_request=request, summary="Offer")
        self.assert_database_rejects(lambda: Notification.objects.create(recipient=self.guest, kind="event_change", join_request=request, summary="Wrong source"))
        self.assert_database_rejects(lambda: Notification.objects.create(recipient=self.guest, kind="group_offer", join_request=request, summary="Duplicate"))
        self.assert_database_rejects(lambda: Notification.objects.create(recipient=self.guest, kind="group_offer", summary="No source"))

    def test_message_deletion_clears_content(self):
        message = Message.objects.create(group=self.group, author=self.owner, body="Hello")
        self.assert_database_rejects(lambda: Message.objects.filter(pk=message.pk).update(deleted_at=timezone.now(), deleted_by=self.owner))
        message.body = ""
        message.deleted_at = timezone.now()
        message.deleted_by = self.owner
        message.save()
        self.assertEqual(Message.objects.get(pk=message.pk).body, "")

    def test_protected_event_and_venue_and_group_cascade(self):
        Membership.objects.create(group=self.group, user=self.owner)
        Message.objects.create(group=self.group, author=self.owner, body="Hello")
        request = JoinRequest.objects.create(group=self.group, applicant=self.guest)
        Notification.objects.create(recipient=self.guest, kind="group_offer", join_request=request, summary="Offer")
        with self.assertRaises(ProtectedError):
            self.event.delete()
        with self.assertRaises(ProtectedError):
            self.venue.delete()
        self.group.delete()
        self.assertFalse(Membership.objects.exists())
        self.assertFalse(Message.objects.exists())
        self.assertFalse(Notification.objects.exists())
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_field_validation_rejects_non_http_urls_and_bad_timezone(self):
        reference = EventListeningReference(
            event=self.event, title="Music", artist_credit="Artist", kind="track", url="ftp://example.org/track",
        )
        with self.assertRaises(ValidationError):
            reference.full_clean()
        with self.assertRaises(ValidationError):
            validate_timezone("Not/A_Timezone")
        validate_timezone("Europe/Paris")

    def test_change_snapshots_require_changed_supported_fields(self):
        for snapshot in [{}, {"price": {"before": 10, "after": 20}}, {"cancelled": {"before": False, "after": False}}]:
            with self.subTest(snapshot=snapshot), self.assertRaises(ValidationError):
                validate_changes(snapshot)
        change = EventChange(event=self.event, actor=self.owner, kind="event_edit", changes={"cancelled": {"before": False, "after": True}})
        change.full_clean()

    def test_domain_admin_is_read_only_until_services_exist(self):
        staff = get_user_model().objects.create_superuser("admin", password="local-test-password")
        self.client.force_login(staff)
        response = self.client.get("/admin/groups/attendancegroup/add/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get("/").json()["status"], "backend services")

    def test_admin_can_confirm_and_delete_unreferenced_account(self):
        staff = get_user_model().objects.create_superuser("admin", password="local-test-password")
        self.client.force_login(staff)
        url = f"/admin/accounts/user/{self.guest.pk}/delete/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="post"')
        self.assertTrue(get_user_model().objects.filter(pk=self.guest.pk).exists())
        self.assertEqual(self.client.post(url, {"post": "yes"}).status_code, 302)
        self.assertFalse(get_user_model().objects.filter(pk=self.guest.pk).exists())

    def test_admin_cannot_delete_account_with_protected_records(self):
        staff = get_user_model().objects.create_superuser("admin", password="local-test-password")
        self.client.force_login(staff)
        url = f"/admin/accounts/user/{self.owner.pk}/delete/"
        response = self.client.post(url, {"post": "yes"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["protected"])
        self.assertTrue(get_user_model().objects.filter(pk=self.owner.pk).exists())
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())
