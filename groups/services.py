"""Group operations; SQLite IMMEDIATE transactions guard membership changes.

Requests and views must use these operations rather than raw ORM writes. Groups
support optional coordination and never represent an attendance requirement.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Max
from django.utils import timezone

from discovery.services import can_manage, get_event, public_events, require_permission, require_user
from notifications.models import Notification
from .models import AttendanceGroup, GroupBan, GroupHistory, GroupNotice, JoinRequest, Membership, Message
from .photos import prepare_photo


def _group(group_id):
    return AttendanceGroup.objects.select_related("event__venue", "owner").get(pk=group_id)


def _manager(actor, group):
    require_user(actor)
    if actor.pk != group.owner_id and not can_manage(actor, "groups.change_attendancegroup"):
        raise PermissionDenied("Only the owner or an authorized admin can manage this group.")


def _available(group):
    if not public_events().filter(pk=group.event_id, cancelled_at__isnull=True).exists():
        raise ValidationError("This event is cancelled or unavailable for new group participation.")
    if timezone.now() >= group.event.starts_at:
        raise ValidationError("New group participation closes when the event starts.")


def _not_banned(group, user):
    if group.bans.filter(user=user, lifted_at__isnull=True).exists():
        raise PermissionDenied("You are banned from this group.")


def _member(actor, group):
    require_user(actor)
    if not group.memberships.filter(user=actor).exists():
        raise PermissionDenied("Only current members may access this conversation.")


def _notify(user_id, kind, summary, *, request=None, group=None):
    notice = Notification(recipient_id=user_id, kind=kind, summary=summary,
                          join_request=request, group=group)
    notice.full_clean()
    notice.save()
    return notice


def visible_groups(*, event_id, actor=None):
    # Public descriptions remain visible for both joining modes. Private means approval,
    # not hidden. This does not grant access to messages, requests, or ban reasons.
    event = get_event(event_id=event_id, actor=actor)
    return AttendanceGroup.objects.filter(event=event).select_related("owner").order_by("created_at", "id")


def get_group(*, group_id, actor=None):
    group = _group(group_id)
    if actor and actor.is_authenticated and actor.is_active:
        if group.memberships.filter(user=actor).exists() or can_manage(actor, "groups.view_attendancegroup"):
            return group
    get_event(event_id=group.event_id, actor=actor)
    return group


def save_group(*, actor, data, group_id=None, photo=None, remove_photo=False):
    """Top-level write boundary: remove any newly written file if this write fails."""
    require_user(actor)
    if group_id:
        _manager(actor, _group(group_id))
    if photo is not None and remove_photo:
        raise ValidationError("Choose either a new photo or photo removal.")
    prepared = prepare_photo(photo) if photo is not None else None
    new_name = None
    storage = AttendanceGroup._meta.get_field("photo").storage
    try:
        with transaction.atomic():
            if group_id:
                group = _group(group_id)
                _manager(actor, group)
                allowed = {"name", "description", "capacity", "joining_mode"}
            else:
                allowed = {"event", "name", "description", "capacity", "joining_mode"}
                group = AttendanceGroup(owner=actor)
            if set(data) - allowed:
                raise ValidationError("Unsupported group fields; an existing group cannot change events.")
            for key, value in data.items():
                setattr(group, key, value.strip() if isinstance(value, str) else value)
            if not group_id:
                if not group.event_id:
                    raise ValidationError("An event is required.")
                # Refresh the event to prevent caller-supplied status/times bypassing checks.
                from discovery.models import Event
                group.event = Event.objects.select_related("venue").get(pk=group.event_id)
                _available(group)
                if Membership.objects.filter(user=actor, group__event_id=group.event_id).exists():
                    raise ValidationError("Leave your existing group before creating another for this event.")
            group.full_clean()
            if len(group.description) > 2000:
                raise ValidationError("Group descriptions must be at most 2,000 characters.")
            if group_id and group.capacity < group.memberships.count():
                raise ValidationError("Capacity cannot be below the current number of members.")
            old_name = group.photo.name
            if prepared is not None:
                group.photo.save(prepared.name, prepared, save=False)
                new_name = group.photo.name
            elif remove_photo:
                group.photo = ""
            group.save()
            if not group_id:
                Membership.objects.create(group=group, user=actor)
                _record(actor, GroupHistory.Kind.CREATED, group)
            if (prepared is not None or remove_photo) and old_name:
                transaction.on_commit(lambda: storage.delete(old_name), robust=True)
        return group
    except Exception:
        if new_name:
            storage.delete(new_name)
        raise


def _record(user, kind, group):
    GroupHistory.objects.create(user=user, kind=kind, group=group, group_name=group.name, event_title=group.event.title)


def _leave(group, user, *, announce=True):
    """Remove a membership. Leaving or switching away is announced in the chat; removals and bans are not."""
    membership = group.memberships.filter(user=user).first()
    if not membership:
        return
    membership.delete()
    _record(user, GroupHistory.Kind.LEFT if announce else GroupHistory.Kind.REMOVED, group)
    successor = group.memberships.select_related("user").order_by("joined_at", "id").first()
    if not successor:
        _delete(group)
        return
    if announce:
        GroupNotice.objects.create(group=group, kind=GroupNotice.Kind.LEFT, subject=user)
    if group.owner_id == user.pk:
        group.owner = successor.user
        group.save(update_fields=["owner", "updated_at"])
        GroupNotice.objects.create(group=group, kind=GroupNotice.Kind.PROMOTED, subject=successor.user)
        _notify(successor.user_id, Notification.Kind.OWNER_TRANSFER,
                "You are now the owner of an attendance group.", group=group)


def _delete(group):
    storage, name = group.photo.storage, group.photo.name
    group.delete()
    if name:
        transaction.on_commit(lambda: storage.delete(name), robust=True)


@transaction.atomic
def delete_group(*, actor, group_id):
    require_permission(actor, "groups.delete_attendancegroup")
    _delete(_group(group_id))


@transaction.atomic
def leave_group(*, actor, group_id):
    require_user(actor)
    group = _group(group_id)
    _leave(group, actor)
    if group.pk:
        group.join_requests.filter(applicant=actor, status__in=["pending", "approved"]).update(status="cancelled")


def _join(actor, group, *, confirm_switch=False):
    require_user(actor)
    _available(group)
    _not_banned(group, actor)
    if group.memberships.filter(user=actor).exists():
        return group.memberships.get(user=actor)
    if group.memberships.count() >= group.capacity:
        raise ValidationError("This group is full; your current membership has not changed.")
    current = Membership.objects.select_related("group__event__venue", "group__owner").filter(user=actor, group__event_id=group.event_id).first()
    if not isinstance(confirm_switch, bool):
        raise ValidationError("Switch confirmation must be true or false.")
    if current and not confirm_switch:
        raise ValidationError("Confirm leaving your current group to join this one.")
    if current:
        _leave(current.group, actor)
    membership = Membership.objects.create(group=group, user=actor)
    GroupNotice.objects.create(group=group, kind=GroupNotice.Kind.JOINED, subject=actor)
    _record(actor, GroupHistory.Kind.JOINED, group)
    # Preserve other groups' pending requests/offers; only this destination is accepted.
    # Its old accepted request does not grant permanent private-group access.
    group.join_requests.filter(applicant=actor, status__in=["pending", "approved"]).update(status="accepted", accepted_at=timezone.now())
    return membership


@transaction.atomic
def join_group(*, actor, group_id, confirm_switch=False):
    group = _group(group_id)
    if group.joining_mode != AttendanceGroup.JoiningMode.PUBLIC:
        raise ValidationError("Request approval before joining this group.")
    return _join(actor, group, confirm_switch=confirm_switch)


@transaction.atomic
def request_join(*, actor, group_id):
    require_user(actor)
    group = _group(group_id)
    _available(group)
    _not_banned(group, actor)
    if group.joining_mode != AttendanceGroup.JoiningMode.APPROVAL:
        raise ValidationError("This group allows joining directly.")
    if group.memberships.filter(user=actor).exists():
        raise ValidationError("You already belong to this group.")
    existing = group.join_requests.filter(applicant=actor, status__in=["pending", "approved"]).first()
    if existing:
        return existing
    request = JoinRequest.objects.create(group=group, applicant=actor)
    _notify(group.owner_id, Notification.Kind.GROUP_REQUEST, "Someone requested to join your attendance group.", request=request)
    return request


@transaction.atomic
def review_request(*, actor, request_id, approve):
    request = JoinRequest.objects.select_related("group__event__venue", "group__owner", "applicant").get(pk=request_id)
    group = request.group
    _manager(actor, group)
    _available(group)
    _not_banned(group, request.applicant)
    if request.status != JoinRequest.Status.PENDING:
        raise ValidationError("Only pending requests can be reviewed.")
    if not isinstance(approve, bool):
        raise ValidationError("Approval must be true or false.")
    request.status = JoinRequest.Status.APPROVED if approve else JoinRequest.Status.REJECTED
    request.reviewed_by, request.reviewed_at = actor, timezone.now()
    request.save()
    kind = Notification.Kind.GROUP_OFFER if approve else Notification.Kind.GROUP_REJECTED
    summary = "Your group request was approved. Accept to join; space is not reserved." if approve else "Your group request was declined."
    _notify(request.applicant_id, kind, summary, request=request)
    return request


@transaction.atomic
def accept_offer(*, actor, request_id, confirm_switch=False):
    require_user(actor)
    request = JoinRequest.objects.select_related("group__event__venue", "group__owner").get(pk=request_id, applicant=actor)
    if request.status != JoinRequest.Status.APPROVED:
        raise ValidationError("This request is not an approved offer.")
    return _join(actor, request.group, confirm_switch=confirm_switch)


@transaction.atomic
def cancel_request(*, actor, request_id):
    require_user(actor)
    request = JoinRequest.objects.get(pk=request_id, applicant=actor)
    if request.status not in ["pending", "approved"]:
        raise ValidationError("Only unresolved requests can be cancelled.")
    request.status = JoinRequest.Status.CANCELLED
    request.save(update_fields=["status"])
    return request


@transaction.atomic
def remove_member(*, actor, group_id, user_id, ban=False, reason=""):
    group = _group(group_id)
    _manager(actor, group)
    if not isinstance(ban, bool):
        raise ValidationError("Ban selection must be true or false.")
    if user_id == group.owner_id:
        raise ValidationError("The owner must leave and transfer ownership; they cannot be removed or banned here.")
    user = get_user_model().objects.get(pk=user_id)
    if len(reason) > 2000:
        raise ValidationError("Ban reasons must be at most 2,000 characters.")
    if ban:
        record, created = GroupBan.objects.get_or_create(group=group, user=user, lifted_at__isnull=True,
            defaults={"issued_by": actor, "reason": reason.strip()})
        if not created:
            return record
    elif not group.memberships.filter(user=user).exists():
        raise ValidationError("This user is not a current member.")
    _leave(group, user, announce=False)
    group.join_requests.filter(applicant=user, status__in=["pending", "approved"]).update(status="cancelled")
    _notify(user.pk, Notification.Kind.MEMBER_BANNED if ban else Notification.Kind.MEMBER_REMOVED,
            "You were banned from an attendance group." if ban else "You were removed from an attendance group.", group=group)
    return record if ban else None


@transaction.atomic
def lift_ban(*, actor, ban_id):
    ban = GroupBan.objects.select_related("group__event__venue", "group__owner").get(pk=ban_id)
    _manager(actor, ban.group)
    if ban.lifted_at is None:
        ban.lifted_at, ban.lifted_by = timezone.now(), actor
        ban.save(update_fields=["lifted_at", "lifted_by"])
    return ban


def messages(*, actor, group_id):
    group = _group(group_id)
    _member(actor, group)
    return group.messages.select_related("author").order_by("created_at", "id")


def _text(body):
    if not isinstance(body, str) or not body.strip() or len(body.strip()) > 4000:
        raise ValidationError("Messages must contain 1–4,000 characters.")
    return body.strip()


@transaction.atomic
def post_message(*, actor, group_id, body):
    group = _group(group_id)
    _member(actor, group)
    return Message.objects.create(group=group, author=actor, body=_text(body))


@transaction.atomic
def edit_message(*, actor, message_id, body):
    message = Message.objects.select_related("group__event__venue", "group__owner").get(pk=message_id)
    _member(actor, message.group)
    if message.author_id != actor.pk:
        raise PermissionDenied("You may edit only your own messages.")
    if message.deleted_at:
        raise ValidationError("Deleted messages cannot be edited.")
    body = _text(body)
    if body != message.body:
        message.body, message.edited_at = body, timezone.now()
        message.save(update_fields=["body", "edited_at"])
    return message


@transaction.atomic
def delete_message(*, actor, message_id):
    message = Message.objects.select_related("group__event__venue", "group__owner").get(pk=message_id)
    require_user(actor)
    if not can_manage(actor, "groups.delete_message"):
        _member(actor, message.group)
        if message.author_id != actor.pk:
            raise PermissionDenied("You may delete only your own messages.")
    if not message.deleted_at:
        message.body, message.deleted_at, message.deleted_by = "", timezone.now(), actor
        message.save(update_fields=["body", "deleted_at", "deleted_by"])
    return message


def chat_signature(*, actor, group_id):
    """A cheap fingerprint of everything the live chat shows; changes whenever any of it does.

    Members only. It covers new, edited and removed messages, notices, and the member list/owner, so the page
    can poll this and fetch fresh content only when it differs.
    """
    group = _group(group_id)
    _member(actor, group)
    messages = group.messages.aggregate(n=Count("id"), last=Max("id"), edited=Max("edited_at"), deleted=Max("deleted_at"))
    members = group.memberships.aggregate(n=Count("id"), last=Max("id"))
    notices = group.notices.aggregate(last=Max("id"))
    parts = (messages["n"], messages["last"], messages["edited"], messages["deleted"], members["n"], members["last"],
             notices["last"], group.owner_id, group.capacity)
    return "|".join("" if part is None else str(part) for part in parts)


def open_photo(*, group_id, actor=None):
    # Same visibility as the discoverable group card; messages remain members-only.
    group = get_group(group_id=group_id, actor=actor)
    if not group.photo:
        raise FileNotFoundError("This group has no uploaded photo.")
    return group.photo.open("rb")
