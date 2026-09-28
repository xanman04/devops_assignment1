from zoneinfo import ZoneInfo
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from config.web import endpoint, form_page
from groups import services as group_services
from . import models, services
from .forms import EventForm, VenueProposalForm, EventReportForm, EventReferenceForm


@endpoint
@require_GET
def home(request):
    events = services.search_events()
    return render(request, "discovery/home.html", {
        "categories": models.GenreCategory.objects.all(),
        "tags": models.GenreTag.objects.select_related("category").order_by("category__display_order", "name"),
        "events": Paginator(events, 20).get_page(request.GET.get("page")),
    })


@endpoint
@require_GET
def genres(request, genre_id=None):
    category = get_object_or_404(models.GenreCategory, pk=genre_id) if genre_id else None
    return render(request, "discovery/genres.html", {
        "category": category, "categories": models.GenreCategory.objects.all(),
        "tags": category.tags.all() if category else [],
        "references": category.listening_references.prefetch_related("categories", "tags") if category else [],
    })


@endpoint
@require_GET
def event_detail(request, event_id):
    event = services.get_event(event_id=event_id, actor=request.user)
    return render(request, "discovery/event.html", {
        "event": event, "venue_zone": ZoneInfo(event.venue.timezone),
        "tempo": services.tempo_estimate(event),
        "editor": request.user.is_authenticated and (request.user.pk == event.creator_id or services.can_manage(request.user, "discovery.change_event")),
        "following": request.user.is_authenticated and event.follows.filter(user=request.user).exists(),
        "public": services.public_events().filter(pk=event.pk).exists(),
        "groups": group_services.visible_groups(event_id=event_id, actor=request.user),
        "joining_open": event.cancelled_at is None and not event.moderation_hidden and event.venue.review_status == "approved" and timezone.now() < event.starts_at,
    })


@endpoint
@login_required
@require_http_methods(["GET", "POST"])
def event_form(request, event_id=None):
    event = models.Event.objects.get(pk=event_id) if event_id else models.Event(creator=request.user)
    if event_id:
        services.require_event_editor(request.user, event)
    form = EventForm(request.POST if request.method == "POST" else None, instance=event, actor=request.user)

    def save(data):
        saved = services.save_event(actor=request.user, event_id=event_id,
            data={name: data[name] for name in services.EVENT_FIELDS},
            category_ids=data["categories"].values_list("pk", flat=True),
            tag_ids=data["tags"].values_list("pk", flat=True), cancelled=data["cancelled"])
        return redirect("event-detail", event_id=saved.pk)
    return form_page(request, form, "Edit event" if event_id else "List an event", save,
        context={"hint": "Choose an existing approved venue or propose a new venue first. Pending locations stay off the public map.", "venue_link": True})


@endpoint
@login_required
@require_http_methods(["GET", "POST"])
def venue_new(request):
    form = VenueProposalForm(request.POST if request.method == "POST" else None)

    def save(data):
        services.save_venue(actor=request.user, data=data)
        return redirect("event-new")
    return form_page(request, form, "Propose a venue", save,
                     context={"hint": "New locations require admin review before events appear publicly."})


@endpoint
@login_required
@require_POST
def event_action(request, event_id, action):
    if action == "cancel":
        event = models.Event.objects.get(pk=event_id)
        services.save_event(actor=request.user, event_id=event_id, data={},
            category_ids=event.categories.values_list("pk", flat=True),
            tag_ids=event.tags.values_list("pk", flat=True), cancelled=True)
    elif action == "follow":
        services.follow_event(actor=request.user, event_id=event_id)
    else:
        services.unfollow_event(actor=request.user, event_id=event_id)
        return redirect("activity")
    return redirect("event-detail", event_id=event_id)


@endpoint
@login_required
@require_http_methods(["GET", "POST"])
def event_report(request, event_id):
    services.public_events().get(pk=event_id)
    form = EventReportForm(request.POST if request.method == "POST" else None)

    def save(data):
        services.report_event(actor=request.user, event_id=event_id, **data)
        return redirect("event-detail", event_id=event_id)
    return form_page(request, form, "Report event", save)


@endpoint
@login_required
@require_http_methods(["GET", "POST"])
def reference_form(request, event_id, reference_id=None):
    event = models.Event.objects.get(pk=event_id)
    services.require_event_editor(request.user, event)
    reference = models.EventListeningReference.objects.get(pk=reference_id, event=event) if reference_id else models.EventListeningReference(event=event)
    form = EventReferenceForm(request.POST if request.method == "POST" else None, instance=reference)

    def save(data):
        services.save_event_reference(actor=request.user, event_id=event_id, reference_id=reference_id, data=data)
        return redirect("event-detail", event_id=event_id)
    return form_page(request, form, "Music listening reference", save)


@endpoint
@login_required
@require_POST
def reference_delete(request, reference_id):
    reference = models.EventListeningReference.objects.get(pk=reference_id)
    event_id = reference.event_id
    services.delete_event_reference(actor=request.user, reference_id=reference_id)
    return redirect("event-detail", event_id=event_id)
