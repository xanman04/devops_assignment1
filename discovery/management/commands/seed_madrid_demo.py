"""Fictional music nights at real Madrid venues for a classroom demonstration.

Venue names/addresses and coordinates are reference data, not copied event listings.
Every title, artist name, description and poster is original fiction.
"""
from datetime import datetime, time, timedelta
from hashlib import sha256
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from discovery import models, services


ZONE = ZoneInfo("Europe/Madrid")
USERS = ("demo_organizer", "demo_alex", "demo_sam", "demo_jo", "demo_morgan")
# Coordinates: OpenStreetMap Nominatim venue or street-address matches, checked 2026-09-30.
# Club names/addresses cross-checked against venue directories; see README sources.
VENUES = {
    "fabrik": ("Fabrik", "Avenida de la Industria 82, Humanes de Madrid", "40.265301", "-3.840565"),
    "villanos": ("Sala Villanos", "Calle de Bernardino Obregón 18, Madrid", "40.403937", "-3.700005"),
    "siroco": ("Sala Siroco", "Calle de San Dimas 3, Madrid", "40.426920", "-3.707737"),
    "berlin": ("Café Berlín", "Costanilla de los Ángeles 20, Madrid", "40.419538", "-3.707964"),
    "elsol": ("Sala El Sol", "Calle de los Jardines 3, Madrid", "40.418979", "-3.701625"),
    "mondo": ("Mondo Disko", "Calle de Alcalá 20, Madrid", "40.417827", "-3.698938"),
    "riviera": ("La Riviera", "Paseo Bajo de la Virgen del Puerto, Madrid", "40.412955", "-3.722134"),
    "mon": ("Sala Mon", "Calle de Hilarión Eslava 36, Madrid", "40.435766", "-3.716496"),
    "specka": ("Specka", "Calle de Orense 26, Madrid", "40.451569", "-3.694916"),
    "bassement": ("The Bassement", "Calle de Galileo 26, Madrid", "40.432557", "-3.710202"),
    "goya": ("Goya Social Club", "Calle de Goya 43, Madrid", "40.425401", "-3.682926"),
    "lula": ("Lula Club", "Gran Vía 54, Madrid", "40.421235", "-3.707137"),
    "sotano": ("El Sótano", "Calle de las Maldonadas 6, Madrid", "40.410940", "-3.707705"),
    "clamores": ("Sala Clamores", "Calle de Alburquerque 14, Madrid", "40.431110", "-3.700993"),
}

# key, title, venue, weekday, week, start hour, length, categories, tags, art, fictional lineup, short pitch
# Weekday follows Python's Monday=0. Times mirror common afternoon/live and late-night club slots.
NIGHTS = [
    ("blue-hour", "Blue Hour Circuit", "mondo", 3, 0, 23, 6, ("House",), ("Deep House", "Progressive House"), "house", "Luna Vela · Cero Norte", "Deep, melodic house building into a late-night peak."),
    ("subsuelo", "Subsuelo / Frequencies", "bassement", 4, 0, 23, 7, ("Techno",), ("Hypnotic Techno", "Raw Techno"), "techno", "Eira Sanz · Teo Flux", "A stripped-back, rolling techno session for the long room."),
    ("naranja", "Naranja Subterránea", "siroco", 4, 0, 23, 6, ("Drum & Bass",), ("Liquid DnB", "Jungle"), "bass", "Mina Rota · Delta Sur", "Liquid selections give way to fast jungle breaks."),
    ("pulso", "Pulso de Tetuán", "specka", 4, 0, 23, 7, ("Techno", "Electro"), ("Acid Techno", "Electro"), "techno", "Nexo 44 · Mara Luz", "Acid lines, electro pressure and late-night techno."),
    ("tarde-club", "Tarde de Club", "berlin", 5, 0, 18, 5, ("House", "Nu Disco / Disco"), ("Funky House", "Nu Disco"), "house", "Solena · Roda", "An early session of warm grooves and disco-rooted house."),
    ("fractal", "Fractal / 140", "mon", 5, 0, 23, 7, ("Dubstep / 140", "Bass / Club"), ("Deep Dubstep", "UK Bass"), "bass", "Ivo Raíz · Nara 140", "Low-end pressure, spacious 140 and left-field club rhythms."),
    ("cromo", "Cromo Rojo", "fabrik", 5, 0, 22, 9, ("Hard Techno", "Hard Dance / Hardcore"), ("Hard Techno", "Hardstyle"), "techno", "Vanta R · Doble Fase", "A large-room night that climbs from driving techno to harder edges."),
    ("ritmos", "Ritmos Cruzados", "villanos", 5, 0, 20, 6, ("Latin Electronic", "House"), ("Latin Club", "Piano House"), "ambient", "Alba Brava · Pálida", "Latin percussion and house rhythms in a room-sized session."),
    ("cintas", "Cintas Magnéticas", "elsol", 5, 0, 21, 6, ("Indie Dance", "Nu Disco / Disco"), ("Indie Dance", "Italo Disco"), "ambient", "Lado B · Vera Modul", "Guitar-adjacent electronic dance and luminous disco."),
    ("neblina", "Neblina de Domingo", "berlin", 6, 0, 19, 4, ("Ambient / Experimental",), ("Ambient", "Downtempo"), "ambient", "Iria Nube · Cometa Gris", "A slower listening session of texture, space and soft pulse."),
    ("surco", "Surco y Señal", "specka", 3, 1, 22, 6, ("Electro", "Breaks / Breakbeat"), ("Modern Electro", "Breakbeat"), "bass", "Cinta 09 · Leo Vértice", "Breakbeat cuts and sharp electro turns."),
    ("otra-orilla", "La Otra Orilla", "siroco", 4, 1, 23, 6, ("UK Garage / Bassline", "Drum & Bass"), ("UK Garage", "Liquid DnB"), "bass", "Río K · Vale Senda", "Two-step swing flowing into soulful drum and bass."),
    ("presion", "Presión Continua", "bassement", 4, 1, 23, 7, ("Techno", "Hard Techno"), ("Raw Techno", "Hard Techno"), "techno", "Aro N · Prisma Cero", "Percussive hardgroove with a tougher final stretch."),
    ("patio", "Patio Eléctrico", "mondo", 4, 1, 23, 6, ("House", "Afro Electronic"), ("Deep House", "Amapiano"), "house", "Amara Sol · Duna K", "Warm house, polyrhythm and a late Afro-electronic turn."),
    ("luz-baja", "Luz Baja", "villanos", 5, 1, 20, 6, ("Indie Dance", "House"), ("Indie Dance", "Deep House"), "ambient", "Nila Mar · Bosco V", "A live-room feel that settles into low-slung house."),
    ("carbon", "Carbono", "fabrik", 5, 1, 22, 9, ("Techno", "Trance"), ("Peak-Time / Driving", "Progressive Trance"), "techno", "Cora 7 · Elian K", "Driving techno opening into a wide, melodic sunrise set."),
    ("disco-sombra", "Disco de Sombra", "elsol", 5, 1, 22, 6, ("Nu Disco / Disco",), ("Italo Disco", "Space Disco"), "ambient", "Lira Oeste · Polo Magnet", "Analog synths, space disco and a playful dancefloor."),
    ("marea", "Marea Baja", "riviera", 5, 1, 21, 7, ("Drum & Bass", "Breaks / Breakbeat"), ("Jungle", "Breaks"), "bass", "Kael Mar · Senda 22", "A broad-room bass night built around breaks and jungle."),
    ("norte", "Norte Magnético", "mon", 5, 1, 23, 7, ("Trance", "Psy-Trance"), ("Uplifting Trance", "Progressive Psy"), "house", "Vela D · Orión Azul", "A gradual climb from melodic trance into psychedelic momentum."),
    ("cierre", "Cierre en Azul", "berlin", 6, 1, 19, 5, ("House", "Ambient / Experimental"), ("Organic House", "Downtempo"), "house", "Luna Vela · Iria Nube", "A relaxed Sunday finish with layered electronic textures."),
    ("goya-sessions", "Goya Deep Sessions", "goya", 4, 0, 23, 6, ("House",), ("Deep House", "Funky House"), "house", "Mara Viento · Nico Valle", "A focused house night built around warm chords and patient grooves."),
    ("lula-pulse", "Lula Pulse", "lula", 5, 0, 23, 7, ("Techno",), ("Hypnotic Techno", "Peak-Time / Driving"), "techno", "Vera Hex · Óscar Lumen", "A pure techno arc from hypnotic loops to peak-time drive."),
    ("sotano-breaks", "Bajo el Suelo", "sotano", 4, 1, 22, 6, ("Drum & Bass",), ("Jungle", "Liquid DnB"), "bass", "Iria Break · Surco 5", "A compact bass-room session moving from liquid drums to rougher jungle."),
    ("clamores-afro", "Clamores en Movimiento", "clamores", 5, 1, 23, 6, ("Afro Electronic",), ("Afro House", "Amapiano"), "ambient", "Ada Kora · Selma Sur", "Polyrhythmic Afro-electronic selections for a late dancefloor."),
]


class Command(BaseCommand):
    help = "Seed clearly fictional Madrid events at real venues, using existing demo users and genre data."

    def add_arguments(self, parser):
        parser.add_argument("--refresh-dates", action="store_true", help="Move existing fixture nights to the next two-week schedule; normal change notices apply.")

    def handle(self, *args, **options):
        users = self._users()
        categories, tags = self._classification()
        created_venues = created_events = refreshed_events = 0
        with transaction.atomic():
            venues = {}
            for key, (name, address, latitude, longitude) in VENUES.items():
                venue = models.Venue.objects.filter(name=name, address=address).first()
                if venue is None:
                    venue = models.Venue(name=name, address=address, latitude=latitude, longitude=longitude,
                        timezone="Europe/Madrid", submitted_by=users[0], review_status="approved",
                        review_note="Classroom fixture: real venue coordinates checked against open map data; no organizer affiliation or safety verification is implied.")
                    venue.full_clean()
                    venue.save()
                    created_venues += 1
                elif venue.review_status != "approved":
                    raise CommandError(f"Existing venue {name} is not approved; resolve it in admin before seeding.")
                venues[key] = venue

            today = timezone.localdate(timezone=ZONE)
            for key, title, venue_key, weekday, week, hour, hours, category_names, tag_names, art, artists, pitch in NIGHTS:
                creator = users[int.from_bytes(sha256(key.encode()).digest()[:4], "big") % len(users)]
                poster_path = f"demo-posters/{key}.webp"
                event = models.Event.objects.filter(demo_poster=poster_path, creator=creator).first()
                day_offset = ((weekday - today.weekday() - 1) % 7) + 1 + week * 7
                starts = datetime.combine(today + timedelta(days=day_offset), time(hour), tzinfo=ZONE)
                ends = starts + timedelta(hours=hours)
                selected_categories = [categories[name].pk for name in category_names]
                selected_tags = [tags[(category, name)].pk for category in category_names for name in tag_names if (category, name) in tags]
                if len(selected_tags) != len(tag_names):
                    raise CommandError(f"Ambiguous or missing tag for {title}; seed aborted.")
                description = f"{pitch}\n\nLineup: {artists}."
                if event is None:
                    event = services.save_event(actor=creator, data={"venue": venues[venue_key], "title": title,
                        "description": description, "starts_at": starts, "ends_at": ends},
                        category_ids=selected_categories, tag_ids=selected_tags)
                    event.demo_poster = poster_path
                    event.save(update_fields=["demo_poster"])
                    created_events += 1
                else:
                    if "Fictional classroom demo listing." in event.description:
                        event.description = description
                        event.save(update_fields=["description"])
                    if options["refresh_dates"] and (event.starts_at != starts or event.ends_at != ends):
                        services.save_event(actor=creator, event_id=event.pk, data={"starts_at": starts, "ends_at": ends},
                            category_ids=event.categories.values_list("pk", flat=True),
                            tag_ids=event.tags.values_list("pk", flat=True))
                        refreshed_events += 1
        self.stdout.write(self.style.SUCCESS(
            f"Madrid demo: {created_venues} venues, {created_events} events created; {refreshed_events} event dates refreshed."
        ))
        self.stdout.write("All event titles, lineups, descriptions and posters are fictional. No accounts or genres were created.")

    def _users(self):
        users = list(get_user_model().objects.filter(username__in=USERS))
        by_name = {user.username: user for user in users}
        if set(by_name) != set(USERS) or any(user.email != f"{user.username}@example.invalid" for user in users):
            raise CommandError("First run seed_demo to create the five marked demo accounts; no accounts were changed.")
        return [by_name[name] for name in USERS]

    def _classification(self):
        category_names = {name for night in NIGHTS for name in night[7]}
        categories = {category.name: category for category in models.GenreCategory.objects.filter(name__in=category_names)}
        if set(categories) != category_names:
            raise CommandError("Curate the required broad electronic genres before seeding Madrid events.")
        tags = {(tag.category.name, tag.name): tag for tag in models.GenreTag.objects.select_related("category").filter(category__name__in=category_names)}
        for night in NIGHTS:
            for name in night[8]:
                matches = [key for key in tags if key[0] in night[7] and key[1] == name]
                if len(matches) != 1:
                    raise CommandError(f"Tag {name} for {night[1]} is missing or ambiguous; seed aborted.")
        return categories, tags
