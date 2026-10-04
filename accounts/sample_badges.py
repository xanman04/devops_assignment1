# Copyright © 2026 Xander Chen. All rights reserved.
"""Mock collection for the profile, so the layout and card effects can be judged before anything is earned.

Only event cards are stored. Achievements are never listed by hand: `achievements()` works them out from the event
cards, so an achievement can only appear when the cards that prove it are in the collection. Replace SAMPLE_EVENTS
with verified attendance records once check-ins exist."""

GENRE_COLOURS = {"Drum & Bass": "#FF7A00", "Techno": "#5B21B6", "House": "#1D4ED8", "Trance": "#9670F4", "Dubstep / 140": "#5A0F1A"}

# Events attended needed for each tier, lowest first.
TIERS = ((3, "Bronze"), (5, "Silver"), (10, "Gold"), (15, "Platinum"), (20, "Diamond"))
TIER_COLOURS = {"Bronze": "#cd7f32", "Silver": "#c4ccd8", "Gold": "#ffc933", "Platinum": "#d5e6ff", "Diamond": "#7ff0ff"}
TIER_RANK = {name: rank for rank, (_, name) in enumerate(TIERS)}

# Special names for some genres; any other genre is called "<genre> Fan".
GENRE_TITLES = {"Drum & Bass": "DnB Lover", "Techno": "Techno Head", "House": "House Regular", "Trance": "Trance Voyager"}
ALL_TITLE = "Scene Regular"
TOTAL_SLOTS = 20

_POSTERS = ("surco", "presion", "sotano-breaks", "naranja", "marea", "fractal", "blue-hour", "cromo", "carbon", "subsuelo",
            "techno", "house", "cintas", "ritmos", "lula-pulse", "tarde-club", "neblina", "norte", "otra-orilla", "patio",
            "pulso", "luz-baja", "goya-sessions", "disco-sombra", "clamores-afro", "cierre", "bass", "ambient")
_VENUES = ("Specka", "Sala Villanos", "Fabrik", "Café Berlín", "Lula Club", "Sala Mon", "Sala El Sol", "The Bassement", "Mondo Disko")
_NAMES = ("Surco y Señal", "Presión Continua", "Sótano Breaks", "Naranja Subterránea", "Marea Baja", "Fractal / 140", "Blue Hour Circuit",
          "Cromo Rojo", "Carbón", "Subsuelo", "Neon Pulse", "Luz Baja", "Cintas Magnéticas", "Ritmos Cruzados", "Lula Pulse",
          "Tarde de Club", "Neblina de Domingo", "Norte", "Otra Orilla", "Patio Abierto", "Pulso de Tetuán", "Goya Sessions",
          "Disco Sombra", "Clamores", "Cierre", "Bajo el Suelo", "Ambient Noche", "Kick Drum Club", "Aurora 130", "Subgrave",
          "Madrugada", "Terraza 2AM", "Pista Central")
_COUNTS = (("Drum & Bass", 15), ("Techno", 10), ("Trance", 5), ("House", 3))


def sample_events():
    events, k = [], 0
    for genre, count in _COUNTS:
        for _ in range(count):
            when = f"{(k * 3) % 27 + 1} {('Sep', 'Oct')[k % 2]}"
            events.append((_NAMES[k % len(_NAMES)], genre, f"{_VENUES[k % len(_VENUES)]} · {when}", f"demo-posters/{_POSTERS[k % len(_POSTERS)]}.webp"))
            k += 1
    return tuple(events)


def event_cards(events=None):
    return [{"kind": "event", "title": title, "genre": genre, "detail": detail, "poster": poster,
             "color": GENRE_COLOURS.get(genre, "#8d95a6"), "tier": "", "proof": []}
            for title, genre, detail, poster in (events if events is not None else sample_events())]


def achievements(cards):
    """Achievement cards earned by these event cards, each listing the cards that prove it."""
    events = [card for card in cards if card["kind"] == "event"]
    groups = [(ALL_TITLE, None, events)]
    for genre in dict.fromkeys(card["genre"] for card in events if card["genre"]):
        groups.append((GENRE_TITLES.get(genre, f"{genre} Fan"), genre, [card for card in events if card["genre"] == genre]))
    earned = []
    for title, genre, proof in groups:
        tier = next((name for needed, name in reversed(TIERS) if len(proof) >= needed), "")
        if tier:
            earned.append({"kind": "achievement", "title": title, "genre": genre or "", "tier": tier, "poster": "", "poster_id": None,
                           "color": TIER_COLOURS[tier],
                           "detail": f"{len(proof)} {genre + ' nights' if genre else 'events attended'}",
                           "proof": [{"title": card["title"], "detail": card["detail"]} for card in proof]})
    earned.sort(key=lambda badge: -TIER_RANK[badge["tier"]])
    return earned


def cards_for(user):
    """This person's event cards, newest event first, as the dicts the profile draws."""
    from discovery.models import EventCard
    rows = (EventCard.objects.filter(user=user).select_related("event__venue").prefetch_related("event__categories")
            .order_by("-event__starts_at", "-id"))
    cards = []
    for row in rows:
        event = row.event
        categories = list(event.categories.all())
        cards.append({"kind": "event", "title": event.title, "genre": categories[0].name if categories else "",
                      "detail": f"{event.venue.name} · {event.starts_at.day} {event.starts_at:%b}",
                      "poster": event.demo_poster, "poster_id": event.pk if event.poster else None,
                      "color": categories[0].color if categories else "#8d95a6", "tier": "", "proof": []})
    return cards


def collection(user):
    cards = cards_for(user)
    return achievements(cards) + cards
