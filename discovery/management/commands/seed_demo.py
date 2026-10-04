# Copyright © 2026 Xander Chen. All rights reserved.
"""Explicit fictional fixtures. Never creates or edits genre classifications."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from discovery import models, services
from groups import models as group_models, services as groups


DEMO_PASSWORD = "Demo-music-2026!"
PEOPLE = {
    "organizer": "Demo Organizer",
    "alex": "Demo Alex",
    "sam": "Demo Sam",
    "jo": "Demo Jo",
    "morgan": "Demo Morgan",
}
VENUES = [
    ("Demo: Canal Room", "48.871000", "2.363000", "approved"),
    ("Demo: Left Bank Studio", "48.849000", "2.343000", "approved"),
    ("Demo: Northside Hall", "48.889000", "2.351000", "approved"),
    ("Demo: Proposed Space", "48.862000", "2.379000", "pending"),
    ("Demo: Rejected Proposal", "48.858000", "2.324000", "rejected"),
]


class Command(BaseCommand):
    help = "Add fictional local demo accounts/venues; optionally use existing category IDs for events/groups."

    def add_arguments(self, parser):
        parser.add_argument("--category", type=int, action="append", default=[],
                            help="Existing genre-category ID; repeat for mixed-genre examples. No genres are created.")
        parser.add_argument("--refresh-dates", action="store_true",
                            help="Move this fixture's existing events into the coming week; notify their followers normally.")

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                self.seed(options)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        self.stdout.write(self.style.SUCCESS(
            f"Created {self.created_users} accounts, {self.created_venues} venues, "
            f"{self.created_events} events, {self.created_groups} groups. Existing records were retained."
        ))
        self.stdout.write("Demo logins: " + ", ".join(f"demo_{key}" for key in PEOPLE))
        self.stdout.write(f"Password for newly created demo accounts: {DEMO_PASSWORD}")
        self.stdout.write("New demo accounts are ordinary users; this command grants no admin privileges.")
        if not options["category"]:
            self.stdout.write("No genre data changed. Events/groups were skipped; use --category ID after curating genres.")
        if self.skipped_groups:
            self.stdout.write("Some events are closed for new groups. Use --refresh-dates to move demo event times forward.")

    def seed(self, options):
        self.created_users = self.created_venues = self.created_events = self.created_groups = 0
        self.skipped_groups = False
        ids = list(dict.fromkeys(options["category"]))
        categories = list(models.GenreCategory.objects.filter(pk__in=ids).order_by("id"))
        if len(categories) != len(ids):
            raise CommandError("Every --category must identify an existing category. No data was added.")
        if options["refresh_dates"] and not ids:
            raise CommandError("--refresh-dates requires --category ID. No data was changed.")
        people = self.people()
        venues = self.venues(people["organizer"])
        if not categories:
            return
        category_ids = [category.pk for category in categories]
        tomorrow = timezone.localdate(timezone=ZoneInfo("Europe/Paris")) + timedelta(days=1)
        definitions = [
            ("Demo: Early Session", 0, 1, 19, [category_ids[0]]),
            ("Demo: Late Session", 0, 1, 23, category_ids),
            ("Demo: Weekend Meetup", 1, 3, 21, [category_ids[-1]]),
            ("Demo: Northside Night", 2, 5, 20, category_ids),
            ("Demo: Awaiting Venue Review", 3, 2, 19, [category_ids[0]]),
            ("Demo: Cancelled Listing", 1, 4, 20, [category_ids[0]]),
        ]
        events = []
        new_events = []
        for title, venue_index, day, hour, selection in definitions:
            event = models.Event.objects.filter(creator=people["organizer"], title=title).first()
            created = event is None
            starts_at = datetime.combine(tomorrow + timedelta(days=day), time(hour), tzinfo=ZoneInfo("Europe/Paris"))
            if created:
                event = services.save_event(actor=people["organizer"], data={
                    "venue": venues[venue_index], "title": title,
                    "description": "Fictional demo listing for interface testing. This is not a real event or destination.",
                    "starts_at": starts_at, "ends_at": starts_at + timedelta(hours=4),
                }, category_ids=selection)
                self.created_events += 1
            elif options["refresh_dates"]:
                event = services.save_event(actor=people["organizer"], event_id=event.pk,
                    data={"starts_at": starts_at, "ends_at": starts_at + timedelta(hours=4)},
                    category_ids=event.categories.values_list("pk", flat=True),
                    tag_ids=event.tags.values_list("pk", flat=True))
            events.append(event)
            new_events.append(created)
        self.social_examples(people, events[0])
        # Only newly created examples get initial follows/cancellation; reruns preserve user activity.
        if new_events[-1]:
            cancelled = events[-1]
            services.follow_event(actor=people["alex"], event_id=cancelled.pk)
            services.save_event(actor=people["organizer"], event_id=cancelled.pk, data={},
                category_ids=cancelled.categories.values_list("pk", flat=True), cancelled=True)

    def people(self):
        User = get_user_model()
        people = {}
        # Reject collisions before creating anything; existing passwords/profile fields are never reset.
        for key in PEOPLE:
            username = f"demo_{key}"
            existing = User.objects.filter(username__iexact=username).first()
            if existing and (existing.username != username or existing.email != f"{username}@example.invalid"):
                raise CommandError(f"Account {username} already exists without the demo marker. Nothing was changed.")
        for key, display_name in PEOPLE.items():
            username = f"demo_{key}"
            user = User.objects.filter(username=username).first()
            if user is None:
                user = User(username=username, display_name=display_name, email=f"{username}@example.invalid")
                user.set_password(DEMO_PASSWORD)
                user.full_clean()
                user.save()
                self.created_users += 1
            people[key] = user
        return people

    def venues(self, organizer):
        venues = []
        for name, latitude, longitude, status in VENUES:
            venue = models.Venue.objects.filter(name=name, submitted_by=organizer).first()
            if venue is None:
                # Synthetic fixture states, not a claim that a real location has been reviewed.
                venue = models.Venue(name=name, submitted_by=organizer,
                    address="Fictional demo venue — not a real address or destination.",
                    latitude=latitude, longitude=longitude, timezone="Europe/Paris", review_status=status,
                    review_note="Synthetic demo review state; no real venue verification was performed.")
                venue.full_clean()
                venue.save()
                self.created_venues += 1
            venues.append(venue)
        return venues

    def social_examples(self, people, event):
        if not services.public_events().filter(pk=event.pk, cancelled_at__isnull=True).exists() or event.starts_at <= timezone.now():
            self.skipped_groups = True
            return
        public, public_created = self.group(people["organizer"], event, "Demo: First Timers", "public", 4)
        private, private_created = self.group(people["morgan"], event, "Demo: Small Crew", "approval_required", 3)
        if public_created:
            groups.join_group(actor=people["alex"], group_id=public.pk)
            groups.post_message(actor=people["organizer"], group_id=public.pk,
                body="Demo message: let's compare plans before arranging an external group chat.")
            groups.post_message(actor=people["alex"], group_id=public.pk,
                body="Demo reply: I'm coming solo and would like some company.")
            services.follow_event(actor=people["alex"], event_id=event.pk)
        if private_created:
            offer = groups.request_join(actor=people["alex"], group_id=private.pk)
            groups.review_request(actor=people["morgan"], request_id=offer.pk, approve=True)
            groups.request_join(actor=people["sam"], group_id=private.pk)
            groups.post_message(actor=people["morgan"], group_id=private.pk,
                body="Demo private board: only current members can see this message.")

    def group(self, owner, event, name, mode, capacity):
        group = group_models.AttendanceGroup.objects.filter(event=event, name=name).first()
        if group:
            return group, False
        group = groups.save_group(actor=owner, data={"event": event, "name": name,
            "description": "Fictional demo group for testing optional solo-attendee coordination.",
            "capacity": capacity, "joining_mode": mode})
        self.created_groups += 1
        return group, True
