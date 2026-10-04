from django.contrib.auth import login
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from config.web import endpoint, form_page
from config.images import prepare_image
from discovery.models import EventCard, EventFollow
from discovery.services import public_events
from groups.models import Membership
from discovery.models import GenreCategory
from django.conf import settings as django_settings
from . import badge_palette, genre_chart, sample_badges
from .forms import RegistrationForm, AccountSettingsForm
from .models import User


@endpoint
@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("profile")
    form = RegistrationForm(request.POST if request.method == "POST" else None, request.FILES if request.method == "POST" else None)

    def save(data):
        upload = data.get("avatar")
        picture = prepare_image(upload, kind="picture") if upload else None
        user = form.save(commit=False)
        if picture:
            user.avatar.save("avatar.jpg", picture, save=False)
        user.save()
        login(request, user)
        return redirect("profile")
    return form_page(request, form, "Create account", save, context={"new_session": True, "mark_fields": True,
                     "hint": "Only the username and password are needed. Everything marked Optional can be added later from your profile."})


@endpoint
@login_required
@require_GET
def profile(request):
    user = request.user
    now = timezone.now()
    followed = list(EventFollow.objects.filter(user=user, event__ends_at__gte=now,
                                               event__in=public_events()).select_related("event__venue")
                    .prefetch_related("event__categories").order_by("event__starts_at")[:12])
    next_up = []
    for follow in followed:
        event, categories = follow.event, list(follow.event.categories.all())
        next_up.append({"event": event, "accent": categories[0].color if categories else "#8d95a6",
                        "uploaded_poster_id": event.pk if event.poster else None, "poster": event.demo_poster})
    memberships = list(Membership.objects.filter(user=user).select_related("group__event")
                       .prefetch_related("group__event__categories").order_by("-joined_at")[:3])
    for membership in memberships:
        categories = list(membership.group.event.categories.all())
        membership.accent = categories[0].color if categories else "#8d95a6"
    categories = list(GenreCategory.objects.order_by("id"))
    cards = sample_badges.cards_for(user)
    badges = sample_badges.achievements(cards) + cards
    return render(request, "accounts/profile.html", {
        "socials": user.social_links, "next_up": next_up, "memberships": memberships,
        "collection_name": django_settings.COLLECTION_NAME,
        "genre_chart": genre_chart.build(categories, genre_chart.values_from_cards(categories, cards)),
        "badges": [badge | {"palette": badge_palette.for_badge(badge)} for badge in badges], "locked_slots": range(max(sample_badges.TOTAL_SLOTS - len(badges), 0)),
        "stats": {"followed": EventFollow.objects.filter(user=user).count(),
                  "attended": EventCard.objects.filter(user=user).count(),
                  "groups": Membership.objects.filter(user=user).count()},
    })


@endpoint
@login_required
@require_http_methods(["GET", "POST"])
def settings(request):
    form = AccountSettingsForm(request.POST if request.method == "POST" else None,
                               request.FILES if request.method == "POST" else None, instance=request.user)

    if request.user.avatar:
        form.fields["avatar"].widget.attrs["data-current-src"] = reverse("avatar", args=[request.user.pk])

    def save(data):
        user, upload = form.save(commit=False), data.get("avatar")
        old_name = request.user.avatar.name
        if upload:
            user.avatar.save("avatar.jpg", prepare_image(upload, kind="picture"), save=False)
        user.save()
        if upload and old_name:
            storage = user.avatar.storage
            if storage.exists(old_name):
                storage.delete(old_name)
        return redirect("profile")
    return form_page(request, form, "Edit profile", save, context={"profile_form": True, "mark_fields": True, "current_avatar_id": None})


@login_required
@require_GET
def avatar(request, user_id):
    person = get_object_or_404(User, pk=user_id)
    if not person.avatar:
        raise Http404("No picture is available.")
    response = FileResponse(person.avatar.open("rb"), content_type="image/jpeg")
    response["Cache-Control"] = "private, no-store"
    response["Vary"] = "Cookie"
    return response


@require_GET
def whoami(request):
    """Which account this browser is signed in as right now; open tabs compare it with the account they were built for."""
    user = request.user
    response = JsonResponse({"id": user.pk if user.is_authenticated else None, "name": user.public_name if user.is_authenticated else ""})
    response["Cache-Control"] = "private, no-store"
    return response
