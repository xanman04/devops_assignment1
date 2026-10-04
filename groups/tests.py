# Copyright © 2026 Xander Chen. All rights reserved.
from datetime import timedelta
from io import BytesIO
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from PIL import Image

from discovery import services as discovery
from notifications.models import Notification
from . import services as s
from .models import AttendanceGroup, GroupBan, JoinRequest, Membership, Message
from .photos import prepare_photo


class GroupServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser("admin", password="example-password")
        cls.owner = get_user_model().objects.create_user("owner")
        cls.guest = get_user_model().objects.create_user("guest")
        cls.other = get_user_model().objects.create_user("other")
        category = discovery.save_category(actor=cls.admin, data={"name": "House", "color": "#0000FF", "description": "Music"})
        venue = discovery.save_venue(actor=cls.admin, review_status="approved", data={"name": "Venue", "latitude": 48, "longitude": 2, "timezone": "Europe/Paris"})
        cls.event = discovery.save_event(actor=cls.owner, category_ids=[category.pk], data={
            "venue": venue, "title": "Event", "description": "Music",
            "starts_at": timezone.now()+timedelta(days=1), "ends_at": timezone.now()+timedelta(days=1, hours=5),
        })

    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory(prefix="group-photo-tests-")
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_override.enable()
        self.addCleanup(self.media_dir.cleanup)
        self.addCleanup(self.media_override.disable)

    def make_group(self, actor=None, mode="public", capacity=4, **kwargs):
        return s.save_group(actor=actor or self.owner, data={"event": self.event, "name": "Company",
            "description": "Meet then coordinate elsewhere", "capacity": capacity, "joining_mode": mode}, **kwargs)

    def photo(self, size=(1800, 900), name="picture.png"):
        output = BytesIO()
        image = Image.new("RGB", size, "blue")
        exif = Image.Exif()
        exif[270] = "private camera metadata"
        image.save(output, "PNG", exif=exif)
        return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")

    def test_owner_is_member_and_cannot_create_another_same_event(self):
        group = self.make_group()
        self.assertTrue(group.memberships.filter(user=self.owner).exists())
        with self.assertRaises(ValidationError):
            self.make_group()
        self.assertEqual(AttendanceGroup.objects.count(), 1)

    def test_public_join_capacity_and_idempotence(self):
        group = self.make_group(capacity=2)
        first = s.join_group(actor=self.guest, group_id=group.pk)
        self.assertEqual(s.join_group(actor=self.guest, group_id=group.pk), first)
        with self.assertRaises(ValidationError):
            s.join_group(actor=self.other, group_id=group.pk)
        self.assertEqual(group.memberships.count(), 2)

    def elsewhere(self, user):
        """Put someone in a different group for the same event."""
        holder = get_user_model().objects.create_user(f"holder{user.pk}")
        other_group = s.save_group(actor=holder, data={"event": self.event, "name": "Elsewhere", "description": "x", "capacity": 4, "joining_mode": "public"})
        s.join_group(actor=user, group_id=other_group.pk)

    def test_owner_approval_adds_someone_with_no_other_group_straight_away(self):
        group = self.make_group(mode="approval_required")
        request = s.request_join(actor=self.guest, group_id=group.pk)
        self.assertEqual(request.status, "pending")                      # the owner still decides
        approved = s.review_request(actor=self.owner, request_id=request.pk, approve=True)
        self.assertEqual(approved.status, "accepted")                    # no second step for the applicant
        self.assertTrue(group.memberships.filter(user=self.guest).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.guest, summary__contains="have joined").exists())
        self.assertTrue(group.notices.filter(kind="joined", subject=self.guest).exists())

    def test_approval_for_someone_in_another_group_stays_an_offer_and_does_not_reserve_a_place(self):
        group = self.make_group(mode="approval_required", capacity=2)
        self.elsewhere(self.guest)
        request = s.request_join(actor=self.guest, group_id=group.pk)
        self.assertEqual(s.request_join(actor=self.guest, group_id=group.pk), request)
        with self.assertRaises(ValidationError):
            s.join_group(actor=self.guest, group_id=group.pk)
        s.review_request(actor=self.owner, request_id=request.pk, approve=True)
        request.refresh_from_db()
        self.assertEqual((request.status, group.memberships.count()), ("approved", 1))      # an offer, nobody added
        second = s.request_join(actor=self.other, group_id=group.pk)
        s.review_request(actor=self.owner, request_id=second.pk, approve=True)             # joins directly and fills the group
        self.assertEqual(group.memberships.count(), 2)
        with self.assertRaises(ValidationError):
            s.accept_offer(actor=self.guest, request_id=request.pk, confirm_switch=True)   # full now
        request.refresh_from_db()
        self.assertEqual(request.status, "approved")

    def test_private_request_rejection_and_reapplication(self):
        group = self.make_group(mode="approval_required")
        request = s.request_join(actor=self.guest, group_id=group.pk)
        s.review_request(actor=self.owner, request_id=request.pk, approve=False)
        replacement = s.request_join(actor=self.guest, group_id=group.pk)
        self.assertNotEqual(replacement.pk, request.pk)
        self.assertTrue(Notification.objects.filter(recipient=self.guest, kind="group_rejected").exists())

    def test_confirmed_private_switch_and_owner_handover(self):
        old = self.make_group()
        s.join_group(actor=self.guest, group_id=old.pk)
        destination = self.make_group(actor=self.other, mode="approval_required")
        request = s.request_join(actor=self.owner, group_id=destination.pk)
        s.review_request(actor=self.other, request_id=request.pk, approve=True)
        with self.assertRaises(ValidationError):
            s.accept_offer(actor=self.owner, request_id=request.pk)
        s.accept_offer(actor=self.owner, request_id=request.pk, confirm_switch=True)
        old.refresh_from_db()
        self.assertEqual(old.owner, self.guest)
        self.assertEqual(Membership.objects.filter(user=self.owner, group__event=self.event).count(), 1)
        self.assertTrue(Notification.objects.filter(recipient=self.guest, kind="owner_transfer").exists())

    def test_full_switch_keeps_original_membership(self):
        old = self.make_group()
        destination = self.make_group(actor=self.other, capacity=1)
        with self.assertRaises(ValidationError):
            s.join_group(actor=self.owner, group_id=destination.pk, confirm_switch=True)
        self.assertTrue(old.memberships.filter(user=self.owner).exists())

    def test_failed_switch_notification_rolls_back_entire_transition(self):
        old = self.make_group()
        s.join_group(actor=self.guest, group_id=old.pk)
        destination = self.make_group(actor=self.other)
        with patch("groups.services._notify", side_effect=RuntimeError("notification failed")):
            with self.assertRaises(RuntimeError):
                s.join_group(actor=self.owner, group_id=destination.pk, confirm_switch=True)
        old.refresh_from_db()
        self.assertEqual(old.owner, self.owner)
        self.assertTrue(old.memberships.filter(user=self.owner).exists())
        self.assertFalse(destination.memberships.filter(user=self.owner).exists())

    def test_owner_departure_uses_seniority_and_empty_group_deletes(self):
        group = self.make_group()
        s.join_group(actor=self.guest, group_id=group.pk)
        s.join_group(actor=self.other, group_id=group.pk)
        s.leave_group(actor=self.owner, group_id=group.pk)
        group.refresh_from_db()
        self.assertEqual(group.owner, self.guest)
        s.leave_group(actor=self.guest, group_id=group.pk)
        group.refresh_from_db()
        self.assertEqual(group.owner, self.other)
        s.leave_group(actor=self.other, group_id=group.pk)
        self.assertFalse(AttendanceGroup.objects.exists())

    def test_group_settings_ownership_capacity_and_mode_changes(self):
        group = self.make_group()
        s.join_group(actor=self.guest, group_id=group.pk)
        with self.assertRaises(PermissionDenied):
            s.save_group(actor=self.guest, group_id=group.pk, data={"name": "Mine"})
        with self.assertRaises(ValidationError):
            s.save_group(actor=self.owner, group_id=group.pk, data={"capacity": 1})
        with self.assertRaises(ValidationError):
            s.save_group(actor=self.owner, group_id=group.pk, data={"event": self.event})
        s.save_group(actor=self.owner, group_id=group.pk, data={"joining_mode": "approval_required", "name": "New"})
        self.assertEqual(group.memberships.count(), 2)
        s.leave_group(actor=self.guest, group_id=group.pk)
        with self.assertRaises(ValidationError):
            s.join_group(actor=self.guest, group_id=group.pk)
        self.assertEqual(s.request_join(actor=self.guest, group_id=group.pk).status, "pending")

    def test_private_to_public_preserves_requests_and_members(self):
        group = self.make_group(mode="approval_required")
        request = s.request_join(actor=self.guest, group_id=group.pk)
        s.save_group(actor=self.owner, group_id=group.pk, data={"joining_mode": "public"})
        request.refresh_from_db()
        self.assertEqual(request.status, "pending")
        s.join_group(actor=self.guest, group_id=group.pk)
        request.refresh_from_db()
        self.assertEqual(request.status, "accepted")

    def test_remove_rejoin_ban_lift_and_request_cancellation(self):
        group = self.make_group()
        s.join_group(actor=self.guest, group_id=group.pk)
        s.remove_member(actor=self.owner, group_id=group.pk, user_id=self.guest.pk)
        s.join_group(actor=self.guest, group_id=group.pk)
        ban = s.remove_member(actor=self.owner, group_id=group.pk, user_id=self.guest.pk, ban=True)
        with self.assertRaises(PermissionDenied):
            s.join_group(actor=self.guest, group_id=group.pk)
        s.lift_ban(actor=self.owner, ban_id=ban.pk)
        s.join_group(actor=self.guest, group_id=group.pk)
        self.assertEqual(GroupBan.objects.get().lifted_by, self.owner)
        self.assertTrue(Notification.objects.filter(kind="member_removed").exists())
        self.assertTrue(Notification.objects.filter(kind="member_banned").exists())

    def test_owner_cannot_be_banned_and_outsider_cannot_manage(self):
        group = self.make_group()
        with self.assertRaises(ValidationError):
            s.remove_member(actor=self.owner, group_id=group.pk, user_id=self.owner.pk, ban=True)
        with self.assertRaises(PermissionDenied):
            s.remove_member(actor=self.guest, group_id=group.pk, user_id=self.other.pk, ban=True)

    def test_join_cutoff_creation_requests_and_offer_acceptance(self):
        group = self.make_group(mode="approval_required")
        request = s.request_join(actor=self.guest, group_id=group.pk)
        s.review_request(actor=self.owner, request_id=request.pk, approve=True)
        boundary = self.event.starts_at
        with patch("groups.services.timezone.now", return_value=boundary):
            with self.assertRaises(ValidationError):
                s.accept_offer(actor=self.guest, request_id=request.pk)
            with self.assertRaises(ValidationError):
                s.request_join(actor=self.other, group_id=group.pk)
            with self.assertRaises(ValidationError):
                self.make_group(actor=self.other)
            self.assertEqual(s.post_message(actor=self.owner, group_id=group.pk, body="I am here").body, "I am here")

    def test_cancellation_blocks_new_participation_keeps_messages(self):
        group = self.make_group()
        discovery.save_event(actor=self.owner, event_id=self.event.pk, data={},
            category_ids=self.event.categories.values_list("id", flat=True), cancelled=True)
        with self.assertRaises(ValidationError):
            s.join_group(actor=self.guest, group_id=group.pk)
        message = s.post_message(actor=self.owner, group_id=group.pk, body="Cancelled; contact me")
        self.assertEqual(s.messages(actor=self.owner, group_id=group.pk).get(), message)

    def test_messages_author_edit_delete_and_admin_removal(self):
        group = self.make_group()
        s.join_group(actor=self.guest, group_id=group.pk)
        message = s.post_message(actor=self.guest, group_id=group.pk, body="WhatsApp link later")
        with self.assertRaises(PermissionDenied):
            s.edit_message(actor=self.owner, message_id=message.pk, body="Rewritten")
        with self.assertRaises(PermissionDenied):
            s.delete_message(actor=self.owner, message_id=message.pk)
        s.edit_message(actor=self.guest, message_id=message.pk, body="Corrected")
        message.refresh_from_db()
        self.assertIsNotNone(message.edited_at)
        s.delete_message(actor=self.admin, message_id=message.pk)
        message.refresh_from_db()
        self.assertEqual(message.body, "")
        self.assertEqual(message.deleted_by, self.admin)

    def test_former_member_loses_message_access_but_history_remains(self):
        group = self.make_group()
        s.join_group(actor=self.guest, group_id=group.pk)
        message = s.post_message(actor=self.guest, group_id=group.pk, body="Hello")
        s.leave_group(actor=self.guest, group_id=group.pk)
        with self.assertRaises(PermissionDenied):
            s.messages(actor=self.guest, group_id=group.pk)
        with self.assertRaises(PermissionDenied):
            s.edit_message(actor=self.guest, message_id=message.pk, body="Changed")
        self.assertEqual(Message.objects.get().body, "Hello")

    def test_message_and_group_description_limits(self):
        group = self.make_group()
        for body in ["", "   ", "a" * 4001]:
            with self.assertRaises(ValidationError):
                s.post_message(actor=self.owner, group_id=group.pk, body=body)
        with self.assertRaises(ValidationError):
            s.save_group(actor=self.owner, group_id=group.pk, data={"description": "a" * 2001})

    def test_admin_only_populated_group_deletion(self):
        group = self.make_group()
        with self.assertRaises(PermissionDenied):
            s.delete_group(actor=self.owner, group_id=group.pk)
        s.delete_group(actor=self.admin, group_id=group.pk)
        self.assertFalse(Membership.objects.exists())
        self.assertTrue(self.event.__class__.objects.filter(pk=self.event.pk).exists())

    def test_photo_reencoded_resized_metadata_removed_and_replacement_cleaned(self):
        group = self.make_group(photo=self.photo())
        original = Path(group.photo.path)
        with Image.open(original) as image:
            self.assertEqual(image.size, (1600, 800))
            self.assertEqual(image.format, "JPEG")
            self.assertFalse(image.getexif())
        with self.captureOnCommitCallbacks(execute=True):
            group = s.save_group(actor=self.owner, group_id=group.pk, data={}, photo=self.photo(size=(100, 100)))
        self.assertFalse(original.exists())
        self.assertTrue(Path(group.photo.path).exists())
        with self.captureOnCommitCallbacks(execute=True):
            s.leave_group(actor=self.owner, group_id=group.pk)
        self.assertFalse(list(Path(self.media_dir.name).rglob("*.jpg")))

    def test_invalid_photo_and_size_do_not_create_group(self):
        uploads = [SimpleUploadedFile("x.png", b"not an image"), self.photo(name="x.svg"),
                   SimpleUploadedFile("x.jpg", b"x"*(5*1024*1024+1))]
        for upload in uploads:
            with self.subTest(name=upload.name), self.assertRaises(ValidationError):
                self.make_group(photo=upload)
        self.assertFalse(AttendanceGroup.objects.exists())

    def test_failed_photo_database_write_removes_new_file(self):
        with patch("groups.services.Membership.objects.create", side_effect=RuntimeError("DB failed")):
            with self.assertRaises(RuntimeError):
                self.make_group(photo=self.photo())
        self.assertFalse(AttendanceGroup.objects.exists())
        self.assertFalse(list(Path(self.media_dir.name).rglob("*.jpg")))

    def test_discoverable_private_group_does_not_expose_messages(self):
        group = self.make_group(mode="approval_required")
        self.assertEqual(s.visible_groups(event_id=self.event.pk).get(), group)
        with self.assertRaises(PermissionDenied):
            s.messages(actor=self.guest, group_id=group.pk)

    def test_request_cancel_and_offer_owned_by_applicant(self):
        group = self.make_group(mode="approval_required")
        request = s.request_join(actor=self.guest, group_id=group.pk)
        with self.assertRaises(JoinRequest.DoesNotExist):
            s.cancel_request(actor=self.other, request_id=request.pk)
        s.cancel_request(actor=self.guest, request_id=request.pk)
        request.refresh_from_db()
        self.assertEqual(request.status, "cancelled")

    def test_admin_disband_and_message_moderation_actions(self):
        group = self.make_group()
        message = s.post_message(actor=self.owner, group_id=group.pk, body="Remove me")
        self.client.force_login(self.admin)
        response = self.client.post("/admin/groups/message/", {
            "action": "remove_content", "_selected_action": [message.pk], "index": 0,
        })
        self.assertEqual(response.status_code, 302)
        message.refresh_from_db()
        self.assertEqual(message.body, "")
        response = self.client.post(f"/admin/groups/attendancegroup/{group.pk}/delete/", {"post": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(AttendanceGroup.objects.exists())


class ConcurrentMembershipTests(TransactionTestCase):
    """Separate SQLite connections must not overfill or double-join on a race."""
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("admin", password="example-password")
        self.first_owner = get_user_model().objects.create_user("first_owner")
        self.second_owner = get_user_model().objects.create_user("second_owner")
        self.guest = get_user_model().objects.create_user("guest")
        self.other = get_user_model().objects.create_user("other")
        category = discovery.save_category(actor=self.admin, data={"name": "House", "color": "#0000FF", "description": "Music"})
        venue = discovery.save_venue(actor=self.admin, review_status="approved", data={"name": "Venue", "latitude": 48, "longitude": 2, "timezone": "UTC"})
        self.event = discovery.save_event(actor=self.first_owner, category_ids=[category.pk], data={
            "venue": venue, "title": "Event", "description": "Music",
            "starts_at": timezone.now()+timedelta(days=1), "ends_at": timezone.now()+timedelta(days=2),
        })

    def group(self, owner, capacity=3):
        return s.save_group(actor=owner, data={"event": self.event, "name": "Company", "description": "Meet",
            "capacity": capacity, "joining_mode": "public"})

    def race(self, attempts):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections, OperationalError
        gate = Barrier(len(attempts))

        def worker(attempt):
            actor, group = attempt
            try:
                gate.wait(timeout=10)
                s.join_group(actor=actor, group_id=group.pk)
                return "joined"
            except (ValidationError, OperationalError):
                # SQLite may reject a competing writer; it must never partly join.
                return "rejected"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(attempts)) as executor:
            return list(executor.map(worker, attempts))

    def test_simultaneous_joins_keep_one_group_per_event(self):
        first, second = self.group(self.first_owner), self.group(self.second_owner)
        outcomes = self.race([(self.guest, first), (self.guest, second)])
        self.assertEqual(outcomes.count("joined"), 1)
        self.assertEqual(Membership.objects.filter(user=self.guest, group__event=self.event).count(), 1)

    def test_simultaneous_joins_do_not_overfill(self):
        group = self.group(self.first_owner, capacity=2)
        outcomes = self.race([(self.guest, group), (self.other, group)])
        self.assertEqual(outcomes.count("joined"), 1)
        self.assertEqual(group.memberships.count(), 2)
