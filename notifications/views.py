from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST
from config.web import endpoint
from . import services


@endpoint
@login_required
@require_GET
def inbox(request):
    notices = services.inbox(actor=request.user, unread_only=request.GET.get("unread") == "1").select_related("join_request", "event_change")
    return render(request, "notifications/inbox.html", {"notices": Paginator(notices, 30).get_page(request.GET.get("page"))})


@endpoint
@login_required
@require_POST
def read(request, notification_id):
    services.mark_read(actor=request.user, notification_id=notification_id)
    return redirect("inbox")
