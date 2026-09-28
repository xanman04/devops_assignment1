from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods
from config.web import endpoint, form_page
from .forms import RegistrationForm, AccountSettingsForm


@endpoint
@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("activity")
    form = RegistrationForm(request.POST if request.method == "POST" else None)

    def save(data):
        user = form.save()
        login(request, user)
        return redirect("activity")
    return form_page(request, form, "Create account", save)


@endpoint
@login_required
@require_http_methods(["GET", "POST"])
def settings(request):
    form = AccountSettingsForm(request.POST if request.method == "POST" else None, instance=request.user)

    def save(data):
        form.save()
        return redirect("account-settings")
    return form_page(request, form, "Account settings", save)
