"""Read-only map endpoint; write operations use admin/services for now."""
from datetime import datetime
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .services import map_pins, search_events


def _date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValidationError("Dates must be ISO datetimes including a timezone.")


def _csv(value):
    return value.split(",") if value else []


@require_GET
def map_events(request):
    try:
        events = search_events(
            starts_at=_date(request.GET.get("start")), ends_at=_date(request.GET.get("end")),
            category_ids=_csv(request.GET.get("categories")), tag_ids=_csv(request.GET.get("tags")),
            match=request.GET.get("match", "any"),
            bounds=_csv(request.GET["bounds"]) if "bounds" in request.GET else None,
        )
        results = list(events[:1001])
        if len(results) > 1000:
            return JsonResponse({"error": "Too many events; narrow the dates or map area."}, status=400)
        return JsonResponse({"venues": map_pins(results)})
    except ValidationError as error:
        return JsonResponse({"errors": error.messages}, status=400)
