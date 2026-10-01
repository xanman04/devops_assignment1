from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from django.views.generic import RedirectView
from accounts import views as accounts
from discovery import pages as discovery
from discovery.views import map_events
from groups import pages as groups
from notifications import views as notices
from .pages import activity, my_events, my_groups

admin.site.site_header = "Bassline administration"
admin.site.site_title = "Bassline admin"
admin.site.index_title = "Bassline records"


urlpatterns = [
    path("ui/", RedirectView.as_view(url="/static/prototype/index.html", permanent=False), name="ui-prototype"),
    path("", discovery.home, name="home"),
    path("discover/", discovery.discover, name="discover"),
    path("my-events/", my_events, name="my-events"),
    path("groups/", my_groups, name="my-groups"),
    path("admin/", admin.site.urls),
    path("api/map/events/", map_events, name="map-events"),
    path("genres/", discovery.genres, name="genres"),
    path("genres/<int:genre_id>/", discovery.genres, name="genre-detail"),
    path("djs/<int:dj_id>/", discovery.dj_detail, name="dj-detail"),
    path("accounts/register/", accounts.register, name="register"),
    path("accounts/login/", LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/settings/", accounts.settings, name="account-settings"),
    path("events/new/", discovery.event_form, name="event-new"),
    path("events/<int:event_id>/", discovery.event_detail, name="event-detail"),
    path("events/<int:event_id>/edit/", discovery.event_form, name="event-edit"),
    path("events/<int:event_id>/cancel/", discovery.event_action, {"action": "cancel"}, name="event-cancel"),
    path("events/<int:event_id>/follow/", discovery.event_action, {"action": "follow"}, name="event-follow"),
    path("events/<int:event_id>/unfollow/", discovery.event_action, {"action": "unfollow"}, name="event-unfollow"),
    path("events/<int:event_id>/report/", discovery.event_report, name="event-report"),
    path("venues/new/", discovery.venue_new, name="venue-new"),
    path("events/<int:event_id>/references/new/", discovery.reference_form, name="reference-new"),
    path("events/<int:event_id>/references/<int:reference_id>/edit/", discovery.reference_form, name="reference-edit"),
    path("references/<int:reference_id>/delete/", discovery.reference_delete, name="reference-delete"),
    path("events/<int:event_id>/groups/new/", groups.group_form, name="group-new"),
    path("groups/<int:group_id>/", groups.group_detail, name="group-detail"),
    path("groups/<int:group_id>/edit/", groups.group_form, name="group-edit"),
    path("groups/<int:group_id>/join/", groups.group_action, {"action": "join"}, name="group-join"),
    path("groups/<int:group_id>/request/", groups.group_action, {"action": "request"}, name="group-request"),
    path("groups/<int:group_id>/leave/", groups.group_action, {"action": "leave"}, name="group-leave"),
    path("groups/<int:group_id>/requests/", groups.requests_list, name="group-requests"),
    path("requests/<int:request_id>/approve/", groups.request_action, {"action": "approve"}, name="request-approve"),
    path("requests/<int:request_id>/reject/", groups.request_action, {"action": "reject"}, name="request-reject"),
    path("requests/<int:request_id>/accept/", groups.request_action, {"action": "accept"}, name="request-accept"),
    path("requests/<int:request_id>/cancel/", groups.request_action, {"action": "cancel"}, name="request-cancel"),
    path("groups/<int:group_id>/members/<int:user_id>/remove/", groups.member_action, {"action": "remove"}, name="member-remove"),
    path("groups/<int:group_id>/members/<int:user_id>/ban/", groups.member_action, {"action": "ban"}, name="member-ban"),
    path("bans/<int:ban_id>/lift/", groups.ban_lift, name="ban-lift"),
    path("groups/<int:group_id>/photo/", groups.photo, name="group-photo"),
    path("groups/<int:group_id>/messages/new/", groups.message_new, name="message-new"),
    path("messages/<int:message_id>/edit/", groups.message_edit, name="message-edit"),
    path("messages/<int:message_id>/delete/", groups.message_delete, name="message-delete"),
    path("notifications/", notices.inbox, name="inbox"),
    path("notifications/<int:notification_id>/read/", notices.read, name="notification-read"),
    path("my-activity/", activity, name="activity"),
]
