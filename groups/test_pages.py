"""Rendering of the restyled group pages: list, detail/conversation, requests."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from discovery import models as dm, services as ds
from groups import services as gs


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class GroupPageTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", password="Test-password-492!", display_name="Olive Owner")
        self.alex = User.objects.create_user("alex", password="Test-password-492!", display_name="Alex")
        self.outsider = User.objects.create_user("outsider", password="Test-password-492!")
        category = dm.GenreCategory.objects.create(name="House", color="#0066ff", description="House", bpm_min=115, bpm_max=130)
        venue = dm.Venue.objects.create(name="Club", latitude=40.4, longitude=-3.7, timezone="Europe/Madrid",
                                        submitted_by=self.owner, review_status="approved")
        start = timezone.now() + timedelta(days=4)
        self.event = ds.save_event(actor=self.owner, data={"venue": venue, "title": "House night", "description": "x",
                                                            "starts_at": start, "ends_at": start + timedelta(hours=5)},
                                   category_ids=[category.pk])
        self.group = gs.save_group(actor=self.owner, data={"event": self.event, "name": "Night Owls", "capacity": 4,
                                                           "joining_mode": "public", "description": "Meet at the door."})
        gs.join_group(actor=self.alex, group_id=self.group.pk)
        self.first = gs.post_message(actor=self.owner, group_id=self.group.pk, body="Hello\nsecond line")
        self.mine = gs.post_message(actor=self.alex, group_id=self.group.pk, body="Hi all")
        removed = gs.post_message(actor=self.alex, group_id=self.group.pk, body="oops")
        gs.delete_message(actor=self.alex, message_id=removed.pk)

    def page(self, user, path):
        if user:
            self.client.force_login(user)
        return self.client.get(path)

    def test_conversation_is_a_styled_board_with_roles_and_own_messages(self):
        page = self.page(self.alex, f"/groups/{self.group.pk}/")
        html = page.content.decode()
        self.assertContains(page, "grp-hero")
        self.assertContains(page, "2/4</span> members")
        self.assertContains(page, "grp-messages")
        self.assertContains(page, "grp-composer")
        self.assertContains(page, "<h2 id=\"board-heading\">Chat</h2>")
        self.assertContains(page, ">Send</button>")
        self.assertNotContains(page, "Post message")
        self.assertNotContains(page, "Message board")
        self.assertContains(page, 'placeholder="Write a message')
        self.assertEqual(html.count("grp-msg--mine"), 2)       # Alex's own live and removed messages
        self.assertContains(page, "grp-bubble--removed")
        self.assertContains(page, "Message removed.")
        self.assertContains(page, "Hello<br>second line")
        self.assertContains(page, '<span class="grp-badge">Owner</span>', count=2)  # the owner's message and the member row
        self.assertContains(page, "Leave group")
        self.assertNotContains(page, 'class="grp-manage"')     # members cannot moderate
        self.assertContains(page, f"/messages/{self.mine.pk}/edit/")
        self.assertNotContains(page, f"/messages/{self.first.pk}/edit/")

    def test_non_members_see_a_locked_board_and_no_member_list(self):
        page = self.page(self.outsider, f"/groups/{self.group.pk}/")
        self.assertContains(page, "grp-locked")
        self.assertContains(page, "Only current members can read or post messages.")
        self.assertContains(page, "Join group")
        self.assertNotContains(page, "Hello")
        self.assertNotContains(page, 'id="grp-members"')
        self.assertNotContains(page, 'class="grp-composer"')
        self.client.logout()
        self.assertContains(self.client.get(f"/groups/{self.group.pk}/"), "Log in to join")

    def test_owner_gets_management_controls(self):
        page = self.page(self.owner, f"/groups/{self.group.pk}/")
        self.assertContains(page, "Edit group")
        self.assertContains(page, "Requests and bans")
        self.assertContains(page, 'class="grp-manage"', count=1)  # one menu, for the single other member
        self.assertContains(page, f"/groups/{self.group.pk}/members/{self.alex.pk}/ban/")
        self.assertNotContains(page, f"/groups/{self.group.pk}/members/{self.owner.pk}/ban/")

    def test_my_groups_cards_requests_and_empty_states(self):
        private = gs.save_group(actor=self.outsider, data={"event": self.event, "name": "Quiet Corner", "capacity": 3,
                                                           "joining_mode": "approval_required", "description": "Small."})
        request = gs.request_join(actor=self.alex, group_id=private.pk)
        gs.review_request(actor=self.outsider, request_id=request.pk, approve=True)
        page = self.page(self.alex, "/groups/")
        self.assertContains(page, "grp-card")
        self.assertContains(page, "Night Owls")
        self.assertContains(page, "House night")
        self.assertContains(page, "2 of 4 joined")
        self.assertContains(page, "Open to accept")
        self.assertContains(page, "grp-status--approved")
        self.assertContains(page, "Quiet Corner")
        owner_page = self.page(self.owner, "/groups/")
        self.assertContains(owner_page, '<span class="grp-badge grp-card-role">Owner</span>')
        self.client.logout()
        newcomer = get_user_model().objects.create_user("newcomer", password="Test-password-492!")
        empty = self.page(newcomer, "/groups/")
        self.assertContains(empty, "No group memberships yet.")
        self.assertContains(empty, "No requests yet.")
        self.assertContains(empty, "Find an event")

    def test_requests_page_lists_pending_requests_with_actions(self):
        private = gs.save_group(actor=self.outsider, data={"event": self.event, "name": "Quiet Corner", "capacity": 3,
                                                           "joining_mode": "approval_required", "description": "Small."})
        gs.request_join(actor=self.alex, group_id=private.pk)
        page = self.page(self.outsider, f"/groups/{private.pk}/requests/")
        self.assertContains(page, "grp-req")
        self.assertContains(page, "grp-status--pending")
        self.assertContains(page, "Approve offer")
        self.assertContains(page, "Decline")
        self.assertContains(page, "No active bans.")
        self.assertEqual(self.page(self.alex, f"/groups/{private.pk}/requests/").status_code, 403)

    def test_back_arrows_cannot_bounce_between_a_group_and_its_subpages(self):
        # The group page must not "go back" into its own requests/edit/new pages, and the requests page
        # must use browser history instead of adding a new entry that points back at the group.
        group_page = self.page(self.owner, f"/groups/{self.group.pk}/").content.decode()
        self.assertIn("data-back-link", group_page)
        self.assertIn('data-back-avoid="/(requests|edit|new)/$"', group_page)
        requests_page = self.page(self.owner, f"/groups/{self.group.pk}/requests/").content.decode()
        self.assertIn("data-back-link", requests_page)
        script = open("static/browse.js", encoding="utf-8").read()
        self.assertIn("referrer.pathname===location.pathname", script)
        self.assertIn("backAvoid", script)

    def test_composer_is_flat_with_a_character_counter_and_no_enter_to_send(self):
        page = self.page(self.alex, f"/groups/{self.group.pk}/")
        html = page.content.decode()
        self.assertContains(page, "<span data-count>0</span>/4000 characters")
        self.assertContains(page, "grp-composer-row")
        self.assertContains(page, 'rows="1"')
        self.assertNotContains(page, "Enter to send")
        self.assertNotContains(page, "Shift+Enter")
        self.assertNotIn("event.key==='Enter'", html)
        self.assertNotContains(page, "Ownership transfers")

    def test_groups_page_title_has_the_discover_masthead_and_no_subtitle(self):
        page = self.page(self.alex, "/groups/")
        self.assertContains(page, '<header class="discover-masthead"><h1>Groups</h1></header>')
        self.assertNotContains(page, "A little company")


class RequestsSplitTests(TestCase):
    """The Groups page separates requests you sent from requests other people sent to your groups."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        self.User = get_user_model()
        self.owner = self.User.objects.create_user("owner", password="x", display_name="Olive")
        self.guest = self.User.objects.create_user("guest", password="x", display_name="Gus")

    def make_group(self):
        from datetime import timedelta
        from django.utils import timezone
        from discovery import models as dm
        from groups.models import AttendanceGroup, Membership
        category = dm.GenreCategory.objects.create(name="House", color="#0066ff", description="House", bpm_min=115, bpm_max=130)
        venue = dm.Venue.objects.create(name="Club", latitude=40.4, longitude=-3.7, timezone="Europe/Madrid",
                                        submitted_by=self.owner, review_status="approved")
        event = dm.Event.objects.create(creator=self.owner, venue=venue, title="Night", description="x",
                                        starts_at=timezone.now() + timedelta(days=2), ends_at=timezone.now() + timedelta(days=2, hours=5))
        event.categories.add(category)
        group = AttendanceGroup.objects.create(event=event, owner=self.owner, name="Front row", description="x", capacity=4,
                                               joining_mode="approval_required")
        Membership.objects.create(group=group, user=self.owner)
        return group

    def test_group_owner_sees_received_requests_and_everyone_keeps_sent_ones(self):
        from groups.models import JoinRequest
        group = self.make_group()
        JoinRequest.objects.create(group=group, applicant=self.guest)
        self.client.force_login(self.owner)
        page = self.client.get("/groups/")
        for text in ("Sent", "Received", "Gus", "Review →", "Front row"):
            self.assertContains(page, text)
        self.assertNotContains(page, "Groups you&#x27;ve joined")
        self.assertNotContains(page, "Requests to join other groups")
        self.client.force_login(self.guest)
        page = self.client.get("/groups/")
        self.assertContains(page, "Sent")
        self.assertContains(page, "Pending")
        self.assertContains(page, "Received")                      # the tab is always there
        self.assertContains(page, "No requests to review.")
        self.assertNotContains(page, "Review →")

    def test_sent_requests_show_the_group_photo_when_there_is_one(self):
        from groups.models import JoinRequest
        group = self.make_group()
        group.photo = "groups/example.jpg"
        group.save(update_fields=["photo"])
        JoinRequest.objects.create(group=group, applicant=self.guest)
        self.client.force_login(self.guest)
        page = self.client.get("/groups/")
        self.assertContains(page, f'<img src="/groups/{group.pk}/photo/"')

    def test_requests_button_shows_a_dot_with_the_pending_count_and_pictures_show_on_the_requests_page(self):
        from groups.models import JoinRequest
        group = self.make_group()
        self.client.force_login(self.owner)
        self.assertNotContains(self.client.get(f"/groups/{group.pk}/"), "notify-dot")
        self.guest.avatar = "avatars/example.jpg"
        self.guest.save(update_fields=["avatar"])
        JoinRequest.objects.create(group=group, applicant=self.guest)
        page = self.client.get(f"/groups/{group.pk}/")
        self.assertContains(page, 'class="notify-dot"')
        self.assertContains(page, "1 pending request")
        self.client.force_login(self.guest)
        self.assertNotContains(self.client.get(f"/groups/{group.pk}/"), "notify-dot")           # only the people who manage it see it
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(f"/groups/{group.pk}/requests/"), f'<img src="/accounts/avatar/{self.guest.pk}/"')


@override_settings(MEDIA_ROOT=__import__("tempfile").mkdtemp())
class GroupPhotoKeepTests(TestCase):
    def test_group_form_has_no_remove_photo_option_and_keeps_the_photo_on_save(self):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        owner = get_user_model().objects.create_user("phot", password="x")
        category = dm.GenreCategory.objects.create(name="House", color="#0066ff", description="x", bpm_min=1, bpm_max=2)
        venue = dm.Venue.objects.create(name="C", latitude=1, longitude=1, timezone="Europe/Madrid", submitted_by=owner, review_status="approved")
        start = timezone.now() + timedelta(days=2)
        event = ds.save_event(actor=owner, data={"venue": venue, "title": "N", "description": "x", "starts_at": start, "ends_at": start + timedelta(hours=4)}, category_ids=[category.pk])
        self.client.force_login(owner)
        buffer = BytesIO()
        Image.new("RGB", (80, 60), "teal").save(buffer, "PNG")
        data = {"name": "G", "description": "x", "capacity": 4, "joining_mode": "public",
                "photo": SimpleUploadedFile("p.png", buffer.getvalue(), content_type="image/png")}
        self.assertEqual(self.client.post(f"/events/{event.pk}/groups/new/", data).status_code, 302)
        group = __import__("groups.models", fromlist=["x"]).AttendanceGroup.objects.get(name="G")
        self.assertTrue(group.photo)
        page = self.client.get(f"/groups/{group.pk}/edit/")
        self.assertNotContains(page, "remove_photo")
        self.assertContains(page, f'data-current-src="/groups/{group.pk}/photo/"')
        self.assertEqual(self.client.post(f"/groups/{group.pk}/edit/", {"name": "G2", "description": "x", "capacity": 4, "joining_mode": "public"}).status_code, 302)
        group.refresh_from_db()
        self.assertTrue(group.photo)                      # saving without a file keeps it


