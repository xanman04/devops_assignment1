"""HTTP integration checks for permissions, form/service boundaries and privacy."""
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from discovery import models as dm, services as ds
from groups import models as gm, services as gs
from notifications.models import Notification


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class WebTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        User = get_user_model()
        self.owner = User.objects.create_user('owner', password='Test-password-492!', display_name='Music owner', email='private-owner@example.org')
        self.guest = User.objects.create_user('guest', password='Test-password-492!', email='private-guest@example.org')
        self.other = User.objects.create_user('other', password='Test-password-492!')
        self.category = dm.GenreCategory.objects.create(name='House', description='House music', color='#0066ff', bpm_min=115, bpm_max=130)
        self.tag = dm.GenreTag.objects.create(category=self.category, name='Afrohouse', description='Example')
        self.venue = dm.Venue.objects.create(name='Approved venue', latitude=48.85, longitude=2.35, address='Public address', timezone='Europe/Paris', submitted_by=self.owner, review_status='approved')
        self.pending = dm.Venue.objects.create(name='Secret venue', latitude=47.123456, longitude=3.654321, address='Private proposed address', timezone='Europe/Paris', submitted_by=self.other)
        self.event = ds.save_event(actor=self.owner, data={'venue':self.venue,'title':'House night','description':'Music-first event','starts_at':timezone.now()+timedelta(days=3),'ends_at':timezone.now()+timedelta(days=3,hours=5)}, category_ids=[self.category.pk], tag_ids=[self.tag.pk])
        self.group = gs.save_group(actor=self.owner, data={'event':self.event,'name':'Solo crew','description':'Meet up','capacity':4,'joining_mode':'public'})

    def login(self, user=None):
        self.client.force_login(user or self.owner)

    def event_data(self, **changes):
        data = {'venue':self.venue.pk,'title':'Another night','description':'Test event',
                'starts_at_0':'2026-10-02','starts_at_1':'21:00:00','ends_at_0':'2026-10-03','ends_at_1':'03:00:00',
                'categories':[self.category.pk],'tags':[self.tag.pk], 'ticket_url':''}
        return {**data, **changes}

    def poster_upload(self, color='purple'):
        image = BytesIO()
        Image.new('RGB', (80, 120), color).save(image, 'PNG')
        return SimpleUploadedFile('night.png', image.getvalue(), content_type='image/png')

    def test_event_poster_upload_replacement_removal_and_visibility(self):
        self.login()
        self.assertContains(self.client.get('/events/new/'), 'Event poster')
        response = self.client.post('/events/new/', self.event_data(poster_upload=self.poster_upload()))
        self.assertEqual(response.status_code, 302)
        event = dm.Event.objects.get(title='Another night')
        self.assertTrue(event.poster.name.startswith('events/'))
        self.assertTrue(event.poster.name.endswith('.jpg'))
        self.assertContains(self.client.get(f'/events/{event.pk}/'), f'/events/{event.pk}/poster/')
        self.assertContains(self.client.get('/discover/'), f'/events/{event.pk}/poster/')
        poster = self.client.get(f'/events/{event.pk}/poster/')
        self.assertEqual(poster['Content-Type'], 'image/jpeg')
        self.assertEqual(poster['Cache-Control'], 'private, no-store')
        self.assertEqual(Image.open(BytesIO(b''.join(poster.streaming_content))).format, 'JPEG')
        poster.close()
        first_path = event.poster.path
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(f'/events/{event.pk}/edit/',
                self.event_data(poster_upload=self.poster_upload('green'))).status_code, 302)
        event.refresh_from_db()
        self.assertNotEqual(event.poster.path, first_path)
        self.assertFalse(Path(first_path).exists())
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(f'/events/{event.pk}/edit/',
                self.event_data(remove_poster='on')).status_code, 302)
        event.refresh_from_db()
        self.assertFalse(event.poster)
        self.assertEqual(self.client.get(f'/events/{event.pk}/poster/').status_code, 404)

        pending_event = ds.save_event(actor=self.other, data={'venue': self.pending,
            'title': 'Pending night', 'description': 'Private until review',
            'starts_at': timezone.now() + timedelta(days=2),
            'ends_at': timezone.now() + timedelta(days=2, hours=2)},
            category_ids=[self.category.pk], poster=self.poster_upload())
        self.client.logout()
        self.assertEqual(self.client.get(f'/events/{pending_event.pk}/poster/').status_code, 404)
        self.login(self.other)
        private_poster = self.client.get(f'/events/{pending_event.pk}/poster/')
        self.assertEqual(private_poster.status_code, 200)
        private_poster.close()

    def test_invalid_event_poster_does_not_change_listing(self):
        self.login()
        response = self.client.post(f'/events/{self.event.pk}/edit/', self.event_data(
            title='Should not save', poster_upload=SimpleUploadedFile('bad.png', b'not an image')))
        self.assertEqual(response.status_code, 400)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, 'House night')
        self.assertFalse(self.event.poster)

    def test_admin_event_form_accepts_poster_upload(self):
        admin = get_user_model().objects.create_superuser('posteradmin', password='Test-password-492!')
        self.login(admin)
        add_page = self.client.get('/admin/discovery/event/add/')
        self.assertContains(add_page, 'Event poster')
        self.assertContains(add_page, 'name="poster_upload"')
        self.assertNotContains(add_page, 'name="poster"')
        response = self.client.post('/admin/discovery/event/add/',
            self.event_data(title='Admin poster night', poster_upload=self.poster_upload(), _save='Save'))
        self.assertEqual(response.status_code, 302)
        event = dm.Event.objects.get(title='Admin poster night')
        self.assertTrue(event.poster)
        self.assertContains(self.client.get(f'/admin/discovery/event/{event.pk}/change/'), 'Remove current poster')

    def test_public_pages_render_without_account_or_private_email(self):
        for url in ['/', '/genres/', f'/genres/{self.category.pk}/', f'/events/{self.event.pk}/', f'/groups/{self.group.pk}/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertNotContains(response, self.owner.email)
            self.assertNotContains(response, self.guest.email)

    def test_live_browsing_uses_public_records_and_curated_music(self):
        dm.GenreListeningReference.objects.create(title='A curated mix', artist_credit='Example DJ',
            url='https://example.org/mix', kind='set')
        response = self.client.get('/discover/')
        self.assertContains(response, 'House night')
        self.assertContains(response, 'House')
        self.assertContains(response, 'Example DJ')
        self.assertNotContains(response, 'Secret venue')
        self.assertContains(self.client.get('/discover/?q=Approved+venue'), 'House night')
        self.event.moderation_hidden = True
        self.event.save(update_fields=['moderation_hidden'])
        self.assertNotContains(self.client.get('/discover/'), 'House night')
        self.assertNotContains(self.client.get('/discover/?q=House'), 'House night')

    def test_my_carousels_require_login_and_hide_unavailable_tracked_events(self):
        self.assertEqual(self.client.get('/my-events/').status_code, 302)
        self.assertEqual(self.client.get('/groups/').status_code, 302)
        ds.follow_event(actor=self.guest, event_id=self.event.pk)
        gm.JoinRequest.objects.create(group=self.group, applicant=self.guest)
        self.login(self.guest)
        self.assertContains(self.client.get('/groups/'), 'Solo crew')
        self.assertContains(self.client.get('/groups/'), 'Pending')
        self.assertContains(self.client.get('/my-events/'), 'House night')
        self.event.moderation_hidden = True
        self.event.save(update_fields=['moderation_hidden'])
        response = self.client.get('/my-events/')
        self.assertContains(response, 'Tracked event unavailable')
        self.assertNotContains(response, 'House night')
        self.login(self.owner)
        self.assertContains(self.client.get('/my-events/'), 'House night')

    def test_registration_ignores_privilege_fields_and_settings_are_private(self):
        response = self.client.post('/accounts/register/', {'username':'newuser','display_name':'New music fan','email':'new-private@example.org','password1':'Valid-passphrase-894!','password2':'Valid-passphrase-894!','is_staff':'on','is_superuser':'on'})
        self.assertRedirects(response, '/my-activity/')
        user = get_user_model().objects.get(username='newuser')
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertContains(self.client.get('/accounts/settings/'), user.email)
        self.assertRedirects(self.client.post('/accounts/settings/', {'display_name':'Changed','email':'updated@example.org','username':'owner'}), '/accounts/settings/')
        user.refresh_from_db()
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'updated@example.org')
        self.assertEqual(self.client.post('/accounts/register/', {}).status_code, 302)

    def test_invalid_registration_keeps_form_and_creates_no_account(self):
        self.assertEqual(self.client.post('/accounts/register/', {'username':'owner','password1':'a','password2':'b'}).status_code, 400)
        self.assertEqual(get_user_model().objects.count(), 3)

    def test_login_logout_and_external_next(self):
        response = self.client.post('/accounts/login/?next=https://example.org/', {'username':'guest','password':'Test-password-492!'})
        self.assertRedirects(response, '/my-activity/')
        self.assertEqual(self.client.get('/accounts/logout/').status_code, 405)
        self.assertRedirects(self.client.post('/accounts/logout/'), '/')
        self.assertEqual(self.client.get('/accounts/settings/').status_code, 302)

    def test_csrf_required_for_account_and_domain_writes(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/accounts/register/', {}).status_code, 403)
        client.force_login(self.owner)
        self.assertEqual(client.post(f'/events/{self.event.pk}/cancel/').status_code, 403)
        client.get(f'/events/{self.event.pk}/')
        self.assertEqual(client.post(f'/events/{self.event.pk}/cancel/', {'csrfmiddlewaretoken':client.cookies['csrftoken'].value}).status_code, 302)

    def test_post_actions_reject_get(self):
        self.login()
        for url in [f'/events/{self.event.pk}/cancel/', f'/events/{self.event.pk}/follow/', f'/events/{self.event.pk}/unfollow/',
                    f'/groups/{self.group.pk}/join/', f'/groups/{self.group.pk}/request/', f'/groups/{self.group.pk}/leave/',
                    f'/groups/{self.group.pk}/messages/new/']:
            self.assertEqual(self.client.get(url).status_code, 405, url)
        self.event.refresh_from_db()
        self.assertIsNone(self.event.cancelled_at)

    def test_event_creation_local_time_and_forged_owner_moderation_ignored(self):
        self.login(self.guest)
        response = self.client.post('/events/new/', self.event_data(creator=self.owner.pk, moderation_hidden='on', bpm_min=999))
        event = dm.Event.objects.get(title='Another night')
        self.assertRedirects(response, f'/events/{event.pk}/')
        self.assertEqual(event.creator_id,self.guest.pk)
        self.assertFalse(event.moderation_hidden)
        self.assertEqual(event.starts_at.hour,19)  # Paris summer time -> UTC
        self.assertEqual(ds.tempo_estimate(event),(115,130))

    def test_venue_choices_and_submission_reject_other_pending_venue(self):
        self.login(self.guest)
        response = self.client.get('/events/new/')
        self.assertNotContains(response, 'Secret venue')
        self.assertEqual(self.client.post('/events/new/', self.event_data(venue=self.pending.pk)).status_code,400)
        self.assertFalse(dm.Event.objects.filter(title='Another night').exists())

    def test_venue_proposal_pending_and_own_pending_event_private(self):
        self.login(self.guest)
        response = self.client.post('/venues/new/', {'name':'Proposed club','address':'Proposal address','latitude':'48.123456','longitude':'2.123456','timezone':'Europe/Paris','review_status':'approved','submitted_by':self.owner.pk})
        self.assertRedirects(response,'/events/new/')
        venue = dm.Venue.objects.get(name='Proposed club')
        self.assertEqual((venue.review_status,venue.submitted_by_id),('pending',self.guest.pk))
        self.assertEqual(self.client.post('/events/new/',self.event_data(venue=venue.pk)).status_code,302)
        event = dm.Event.objects.get(title='Another night')
        self.assertContains(self.client.get(f'/events/{event.pk}/'),'Location pending')
        self.client.logout()
        self.assertEqual(self.client.get(f'/events/{event.pk}/').status_code,404)
        self.assertNotContains(self.client.get('/'),'Proposed club')
        self.assertEqual(self.client.post('/venues/new/',{}).status_code,302)

    def test_invalid_times_tags_and_venue_coordinates_leave_no_partial_rows(self):
        self.login()
        self.assertEqual(self.client.post('/events/new/',self.event_data(ends_at_0='2026-10-01')).status_code,400)
        other = dm.GenreCategory.objects.create(name='Rock',description='Rock',color='#ff0000')
        self.assertEqual(self.client.post('/events/new/',self.event_data(categories=[other.pk])).status_code,400)
        self.assertEqual(self.client.post('/venues/new/',{'name':'Bad','latitude':91,'longitude':0,'timezone':'Wrong/Zone'}).status_code,400)
        self.assertFalse(dm.Event.objects.filter(title='Another night').exists())

    def test_only_creator_can_edit_cancel_and_manage_listening_references(self):
        self.login(self.guest)
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/edit/').status_code,403)
        self.assertEqual(self.client.post(f'/events/{self.event.pk}/cancel/').status_code,403)
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/references/new/').status_code,403)
        self.login()
        response = self.client.post(f'/events/{self.event.pk}/references/new/',{'title':'A set','artist_credit':'An artist','url':'https://example.org/set','kind':'set','display_order':0})
        self.assertEqual(response.status_code,302)
        reference = self.event.listening_references.get()
        self.assertContains(self.client.get(f'/events/{self.event.pk}/'),'A set')
        self.assertEqual(self.client.post(f'/references/{reference.pk}/delete/').status_code,302)

    def test_follow_cancel_inbox_recipient_scope_and_retained_record(self):
        self.login(self.guest)
        self.assertEqual(self.client.post(f'/events/{self.event.pk}/follow/').status_code,302)
        self.login()
        self.assertEqual(self.client.post(f'/events/{self.event.pk}/cancel/').status_code,302)
        notice = Notification.objects.get(recipient=self.guest)
        self.assertEqual(self.client.post(f'/notifications/{notice.pk}/read/').status_code,404)
        self.assertNotContains(self.client.get('/notifications/'),'A tracked event changed')
        self.login(self.guest)
        self.assertContains(self.client.get('/notifications/'),'cancellation status')
        self.assertEqual(self.client.post(f'/notifications/{notice.pk}/read/').status_code,302)
        self.event.refresh_from_db()
        self.assertIsNotNone(self.event.cancelled_at)
        self.assertNotContains(self.client.get('/'),'House night')

    def test_report_sanitizes_ownership_and_ignores_moderation_input(self):
        self.login(self.guest)
        response = self.client.post(f'/events/{self.event.pk}/report/',{'reason':'safety_concern','explanation':'Check this','status':'actioned','reporter':self.owner.pk})
        self.assertEqual(response.status_code,302)
        report = dm.EventReport.objects.get()
        self.assertEqual((report.status,report.reporter_id),('pending',self.guest.pk))
        self.assertEqual(self.client.post(f'/events/{self.event.pk}/report/', {'reason':'bad'}).status_code,400)

    def test_group_creation_settings_and_photos_service_boundary(self):
        self.login(self.guest)
        content=BytesIO(); Image.new('RGB',(50,30),'green').save(content,'PNG')
        response=self.client.post(f'/events/{self.event.pk}/groups/new/',{'name':'Guest crew','description':'Together','capacity':3,'joining_mode':'approval_required','photo':SimpleUploadedFile('photo.png',content.getvalue(),content_type='image/png'),'owner':self.owner.pk,'event':999})
        group=gm.AttendanceGroup.objects.get(name='Guest crew')
        self.assertRedirects(response,f'/groups/{group.pk}/')
        self.assertEqual(group.owner_id,self.guest.pk)
        self.assertTrue(group.memberships.filter(user=self.guest).exists())
        self.assertEqual(group.event_id,self.event.pk)
        response=self.client.get(f'/groups/{group.pk}/photo/')
        self.assertEqual(response['Content-Type'],'image/jpeg')
        self.assertTrue(response.streaming)
        response.close()
        self.assertEqual(self.client.post(f'/events/{self.event.pk}/groups/new/',{'name':'Extra','description':'No','capacity':3,'joining_mode':'public'}).status_code,400)
        self.login(self.other)
        self.assertEqual(self.client.get(f'/groups/{group.pk}/edit/').status_code,403)

    def test_invalid_group_photo_creates_no_group(self):
        self.login(self.guest)
        self.assertEqual(self.client.post(f'/events/{self.event.pk}/groups/new/',{'name':'Bad photo','description':'No','capacity':3,'joining_mode':'public','photo':SimpleUploadedFile('bad.png',b'not an image')}).status_code,400)
        self.assertFalse(gm.AttendanceGroup.objects.filter(name='Bad photo').exists())

    def test_event_edit_changes_categories_and_preserves_admin_hiding(self):
        self.event.moderation_hidden=True; self.event.save()
        rock=dm.GenreCategory.objects.create(name='Rock',description='Rock',color='#ff0000')
        self.login()
        response=self.client.post(f'/events/{self.event.pk}/edit/',self.event_data(title='Rock night',categories=[rock.pk],tags=[],moderation_hidden=''))
        self.assertEqual(response.status_code,302)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title,'Rock night')
        self.assertTrue(self.event.moderation_hidden)
        self.assertEqual(list(self.event.categories.values_list('pk',flat=True)),[rock.pk])
        self.assertFalse(self.event.tags.exists())

    def test_group_settings_keep_event_owner_members_and_enforce_capacity(self):
        gs.join_group(actor=self.guest,group_id=self.group.pk)
        self.login()
        data={'name':'Renamed crew','description':'Still here','capacity':1,'joining_mode':'approval_required','event':999,'owner':self.other.pk}
        self.assertEqual(self.client.post(f'/groups/{self.group.pk}/edit/',data).status_code,400)
        data['capacity']=3
        self.assertEqual(self.client.post(f'/groups/{self.group.pk}/edit/',data).status_code,302)
        self.group.refresh_from_db()
        self.assertEqual((self.group.event_id,self.group.owner_id,self.group.memberships.count()),(self.event.pk,self.owner.pk,2))
        self.assertEqual(self.group.joining_mode,'approval_required')

    def test_private_offer_and_confirmed_switch(self):
        destination=gs.save_group(actor=self.other,data={'event':self.event,'name':'Private crew','description':'Request','capacity':3,'joining_mode':'approval_required'})
        self.login(self.guest)
        self.assertEqual(self.client.post(f'/groups/{self.group.pk}/join/').status_code,302)
        self.assertEqual(self.client.post(f'/groups/{destination.pk}/request/').status_code,302)
        record=destination.join_requests.get()
        self.assertEqual(self.client.get(f'/groups/{destination.pk}/requests/').status_code,403)
        self.login(self.other)
        self.assertContains(self.client.get(f'/groups/{destination.pk}/requests/'),'guest')
        self.assertEqual(self.client.post(f'/requests/{record.pk}/approve/').status_code,302)
        self.login(self.guest)
        self.assertContains(self.client.get(f'/groups/{destination.pk}/'),'Accept offer')
        self.assertEqual(self.client.post(f'/requests/{record.pk}/accept/').status_code,400)
        self.assertTrue(self.group.memberships.filter(user=self.guest).exists())
        self.assertEqual(self.client.post(f'/requests/{record.pk}/accept/',{'confirm_switch':'on'}).status_code,302)
        self.assertFalse(self.group.memberships.filter(user=self.guest).exists())
        self.assertTrue(destination.memberships.filter(user=self.guest).exists())

    def test_owner_cannot_review_or_cancel_another_users_request(self):
        gs.save_group(actor=self.owner,group_id=self.group.pk,data={'joining_mode':'approval_required'})
        record=gs.request_join(actor=self.guest,group_id=self.group.pk)
        self.login(self.other)
        self.assertEqual(self.client.post(f'/requests/{record.pk}/approve/').status_code,403)
        self.assertEqual(self.client.post(f'/requests/{record.pk}/cancel/').status_code,404)
        self.login(self.owner)
        self.assertEqual(self.client.post(f'/requests/{record.pk}/reject/').status_code,302)

    def test_message_visibility_escape_author_edits_and_departure(self):
        secret=gs.post_message(actor=self.owner,group_id=self.group.pk,body='<script>private board</script>')
        self.assertNotContains(self.client.get(f'/groups/{self.group.pk}/'),'private board')
        self.login(self.guest)
        self.assertEqual(self.client.post(f'/groups/{self.group.pk}/messages/new/',{'body':'Not a member'}).status_code,403)
        self.client.post(f'/groups/{self.group.pk}/join/')
        self.assertContains(self.client.get(f'/groups/{self.group.pk}/'),'&lt;script&gt;private board&lt;/script&gt;')
        self.assertEqual(self.client.get(f'/messages/{secret.pk}/edit/').status_code,403)
        self.client.post(f'/groups/{self.group.pk}/messages/new/',{'body':'My message','author':self.owner.pk})
        message=gm.Message.objects.get(body='My message')
        self.assertEqual(message.author_id,self.guest.pk)
        self.assertEqual(self.client.post(f'/messages/{message.pk}/edit/',{'body':'Edited'}).status_code,302)
        self.client.post(f'/groups/{self.group.pk}/leave/')
        self.assertEqual(self.client.post(f'/messages/{message.pk}/delete/').status_code,403)
        self.assertNotContains(self.client.get(f'/groups/{self.group.pk}/'),'Edited')

    def test_owner_ban_lift_and_message_delete_tombstone(self):
        gs.join_group(actor=self.guest,group_id=self.group.pk)
        self.login()
        message=gs.post_message(actor=self.owner,group_id=self.group.pk,body='Remove me')
        self.assertEqual(self.client.post(f'/messages/{message.pk}/delete/').status_code,302)
        self.assertContains(self.client.get(f'/groups/{self.group.pk}/'),'Message removed')
        self.assertEqual(self.client.post(f'/groups/{self.group.pk}/members/{self.guest.pk}/ban/',{'reason':'Owner only reason'}).status_code,302)
        ban=gm.GroupBan.objects.get()
        self.login(self.guest)
        self.assertNotContains(self.client.get(f'/groups/{self.group.pk}/'),'Owner only reason')
        self.assertEqual(self.client.post(f'/bans/{ban.pk}/lift/').status_code,403)
        self.login()
        self.assertEqual(self.client.post(f'/bans/{ban.pk}/lift/').status_code,302)

    def test_existing_members_board_retained_without_pending_venue_leak(self):
        gs.join_group(actor=self.guest,group_id=self.group.pk)
        gs.post_message(actor=self.owner,group_id=self.group.pk,body='Keep coordinating')
        ds.follow_event(actor=self.guest,event_id=self.event.pk)
        self.pending.submitted_by=self.owner; self.pending.save()
        ds.save_event(actor=self.owner,event_id=self.event.pk,data={'venue':self.pending},category_ids=[self.category.pk])
        self.login(self.guest)
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/').status_code,404)
        response=self.client.get(f'/groups/{self.group.pk}/')
        self.assertContains(response,'Keep coordinating')
        for url in [f'/groups/{self.group.pk}/','/my-activity/','/notifications/']:
            response=self.client.get(url)
            self.assertNotContains(response,'Private proposed address')
            self.assertNotContains(response,'47.123456')
        self.assertContains(self.client.get('/my-activity/'),'Tracked event unavailable')

    def test_start_cutoff_blocks_new_members_but_keeps_existing_board(self):
        self.event.starts_at=timezone.now()-timedelta(hours=1); self.event.ends_at=timezone.now()+timedelta(hours=2); self.event.save()
        self.login(self.guest)
        self.assertContains(self.client.get(f'/groups/{self.group.pk}/'),'New participation is closed')
        self.assertEqual(self.client.post(f'/groups/{self.group.pk}/join/').status_code,400)
        self.login()
        self.assertEqual(self.client.post(f'/groups/{self.group.pk}/messages/new/',{'body':'Still here'}).status_code,302)

    def test_not_found_hidden_records_and_missing_photos(self):
        for url in ['/events/99999/','/groups/99999/','/genres/99999/',f'/groups/{self.group.pk}/photo/','/media/groups/missing.jpg']:
            self.assertEqual(self.client.get(url).status_code,404,url)
        self.event.moderation_hidden=True; self.event.save()
        self.assertEqual(self.client.get(f'/events/{self.event.pk}/').status_code,404)
        self.assertEqual(self.client.get(f'/groups/{self.group.pk}/').status_code,404)

    def test_sqlite_lock_returns_retry_response_not_internal_trace(self):
        self.login()
        with patch('discovery.pages.services.save_venue',side_effect=OperationalError('database is locked')):
            response=self.client.post('/venues/new/',{'name':'Locked','latitude':'48','longitude':'2','timezone':'Europe/Paris'})
        self.assertEqual(response.status_code,503)
        self.assertContains(response,'Please retry',status_code=503)
