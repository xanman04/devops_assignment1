# Step 2: Django pages, forms, and request handlers

Proposed September 28, 2026, pending discussion. Only the status root, Django admin, and `/api/map/events/` exist. This plan does not claim the additional routes are implemented.

Most interactions use Django templates and POST forms, redirecting after successful writes. GET reads; POST writes with CSRF protection. Map refresh uses JSON. No REST Framework or separate frontend server is needed. Views pass request.user to existing services rather than trusting submitted actor/creator/reviewer/recipient fields.

| Route | Methods | Responsibility |
|---|---|---|
| `/` | GET | Map landing page, date/genre controls, location fallback |
| `/api/map/events/` | GET | Existing filtered venue/event JSON |
| `/genres/`, `/genres/<id>/` | GET | Curated categories, subgenre tags, music references |
| `/accounts/register/` | GET, POST | Username/password, optional display name/private email |
| `/accounts/login/` | GET, POST | Django login |
| `/accounts/logout/` | POST | Django logout |
| `/accounts/settings/` | GET, POST | Owner-only name/email settings |
| `/events/new/`, `/events/<id>/edit/` | GET, POST | Creator-authorized listing forms with venue-local times |
| `/events/<id>/` | GET | Music/event details and optional “Attending alone?” groups |
| `/events/<id>/cancel/` | POST | Retain event, remove from map, notify followers |
| `/events/<id>/follow/`, `/events/<id>/unfollow/` | POST | Follow updates independently of attendance/groups |
| `/events/<id>/report/` | GET, POST | Reason/explanation for admin review |
| `/venues/new/` | GET, POST | Propose venue name/address/pin/timezone; pending review |
| `/events/<id>/groups/new/` | GET, POST | Create group, owner membership, optional processed photo |
| `/groups/<id>/` | GET | Public card details; conversation only for current members |
| `/groups/<id>/edit/` | GET, POST | Owner settings and photo; group event cannot change |
| `/groups/<id>/join/`, `/groups/<id>/request/` | POST | Public joining or approval request |
| `/groups/<id>/leave/` | POST | Leave, transfer ownership, or delete empty group |
| `/groups/<id>/requests/` | GET | Owner's request/offer management |
| `/requests/<id>/approve/`, `/requests/<id>/reject/` | POST | Owner review and applicant notification |
| `/requests/<id>/accept/` | POST | Applicant accepts; explicit switch confirmation, fresh capacity/cutoff check |
| `/requests/<id>/cancel/` | POST | Applicant cancels pending request/offer |
| `/groups/<id>/members/<user_id>/remove/`, `/groups/<id>/members/<user_id>/ban/` | POST | Owner moderation; removal and ban are distinct |
| `/bans/<id>/lift/` | POST | Owner lifts ban |
| `/groups/<id>/photo/` | GET | Serve processed photo after group visibility checks |
| `/groups/<id>/messages/new/` | POST | Member text message |
| `/messages/<id>/edit/` | GET, POST | Current-member author edits own content |
| `/messages/<id>/delete/` | POST | Author removes own content; admin moderation remains in admin |
| `/notifications/` | GET | Recipient-only inbox, no raw private snapshots |
| `/notifications/<id>/read/` | POST | Mark own notification read |
| `/my-activity/` | GET | Own listings, follows, memberships, requests/offers |
| `/admin/` | Django admin | Existing discovery review, group deletion, message moderation |

## Handler and display rules

- Event venue choices include approved records and the user's own pending proposals. Propose a venue separately before selecting it for a listing; no geocoding API is required.
- Event forms require a category and valid local start/end. Tags are optional; tempo is computed.
- Group forms use multipart upload. Owners cannot directly assign another owner or change the event.
- Public/private group modes are discoverable. Both retain existing members when changed. Keep pending request lists, ban reasons, and messages out of public card data.
- Show full/cancelled/start-cutoff state before rendering join controls; services recheck on submission. Approved offers reserve no place and require explicit confirmation before switching memberships.
- Existing members retain coordination after cancellation and event start/end; former members lose conversation access. Do not expose pending/unapproved venue coordinates through group pages or notifications unless authorized as creator/admin.
- Serve photos through the checked route; do not expose raw MEDIA_ROOT. Optional-photo absence uses a default UI image.
- Render names, messages, and descriptions with Django escaping. External URLs use validated HTTP/HTTPS. No live message polling is required; load/refresh retrieves messages, with pagination for long histories.
- Translate domain ValidationError into form errors and permissions into 403/404 as appropriate. A competing SQLite lock failure produces a retry message without partial changes.
- Photo services own the write boundary; avoid wrapping them in another request transaction. Cleanup of old files runs after commit. A process crash can still orphan a file and needs maintenance in a future production version.

## Suggested order

Account views and a basic shared layout; event forms/detail and venue proposal; group/request/message/photo pages and notifications; map integration against existing JSON; visual polish. Discuss route/navigation behavior before implementing the plan in a larger batch.
