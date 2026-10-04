# Step 2: Django pages, forms, and request handlers

Approved and implemented September 28, 2026. The root now serves the discovery page; all routes below are connected to Django forms/templates and the existing domain services. This table was updated through October 4, 2026.

Most interactions use Django templates and POST forms, redirecting after successful writes. GET reads; POST writes with CSRF protection. Map refresh uses JSON. No REST Framework or separate frontend server is needed. Views pass request.user to existing services rather than trusting submitted actor/creator/reviewer/recipient fields.

| Route | Methods | Responsibility |
|---|---|---|
| `/` | GET | Map landing page, date/genre controls, location fallback |
| `/discover/` | GET | Public event, genre, subgenre, and performer discovery; text search hides empty rows |
| `/my-events/` | GET, login required | Followed events and the user's listings together |
| `/groups/` | GET, login required | Memberships and join requests together |
| `/api/map/events/` | GET | Existing filtered venue/event JSON |
| `/genres/`, `/genres/<id>/` | GET | Curated categories, subgenre tags, music references |
| `/accounts/register/` | GET, POST | Username/password, optional display name/private email |
| `/accounts/login/` | GET, POST | Django login |
| `/accounts/logout/` | POST | Django logout |
| `/accounts/settings/` | GET, POST | Owner-only Edit profile form: name, bio, email, picture, music links |
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
| `/groups/<id>/chat/` | GET, members only | Live chat: takes the page's current `sig`; answers `{changed:false}` or fresh chat and member HTML, count and a new `sig`. Private, never cached |
| `/groups/<id>/messages/new/` | POST | Member text message |
| `/messages/<id>/edit/` | GET, POST | Current-member author edits own content |
| `/messages/<id>/delete/` | POST | Author removes own content; admin moderation remains in admin |
| `/t<8 hex>/…` | any | A tab's own login: the same routes under a per-tab prefix with its own session and CSRF cookies; created by JavaScript when a tab signs in or registers |
| `/accounts/profile/` | GET, signed in | Own profile page: picture, bio, music links, counts, next followed events, groups, collection of event cards with achievements and genre chart |
| `/accounts/avatar/<user_id>/` | GET, signed in | A profile picture as JPEG; 404 if none; never cached |
| `/accounts/whoami/` | GET | JSON `{id, name}` of the signed-in account (`null`/empty when anonymous), never cached; used by the tab account guard |
| `/notifications/` | GET | Recipient-only inbox, no raw private snapshots |
| `/notifications/<id>/read/` | POST | Mark own notification read |
| `/my-activity/` | GET | One newest-first timeline of own listings, follows, memberships, requests/offers and venue proposals; `?page=` |
| `/admin/` | Django admin | Existing discovery review, group deletion, message moderation |

## Handler and display rules

- Event venue choices include approved records and the user's own pending proposals. Propose a venue separately before selecting it for a listing; no geocoding API is required.
- Event forms require a category and valid local start/end. Tags are optional; tempo is computed.
- Group forms use multipart upload. Owners cannot directly assign another owner or change the event.
- Public/private group modes are discoverable. Both retain existing members when changed. Keep pending request lists, ban reasons, and messages out of public card data.
- Show full/cancelled/start-cutoff state before rendering join controls; services recheck on submission. Approved offers reserve no place and require explicit confirmation before switching memberships.
- Existing members retain coordination after cancellation and event start/end; former members lose conversation access. Do not expose pending/unapproved venue coordinates through group pages or notifications unless authorized as creator/admin.
- Serve photos through the checked route; do not expose raw MEDIA_ROOT. Optional-photo absence uses a default UI image.
- Render names, messages, and descriptions with Django escaping. External URLs use validated HTTP/HTTPS. The group chat refreshes by short polling of `/groups/<id>/chat/` (no WebSockets); other pages load on request, with pagination for long histories.
- Translate domain ValidationError into form errors and permissions into 403/404 as appropriate. A competing SQLite lock failure produces a retry message without partial changes.
- Photo services own the write boundary; avoid wrapping them in another request transaction. Cleanup of old files runs after commit. A process crash can still orphan a file and needs maintenance in a future production version.

## Implementation and verification

Account registration/login/settings; event/venue/report/reference forms; group membership/request/moderation/message/photo routes; inbox and paginated My Activity are implemented. Services handle domain writes; views allowlist submitted fields, authenticate actors, and render validation/permission/not-found/retry responses. State-changing endpoints require POST and CSRF; successful writes redirect.

The discovery page uses MapLibre GL JS and OpenFreeMap's Dark vector style, with browser geolocation and a Madrid fallback, genre/subgenre ANY/ALL filters, a two-week window, automatic refresh after panning, and gradient/count venue markers. Browser geolocation centers the map and draws a small location dot. The map list closes via X, Escape, List, or map click. Listing text and popup contents use DOM text nodes. An ordinary server-rendered upcoming-events list remains available without JavaScript. Location is not persisted to accounts; external map assets require internet access. Provider attribution is visible. No tile prefetch or offline download is implemented.

216 automated tests pass (October 4, 2026), including CSRF, forged actor/permission fields, venue privacy, messages, confirmed switching, processed uploads, and dynamic tempo estimates. JavaScript syntax and migration consistency checks pass.
