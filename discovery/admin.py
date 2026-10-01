from django.contrib import admin
from django import forms
from config.admin import SchemaReadOnlyAdmin
from . import models, services
from .forms import CategoryForm, EventForm, GenreReferenceForm, ReportForm, TagForm


def apply_saved(instance, saved):
    # Admin subsequently logs this same object and builds its edit URL.
    instance.__dict__.update(saved.__dict__)


class RetainedAdmin(admin.ModelAdmin):
    """No bulk edits/deletions bypassing the services and their history."""
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False


class TempoReferenceAdmin(RetainedAdmin):
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for name, label in (("bpm_min", "Typical BPM minimum"), ("bpm_max", "Typical BPM maximum")):
            if name in form.base_fields:
                form.base_fields[name].label = label
                form.base_fields[name].required = True
                form.base_fields[name].help_text = (
                    "Admin-curated reference range used to estimate event tempo automatically. "
                    "Enter both numeric bounds; event creators never enter BPM."
                )
        return form


@admin.register(models.GenreCategory)
class CategoryAdmin(TempoReferenceAdmin):
    form = CategoryForm
    list_display = ("name", "color", "bpm_display", "display_order")
    search_fields = ("name",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        color = form.base_fields["color"]
        color.widget = forms.TextInput(attrs={"placeholder": "#RRGGBB", "pattern": "#[0-9a-fA-F]{6}"})
        color.help_text = "Enter a six-digit hex color, such as #367BF5. This colors map pins and genre labels."
        return form

    def save_model(self, request, obj, form, change):
        apply_saved(obj, services.save_category(actor=request.user, category_id=obj.pk, data=form.cleaned_data))


@admin.register(models.GenreTag)
class TagAdmin(TempoReferenceAdmin):
    form = TagForm
    list_display = ("name", "category", "bpm_display")
    list_filter = ("category",)
    search_fields = ("name",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.bpm_min is None and obj.bpm_max is None:
            for field in ("bpm_min", "bpm_max"):
                form.base_fields[field].required = False
            form.base_fields["bpm_max"].help_text = (
                "Leave both bounds blank to use the parent category's BPM range, "
                "or enter a tag-specific range."
            )
        return form

    def save_model(self, request, obj, form, change):
        apply_saved(obj, services.save_tag(actor=request.user, tag_id=obj.pk, data=form.cleaned_data))


@admin.register(models.DJProfile)
class DJProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order")
    search_fields = ("name", "description")
    filter_horizontal = ("categories",)


@admin.register(models.Venue)
class VenueAdmin(RetainedAdmin):
    list_display = ("name", "review_status", "timezone", "submitted_by")
    list_filter = ("review_status",)
    search_fields = ("name", "address")
    readonly_fields = ("submitted_by", "reviewed_by", "reviewed_at", "created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        return fields if request.user.has_perm("discovery.change_venue") else fields + ("review_status", "review_note")

    def save_model(self, request, obj, form, change):
        apply_saved(obj, services.save_venue(actor=request.user, venue_id=obj.pk,
            data={key: form.cleaned_data[key] for key in services.VENUE_FIELDS},
            review_status=form.cleaned_data.get("review_status"), review_note=form.cleaned_data.get("review_note", "")))


@admin.register(models.Event)
class EventAdmin(RetainedAdmin):
    form = EventForm
    list_display = ("title", "venue", "starts_at", "cancelled_at", "moderation_hidden")
    list_filter = ("moderation_hidden", "venue__review_status")
    search_fields = ("title", "venue__name")
    readonly_fields = ("creator", "typical_tempo", "created_at", "updated_at")

    @admin.display(description="Typical tempo estimate (automatic)")
    def typical_tempo(self, obj):
        if not obj or not obj.pk:
            return "Calculated after saving the selected categories and tags."
        return services.tempo_display(obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "venue" and not request.user.has_perm("discovery.change_event"):
            from django.db.models import Q
            kwargs["queryset"] = models.Venue.objects.filter(
                Q(review_status="approved") | Q(review_status="pending", submitted_by=request.user)
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        return fields if request.user.has_perm("discovery.change_event") else fields + ("moderation_hidden",)

    def save_model(self, request, obj, form, change):
        apply_saved(obj, services.save_event(
            actor=request.user, event_id=obj.pk,
            data={key: form.cleaned_data[key] for key in services.EVENT_FIELDS},
            category_ids=form.cleaned_data["categories"].values_list("pk", flat=True),
            tag_ids=form.cleaned_data["tags"].values_list("pk", flat=True),
            cancelled=form.cleaned_data["cancelled"], hidden=form.cleaned_data.get("moderation_hidden"),
        ))

    def save_related(self, request, form, formsets, change):
        # Explicit through tables are already validated and saved by the service.
        pass


@admin.register(models.GenreListeningReference)
class GenreReferenceAdmin(RetainedAdmin):
    form = GenreReferenceForm
    list_display = ("title", "artist_credit", "kind")

    def save_model(self, request, obj, form, change):
        apply_saved(obj, services.save_genre_reference(actor=request.user, reference_id=obj.pk,
            data={key: form.cleaned_data[key] for key in services.REFERENCE_FIELDS},
            category_ids=form.cleaned_data["categories"].values_list("pk", flat=True),
            tag_ids=form.cleaned_data["tags"].values_list("pk", flat=True)))

    def save_related(self, request, form, formsets, change):
        pass


@admin.register(models.EventListeningReference)
class EventReferenceAdmin(RetainedAdmin):
    list_display = ("title", "artist_credit", "event", "kind")

    def get_readonly_fields(self, request, obj=None):
        return ("event",) if obj else ()

    def has_add_permission(self, request):
        return super().has_add_permission(request) and request.user.has_perm("discovery.change_event")

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and request.user.has_perm("discovery.change_event")

    def save_model(self, request, obj, form, change):
        apply_saved(obj, services.save_event_reference(actor=request.user, event_id=obj.event_id,
            reference_id=obj.pk, data={key: form.cleaned_data[key] for key in services.REFERENCE_FIELDS}))


@admin.register(models.EventReport)
class ReportAdmin(RetainedAdmin):
    form = ReportForm
    fields = ("event", "reporter", "reason", "explanation", "status", "resolution_note", "hide_event", "reviewed_by", "reviewed_at")
    readonly_fields = ("event", "reporter", "reason", "explanation", "reviewed_by", "reviewed_at")
    list_display = ("event", "reason", "status", "created_at")
    list_filter = ("status", "reason")

    def has_add_permission(self, request):
        return False

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "hide_event" in form.base_fields and not request.user.has_perm("discovery.change_event"):
            form.base_fields["hide_event"].disabled = True
        return form

    def save_model(self, request, obj, form, change):
        apply_saved(obj, services.review_report(actor=request.user, report_id=obj.pk,
            status=form.cleaned_data["status"], resolution_note=form.cleaned_data["resolution_note"],
            hide_event=form.cleaned_data.get("hide_event", False)))


admin.site.register(models.EventFollow, SchemaReadOnlyAdmin)
admin.site.register(models.EventChange, SchemaReadOnlyAdmin)
