from django.contrib.auth.decorators import login_required
from zoneinfo import ZoneInfo
from django.core.paginator import Paginator
from django.db.models import Count
from django.utils import timezone
from django.shortcuts import render
from django.views.decorators.http import require_GET
from config.web import endpoint
from discovery.models import Event, EventFollow, Venue
from discovery.services import public_events
from groups.models import GroupHistory, Membership, JoinRequest


@endpoint
@login_required
@require_GET
def activity(request):
    """Everything the account has done, newest first, as one list; each entry says what kind of activity it was."""
    user, limit = request.user, 200
    items = []
    own = Event.objects.filter(creator=user)
    for event in own.select_related("venue").order_by("-created_at")[:limit]:
        items.append({"kind": "listed", "at": event.created_at, "event": event})
    follows = list(EventFollow.objects.filter(user=user).select_related("event").order_by("-created_at", "-id")[:limit])
    followed_ids = [follow.event_id for follow in follows]
    accessible = set(public_events().filter(pk__in=followed_ids).values_list("pk", flat=True))
    accessible.update(own.filter(pk__in=followed_ids).values_list("pk", flat=True))
    for follow in follows:
        available = follow.event_id in accessible
        items.append({"kind": "followed", "at": follow.created_at, "event_id": follow.event_id, "available": available,
                      "title": follow.event.title if available else "Followed event unavailable"})
    history = list(GroupHistory.objects.filter(user=user).order_by("-created_at", "-id")[:limit])
    recorded = {row.group_id for row in history if row.kind in ("created", "joined") and row.group_id}
    for row in history:
        items.append({"kind": row.kind, "at": row.created_at, "group_id": row.group_id, "group_name": row.group_name,
                      "event_title": row.event_title})
    for membership in Membership.objects.filter(user=user).select_related("group__event").order_by("-joined_at")[:limit]:
        if membership.group_id not in recorded:
            items.append({"kind": "joined", "at": membership.joined_at, "group_id": membership.group_id,
                          "group_name": membership.group.name, "event_title": membership.group.event.title})
    for request_row in JoinRequest.objects.filter(applicant=user).select_related("group__event").order_by("-requested_at", "-id")[:limit]:
        items.append({"kind": "requested", "at": request_row.requested_at, "request": request_row, "group": request_row.group})
    for venue in Venue.objects.filter(submitted_by=user).order_by("-created_at")[:limit]:
        items.append({"kind": "venue", "at": venue.created_at, "venue": venue})
    items.sort(key=lambda item: item["at"], reverse=True)
    return render(request, "activity.html", {"timeline": Paginator(items, 25).get_page(request.GET.get("page"))})


def _event_card(event, *, zone_cache, extra=None):
    """What a card for an event needs: art, local date, genres and a status label."""
    if event.venue.timezone not in zone_cache:
        zone_cache[event.venue.timezone] = ZoneInfo(event.venue.timezone)
    categories = list(event.categories.all())
    status = ("Cancelled" if event.cancelled_at else "Hidden" if event.moderation_hidden else
              "Location pending" if event.venue.review_status != "approved" else "")
    card = {"event": event, "zone": zone_cache[event.venue.timezone], "accent": categories[0].color if categories else "#8d95a6",
            "genres": [{"name": category.name, "color": category.color} for category in categories[:3]],
            "extra_genres": max(len(categories) - 3, 0),
            "uploaded_poster_id": event.pk if event.poster else None, "poster": event.demo_poster,
            "status": status, "past": event.ends_at < timezone.now(), "available": True}
    return card | (extra or {})


@endpoint
@login_required
@require_GET
def my_events(request):
    own_query = Event.objects.filter(creator=request.user)
    own = list(own_query.select_related("venue").prefetch_related("categories").order_by("-created_at")[:24])
    follows = list(EventFollow.objects.filter(user=request.user).select_related("event__venue")
                   .prefetch_related("event__categories").order_by("-created_at", "-id")[:24])
    visible = set(public_events().filter(pk__in=[follow.event_id for follow in follows]).values_list("pk", flat=True))
    visible.update(own_query.filter(pk__in=[follow.event_id for follow in follows]).values_list("pk", flat=True))
    zones = {}
    followed = [_event_card(follow.event, zone_cache=zones) if follow.event_id in visible else
                {"available": False, "title": "Followed event unavailable", "subtitle": "This listing is no longer public"}
                for follow in follows]
    listings = [_event_card(event, zone_cache=zones) for event in own]
    return render(request, "my_events.html", {"followed": followed, "listings": listings})


def _group_art(group):
    event = group.event
    return {"photo_id": group.pk if group.photo else None,
            "uploaded_poster_id": event.pk if event.poster else None, "poster": event.demo_poster}


@endpoint
@login_required
@require_GET
def my_groups(request):
    memberships = list(Membership.objects.filter(user=request.user).select_related("group__event__venue", "group__owner")
                       .prefetch_related("group__event__categories").order_by("-joined_at", "-id")[:24])
    counts = dict(Membership.objects.filter(group_id__in=[m.group_id for m in memberships]).values("group_id")
                  .annotate(n=Count("id")).values_list("group_id", "n"))
    cards = []
    for member in memberships:
        group, event = member.group, member.group.event
        categories = list(event.categories.all())
        joined = counts.get(group.pk, 0)
        cards.append({
            "group": group, "event": event, "owner": group.owner_id == request.user.pk, "joined": joined,
            "dots": [index < joined for index in range(min(group.capacity, 12))],
            "full": joined >= group.capacity, "starts_at": event.starts_at, "zone": ZoneInfo(event.venue.timezone),
            "accent": categories[0].color if categories else "#8d95a6", "past": event.ends_at < timezone.now(),
            "cancelled": event.cancelled_at is not None, **_group_art(group),
        })
    requests = []
    for item in JoinRequest.objects.filter(applicant=request.user).select_related("group__event__venue")             .prefetch_related("group__event__categories").order_by("-requested_at", "-id")[:24]:
        categories = list(item.group.event.categories.all())
        requests.append({"item": item, "group": item.group, "event": item.group.event, "status": item.status,
                         "accent": categories[0].color if categories else "#8d95a6",
                         "zone": ZoneInfo(item.group.event.venue.timezone)})
    received = []
    for item in (JoinRequest.objects.filter(group__owner=request.user, status=JoinRequest.Status.PENDING)
                 .select_related("applicant", "group__event__venue").prefetch_related("group__event__categories")
                 .order_by("requested_at", "id")[:12]):
        categories = list(item.group.event.categories.all())
        received.append({"item": item, "group": item.group, "event": item.group.event,
                         "accent": categories[0].color if categories else "#8d95a6"})
    return render(request, "groups/mine.html", {"cards": cards, "requests": requests, "received": received})
