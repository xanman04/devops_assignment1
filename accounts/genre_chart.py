# Copyright © 2026 Xander Chen. All rights reserved.
"""Geometry for the genre chart on the profile: one spoke per genre category, coloured by the genre, reaching
further out the more that genre is attended. Everything is worked out here so the page only draws shapes."""
import math

SIZE = 320
CENTRE = SIZE / 2
RADIUS = 112
RINGS = (0.25, 0.5, 0.75, 1.0)

# Mock values (0 to 1) until real attendance exists; spread so the shape looks like a person with a taste.
SAMPLE_VALUES = (0.12, 0.5, 0.18, 0.08, 0.28, 0.88, 0.22, 0.42, 0.34, 0.2, 0.1, 0.3,
                 0.16, 0.52, 0.96, 0.62, 0.46, 0.9, 0.36, 0.2, 0.3, 0.4)


def _point(index, count, fraction):
    angle = -math.pi / 2 + 2 * math.pi * index / count
    return CENTRE + RADIUS * fraction * math.cos(angle), CENTRE + RADIUS * fraction * math.sin(angle)


def _points(pairs):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in pairs)


def values_from_cards(categories, cards):
    """0 to 1 per category: that genre's share of the most-attended genre."""
    counts = [sum(1 for card in cards if card["kind"] == "event" and card["genre"] == category.name) for category in categories]
    top = max(counts, default=0)
    return [count / top if top else 0.0 for count in counts]


def build(categories, values=None):
    """categories: objects with .name and .color, in the order they sit around the circle."""
    categories = list(categories)
    count = len(categories)
    if not count:
        return None
    values = list(values) if values is not None else [SAMPLE_VALUES[i % len(SAMPLE_VALUES)] for i in range(count)]
    values = [min(max(float(value), 0.0), 1.0) for value in values]
    shown = [_point(i, count, max(values[i], 0.05)) for i in range(count)]     # a small stub so empty genres stay visible
    chart = {"size": SIZE, "centre": CENTRE, "vertices": [], "sectors": [], "spokes": [], "rings": []}
    for i, category in enumerate(categories):
        outer = _point(i, count, 1)
        x, y = shown[i]
        nx, ny = shown[(i + 1) % count]
        chart["vertices"].append({"name": category.name, "color": category.color, "x": round(x, 1), "y": round(y, 1),
                                  "ox": round(outer[0], 1), "oy": round(outer[1], 1), "percent": round(values[i] * 100)})
        chart["sectors"].append({"color": category.color, "points": _points([(CENTRE, CENTRE), (x, y), (nx, ny)])})
        chart["spokes"].append({"color": category.color, "x": round(outer[0], 1), "y": round(outer[1], 1)})
    chart["outline"] = _points(shown)
    chart["rings"] = [_points([_point(i, count, fraction) for i in range(count)]) for fraction in RINGS]
    ranked = sorted(chart["vertices"], key=lambda vertex: vertex["percent"], reverse=True)[:3]
    chart["top"] = [{"name": vertex["name"], "color": vertex["color"]} for vertex in ranked if vertex["percent"] > 0]
    return chart
