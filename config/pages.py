from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.http import require_GET
from config.web import endpoint
from discovery.models import Event, EventFollow, Venue
from discovery.services import public_events
from groups.models import Membership, JoinRequest


@endpoint
@login_required
@require_GET
def activity(request):
    follows = Paginator(EventFollow.objects.filter(user=request.user).select_related("event").order_by("-created_at", "-id"), 20).get_page(request.GET.get("follows_page"))
    followed_ids = [follow.event_id for follow in follows]
    accessible = set(public_events().filter(pk__in=followed_ids).values_list("pk", flat=True))
    own = Event.objects.filter(creator=request.user)
    accessible.update(own.filter(pk__in=followed_ids).values_list("pk", flat=True))
    follows.object_list = [{"id": f.event_id, "title": f.event.title if f.event_id in accessible else "Tracked event unavailable",
                "available": f.event_id in accessible} for f in follows]
    return render(request, "activity.html", {
        "events": Paginator(own.select_related("venue").order_by("-created_at"), 20).get_page(request.GET.get("events_page")),
        "follows": follows,
        "memberships": Paginator(Membership.objects.filter(user=request.user).select_related("group__event").order_by("-joined_at"), 20).get_page(request.GET.get("memberships_page")),
        "requests": Paginator(JoinRequest.objects.filter(applicant=request.user).select_related("group").order_by("-requested_at", "-id"), 20).get_page(request.GET.get("requests_page")),
        "venues": Paginator(Venue.objects.filter(submitted_by=request.user).order_by("-created_at"), 20).get_page(request.GET.get("venues_page")),
    })


@endpoint
@login_required
@require_GET
def my_events(request):
    own_query = Event.objects.filter(creator=request.user)
    own = list(own_query.select_related("venue").order_by("-created_at")[:24])
    follows = list(EventFollow.objects.filter(user=request.user).select_related("event__venue").order_by("-created_at", "-id")[:24])
    visible = set(public_events().filter(pk__in=[follow.event_id for follow in follows]).values_list("pk", flat=True))
    visible.update(own_query.filter(pk__in=[follow.event_id for follow in follows]).values_list("pk", flat=True))
    def card(event):
        return {"title": event.title, "subtitle": event.venue.name, "href": f"/events/{event.pk}/", "symbol": "events"}
    tracked = [card(follow.event) if follow.event_id in visible else
               {"title": "Tracked event unavailable", "subtitle": "This listing is no longer public", "symbol": "events"}
               for follow in follows]
    listings = [card(event) | {"status": "Cancelled" if event.cancelled_at else
                "Hidden" if event.moderation_hidden else
                "Location pending" if event.venue.review_status != "approved" else ""} for event in own]
    sections = [
        {"id": "tracked", "title": "Tracked events", "description": "Events you're keeping an eye on", "cards": tracked, "empty": "No tracked events yet."},
        {"id": "listings", "title": "Your listings", "description": "Events you have shared", "cards": listings, "empty": "No listings yet."},
    ]
    return render(request, "browse.html", {"title": "My events", "intro": "The nights you're keeping an eye on.",
                                           "sections": sections, "create_event": True, "all_activity": True})


@endpoint
@login_required
@require_GET
def my_groups(request):
    memberships = Membership.objects.filter(user=request.user).select_related("group__event").order_by("-joined_at", "-id")[:24]
    requests = JoinRequest.objects.filter(applicant=request.user).select_related("group__event").order_by("-requested_at", "-id")[:24]
    group_cards = [{"title": member.group.name, "subtitle": member.group.event.title,
                    "href": f"/groups/{member.group_id}/", "photo_id": member.group_id if member.group.photo else None,
                    "symbol": "groups", "group": True}
                   for member in memberships]
    request_cards = [{"title": item.group.name, "subtitle": item.group.event.title,
                      "href": f"/groups/{item.group_id}/", "status": item.get_status_display(), "symbol": "groups", "group": True}
                     for item in requests]
    sections = [
        {"id": "my-groups", "title": "My groups", "description": "Groups you've joined", "cards": group_cards, "empty": "No group memberships yet."},
        {"id": "requests", "title": "Requests", "description": "Requests to join other groups", "cards": request_cards, "empty": "No requests yet."},
    ]
    return render(request, "browse.html", {"title": "Groups", "intro": "A little company for your next night out.",
                                           "sections": sections, "all_activity": True})
