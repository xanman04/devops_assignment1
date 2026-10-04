# Copyright © 2026 Xander Chen. All rights reserved.
"""Small HTTP helpers; domain services own transactions and authorization."""
from functools import wraps
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import OperationalError
from django.http import Http404
from django.shortcuts import render


def endpoint(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except ObjectDoesNotExist as error:
            raise Http404("This record is unavailable.") from error
        except ValidationError as error:
            return render(request, "error.html", {"errors": error.messages}, status=400)
        except OperationalError as error:
            if "locked" not in str(error).lower() and "busy" not in str(error).lower():
                raise
            return render(request, "error.html", {
                "errors": ["Another update is in progress. Please retry; this action was not completed."],
            }, status=503)
    return wrapped


def form_page(request, form, title, save, *, context=None):
    if request.method == "POST" and form.is_valid():
        try:
            return save(form.cleaned_data)
        except ValidationError as error:
            for message in error.messages:
                form.add_error(None, message)
    return render(request, "form.html", {"form": form, "title": title, **(context or {})},
                  status=400 if request.method == "POST" else 200)
