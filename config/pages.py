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
