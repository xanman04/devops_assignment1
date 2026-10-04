"""Curated DJ discovery profiles; source and photo credits: DJ_SOURCES.md."""
from django.core.management.base import BaseCommand
from django.db import transaction

from discovery.models import DJMediaLink, DJProfile, DJSocialLink, GenreCategory
from ._dj_media import MEDIA
from ._dj_profiles import DETAILS


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
    help = "Add seven researched DJ profiles and their listening links using existing genre categories; retain later admin edits."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {category.name: category for category in GenreCategory.objects.all()}
        created = existing = skipped = media_created = 0
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
            details = DETAILS.get(name, {})
            # Fill only blank facts so later admin edits are kept.
            changed = [field for field in ("origin", "active_since", "labels")
                       if details.get(field) and not getattr(profile, field)]
            for field in changed:
                setattr(profile, field, details[field])
            if changed:
                profile.save(update_fields=changed)
            for platform, url in details.get("social", {}).items():
                DJSocialLink.objects.get_or_create(dj=profile, platform=platform, defaults={"url": url})
            for link_order, (kind, title, platform, url) in enumerate(MEDIA.get(name, [])):
                link, link_created = DJMediaLink.objects.get_or_create(dj=profile, url=url, defaults={
                    "kind": kind, "title": title, "platform": platform, "display_order": link_order,
                })
                # The seed owns the order of the links it lists (most popular first);
                # titles, other fields and curator-added links are never touched.
                if not link_created and link.display_order != link_order:
                    link.display_order = link_order
                    link.save(update_fields=["display_order"])
                media_created += link_created
            created += was_created
            existing += not was_created
        self.stdout.write(self.style.SUCCESS(
            f"DJ profiles: {created} created, {existing} retained, {skipped} skipped (missing categories); "
            f"{media_created} listening links added."
        ))
