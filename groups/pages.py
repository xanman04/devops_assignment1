from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from config.web import endpoint, form_page
from discovery import services as discovery
from . import models, services
from .forms import GroupForm, MessageForm, JoinForm, BanForm


def manager(actor, group):
    return actor.is_authenticated and (actor.pk == group.owner_id or discovery.can_manage(actor, "groups.change_attendancegroup"))


def require_manager(actor, group):
    if not manager(actor, group):
        raise PermissionDenied("Only the owner or an authorized admin may manage this group.")


@endpoint
@require_GET
def group_detail(request, group_id):
    group = services.get_group(group_id=group_id, actor=request.user)
    member = request.user.is_authenticated and group.memberships.filter(user=request.user).exists()
    board = None
    if member:
        paginator = Paginator(services.messages(actor=request.user, group_id=group_id), 30)
        board = paginator.get_page(request.GET.get("page", paginator.num_pages))
    public = discovery.public_events().filter(pk=group.event_id).exists()
    event_access = public or (request.user.is_authenticated and (request.user.pk == group.event.creator_id or discovery.can_manage(request.user, "discovery.change_event")))
    count = group.memberships.count()
    return render(request, "groups/detail.html", {
        "group": group, "member": member, "manager": manager(request.user, group),
        "board": board, "message_form": MessageForm(), "join_form": JoinForm(), "count": count,
        "event_access": event_access,
        "joining_open": public and group.event.cancelled_at is None and timezone.now() < group.event.starts_at,
        "full": count >= group.capacity,
        "members": group.memberships.select_related("user").order_by("joined_at", "id") if member or manager(request.user, group) else [],
        "offer": group.join_requests.filter(applicant=request.user, status="approved").first() if request.user.is_authenticated else None,
        "pending": group.join_requests.filter(applicant=request.user, status="pending").first() if request.user.is_authenticated else None,
        "banned": group.bans.filter(user=request.user, lifted_at__isnull=True).exists() if request.user.is_authenticated else False,
    })


@endpoint
@login_required
@require_http_methods(["GET", "POST"])
def group_form(request, event_id=None, group_id=None):
    group = services.get_group(group_id=group_id, actor=request.user) if group_id else models.AttendanceGroup()
    if group_id:
        require_manager(request.user, group)
    event = discovery.get_event(event_id=event_id, actor=request.user) if event_id else group.event
    form = GroupForm(request.POST if request.method == "POST" else None, request.FILES if request.method == "POST" else None, instance=group)

    def save(data):
        values = {name: data[name] for name in ("name", "description", "capacity", "joining_mode")}
        if not group_id:
            values["event"] = event
        saved = services.save_group(actor=request.user, group_id=group_id, data=values,
            photo=data.get("photo"), remove_photo=data["remove_photo"])
        return redirect("group-detail", group_id=saved.pk)
    return form_page(request, form, "Edit group" if group_id else "Create a group", save,
        context={"hint": "Groups are optional company for this event. The creator counts toward capacity. Approval does not reserve a place."})


@endpoint
@login_required
@require_POST
def group_action(request, group_id, action):
    services.get_group(group_id=group_id, actor=request.user)
    if action == "join":
        form = JoinForm(request.POST)
        if not form.is_valid():
            raise ValidationError("Invalid switch confirmation.")
        services.join_group(actor=request.user, group_id=group_id, **form.cleaned_data)
    elif action == "request":
        services.request_join(actor=request.user, group_id=group_id)
    elif action == "leave":
        services.leave_group(actor=request.user, group_id=group_id)
        return redirect("activity")
    else:
        raise Http404
    return redirect("group-detail", group_id=group_id)


@endpoint
@login_required
@require_GET
def requests_list(request, group_id):
    group = services.get_group(group_id=group_id, actor=request.user)
    require_manager(request.user, group)
    return render(request, "groups/requests.html", {
        "group": group,
        "requests": Paginator(group.join_requests.select_related("applicant").order_by("-requested_at", "-id"), 30).get_page(request.GET.get("page")),
        "bans": group.bans.filter(lifted_at__isnull=True).select_related("user"),
    })


@endpoint
@login_required
@require_POST
def request_action(request, request_id, action):
    if action in ("approve", "reject"):
        record = services.review_request(actor=request.user, request_id=request_id, approve=action == "approve")
        return redirect("group-requests", group_id=record.group_id)
    if action == "accept":
        form = JoinForm(request.POST)
        if not form.is_valid():
            raise ValidationError("Invalid switch confirmation.")
        membership = services.accept_offer(actor=request.user, request_id=request_id, **form.cleaned_data)
        return redirect("group-detail", group_id=membership.group_id)
    if action == "cancel":
        services.cancel_request(actor=request.user, request_id=request_id)
        return redirect("activity")
    raise Http404


@endpoint
@login_required
@require_POST
def member_action(request, group_id, user_id, action):
    form = BanForm(request.POST)
    if not form.is_valid():
        raise ValidationError("Ban reasons may contain at most 2,000 characters.")
    services.remove_member(actor=request.user, group_id=group_id, user_id=user_id,
                          ban=action == "ban", reason=form.cleaned_data["reason"])
    return redirect("group-detail", group_id=group_id)


@endpoint
@login_required
@require_POST
def ban_lift(request, ban_id):
    record = services.lift_ban(actor=request.user, ban_id=ban_id)
    return redirect("group-requests", group_id=record.group_id)


@endpoint
@login_required
@require_POST
def message_new(request, group_id):
    form = MessageForm(request.POST)
    if not form.is_valid():
        raise ValidationError("Messages must contain 1–4,000 characters.")
    services.post_message(actor=request.user, group_id=group_id, **form.cleaned_data)
    return redirect("group-detail", group_id=group_id)


@endpoint
@login_required
@require_http_methods(["GET", "POST"])
def message_edit(request, message_id):
    message = models.Message.objects.select_related("group").get(pk=message_id)
    services.messages(actor=request.user, group_id=message.group_id)
    if message.author_id != request.user.pk:
        raise PermissionDenied("You may edit only your own messages.")
    if message.deleted_at:
        raise ValidationError("Deleted messages cannot be edited.")
    form = MessageForm(request.POST if request.method == "POST" else None, initial={"body": message.body})

    def save(data):
        services.edit_message(actor=request.user, message_id=message_id, **data)
        return redirect("group-detail", group_id=message.group_id)
    return form_page(request, form, "Edit message", save)


@endpoint
@login_required
@require_POST
def message_delete(request, message_id):
    message = services.delete_message(actor=request.user, message_id=message_id)
    return redirect("group-detail", group_id=message.group_id)


@endpoint
@require_GET
def photo(request, group_id):
    try:
        response = FileResponse(services.open_photo(group_id=group_id, actor=request.user), content_type="image/jpeg")
    except FileNotFoundError as error:
        raise Http404("No photo is available.") from error
    response["Cache-Control"] = "private, no-store"
    response["Vary"] = "Cookie"
    return response
