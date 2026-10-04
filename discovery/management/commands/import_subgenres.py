# Copyright © 2026 Xander Chen. All rights reserved.
"""Import the author-curated electronic subgenre CSV into existing categories."""

import csv
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from discovery.models import GenreCategory, GenreTag


DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "fixtures" / "electronic_subgenres_v1.csv"
CATEGORY_ALIASES = {"EBM / Industrial": "Industrial / EBM"}
REQUIRED_COLUMNS = {"umbrella_genre", "subgenre", "bpm_min", "bpm_max", "pitch"}


def read_rows(path):
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
                raise CommandError(f"CSV must contain: {', '.join(sorted(REQUIRED_COLUMNS))}.")
            rows = list(reader)
    except OSError as error:
        raise CommandError(f"Cannot read CSV: {error}") from error
    if not rows:
        raise CommandError("The CSV has no subgenre rows.")
    return rows


def parse_bpm(row, line):
    raw_max = (row["bpm_max"] or "").strip()
    try:
        minimum = int(row["bpm_min"].strip())
        maximum = int(raw_max)
    except (ValueError, AttributeError) as error:
        raise CommandError(f"Row {line}: BPM bounds must be integers.") from error
    if minimum == 0:
        if "no fixed BPM" not in (row.get("bpm_note") or ""):
            raise CommandError(f"Row {line}: zero BPM requires an explicit no-fixed-BPM note.")
        return None, None
    if minimum < 1 or maximum < minimum:
        raise CommandError(f"Row {line}: invalid BPM range {minimum}–{raw_max}.")
    return minimum, maximum


class Command(BaseCommand):
    help = "Import electronic subgenre tags from the curated CSV; existing category records are required."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=Path, default=DEFAULT_SOURCE,
                            help="CSV path (defaults to the committed electronic subgenre source).")
        parser.add_argument("--dry-run", action="store_true", help="Validate and report without writing tags.")
        parser.add_argument("--update", action="store_true",
                            help="Replace existing tag descriptions/BPM with CSV values; default is to protect edits.")

    def handle(self, *args, **options):
        rows = read_rows(options["file"])
        categories = {category.name.casefold(): category for category in GenreCategory.objects.all()}
        existing = {(tag.category_id, tag.name.casefold()): tag for tag in GenreTag.objects.all()}
        seen = set()
        prepared = []
        for line, row in enumerate(rows, 2):
            source_category = (row["umbrella_genre"] or "").strip()
            name = (row["subgenre"] or "").strip()
            description = (row["pitch"] or "").strip()
            category_name = CATEGORY_ALIASES.get(source_category, source_category)
            category = categories.get(category_name.casefold())
            if not category:
                raise CommandError(f"Row {line}: category {source_category!r} has no matching database category.")
            if not name or len(name) > 80 or not description:
                raise CommandError(f"Row {line}: subgenre name (max 80 characters) and pitch are required.")
            key = (category.pk, name.casefold())
            if key in seen:
                raise CommandError(f"Row {line}: duplicate subgenre {name!r} in {category.name!r}.")
            seen.add(key)
            low, high = parse_bpm(row, line)
            values = {"name": name, "description": description, "bpm_min": low,
                      "bpm_max": high}
            tag = existing.get(key)
            changed = tag is not None and any(getattr(tag, field) != value for field, value in values.items())
            if changed and not options["update"]:
                raise CommandError(
                    f"Row {line}: existing {category.name} / {name} differs from the CSV. "
                    "No tags were changed; use --update to replace curated edits."
                )
            prepared.append((category, tag, values, changed))

        created = sum(tag is None for _, tag, _, _ in prepared)
        updated = sum(changed for _, _, _, changed in prepared)
        unchanged = len(prepared) - created - updated
        if not options["dry_run"]:
            try:
                with transaction.atomic():
                    for category, tag, values, changed in prepared:
                        if tag is not None and not changed:
                            continue
                        tag = tag or GenreTag(category=category)
                        for field, value in values.items():
                            setattr(tag, field, value)
                        tag.full_clean()
                        tag.save()
            except ValidationError as error:
                raise CommandError(" ".join(error.messages)) from error
        status = "Would create" if options["dry_run"] else "Created"
        self.stdout.write(self.style.SUCCESS(
            f"{status} {created} tags; {'would update' if options['dry_run'] else 'updated'} "
            f"{updated}; unchanged {unchanged}; source rows {len(prepared)}."
        ))
        self.stdout.write(f"Category BPM fallbacks: {sum(values['bpm_min'] is None for _, _, values, _ in prepared)}.")
        self.stdout.write("CSV pitch was used verbatim as the tag description (after trimming outer whitespace).")
