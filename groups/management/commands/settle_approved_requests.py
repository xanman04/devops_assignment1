"""Add people whose join request was approved earlier but never accepted, when approval alone is now enough.

Since owner approval adds the applicant straight away, an old "approved" request from someone with no other group
for the event, in a group with room, should already have joined. This completes those; people who are in another group
for the event keep their offer. Safe to run repeatedly."""
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from groups import services
from groups.models import JoinRequest, Membership


class Command(BaseCommand):
    help = "Complete approved requests that no longer need the applicant's acceptance."

    def handle(self, *args, **options):
        done = left = 0
        for request in JoinRequest.objects.filter(status="approved").select_related("applicant", "group").order_by("reviewed_at", "id"):
            group = request.group
            elsewhere = Membership.objects.filter(user=request.applicant, group__event_id=group.event_id).exists()
            if elsewhere or group.memberships.count() >= group.capacity:
                left += 1
                continue
            try:
                services.accept_offer(actor=request.applicant, request_id=request.pk)
            except ValidationError as error:
                left += 1
                self.stdout.write(f"kept offer for {request.applicant.username} in {group.name}: {' '.join(error.messages)}")
                continue
            done += 1
            self.stdout.write(f"added {request.applicant.username} to {group.name}")
        self.stdout.write(f"{done} added, {left} left as offers")
