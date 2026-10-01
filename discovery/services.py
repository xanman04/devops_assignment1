"""Authorized discovery operations shared by admin and public forms.

Writes are atomic. SQLite IMMEDIATE transactions serialize these short operations;
no network work occurs while holding a transaction. Raw ORM writes are not an API.
"""
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from math import asin, cos, isfinite, radians, sin, sqrt

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from config.images import prepare_image
from notifications.models import Notification
from .models import (
    DJProfile, Event, EventChange, EventFollow, EventListeningReference, EventReport,
    GenreCategory, GenreTag, GenreListeningReference, Venue,
)

EVENT_FIELDS = {"venue", "title", "description", "starts_at", "ends_at", "ticket_url"}
VENUE_FIELDS = {"name", "address", "latitude", "longitude", "timezone"}
REFERENCE_FIELDS = {"title", "artist_credit", "url", "kind", "display_order"}


def require_user(actor):
    if not actor or not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("An active account is required.")


def require_permission(actor, permission):
    require_user(actor)
    if not actor.has_perm(permission):
        raise PermissionDenied("You do not have permission for this action.")


def can_manage(actor, permission):
    return bool(actor and actor.is_authenticated and actor.is_active and actor.has_perm(permission))


def require_event_editor(actor, event):
    require_user(actor)
    if event.creator_id != actor.pk and not can_manage(actor, "discovery.change_event"):
        raise PermissionDenied("Only the event creator or an authorized admin may edit it.")


def _assign(instance, data, allowed):
    unknown = set(data) - allowed
    if unknown:
        raise ValidationError(f"Unsupported fields: {', '.join(sorted(unknown))}.")
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(instance, field, value)


def _ids(values):
    try:
        values = list(values)
        if any(isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit() for value in values):
            raise ValueError
        result = {int(value) for value in values}
    except (TypeError, ValueError, OverflowError):
        raise ValidationError("Selections must be integer IDs.")
    if any(not 0 < value <= 9223372036854775807 for value in result):
        raise ValidationError("Selections must be valid positive database IDs.")
    return result


def classification(category_ids, tag_ids):
    """Validate complete selections before storing any event/reference edits."""
    category_ids, tag_ids = _ids(category_ids), _ids(tag_ids)
    categories = list(GenreCategory.objects.filter(pk__in=category_ids))
    tags = list(GenreTag.objects.filter(pk__in=tag_ids))
    if not categories or len(categories) != len(category_ids):
        raise ValidationError("Select at least one existing genre category.")
    if len(tags) != len(tag_ids):
        raise ValidationError("A selected genre tag does not exist.")
    if any(tag.category_id not in category_ids for tag in tags):
        raise ValidationError("Each tag's parent category must also be selected.")
    return categories, tags


def validate_event_times(starts_at, ends_at):
    if not all(isinstance(value, datetime) and timezone.is_aware(value) for value in (starts_at, ends_at)):
        raise ValidationError("Start and end must include timezone information.")
    if ends_at <= starts_at:
        raise ValidationError("Event end must be after its start.")


def _venue_allowed(actor, venue):
    if venue.review_status == Venue.ReviewStatus.REJECTED:
        raise ValidationError("Choose an approved venue or propose a new location.")
    if (venue.review_status != Venue.ReviewStatus.APPROVED and
            venue.submitted_by_id != actor.pk and not can_manage(actor, "discovery.change_event")):
        raise PermissionDenied("You cannot use another user's pending location.")


@transaction.atomic
def save_category(*, actor, data, category_id=None):
    require_permission(actor, f"discovery.{'change' if category_id else 'add'}_genrecategory")
    category = GenreCategory.objects.get(pk=category_id) if category_id else GenreCategory()
    _assign(category, data, {"name", "color", "description", "display_order", "bpm_min", "bpm_max"})
    category.full_clean()
    category.save()
    return category


def validate_tag_move(tag, new_category_id):
    if tag.pk and tag.category_id != new_category_id:
        if tag.events.exists() or tag.listening_references.exists():
            raise ValidationError("A tag in use cannot move categories; create a new tag instead.")


@transaction.atomic
def save_tag(*, actor, data, tag_id=None):
    require_permission(actor, f"discovery.{'change' if tag_id else 'add'}_genretag")
    tag = GenreTag.objects.get(pk=tag_id) if tag_id else GenreTag()
    if "category" in data:
        validate_tag_move(tag, data["category"].pk)
    _assign(tag, data, {"category", "name", "description", "bpm_min", "bpm_max"})
    tag.full_clean()
    tag.save()
    return tag


def _venue_snapshot(venue):
    return {
        "id": venue.pk, "name": venue.name, "address": venue.address,
        "latitude": format(Decimal(str(venue.latitude)), ".6f"),
        "longitude": format(Decimal(str(venue.longitude)), ".6f"), "timezone": venue.timezone,
    }


def _event_snapshot(event):
    return {
        "venue": _venue_snapshot(event.venue),
        "starts_at": event.starts_at.astimezone(dt_timezone.utc).isoformat(),
        "ends_at": event.ends_at.astimezone(dt_timezone.utc).isoformat(),
        "cancelled": event.cancelled_at is not None,
    }


def _record_changes(event, actor, before, after, kind=EventChange.Kind.EVENT_EDIT):
    changes = {key: {"before": before[key], "after": after[key]} for key in before if before[key] != after[key]}
    if not changes:
        return None
    record = EventChange(event=event, actor=actor, kind=kind, changes=changes)
    record.full_clean()
    record.save()
    # Summaries intentionally contain no coordinates, event text, or private snapshots.
    labels = {"venue": "venue", "starts_at": "start time", "ends_at": "end time", "cancelled": "cancellation status"}
    summary = "A tracked event changed: " + ", ".join(labels[key] for key in changes) + "."
    if event.venue.review_status != Venue.ReviewStatus.APPROVED:
        summary += " Location is awaiting approval or unavailable."
    recipients = event.follows.filter(user__is_active=True).values_list("user_id", flat=True)
    Notification.objects.bulk_create([
        Notification(recipient_id=user_id, kind=Notification.Kind.EVENT_CHANGE, event_change=record, summary=summary)
        for user_id in recipients
    ])
    return record


@transaction.atomic
def save_venue(*, actor, data, venue_id=None, review_status=None, review_note=""):
    require_user(actor)
    venue = Venue.objects.get(pk=venue_id) if venue_id else Venue(submitted_by=actor)
    if venue_id:
        require_permission(actor, "discovery.change_venue")
    if review_status is not None:
        require_permission(actor, "discovery.change_venue")
    before = _venue_snapshot(venue) if venue_id else None
    _assign(venue, data, VENUE_FIELDS)
    if review_status is not None:
        if review_status not in Venue.ReviewStatus.values:
            raise ValidationError("Invalid venue review status.")
        if venue.review_status != review_status or venue.review_note != review_note:
            venue.review_status = review_status
            venue.review_note = review_note.strip()
            venue.reviewed_by = actor
            venue.reviewed_at = timezone.now()
    venue.full_clean()
    venue.save()
    after = _venue_snapshot(venue)
    if before and before != after:
        for event in venue.events.select_related("venue"):
            _record_changes(event, actor, {"venue": before}, {"venue": after}, EventChange.Kind.VENUE_EDIT)
    return venue


def save_event(*, actor, data, category_ids, tag_ids=(), event_id=None, cancelled=None, hidden=None,
               poster=None, remove_poster=False, performer_ids=None):
    require_user(actor)
    if event_id:
        require_event_editor(actor, Event.objects.get(pk=event_id))
    if poster is not None and remove_poster:
        raise ValidationError("Choose either a new poster or poster removal.")
    prepared = prepare_image(poster, kind="poster") if poster is not None else None
    new_name = None
    storage = Event._meta.get_field("poster").storage
    try:
        with transaction.atomic():
            event = Event.objects.select_related("venue").get(pk=event_id) if event_id else Event(creator=actor)
            if event_id:
                require_event_editor(actor, event)
            before = _event_snapshot(event) if event_id else None
            categories, tags = classification(category_ids, tag_ids)
            if performer_ids is not None:
                selected_ids = _ids(performer_ids)
                performers = list(DJProfile.objects.filter(pk__in=selected_ids))
                if len(performers) != len(selected_ids):
                    raise ValidationError("A selected artist / DJ profile does not exist.")
            _assign(event, data, EVENT_FIELDS)
            # Reload relationships rather than trusting caller-supplied approval flags.
            if not event.venue_id:
                raise ValidationError("An event needs a venue.")
            event.venue = Venue.objects.get(pk=event.venue_id)
            if not event_id or (before and before["venue"]["id"] != event.venue_id):
                _venue_allowed(actor, event.venue)
            validate_event_times(event.starts_at, event.ends_at)
            if cancelled is not None:
                if not isinstance(cancelled, bool):
                    raise ValidationError("Cancellation must be true or false.")
                event.cancelled_at = (event.cancelled_at or timezone.now()) if cancelled else None
            if hidden is not None:
                require_permission(actor, "discovery.change_event")
                if not isinstance(hidden, bool):
                    raise ValidationError("Visibility must be true or false.")
                event.moderation_hidden = hidden
            old_name = event.poster.name
            if prepared is not None:
                event.poster.save(prepared.name, prepared, save=False)
                new_name = event.poster.name
            elif remove_poster:
                event.poster = ""
            event.full_clean()
            event.save()
            event.categories.set(categories)
            event.tags.set(tags)
            if performer_ids is not None:
                event.performers.set(performers)
            if before:
                _record_changes(event, actor, before, _event_snapshot(event))
            if (prepared is not None or remove_poster) and old_name:
                transaction.on_commit(lambda: storage.delete(old_name), robust=True)
        return event
    except Exception:
        if new_name:
            storage.delete(new_name)
        raise


def public_events():
    """Public detail eligibility includes cancelled/past events for their labels."""
    return Event.objects.filter(venue__review_status="approved", moderation_hidden=False,
                                categories__isnull=False).distinct()


def get_event(*, event_id, actor=None):
    event = Event.objects.select_related("venue", "creator").prefetch_related("categories", "tags").get(pk=event_id)
    privileged = can_manage(actor, "discovery.change_event") or bool(
        actor and actor.is_authenticated and actor.is_active and event.creator_id == actor.pk
    )
    if not privileged and not public_events().filter(pk=event.pk).exists():
        # Deliberately indistinguishable from a nonexistent event to public callers.
        raise Event.DoesNotExist
    return event


def open_poster(*, event_id, actor=None):
    event = get_event(event_id=event_id, actor=actor)
    if not event.poster:
        raise FileNotFoundError("This event has no uploaded poster.")
    return event.poster.open("rb")


def search_events(*, starts_at=None, ends_at=None, category_ids=(), tag_ids=(), match="any", bounds=None, now=None):
    now = now or timezone.now()
    starts_at = starts_at or now
    try:
        ends_at = ends_at or (starts_at + timedelta(days=14))
    except (TypeError, OverflowError):
        raise ValidationError("Date window is outside supported limits.")
    validate_event_times(starts_at, ends_at)
    if match not in {"any", "all"}:
        raise ValidationError("Genre matching must be 'any' or 'all'.")
    categories, tags = _ids(category_ids), _ids(tag_ids)
    if GenreCategory.objects.filter(pk__in=categories).count() != len(categories) or GenreTag.objects.filter(pk__in=tags).count() != len(tags):
        raise ValidationError("Unknown genre selection.")
    events = public_events().filter(cancelled_at__isnull=True, starts_at__lt=ends_at,
                                    ends_at__gt=starts_at).select_related("venue").prefetch_related("categories", "tags")
    if match == "all":
        for category_id in categories:
            events = events.filter(categories__id=category_id)
        for tag_id in tags:
            events = events.filter(tags__id=tag_id)
    elif categories or tags:
        events = events.filter(Q(categories__id__in=categories) | Q(tags__id__in=tags))
    if bounds is not None:
        try:
            south, west, north, east = [Decimal(str(value)) for value in bounds]
            if not all(value.is_finite() for value in (south, west, north, east)):
                raise ValueError
            if not (-90 <= south <= north <= 90 and -180 <= west <= 180 and -180 <= east <= 180):
                raise ValueError
        except (TypeError, ValueError, InvalidOperation):
            raise ValidationError("Bounds must be south, west, north, east within coordinate limits.")
        events = events.filter(venue__latitude__gte=south, venue__latitude__lte=north)
        if west <= east:
            events = events.filter(venue__longitude__gte=west, venue__longitude__lte=east)
        else:  # A viewport crossing the international date line.
            events = events.filter(Q(venue__longitude__gte=west) | Q(venue__longitude__lte=east))
    return events.distinct().order_by("starts_at", "id")


def nearby_performers(*, latitude, longitude, radius_km=30, now=None):
    """One profile per performer, tied to their next public event within 14 days."""
    try:
        lat, lon = float(latitude), float(longitude)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        raise ValidationError("Location must be valid latitude and longitude.")
    if not all(isfinite(value) for value in (lat, lon)):
        raise ValidationError("Location must be finite latitude and longitude.")
    now = now or timezone.now()
    lat_delta = radius_km / 111.0
    lon_delta = min(180, radius_km / max(111.0 * abs(cos(radians(lat))), 0.001))
    events = search_events(starts_at=now, ends_at=now + timedelta(days=14), now=now).filter(
        venue__latitude__gte=max(-90, lat - lat_delta),
        venue__latitude__lte=min(90, lat + lat_delta), performers__isnull=False,
    )
    if lon_delta < 180:
        west, east = lon - lon_delta, lon + lon_delta
        if west < -180:
            events = events.filter(Q(venue__longitude__gte=west + 360) | Q(venue__longitude__lte=east))
        elif east > 180:
            events = events.filter(Q(venue__longitude__gte=west) | Q(venue__longitude__lte=east - 360))
        else:
            events = events.filter(venue__longitude__gte=west, venue__longitude__lte=east)
    results, seen = [], set()
    for event in events.prefetch_related("performers__categories").distinct():
        event_lat, event_lon = radians(float(event.venue.latitude)), radians(float(event.venue.longitude))
        delta_lat = event_lat - radians(lat)
        delta_lon = event_lon - radians(lon)
        a = sin(delta_lat / 2) ** 2 + cos(radians(lat)) * cos(event_lat) * sin(delta_lon / 2) ** 2
        if 6371.0 * 2 * asin(min(1.0, sqrt(a))) > radius_km:
            continue
        for performer in event.performers.all():
            if performer.pk not in seen:
                seen.add(performer.pk)
                results.append((performer, event))
    return results


def _tempo_parts(event):
    """Envelope the selected musical components, using tag ranges before category defaults.

    A midpoint or average could describe a tempo that no selected genre actually uses.
    Keep the estimate derived so edits to curated ranges update existing events.
    """
    tags = list(event.tags.all())
    ranges = []
    for category in event.categories.all():
        selected = [tag for tag in tags if tag.category_id == category.pk] or [category]
        for item in selected:
            low, high = item.bpm_min, item.bpm_max
            if low is None:
                low, high = category.bpm_min, category.bpm_max
            if low is None or high is None:
                return None
            ranges.append((low, high))
    return (min(low for low, _ in ranges), max(high for _, high in ranges)) if ranges else None


def tempo_estimate(event):
    parts = _tempo_parts(event)
    return parts[:2] if parts else None


def _format_tempo(parts):
    if not parts:
        return "Varies"
    low, high = parts
    return f"{low}–{high} BPM"


def tempo_display(event):
    return _format_tempo(_tempo_parts(event))


def map_pins(events):
    """Serialize only already-filtered public results; no review notes or accounts."""
    pins = {}
    for event in events:
        venue = event.venue
        pin = pins.setdefault(venue.pk, {
            "venue_id": venue.pk, "name": venue.name, "latitude": float(venue.latitude),
            "longitude": float(venue.longitude), "categories": {}, "events": [],
        })
        categories = [{"id": c.pk, "name": c.name, "color": c.color} for c in event.categories.all()]
        tempo = _tempo_parts(event)
        pin["categories"].update({c["id"]: c for c in categories})
        pin["events"].append({
            "id": event.pk, "title": event.title, "starts_at": event.starts_at.isoformat(),
            "ends_at": event.ends_at.isoformat(), "timezone": venue.timezone,
            "categories": categories,
            "tags": [{"id": t.pk, "name": t.name, "category_id": t.category_id} for t in event.tags.all()],
            "tempo_estimate": tempo[:2] if tempo else None,
            "tempo_display": _format_tempo(tempo),
        })
    for pin in pins.values():
        pin["categories"] = sorted(pin["categories"].values(), key=lambda c: c["id"])
        pin["count"] = len(pin["events"])
    return list(pins.values())


@transaction.atomic
def follow_event(*, actor, event_id):
    require_user(actor)
    # Even owners cannot subscribe to unpublished records through this operation.
    event = public_events().get(pk=event_id)
    return EventFollow.objects.get_or_create(user=actor, event=event)[0]


@transaction.atomic
def unfollow_event(*, actor, event_id):
    require_user(actor)
    EventFollow.objects.filter(user=actor, event_id=event_id).delete()


@transaction.atomic
def report_event(*, actor, event_id, reason, explanation=""):
    require_user(actor)
    event = public_events().get(pk=event_id)
    report = EventReport(event=event, reporter=actor, reason=reason, explanation=explanation.strip())
    report.full_clean()
    report.save()
    return report


@transaction.atomic
def review_report(*, actor, report_id, status, resolution_note="", hide_event=False):
    require_permission(actor, "discovery.change_eventreport")
    if status not in {EventReport.Status.DISMISSED, EventReport.Status.ACTIONED}:
        raise ValidationError("Resolve a report as dismissed or actioned.")
    if hide_event and status != EventReport.Status.ACTIONED:
        raise ValidationError("A dismissed report cannot hide an event.")
    report = EventReport.objects.select_related("event").get(pk=report_id)
    if hide_event:
        require_permission(actor, "discovery.change_event")
        report.event.moderation_hidden = True
        report.event.save(update_fields=["moderation_hidden", "updated_at"])
    report.status, report.resolution_note = status, resolution_note.strip()
    report.reviewed_by, report.reviewed_at = actor, timezone.now()
    report.full_clean()
    report.save()
    return report


@transaction.atomic
def save_event_reference(*, actor, event_id, data, reference_id=None):
    event = Event.objects.get(pk=event_id)
    require_event_editor(actor, event)
    reference = (EventListeningReference.objects.get(pk=reference_id, event=event)
                 if reference_id else EventListeningReference(event=event))
    _assign(reference, data, REFERENCE_FIELDS)
    reference.full_clean()
    reference.save()
    return reference


@transaction.atomic
def delete_event_reference(*, actor, reference_id):
    reference = EventListeningReference.objects.select_related("event").get(pk=reference_id)
    require_event_editor(actor, reference.event)
    reference.delete()


@transaction.atomic
def save_genre_reference(*, actor, data, category_ids, tag_ids=(), reference_id=None):
    require_permission(actor, f"discovery.{'change' if reference_id else 'add'}_genrelisteningreference")
    categories, tags = classification(category_ids, tag_ids)
    reference = GenreListeningReference.objects.get(pk=reference_id) if reference_id else GenreListeningReference()
    _assign(reference, data, REFERENCE_FIELDS)
    reference.full_clean()
    reference.save()
    reference.categories.set(categories)
    reference.tags.set(tags)
    return reference
