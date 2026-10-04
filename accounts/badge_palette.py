"""Foil colours for a badge, taken from the badge itself so the shimmer matches what is on the card.

For a poster, the three most prominent hues in the picture are used (bright, saturated versions of them). For a
badge without a picture, hues are spread around its own colour."""
import colorsys
from collections import defaultdict
from functools import lru_cache

from django.contrib.staticfiles import finders
from PIL import Image

BINS = 12


def _hex(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, min(max(s, 0), 1), min(max(v, 0), 1))
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def _hue_of(colour):
    colour = colour.lstrip("#")
    r, g, b = (int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hsv(r, g, b)


def from_colour(colour):
    """Three foil colours around one base colour."""
    h, s, v = _hue_of(colour)
    s, v = max(s, 0.7), max(v, 0.9)
    return [_hex(h - 0.08, s, v), _hex(h + 0.02, s, v), _hex(h + 0.1, s, v)]


@lru_cache(maxsize=256)
def from_poster(static_path, fallback_colour):
    """Foil colours for a poster bundled under static/. Falls back to the badge colour if the picture is unusable."""
    path = finders.find(static_path) if static_path else None
    if not path:
        return from_colour(fallback_colour)
    try:
        with Image.open(path) as source:
            image = source.convert("RGB")
            image.thumbnail((64, 64))
            pixels = list(image.getdata())
    except OSError:
        return from_colour(fallback_colour)
    weight, hue_sum, sat_sum, val_sum = defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float)
    for r, g, b in pixels:
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.28 or v < 0.22:
            continue                                     # greys and near-black say nothing about the picture's colour
        w = s * v
        slot = int(h * BINS) % BINS
        weight[slot] += w
        hue_sum[slot] += h * w
        sat_sum[slot] += s * w
        val_sum[slot] += v * w
    chosen = []
    for slot in sorted(weight, key=weight.get, reverse=True):
        if all(min((slot - other) % BINS, (other - slot) % BINS) >= 2 for other in chosen):
            chosen.append(slot)
        if len(chosen) == 3:
            break
    colours = [_hex(hue_sum[s] / weight[s], min(1, sat_sum[s] / weight[s] * 1.1 + 0.1), max(val_sum[s] / weight[s], 0.88))
               for s in chosen]
    for extra in from_colour(fallback_colour):
        if len(colours) >= 3:
            break
        colours.append(extra)
    return colours[:3]


TIER_PALETTES = {
    "Bronze": ["#d9893f", "#f2b27a", "#a5551c"],
    "Silver": ["#d7dde8", "#ffffff", "#9eaabd"],
    "Gold": ["#ffd34d", "#fff2a6", "#e6a100"],
    "Platinum": ["#cfe4ff", "#f1e4ff", "#9fd0ff"],
    "Diamond": ["#4fe3ff", "#ff8fd8", "#8dffd0"],
}


def for_badge(badge):
    """badge: one of the dicts in sample_badges (poster path, colour, tier)."""
    if badge.get("tier") in TIER_PALETTES:
        return TIER_PALETTES[badge["tier"]]
    if badge.get("poster"):
        return from_poster(badge["poster"], badge["color"])
    return from_colour(badge["color"])
