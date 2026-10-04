# Copyright © 2026 Xander Chen. All rights reserved.
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

http_url = URLValidator(schemes=["http", "https"])


def validate_timezone(value):
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValidationError("Use a valid IANA timezone, such as Europe/Paris.")


def validate_changes(value):
    """Validate snapshot structure; actor permissions belong to future services."""
    allowed = {"venue", "starts_at", "ends_at", "cancelled"}
    if not isinstance(value, dict) or not value or not set(value) <= allowed:
        raise ValidationError("Changes must contain supported event fields.")
    for key, change in value.items():
        if not isinstance(change, dict) or set(change) != {"before", "after"}:
            raise ValidationError("Each change requires before and after values.")
        if change["before"] == change["after"]:
            raise ValidationError("Include only fields whose values changed.")
        for snapshot in change.values():
            if key == "cancelled" and not isinstance(snapshot, bool):
                raise ValidationError("Cancellation snapshots must be booleans.")
            if key == "venue":
                required = {"id", "name", "address", "latitude", "longitude", "timezone"}
                if not isinstance(snapshot, dict) or set(snapshot) != required:
                    raise ValidationError("Venue changes require complete location snapshots.")
            if key in {"starts_at", "ends_at"}:
                from datetime import datetime, timedelta
                try:
                    parsed = datetime.fromisoformat(snapshot)
                    if parsed.utcoffset() != timedelta(0):
                        raise ValueError
                except (TypeError, ValueError):
                    raise ValidationError("Time snapshots must be ISO datetimes in UTC.")
