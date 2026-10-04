"""Representative listening links for every genre category and subgenre tag.

Each song is attached to the broad category (and, for subgenre examples, the tag it
represents), so genre pages and event pages can play a sample of that sound. Rerunning
adds anything missing and keeps later admin edits; existing genres are never changed.
Sources and method: DJ_SOURCES.md.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from discovery import services
from discovery.models import GenreCategory, GenreListeningReference, GenreTag

from ._genre_songs import SONGS


class Command(BaseCommand):
    help = "Add curated example songs to every genre category and subgenre (existing genres required)."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {category.name: category for category in GenreCategory.objects.all()}
        tags = {(tag.category.name, tag.name): tag for tag in GenreTag.objects.select_related("category")}
        created = extended = skipped = 0
        for order, song in enumerate(SONGS):
            category_ids, tag_ids = set(), set()
            for category_name, tag_name in song["where"]:
                category = categories.get(category_name)
                tag = tags.get((category_name, tag_name)) if tag_name else None
                if category is None or (tag_name and tag is None):
                    skipped += 1
                    continue
                category_ids.add(category.pk)
                if tag:
                    tag_ids.add(tag.pk)
            if not category_ids:
                continue
            reference = GenreListeningReference.objects.filter(url=song["url"]).first()
            if reference is None:
                services.classification(category_ids, tag_ids)
                reference = GenreListeningReference(title=song["title"], artist_credit=song["artist"],
                                                    url=song["url"], kind=song.get("kind", "track"), display_order=order)
                reference.full_clean()
                reference.save()
                created += 1
            elif not (category_ids <= set(reference.categories.values_list("pk", flat=True)) and
                      tag_ids <= set(reference.tags.values_list("pk", flat=True))):
                extended += 1
            reference.categories.add(*category_ids)
            if tag_ids:
                reference.tags.add(*tag_ids)
        self.stdout.write(self.style.SUCCESS(
            f"Genre songs: {created} created, {extended} extended to more genres, "
            f"{skipped} genre/subgenre pairs skipped (not in the database)."
        ))
