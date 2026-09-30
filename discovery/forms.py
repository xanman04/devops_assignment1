"""Validate public/admin inputs before service-backed saves."""
from django import forms
from datetime import datetime
import re
from zoneinfo import ZoneInfo
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from . import models, services


class ClassificationForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(queryset=models.GenreCategory.objects.all())
    tags = forms.ModelMultipleChoiceField(queryset=models.GenreTag.objects.select_related("category"), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["categories"].initial = self.instance.categories.all()
            self.fields["tags"].initial = self.instance.tags.all()

    def clean(self):
        data = super().clean()
        if "categories" in data and "tags" in data:
            services.classification(data["categories"].values_list("pk", flat=True), data["tags"].values_list("pk", flat=True))
        return data


class VenueLocalDateTimeField(forms.SplitDateTimeField):
    """Interpret wall-clock input in the venue zone, with Django's DST checks."""
    venue_timezone = ZoneInfo("UTC")

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", forms.SplitDateTimeWidget(
            date_attrs={"type": "date"}, time_attrs={"type": "time", "step": "1"},
            date_format="%Y-%m-%d", time_format="%H:%M:%S",
        ))
        super().__init__(*args, **kwargs)

    def compress(self, data_list):
        with timezone.override(self.venue_timezone):
            return super().compress(data_list)

    def prepare_value(self, value):
        if isinstance(value, datetime) and timezone.is_aware(value):
            return value.astimezone(self.venue_timezone).replace(tzinfo=None)
        return super().prepare_value(value)


class EventForm(ClassificationForm):
    starts_at = VenueLocalDateTimeField(label="Start (venue local time)")
    ends_at = VenueLocalDateTimeField(label="End (venue local time)")
    cancelled = forms.BooleanField(required=False, help_text="Retain the event but remove it from upcoming results.")

    class Meta:
        model = models.Event
        fields = ["venue", "title", "description", "starts_at", "ends_at", "ticket_url", "categories", "tags", "cancelled", "moderation_hidden"]

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if actor is not None:
            self.fields.pop("moderation_hidden", None)
            choices = Q(review_status="approved") | Q(review_status="pending", submitted_by=actor)
            if self.instance.pk:
                choices |= Q(pk=self.instance.venue_id)
            self.fields["venue"].queryset = models.Venue.objects.filter(choices).order_by("name", "id")
        self.fields["cancelled"].initial = self.instance.cancelled_at is not None
        venue = self.instance.venue if self.instance.venue_id else None
        if self.is_bound:
            venue_id = self.data.get(self.add_prefix("venue"))
            try:
                # Respect the venue choices available to this particular form.
                venue = self.fields["venue"].queryset.filter(pk=int(venue_id)).first()
            except (TypeError, ValueError, OverflowError):
                venue = None
        elif self.initial.get("venue"):
            venue = self.fields["venue"].queryset.filter(pk=self.initial["venue"]).first()
        zone = ZoneInfo(venue.timezone if venue else "UTC")
        for name in ("starts_at", "ends_at"):
            self.fields[name].venue_timezone = zone
            self.fields[name].help_text = (
                "Enter the local date and time at the selected venue. "
                "Changing venue interprets these values in the new venue's timezone. "
                "Ambiguous or nonexistent daylight-saving times require a different time."
            )

    def clean(self):
        data = super().clean()
        if data.get("starts_at") and data.get("ends_at"):
            services.validate_event_times(data["starts_at"], data["ends_at"])
        venue = data.get("venue")
        if venue and venue.review_status == "rejected" and (not self.instance.pk or self.instance.venue_id != venue.pk):
            raise ValidationError("Choose an approved venue or propose a new location.")
        return data


class GenreReferenceForm(ClassificationForm):
    class Meta:
        model = models.GenreListeningReference
        fields = ["title", "artist_credit", "url", "kind", "display_order", "categories", "tags"]


class TempoRangeAdminForm(forms.ModelForm):
    bpm_max = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "180 or 200+", "inputmode": "text"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.bpm_max is not None:
            self.initial["bpm_max"] = f"{self.instance.bpm_max}{'+' if self.instance.bpm_max_open else ''}"

    def clean_bpm_max(self):
        value = self.cleaned_data["bpm_max"].strip()
        if not value and not self.fields["bpm_max"].required:
            return None
        if not re.fullmatch(r"[1-9][0-9]{0,2}\+?", value):
            raise ValidationError("Enter a BPM maximum from 1 to 200, or 200+.")
        number = int(value.rstrip("+"))
        if number > 200 or (value.endswith("+") and number != 200):
            raise ValidationError("The highest displayable maximum is 200+.")
        return number

    def clean(self):
        data = super().clean()
        if "bpm_max" in data:
            raw = self.data.get(self.add_prefix("bpm_max"), str(data["bpm_max"]))
            open_ended = str(raw).strip().endswith("+")
            data["bpm_max_open"] = open_ended
            self.instance.bpm_max_open = open_ended
        return data


class CategoryForm(TempoRangeAdminForm):
    class Meta:
        model = models.GenreCategory
        fields = ["name", "color", "description", "display_order", "bpm_min", "bpm_max"]


class TagForm(TempoRangeAdminForm):
    class Meta:
        model = models.GenreTag
        fields = ["category", "name", "description", "bpm_min", "bpm_max"]

    def clean(self):
        data = super().clean()
        if self.instance.pk and data.get("category"):
            services.validate_tag_move(models.GenreTag.objects.get(pk=self.instance.pk), data["category"].pk)
        return data


class ReportForm(forms.ModelForm):
    hide_event = forms.BooleanField(required=False)

    class Meta:
        model = models.EventReport
        fields = ["status", "resolution_note"]

    def clean(self):
        data = super().clean()
        if data.get("status") == "pending":
            raise ValidationError("Choose dismissed or actioned to resolve the report.")
        if data.get("hide_event") and data.get("status") != "actioned":
            raise ValidationError("Only actioned reports can hide an event.")
        return data


class VenueProposalForm(forms.ModelForm):
    class Meta:
        model = models.Venue
        fields = ["name", "address", "latitude", "longitude", "timezone"]
        help_texts = {"timezone": "IANA timezone, for example Europe/Paris. Events use this location's local time."}


class EventReportForm(forms.ModelForm):
    class Meta:
        model = models.EventReport
        fields = ["reason", "explanation"]


class EventReferenceForm(forms.ModelForm):
    class Meta:
        model = models.EventListeningReference
        fields = ["title", "artist_credit", "url", "kind", "display_order"]
