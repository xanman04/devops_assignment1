"""Curated DJ discovery profiles; source and photo credits: DJ_SOURCES.md."""
from django.core.management.base import BaseCommand
from django.db import transaction

from discovery.models import DJProfile, GenreCategory


PROFILES = [
    ("Charlotte de Witte", "A driving techno sound built around stripped-back pressure and acid edges. Her KNTXT platform connects the records with a broader club community.",
     "https://charlottedewittemusic.com/", "charlotte_de_witte", "Alan Overbeek", "Charlotte_de_witte-1513626416.jpg", "CC BY-SA 4.0", ["Techno", "Hard Techno"]),
    ("Andy C", "A drum and bass pioneer known for fast, precise mixing and decades of sets and releases with RAM Records.",
     "https://www.ramrecords.com/artist/andy-c", "andy_c", "Stephen West", "Andy_C_live_in_2011_(cropped).jpg", "CC BY 2.0", ["Drum & Bass"]),
    ("Black Coffee", "South African DJ and producer whose house sets put African rhythms and soulful, melodic textures at the center.",
     "https://www.realblackcoffee.net/", "black_coffee", "DeepBluuue", "Black_Coffee_perfoming_at_Hï_Ibiza_in_June_2018.jpg", "CC0 1.0", ["Afro Electronic", "House"]),
    ("Skrillex", "A bass music producer whose work moves between dubstep, UK club rhythms and wider electronic styles.",
     "https://skrillex.com/pages/home", "skrillex", "Michael Nusbaum", "Skrillex.jpg", "CC BY 2.0", ["Dubstep / 140", "Bass / Club", "UK Garage / Bassline"]),
    ("Armin van Buuren", "A long-running voice in trance, from club sets to the A State of Trance radio show and festival stages.",
     "https://www.arminvanbuuren.com/biography/", "armin_van_buuren", "Web Summit / Sam Barnes / Sportsfile", "Armin_van_Buuren,_November_2025.jpg", "CC BY 4.0", ["Trance", "Mainstage / Commercial EDM"]),
    ("Peggy Gou", "House-rooted DJ and producer with a melodic, dancefloor-focused sound and her own Gudu Records label.",
     "https://www.xlrecordings.com/artists/peggy-gou", "peggy_gou", "Davide Guidone", "Peggy_Gou_2019.jpg", "Public domain", ["House", "Nu Disco / Disco"]),
    ("Carl Cox", "A veteran of acid house and techno whose sets bridge early rave history and contemporary underground club music.",
     "https://carlcox.com/biography/", "carl_cox", "Sergey Kozak", "Carl_Cox_@_ADE_2012.jpg", "CC BY 2.0", ["Techno", "House"]),
]


class Command(BaseCommand):
    help = "Add seven researched DJ profiles using existing genre categories; retain later admin edits."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {category.name: category for category in GenreCategory.objects.all()}
        created = existing = skipped = 0
        for order, (name, description, official_url, slug, credit, file_name, license_name, names) in enumerate(PROFILES):
            if any(category_name not in categories for category_name in names):
                skipped += 1
                continue
            profile, was_created = DJProfile.objects.get_or_create(name=name, defaults={
                "description": description, "official_url": official_url, "photo": f"djs/{slug}.webp",
                "photo_credit": credit,
                "photo_source_url": f"https://commons.wikimedia.org/wiki/File:{file_name}",
                "photo_license": license_name, "display_order": order,
            })
            if was_created:
                profile.categories.set(categories[category_name] for category_name in names)
            created += was_created
            existing += not was_created
        self.stdout.write(self.style.SUCCESS(f"DJ profiles: {created} created, {existing} retained, {skipped} skipped (missing categories)."))
