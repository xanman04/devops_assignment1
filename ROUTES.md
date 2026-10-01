# Step 2: Django pages, forms, and request handlers

Approved and implemented September 28, 2026. The root now serves the discovery page; all routes below are connected to Django forms/templates and the existing domain services. The interface is a functional first pass, with visual refinement still to review.

Most interactions use Django templates and POST forms, redirecting after successful writes. GET reads; POST writes with CSRF protection. Map refresh uses JSON. No REST Framework or separate frontend server is needed. Views pass request.user to existing services rather than trusting submitted actor/creator/reviewer/recipient fields.

| Route | Methods | Responsibility |
|---|---|---|
| `/` | GET | Map landing page, date/genre controls, location fallback |
| `/discover/` | GET | Public event, genre, subgenre, and performer discovery; text search hides empty rows |
| `/my-events/` | GET, login required | Tracked events and the user's listings together |
| `/groups/` | GET, login required | Memberships and join requests together |
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
| `/events/<id>/references/new/`, `/events/<id>/references/<reference_id>/edit/` | GET, POST | Creator-authorized external music references |
| `/references/<id>/delete/` | POST | Creator-authorized listening reference removal |
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
| `/events/<id>/poster/` | GET | Serve an uploaded poster after event visibility checks |
| `/api/discover/playing-near-me/` | GET | Return linked artist/DJ profiles from public nearby events within the next two weeks; requires browser-provided coordinates |
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

## Implementation and verification

Account registration/login/settings; event/venue/report/reference forms; group membership/request/moderation/message/photo routes; inbox and paginated My Activity are implemented. Services handle domain writes; views allowlist submitted fields, authenticate actors, and render validation/permission/not-found/retry responses. State-changing endpoints require POST and CSRF; successful writes redirect.

The discovery page uses Leaflet 1.9.4, MapLibre's Leaflet adapter, and OpenFreeMap's Dark vector style, with browser geolocation and a Paris fallback, genre/subgenre ANY/ALL filters, a two-week window, automatic refresh after panning, and gradient/count venue markers. High-accuracy geolocation centers at a zoom chosen from the reported accuracy and shows its uncertainty radius. The map list closes via X, Escape, List, or map click. Listing text and popup contents use DOM text nodes. An ordinary server-rendered upcoming-events list remains available without JavaScript. Location is not persisted to accounts; external map assets require internet access. Provider attribution is visible. No tile prefetch or offline download is implemented.

111 automated tests pass, including CSRF, forged actor/permission fields, venue privacy, messages, confirmed switching, processed uploads, and dynamic tempo estimates. JavaScript syntax and migration consistency checks pass. The live desktop map and notification layout were inspected in a browser; location precision on the author's device and further UI polish remain to be reviewed.
