# Copyright © 2026 Xander Chen. All rights reserved.
"""Discovery records. Use discovery.services for authorized business operations."""
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from .validators import http_url, validate_changes, validate_timezone

USER = settings.AUTH_USER_MODEL


def event_poster_path(instance, filename):
    return f"events/{uuid4().hex}{Path(filename).suffix.lower()}"


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TempoRange(models.Model):
    bpm_min = models.PositiveIntegerField(null=True, blank=True)
    bpm_max = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        abstract = True
        constraints = [models.CheckConstraint(
            condition=(Q(bpm_min__isnull=True, bpm_max__isnull=True) |
                       Q(bpm_min__isnull=False, bpm_max__isnull=False,
                         bpm_min__gt=0, bpm_max__gte=F("bpm_min"))),
            name="%(app_label)s_%(class)s_bpm_range",
        )]

    @property
    def bpm_display(self):
        if self.bpm_min is None or self.bpm_max is None:
            return "Varies"
        return f"{self.bpm_min}–{self.bpm_max} BPM"


class GenreCategory(TempoRange):
    name = models.CharField(max_length=80, unique=True)
    color = models.CharField(max_length=7, validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$")])
    description = models.TextField()
    display_order = models.PositiveIntegerField(default=0)

    class Meta(TempoRange.Meta):
        verbose_name_plural = "genre categories"
        ordering = ["display_order", "name"]
        constraints = TempoRange.Meta.constraints + [
            models.UniqueConstraint(Lower("name"), name="category_name_case_unique"),
        ]

    def clean(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "A name is required."})

    def __str__(self):
        return self.name


class GenreTag(TempoRange):
    category = models.ForeignKey(GenreCategory, on_delete=models.PROTECT, related_name="tags")
    name = models.CharField(max_length=80)
    description = models.TextField()

    class Meta(TempoRange.Meta):
        constraints = TempoRange.Meta.constraints + [
            models.UniqueConstraint(fields=["category", "name"], name="tag_category_name_unique"),
            models.UniqueConstraint(Lower("name"), "category", name="tag_name_case_unique"),
        ]

    def clean(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "A name is required."})

    def __str__(self):
        return self.name


class DJProfile(models.Model):
    """One curated profile for an artist, DJ, producer, or overlapping roles."""

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField()
    official_url = models.URLField(max_length=2048, blank=True, validators=[http_url])
    photo = models.CharField(max_length=160, blank=True, help_text="Optional bundled static image path.")
    photo_credit = models.CharField(max_length=200, blank=True)
    photo_source_url = models.URLField(max_length=2048, blank=True, validators=[http_url])
    photo_license = models.CharField(max_length=80, blank=True)
    origin = models.CharField(max_length=120, blank=True, help_text="Hometown and country, for example Ghent, Belgium.")
    active_since = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1900), MaxValueValidator(2100)])
    labels = models.CharField(max_length=200, blank=True, help_text="Main labels, separated by commas.")
    display_order = models.PositiveIntegerField(default=0)
    categories = models.ManyToManyField(GenreCategory, related_name="djs")

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "artist / DJ profile"
        verbose_name_plural = "artist / DJ profiles"

    def __str__(self):
        return self.name


class DJSocialLink(models.Model):
    """An official social or streaming profile shown beside a profile's website link."""

    class Platform(models.TextChoices):
        INSTAGRAM = "instagram", "Instagram"
        YOUTUBE = "youtube", "YouTube"
        SOUNDCLOUD = "soundcloud", "SoundCloud"
        SPOTIFY = "spotify", "Spotify"

    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name="social_links")
    platform = models.CharField(max_length=10, choices=Platform)
    url = models.URLField(max_length=2048, validators=[http_url])

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["dj", "platform"], name="dj_social_one_per_platform")]

    def __str__(self):
        return f"{self.dj.name}: {self.get_platform_display()}"


class DJMediaLink(models.Model):
    """A curated recording or set linked from an artist / DJ profile."""

    class Kind(models.TextChoices):
        TRACK = "track", "Track"
        SET = "set", "Set"

    class Platform(models.TextChoices):
        SOUNDCLOUD = "soundcloud", "SoundCloud"
        YOUTUBE = "youtube", "YouTube"

    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name="media_links")
    title = models.CharField(max_length=200)
    url = models.URLField(max_length=2048, validators=[http_url])
    kind = models.CharField(max_length=5, choices=Kind)
    platform = models.CharField(max_length=10, choices=Platform)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]
        constraints = [models.UniqueConstraint(fields=["dj", "url"], name="dj_media_unique_url")]

    def __str__(self):
        return f"{self.dj.name}: {self.title}"


class Venue(Timestamped):
    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    name = models.CharField(max_length=160)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timezone = models.CharField(max_length=64, validators=[validate_timezone])
    submitted_by = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="submitted_venues")
    review_status = models.CharField(max_length=8, choices=ReviewStatus, default=ReviewStatus.PENDING, db_index=True)
    reviewed_by = models.ForeignKey(USER, on_delete=models.PROTECT, null=True, blank=True, related_name="reviewed_venues")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(latitude__gte=-90, latitude__lte=90), name="venue_latitude_range"),
            models.CheckConstraint(condition=Q(longitude__gte=-180, longitude__lte=180), name="venue_longitude_range"),
            models.CheckConstraint(condition=Q(review_status__in=["pending", "approved", "rejected"]), name="venue_valid_status"),
        ]

    def __str__(self):
        return self.name


class Event(Timestamped):
    creator = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="created_events")
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="events")
    title = models.CharField(max_length=200)
    description = models.TextField()
    demo_poster = models.CharField(max_length=120, blank=True, default="", help_text="Bundled event poster path.")
    poster = models.ImageField(upload_to=event_poster_path, blank=True, help_text="Uploaded event poster; overrides bundled demo artwork.")
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(db_index=True)
    ticket_url = models.URLField(max_length=2048, blank=True, validators=[http_url])
    cancelled_at = models.DateTimeField(null=True, blank=True)
    moderation_hidden = models.BooleanField(default=False)
    categories = models.ManyToManyField(GenreCategory, through="EventCategory", related_name="events")
    tags = models.ManyToManyField(GenreTag, through="EventTag", related_name="events", blank=True)
    performers = models.ManyToManyField(DJProfile, related_name="events", blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(ends_at__gt=F("starts_at")), name="event_end_after_start")]

    def __str__(self):
        return self.title


class EventCategory(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    category = models.ForeignKey(GenreCategory, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "category"], name="event_category_unique")]


class EventTag(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    tag = models.ForeignKey(GenreTag, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "tag"], name="event_tag_unique")]


class ListeningReference(models.Model):
    class Kind(models.TextChoices):
        TRACK = "track", "Track"
        SET = "set", "Set"
        ARTIST_PAGE = "artist_page", "Artist page"

    title = models.CharField(max_length=200)
    artist_credit = models.CharField(max_length=200)
    url = models.URLField(max_length=2048, validators=[http_url])
    kind = models.CharField(max_length=11, choices=Kind)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ["display_order", "id"]
        constraints = [models.CheckConstraint(condition=Q(kind__in=["track", "set", "artist_page"]), name="%(class)s_valid_kind")]

    @property
    def platform(self):
        """Where the link leads, derived from its host; used for the badge on listing rows."""
        host = urlsplit(self.url).netloc.lower()
        if "youtube.com" in host or "youtu.be" in host:
            return "youtube"
        if "soundcloud.com" in host:
            return "soundcloud"
        if "spotify.com" in host:
            return "spotify"
        return "link"

    @property
    def platform_label(self):
        return {"youtube": "YouTube", "soundcloud": "SoundCloud", "spotify": "Spotify"}.get(self.platform, "Listen")


class EventListeningReference(ListeningReference):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="listening_references")


class GenreListeningReference(ListeningReference):
    categories = models.ManyToManyField(GenreCategory, through="GenreReferenceCategory", related_name="listening_references")
    tags = models.ManyToManyField(GenreTag, through="GenreReferenceTag", related_name="listening_references", blank=True)


class GenreReferenceCategory(models.Model):
    reference = models.ForeignKey(GenreListeningReference, on_delete=models.CASCADE)
    category = models.ForeignKey(GenreCategory, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["reference", "category"], name="genre_reference_category_unique")]


class GenreReferenceTag(models.Model):
    reference = models.ForeignKey(GenreListeningReference, on_delete=models.CASCADE)
    tag = models.ForeignKey(GenreTag, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["reference", "tag"], name="genre_reference_tag_unique")]


class EventReport(models.Model):
    class Reason(models.TextChoices):
        INCORRECT = "incorrect_information", "Incorrect information"
        SPAM = "spam_scam", "Spam or scam"
        SAFETY = "safety_concern", "Safety concern"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DISMISSED = "dismissed", "Dismissed"
        ACTIONED = "actioned", "Actioned"

    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="reports")
    reporter = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="event_reports")
    reason = models.CharField(max_length=24, choices=Reason)
    explanation = models.TextField(blank=True)
    status = models.CharField(max_length=9, choices=Status, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(USER, on_delete=models.PROTECT, null=True, blank=True, related_name="reviewed_reports")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(status__in=["pending", "dismissed", "actioned"]), name="report_valid_status"),
            models.CheckConstraint(condition=Q(reason__in=["incorrect_information", "spam_scam", "safety_concern", "other"]), name="report_valid_reason"),
        ]


class EventFollow(models.Model):
    user = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="event_follows")
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="follows")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "event"], name="event_follow_unique")]


class EventChange(models.Model):
    class Kind(models.TextChoices):
        EVENT_EDIT = "event_edit", "Event edit"
        VENUE_EDIT = "venue_details_edit", "Venue details edit"

    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="changes")
    actor = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="event_changes")
    created_at = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=18, choices=Kind)
    changes = models.JSONField(validators=[validate_changes])

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(kind__in=["event_edit", "venue_details_edit"]), name="event_change_valid_kind")]


class EventCard(models.Model):
    """An event a person has been verified at. The profile collection and its achievements are built from these.

    Nothing creates them yet (check-in is not built); `seed_attendance` fills them for demo accounts."""

    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="event_cards")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="cards")
    collected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "event"], name="event_card_unique")]

