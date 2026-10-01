import re
from zoneinfo import ZoneInfo
from django.http import FileResponse, Http404, JsonResponse
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db.models import Q
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


def _event_card(event):
    local_start = event.starts_at.astimezone(ZoneInfo(event.venue.timezone))
    category = next(iter(event.categories.all()), None)
    return {"title": event.title, "subtitle": f"{event.venue.name} · {local_start:%d %b %Y %H:%M}",
            "href": f"/events/{event.pk}/", "color": category.color if category else "#9ca0a9", "symbol": "events",
            "uploaded_poster_id": event.pk if event.poster else None, "poster": event.demo_poster}


def _first_sentence(description):
    return re.split(r"(?<=[.!?])\s+", description.strip(), maxsplit=1)[0]


def _search_variants(query):
    # People commonly type "and" for the ampersand used in curated genre names.
    return {query, re.sub(r"\band\b", "&", query, flags=re.IGNORECASE), query.replace("&", "and")}


GENRE_ART = {
    "Afro Electronic": "percussion", "Ambient / Experimental": "atmosphere",
    "Bass / Club": "speaker", "Brazilian Funk": "percussion",
    "Breaks / Breakbeat": "breakbeat", "Dance / Pop": "spark",
    "Drum & Bass": "breakbeat", "Dubstep / 140": "speaker",
    "Electro": "circuit", "Hard Dance / Hardcore": "shards",
    "Hard Techno": "shards", "House": "vinyl", "Indie Dance": "strings",
    "Industrial / EBM": "industrial", "Latin Electronic": "percussion",
    "Mainstage / Commercial EDM": "spotlight", "Nu Disco / Disco": "disco",
    "Psy-Trance": "spiral", "Techno": "circuit", "Trance": "horizon",
    "Trap / Future Bass": "synth", "UK Garage / Bassline": "breakbeat",
}


@endpoint
@require_GET
def discover(request):
    query = request.GET.get("q", "").strip()[:80]
    category_query = models.GenreCategory.objects.all()
    event_query = services.search_events()
    reference_query = models.GenreListeningReference.objects.all()
    dj_query = models.DJProfile.objects.all()
    if query:
        category_matches = Q()
        event_matches = Q()
        reference_matches = Q()
        dj_matches = Q()
        for term in _search_variants(query):
            category_matches |= Q(name__icontains=term) | Q(description__icontains=term)
            event_matches |= (Q(title__icontains=term) | Q(venue__name__icontains=term) |
                              Q(categories__name__icontains=term) | Q(tags__name__icontains=term))
            reference_matches |= Q(title__icontains=term) | Q(artist_credit__icontains=term)
            dj_matches |= (Q(name__icontains=term) | Q(description__icontains=term) |
                           Q(categories__name__icontains=term))
        category_query = category_query.filter(category_matches)
        event_query = event_query.filter(event_matches).distinct()
        reference_query = reference_query.filter(reference_matches)
        dj_query = dj_query.filter(dj_matches).distinct()
    categories = list(category_query[:24])
    events = list(event_query.select_related("venue").prefetch_related("categories")[:24])
    references = list(reference_query.order_by("display_order", "id")[:200])
    djs = list(dj_query.prefetch_related("categories")[:24])
    def credit_cards(kind):
        seen, cards = set(), []
        for reference in references:
            if reference.kind not in kind or not reference.artist_credit.strip():
                continue
            credit = reference.artist_credit.strip()
            if credit.casefold() in seen:
                continue
            seen.add(credit.casefold())
            cards.append({"title": credit, "subtitle": reference.title, "href": reference.url,
                          "external": True, "symbol": "profile", "round": True})
        return cards[:24]
    profile_cards = [{"title": dj.name, "subtitle": "", "categories": list(dj.categories.all()),
                 "href": f"/djs/{dj.pk}/", "photo": dj.photo, "symbol": "profile", "round": True} for dj in djs]
    profile_names = {card["title"].casefold() for card in profile_cards}
    profile_cards.extend(card for card in credit_cards({"set", "track", "artist_page"})
                         if card["title"].casefold() not in profile_names)
    sections = [
        {"id": "events", "title": "Events", "description": "Upcoming public events", "cards": [_event_card(e) for e in events], "empty": "No public events yet."},
        {"id": "playing", "title": "Playing near me", "description": "Artists and DJs at upcoming events within 30 km",
         "cards": [], "empty": "Checking your location for upcoming performers."},
        {"id": "genres", "title": "Genres", "description": "Colors match the map pins",
         "cards": [{"title": c.name, "subtitle": _first_sentence(c.description), "href": f"/genres/{c.pk}/",
                    "color": c.color, "genre": True, "motif": GENRE_ART.get(c.name, "wave")} for c in categories],
         "empty": "No curated genres yet."},
        {"id": "performers", "title": "Artists & DJs", "description": "Explore performers and the music they make",
         "cards": profile_cards, "empty": "No artist or DJ profiles yet."},
    ]
    return render(request, "browse.html", {"title": "Discover", "intro": "Explore the music. Find what moves you.",
                                           "sections": sections, "query": query})


@endpoint
@require_GET
def playing_near_me(request):
    query = request.GET.get("q", "").strip()[:80].casefold()
    results = services.nearby_performers(latitude=request.GET.get("latitude"),
                                         longitude=request.GET.get("longitude"))
    cards = []
    for performer, event in results:
        if query and not any(query in value.casefold() for value in (
            performer.name, event.title, event.venue.name,
            *(category.name for category in performer.categories.all()),
        )):
            continue
        cards.append({"title": performer.name, "href": f"/djs/{performer.pk}/",
            "photo_url": staticfiles_storage.url(performer.photo) if performer.photo else "",
            "subtitle": f"{event.title} · {event.venue.name}",
            "categories": [{"name": category.name, "color": category.color}
                           for category in performer.categories.all()]})
    response = JsonResponse({"cards": cards})
    response["Cache-Control"] = "private, no-store"
    return response


@endpoint
@require_GET
def genres(request, genre_id=None):
    category = get_object_or_404(models.GenreCategory, pk=genre_id) if genre_id else None
    tags = list(category.tags.order_by("name")) if category else []
    tag_cards = [{"tag": tag, "preview": _first_sentence(tag.description)} for tag in tags]
    return render(request, "discovery/genres.html", {
        "category": category, "categories": models.GenreCategory.objects.all(),
        "tag_cards": tag_cards,
        "motif": GENRE_ART.get(category.name, "wave") if category else "wave",
        "references": category.listening_references.prefetch_related("categories", "tags") if category else [],
        "djs": category.djs.prefetch_related("categories") if category else [],
    })


@endpoint
@require_GET
def dj_detail(request, dj_id):
    dj = get_object_or_404(models.DJProfile.objects.prefetch_related("categories"), pk=dj_id)
    upcoming = services.public_events().filter(performers=dj, cancelled_at__isnull=True,
        ends_at__gt=timezone.now()).select_related("venue").order_by("starts_at")[:12]
    return render(request, "discovery/dj.html", {"dj": dj, "upcoming": upcoming})


@endpoint
@require_GET
def event_detail(request, event_id):
    event = services.get_event(event_id=event_id, actor=request.user)
    return render(request, "discovery/event.html", {
        "event": event, "venue_zone": ZoneInfo(event.venue.timezone),
        "event_tags": event.tags.select_related("category"),
        "tempo": services.tempo_display(event),
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
    form = EventForm(request.POST if request.method == "POST" else None,
                     request.FILES if request.method == "POST" else None, instance=event, actor=request.user)

    def save(data):
        saved = services.save_event(actor=request.user, event_id=event_id,
            data={name: data[name] for name in services.EVENT_FIELDS},
            category_ids=data["categories"].values_list("pk", flat=True),
            tag_ids=data["tags"].values_list("pk", flat=True),
            performer_ids=data["performers"].values_list("pk", flat=True), cancelled=data["cancelled"],
            poster=data.get("poster_upload"), remove_poster=data.get("remove_poster", False))
        return redirect("event-detail", event_id=saved.pk)
    return form_page(request, form, "Edit event" if event_id else "List an event", save,
        context={"hint": "Choose an existing approved venue or propose a new venue first. Pending locations stay off the public map.",
                 "venue_link": True, "current_poster_id": event.pk if event.poster else None})


@endpoint
@require_GET
def event_poster(request, event_id):
    try:
        response = FileResponse(services.open_poster(event_id=event_id, actor=request.user), content_type="image/jpeg")
    except FileNotFoundError as error:
        raise Http404("No poster is available.") from error
    response["Cache-Control"] = "private, no-store"
    response["Vary"] = "Cookie"
    return response


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
