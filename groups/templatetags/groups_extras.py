from django import template

register = template.Library()


@register.filter
def avatar_hue(value):
    """A stable hue (0-359) per user id, so each person keeps the same avatar colour."""
    try:
        return (int(value) * 67 + 23) % 360
    except (TypeError, ValueError):
        return 210


@register.filter
def initial(value):
    text = str(value or "").strip()
    return text[:1].upper() or "?"
