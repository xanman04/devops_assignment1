# Copyright © 2026 Xander Chen. All rights reserved.
"""Keep per-account pages out of browser and shared caches, and give each tab its own login."""
import re

from django.conf import settings
from django.urls import set_script_prefix


class PrivatePagesMiddleware:
    """Signed-in responses (followed events, groups, chat, notifications) belong to one account only.

    Without this a browser may keep a copy of a page and show it again after the account changes, for example
    on Back after logging out or switching users, which looks like one person's data appearing for another.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method in ("GET", "HEAD") and getattr(request, "user", None) is not None and request.user.is_authenticated:
            if "Cache-Control" not in response:
                response["Cache-Control"] = "private, no-store"
        return response


SLOT_PATH = re.compile(r"^/(t[0-9a-f]{8})(/.*)$")


class TabSlotMiddleware:
    """Let one browser hold a different login in each tab.

    A browser sends the same cookies from every tab, so one session cookie means one account per browser. A tab that
    signs in moves to an address under /t<8 hex>/ and its session and CSRF cookies are named for that slot and limited
    to that path, so other tabs never receive them. The prefix is removed before URL matching and put back by
    reverse(), so views and templates do not know about it. Addresses without a prefix behave as before.
    """

    COOKIES = ("SESSION_COOKIE_NAME", "CSRF_COOKIE_NAME")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        match = SLOT_PATH.match(request.path_info)
        if not match:
            return self.get_response(request)
        slot, rest = match.groups()
        session_name, csrf_name = (getattr(settings, name) for name in self.COOKIES)
        cookies = request.COOKIES
        # A slot never uses the browser-wide login; it only sees its own session cookie.
        own_session = cookies.pop(f"{session_name}_{slot}", None)
        cookies.pop(session_name, None)
        if own_session is not None:
            cookies[session_name] = own_session
        # The first form in a slot (log in, register) still carries a token made from the shared CSRF cookie.
        own_csrf = cookies.pop(f"{csrf_name}_{slot}", None)
        if own_csrf is not None:
            cookies[csrf_name] = own_csrf
        request.path_info = rest
        request.path = f"/{slot}{rest}"
        request.META["SCRIPT_NAME"] = f"/{slot}"
        set_script_prefix(f"/{slot}/")
        try:
            response = self.get_response(request)
        finally:
            set_script_prefix("/")
        for name in (session_name, csrf_name):
            if name in response.cookies:
                morsel = response.cookies.pop(name)
                morsel.set(f"{name}_{slot}", morsel.value, morsel.coded_value)
                morsel["path"] = f"/{slot}/"
                response.cookies[f"{name}_{slot}"] = morsel
        return response
