"""Chat notices ("X has left the group") and live updates."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from discovery import models as dm, services as ds
from groups import models as gm, services as gs


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ChatLiveTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", password="Test-password-492!", display_name="Olive")
        self.alex = User.objects.create_user("alex", password="Test-password-492!", display_name="Alex")
        self.jo = User.objects.create_user("jo", password="Test-password-492!", display_name="Jo")
        self.outsider = User.objects.create_user("outsider", password="Test-password-492!")
        category = dm.GenreCategory.objects.create(name="House", color="#0066ff", description="House", bpm_min=115, bpm_max=130)
        venue = dm.Venue.objects.create(name="Club", latitude=40.4, longitude=-3.7, timezone="Europe/Madrid",
                                        submitted_by=self.owner, review_status="approved")
        start = timezone.now() + timedelta(days=4)
        self.event = ds.save_event(actor=self.owner, data={"venue": venue, "title": "House night", "description": "x",
                                                            "starts_at": start, "ends_at": start + timedelta(hours=5)},
                                   category_ids=[category.pk])
        self.group = gs.save_group(actor=self.owner, data={"event": self.event, "name": "Night Owls", "capacity": 5,
                                                           "joining_mode": "public", "description": "Meet."})
        gs.join_group(actor=self.alex, group_id=self.group.pk)
        gs.join_group(actor=self.jo, group_id=self.group.pk)

    def texts(self):
        return [notice.text for notice in self.group.notices.exclude(kind="joined")]

    def test_leaving_is_announced_and_an_owner_leaving_also_promotes_the_next_member(self):
        gs.post_message(actor=self.alex, group_id=self.group.pk, body="before")
        gs.leave_group(actor=self.alex, group_id=self.group.pk)
        gs.post_message(actor=self.jo, group_id=self.group.pk, body="after")
        self.assertEqual(self.texts(), ["Alex has left the group"])
        gs.leave_group(actor=self.owner, group_id=self.group.pk)
        self.assertEqual(self.texts(), ["Alex has left the group", "Olive has left the group", "Jo was promoted to owner"])
        self.client.force_login(self.jo)
        html = self.client.get(f"/groups/{self.group.pk}/").content.decode()
        order = [html.index(text) for text in ("before", "Alex has left the group", "after", "Olive has left the group", "Jo was promoted to owner")]
        self.assertEqual(order, sorted(order))
        self.assertIn('class="grp-notice"', html)

    def test_removal_and_ban_are_silent(self):
        gs.remove_member(actor=self.owner, group_id=self.group.pk, user_id=self.alex.pk)
        gs.remove_member(actor=self.owner, group_id=self.group.pk, user_id=self.jo.pk, ban=True, reason="x")
        self.assertEqual(self.texts(), [])

    def test_switching_to_another_group_announces_departure_in_the_old_one(self):
        other = gs.save_group(actor=self.outsider, data={"event": self.event, "name": "Other", "capacity": 4,
                                                         "joining_mode": "public", "description": "Other."})
        gs.join_group(actor=self.alex, group_id=other.pk, confirm_switch=True)
        self.assertEqual(self.texts(), ["Alex has left the group"])
        self.assertEqual(other.notices.exclude(kind="joined").count(), 0)

    def test_notices_disappear_with_the_group_and_never_show_to_non_members(self):
        gs.leave_group(actor=self.alex, group_id=self.group.pk)
        self.client.force_login(self.outsider)
        self.assertNotContains(self.client.get(f"/groups/{self.group.pk}/"), "has left the group")
        gs.leave_group(actor=self.jo, group_id=self.group.pk)
        gs.leave_group(actor=self.owner, group_id=self.group.pk)
        self.assertFalse(gm.GroupNotice.objects.exists())

    def test_signature_changes_for_new_edited_and_removed_messages_and_member_changes(self):
        def sig():
            return gs.chat_signature(actor=self.alex, group_id=self.group.pk)
        seen = [sig()]
        message = gs.post_message(actor=self.alex, group_id=self.group.pk, body="one")
        seen.append(sig())
        gs.edit_message(actor=self.alex, message_id=message.pk, body="one!")
        seen.append(sig())
        gs.delete_message(actor=self.alex, message_id=message.pk)
        seen.append(sig())
        gs.join_group(actor=self.outsider, group_id=self.group.pk)
        seen.append(sig())
        gs.leave_group(actor=self.outsider, group_id=self.group.pk)
        seen.append(sig())
        self.assertEqual(len(set(seen)), len(seen))
        self.assertEqual(sig(), sig())
        with self.assertRaises(Exception):
            gs.chat_signature(actor=self.outsider, group_id=self.group.pk)

    def test_live_endpoint_returns_nothing_new_then_fresh_html_only_when_something_changed(self):
        self.client.force_login(self.alex)
        url = f"/groups/{self.group.pk}/chat/"
        first = self.client.get(url).json()
        self.assertTrue(first["changed"])
        self.assertIn("has joined the group", first["chat"])
        self.assertIn("Members", first["members"])
        self.assertEqual(self.client.get(url, {"sig": first["sig"]}).json(), {"changed": False, "sig": first["sig"]})

        gs.post_message(actor=self.jo, group_id=self.group.pk, body="hello <b>there</b>")
        second = self.client.get(url, {"sig": first["sig"]}).json()
        self.assertTrue(second["changed"])
        self.assertIn("hello &lt;b&gt;there&lt;/b&gt;", second["chat"])      # escaped, never raw HTML
        self.assertNotEqual(second["sig"], first["sig"])
        self.assertEqual(second["count"], 3)
        self.assertIn("no-store", self.client.get(url).get("Cache-Control", ""))

        gs.leave_group(actor=self.jo, group_id=self.group.pk)
        third = self.client.get(url, {"sig": second["sig"]}).json()
        self.assertTrue(third["changed"])
        self.assertIn("Jo has left the group", third["chat"])
        self.assertEqual(third["count"], 2)

    def test_live_endpoint_is_for_members_only(self):
        url = f"/groups/{self.group.pk}/chat/"
        self.assertEqual(self.client.get(url).status_code, 302)                    # signed out: to login
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(self.client.get("/groups/999999/chat/").status_code, 404)

    def test_page_exposes_the_live_feed_and_sends_in_the_background(self):
        self.client.force_login(self.alex)
        page = self.client.get(f"/groups/{self.group.pk}/")
        self.assertContains(page, f'data-feed="/groups/{self.group.pk}/chat/"')
        self.assertContains(page, 'data-live="1"')
        self.assertContains(page, "grp-new")
        self.assertContains(page, "New messages")
        self.assertContains(page, "setInterval(poll,3000)")
        self.assertContains(page, "new FormData(form)")
        # an older page of messages is not live
        for index in range(31):
            gs.post_message(actor=self.alex, group_id=self.group.pk, body=f"m{index}")
        self.assertContains(self.client.get(f"/groups/{self.group.pk}/?page=1"), 'data-live="0"')
        self.assertContains(self.client.get(f"/groups/{self.group.pk}/"), 'data-live="1"')


class JoinNoticeTests(TestCase):
    def test_joining_adds_a_grey_notice_like_leaving_does(self):
        from groups.models import GroupNotice
        owner = get_user_model().objects.create_user("own", password="x", display_name="Olive")
        guest = get_user_model().objects.create_user("gst", password="x", display_name="Gus")
        category = dm.GenreCategory.objects.create(name="House", color="#0066ff", description="x", bpm_min=1, bpm_max=2)
        venue = dm.Venue.objects.create(name="C", latitude=1, longitude=1, timezone="Europe/Madrid", submitted_by=owner, review_status="approved")
        start = timezone.now() + timedelta(days=2)
        event = ds.save_event(actor=owner, data={"venue": venue, "title": "N", "description": "x", "starts_at": start, "ends_at": start + timedelta(hours=4)}, category_ids=[category.pk])
        group = gs.save_group(actor=owner, data={"event": event, "name": "G", "description": "x", "capacity": 4, "joining_mode": "public"})
        gs.join_group(actor=guest, group_id=group.pk)
        self.assertEqual([n.text for n in GroupNotice.objects.filter(group=group, kind="joined")], ["Gus has joined the group"])
        self.client.force_login(guest)
        self.assertContains(self.client.get(f"/groups/{group.pk}/"), "Gus has joined the group")


class JoinConfirmAndHistoryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("own2", password="x")
        self.guest = User.objects.create_user("gst2", password="x", display_name="Gus")
        category = dm.GenreCategory.objects.create(name="House", color="#0066ff", description="x", bpm_min=1, bpm_max=2)
        venue = dm.Venue.objects.create(name="C", latitude=1, longitude=1, timezone="Europe/Madrid", submitted_by=self.owner, review_status="approved")
        start = timezone.now() + timedelta(days=2)
        self.event = ds.save_event(actor=self.owner, data={"venue": venue, "title": "Night", "description": "x", "starts_at": start,
                                                           "ends_at": start + timedelta(hours=4)}, category_ids=[category.pk])
        self.owner2 = User.objects.create_user("own3", password="x")
        mk = lambda who, name: gs.save_group(actor=who, data={"event": self.event, "name": name, "description": "x", "capacity": 4, "joining_mode": "public"})
        self.a, self.b = mk(self.owner, "Alpha"), mk(self.owner2, "Beta")

    def test_join_asks_only_when_already_in_another_group_for_the_event(self):
        self.client.force_login(self.guest)
        free = self.client.get(f"/groups/{self.a.pk}/")
        self.assertNotContains(free, "data-switch-from")
        self.assertNotContains(free, "Leave my current group")
        self.assertContains(free, "Join group")
        gs.join_group(actor=self.guest, group_id=self.a.pk)
        page = self.client.get(f"/groups/{self.b.pk}/")
        self.assertContains(page, 'data-switch-from="Alpha"')
        self.assertNotContains(page, "Leave my current group")
        # the server still refuses a switch that was not confirmed
        self.assertEqual(self.client.post(f"/groups/{self.b.pk}/join/", {}).status_code, 400)
        self.assertEqual(self.client.post(f"/groups/{self.b.pk}/join/", {"confirm_switch": "on"}).status_code, 302)

    def test_activity_keeps_leaves_even_when_the_group_is_gone(self):
        from groups.models import GroupHistory
        gs.join_group(actor=self.guest, group_id=self.a.pk)
        gs.leave_group(actor=self.guest, group_id=self.a.pk)
        self.assertEqual([h.kind for h in GroupHistory.objects.filter(user=self.guest).order_by("id")], ["joined", "left"])
        gs.leave_group(actor=self.owner, group_id=self.a.pk)                 # last member: the group is deleted
        self.client.force_login(self.guest)
        page = self.client.get("/my-activity/")
        for text in ("Joined a group", "Left a group", "Alpha"):
            self.assertContains(page, text)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get("/my-activity/"), "Created a group")


class AvatarEverywhereTests(TestCase):
    def test_a_uploaded_picture_shows_wherever_a_person_is_listed(self):
        User = get_user_model()
        owner = User.objects.create_user("avo", password="x")
        member = User.objects.create_user("avm", password="x", display_name="Pic Person")
        member.avatar = "avatars/example.jpg"
        member.save(update_fields=["avatar"])
        category = dm.GenreCategory.objects.create(name="House", color="#0066ff", description="x", bpm_min=1, bpm_max=2)
        venue = dm.Venue.objects.create(name="C", latitude=1, longitude=1, timezone="Europe/Madrid", submitted_by=owner, review_status="approved")
        start = timezone.now() + timedelta(days=2)
        event = ds.save_event(actor=owner, data={"venue": venue, "title": "N", "description": "x", "starts_at": start, "ends_at": start + timedelta(hours=4)}, category_ids=[category.pk])
        group = gs.save_group(actor=owner, data={"event": event, "name": "G", "description": "x", "capacity": 4, "joining_mode": "public"})
        gs.join_group(actor=member, group_id=group.pk)
        gs.post_message(actor=member, group_id=group.pk, body="hello")
        self.client.force_login(owner)
        mark = f'<img src="/accounts/avatar/{member.pk}/"'
        page = self.client.get(f"/groups/{group.pk}/")
        self.assertContains(page, mark, count=2)                      # in the members list and next to the message
        self.assertIn(mark, self.client.get(f"/groups/{group.pk}/chat/").json()["members"])   # the live update carries it too
