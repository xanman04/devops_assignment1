# Music Event Discovery

A music-first event discovery application: find nearby events by genre and date, hear what their music sounds like through listening references, and find people to attend with.

The idea comes from difficulty discovering smaller and niche events. It covers music broadly, including electronic music, rock, and jazz. Attendees and independent event organizers are the intended users.

**Status:** discovery and group business services implemented September 28, 2026. Membership/requests, messages, photo processing, and in-app notification generation are implemented and tested. Public pages/forms and route integration remain pending. The proposal was approved by the professor, as reported by the author on September 24. Product name is provisional.

## Planned features

### Event discovery

- Location-centered map with a default-city fallback when browser location is unavailable or declined; free panning and zooming with automatic result refresh.
- Muted dark basemap and broad-category-colored venue pins. Multiple matching events share an ombre pin with an event count; selecting it opens events ordered by date.
- Next 14 days shown by default, with date controls and genre filters supporting ANY (OR) or ALL (AND) matching. No genre selection means all genres.
- Event details include venue, date/time, genres, description, an app-derived typical tempo estimate from admin-curated category/tag ranges, listening links, and an optional external ticket link.
- Admin-curated Explore Genres directory with consistent names, colors, descriptions, and representative artists/tracks/sets. Event-specific listening references support mixed or hard-to-classify music.
- Registered users submit events and edit their own listings. Existing approved venues are selectable; proposed new locations require admin review before their events become public.
- Valid listings at approved venues publish immediately. Users can report events; admins can review reports, hide listings, and deactivate accounts.

### Attendance groups

- An event's “Attending alone?” section displays discoverable groups.
- Groups have a name, description, capacity, and optional uploaded photo.
- Public groups allow immediate joining; private groups remain visible but require creator approval. Hidden invite-only groups are out of scope.
- One group membership per user per event, including the owner in capacity. Approved private-group offers do not reserve spaces; accepting can atomically switch groups. Owner departure transfers ownership by seniority; empty groups are deleted.
- A members-only, text-based message board stores messages with author and timestamp. Messages load on page opening or refresh, without live chat infrastructure.
- Username/password accounts use Django authentication. Groups and memberships belong to accounts rather than browser-only identities.

### Tracking and classification

- Events require one or more broad color categories and can have multiple detailed subgenre tags. Tempo is estimated from curated ranges, not supplied by event creators.
- Users can follow events independently of attendance or groups and receive in-app venue/time/cancellation updates.
- Groups are optional company for solo attendees, not an attendance requirement or RSVP system.
- Authors can edit/delete their own messages; admins can remove messages. Group removal permits rejoining; a separate group ban prevents it.
- Required start/end times support overnight events; changing an event venue never edits another event's location.

## Stack

| Layer | Decision | Reason |
|---|---|---|
| Backend | Python and Django | Python is the author's strongest language; authentication, admin, models, and forms serve concrete requirements |
| Database | SQLite through Django ORM and migrations | Required storage, with integrated relationships and schema evolution |
| Pages | Django templates, HTML, plain CSS | Familiar tools, responsive layouts, no separate frontend build pipeline |
| Browser behavior | Plain JavaScript and Django JSON endpoints | Refresh map results without page reloads; no REST framework needed yet |
| Map | Leaflet and a muted dark basemap | Panning, zooming, and custom genre markers; tile provider/access terms still to confirm |
| Files | Local group images; file paths in SQLite | Keep data inside the application's configurable data directory |

Dependencies are pinned in the single root `requirements.txt`: Django 5.2.17 LTS, Pillow for image-field support, Waitress for a single-process Windows-compatible server, WhiteNoise for static assets, tzdata for Windows timezones, and Django's transitive dependencies. Verified with Python 3.13.1. Frontend assets must not introduce another package manifest.

## Planned architecture

One Django project runs as one process, with two logical domain apps sharing one SQLite database:

- **`discovery`:** categories/tags, venues, events, listening references, venue review, event reports, follows/change history, and map filtering.
- **`groups`:** attendance groups, join requests, memberships, photos, and messages.

Django authentication supplies shared accounts with display names and optional private email; shared notifications support event-change updates and group offers. Request handlers handle HTTP; domain business rules remain separate from page rendering and map JSON responses. Groups references events by identity and obtains necessary event information through a small discovery interface. A future service split would also need to address shared accounts and database relationships; it is not part of this assignment.

```text
Browser: templates + CSS + JavaScript + Leaflet
              |
       Django pages / JSON
          /           \
     discovery       groups
          \           /
       Django ORM + SQLite
       Local image storage

Browser also requests basemap tiles from the selected provider.
```

Current layout (frontend templates/assets remain future work):

```text
README.md
ADR.md
AI_USAGE.md
DESIGN.md
SCHEMA.md
requirements.txt
manage.py
app.py                 # Automatic migration/static setup and single-process server
config/                # Django settings, URL configuration, startup integration
accounts/              # Django-based user model
notifications/         # Shared in-app notifications
discovery/             # Models, services, admin forms, map JSON view, tests, migrations
groups/                # Models, membership/message services, photos, tests, admin, migrations
test_schema.py         # Focused persistence/integrity checks
```

## Running the application

From the repository root, using Python 3.13 (verified on 3.13.1):

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe app.py
```

On Linux/macOS use `.venv/bin/python` instead. Open http://localhost:8000/ for backend status. Startup applies committed migrations and collects static assets automatically, then starts Waitress on `0.0.0.0` in one process, without a reloader or frontend server. Restart the process after code changes; it does not auto-reload.

| Environment variable | Default / purpose |
|---|---|
| `PORT` | `8000` |
| `DATA_DIR` | Repository `data/`; SQLite at `DATA_DIR/db.sqlite3`, images at `DATA_DIR/media/groups/`, collected assets at `DATA_DIR/static/` |
| `DJANGO_SECRET_KEY` | If absent, a generated local key is persisted in `DATA_DIR/.django-secret-key`; set explicitly for future deployment |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]`; add the real hostname/IP for access from another device |
| `DJANGO_DEBUG` | `0`; use `1` only for local debugging |

No `.env` file or source edit is required. Runtime data and the virtual environment are ignored by Git. Uploaded media has no public route yet.

Optional administration, not required for startup:

```powershell
.venv/Scripts/python.exe manage.py createsuperuser
```

Then visit http://localhost:8000/admin/. You can create/edit categories, tags, venues, events, and listening references, and resolve reports. Discovery saves use services. Groups are inspectable; authorized admins can delete a populated group with confirmation and remove selected message content through moderation. Direct group/membership/request/ban/message editing remains disabled to prevent bypassing services. No default users or seeded listings are introduced.

To try discovery: create a genre category, add a venue and set its review status to approved, then add a future event with at least one category. Optional tags must belong to selected categories. Event forms interpret and display date/time in the selected venue's IANA timezone, storing UTC. Changing venue reinterprets the entered wall-clock times in its timezone; confirm those times when moving an event. Ambiguous/nonexistent daylight-saving times are rejected. Admins may inspect pending locations; they are never returned publicly.

### Discovery services and map endpoint

`discovery/services.py` is the supported business-operation boundary:

| Operations | Rules |
|---|---|
| `save_category`, `save_tag`, `save_genre_reference` | Admin permissions, validated curated values, category/tag consistency; tags already used cannot move to a different category |
| `save_venue` | Logged-in users propose locations; only authorized admins edit/review shared venues; changed location details notify followers of affected events |
| `save_event` | Creator/admin edits, timezone-aware start/end, valid category/tag selections, venue access, cancellation, separate admin-only hiding |
| `get_event`, `search_events`, `map_pins`, `tempo_estimate` | Public visibility, overlap/date/bounds/genre filtering, venue aggregation, derived typical tempo |
| `follow_event`, `unfollow_event` | Idempotent user/event following, separate from group membership or attendance |
| `report_event`, `review_report` | Reports require review; authorized admins can hide an event when marking a report actioned |
| `save_event_reference`, `delete_event_reference` | Creator/admin-owned external listening links, separate from the curated directory |

`notifications/services.py` supplies recipient-scoped `inbox` and `mark_read` operations. Relevant edits produce one EventChange with before/after snapshots and one notification per active follower, inside the edit transaction. Failed notification writes roll back the edit. No alerts are generated for unchanged saves or title-only changes. Notification summaries omit coordinates and private event text; raw snapshots remain admin-only history. User-facing inbox/follow/report forms are not built yet.

Read-only map endpoint: `GET /api/map/events/`. Optional query parameters:

- `start`, `end`: ISO datetimes with timezone, e.g. `2026-10-01T00:00:00Z`; default is now through the next 14 days.
- `categories`, `tags`: comma-separated IDs; empty means unrestricted.
- `match`: `any` (default) or `all`, applied across the selected category/tag IDs.
- `bounds`: `south,west,north,east`; west greater than east handles a viewport crossing the date line.

Example: `/api/map/events/?bounds=48,2,49,3&match=any`. Results contain venue coordinates, distinct category colors, counts, and matching event cards ordered by start time. Only approved-venue, unhidden, uncancelled, categorized events overlapping the requested interval appear. The interval is start-inclusive/end-exclusive; ongoing events match. Cancelled events remain available through authorized detail services but not the map. Invalid queries return 400; queries over 1,000 events ask for narrower filters rather than returning misleading partial pin counts. Text fields are plain text and must be rendered as text by the future frontend.

Admins with user-delete permission can delete unreferenced accounts through Django's confirmation page. Referenced accounts remain protected: Django lists blocking event/group/message records rather than cascading deletion. Deactivate those accounts when their history should remain.

No self-authored Dockerfile, Compose configuration, CI workflow, IaC, external database/cache/queue, or public deployment belongs in this assignment.

## Testing status

```powershell
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
.venv/Scripts/python.exe manage.py test groups discovery test_schema
```

**76 tests pass**: 18 schema checks, 32 discovery tests, and 26 group tests. These cover permissions, rollback, filters, timezone/DST, notifications, membership switching, offers/capacity, bans/ownership, messages, photo processing/cleanup, and separate-connection SQLite races. No coverage percentage has been measured; the **70% core-logic coverage** requirement and ADR-4 remain outstanding.

Database constraints guard row-level invariants. Both domains' services validate and use transactions; raw ORM writes can bypass these rules and are not a supported interface. SQLite uses IMMEDIATE transactions and a timeout; competing lock failures roll back and must become retry messages in future handlers. Public forms/pages, signup, inbox/group-photo routes, and the map interface remain to implement.

### Group services

`groups/services.py` implements group creation/settings, public joining, private requests/review/acceptance/cancellation, confirmed switching, leaving with seniority ownership handover, admin-only populated-group deletion, removal/bans, member-only messages, and checked photo access. A creator is a member: one group per user per event applies to creating and joining alike. Groups remain optional social coordination, never an attendance record.

New groups, joins, requests, and offer acceptance close at event start and freeze on cancellation/hiding. Existing members may coordinate during/after the event or cancellation; former members lose message access. Offers reserve no capacity; public/private mode changes retain existing members and pending requests. Request approval/rejection, owner transfer, removal/ban, and new requests generate in-app notices; messages do not.

Photos accept JPG/PNG/WebP up to 5 MiB and 20 megapixels, reject animation/invalid contents, resize to a maximum 1,600-pixel edge, and save a fresh JPEG without input metadata. Group descriptions allow 2,000 characters and messages 4,000. Old images delete after commit; newly written files are removed on a failed service write. Database and filesystem are not one transaction: callers must respect the service boundary, and production maintenance must handle crash-orphaned files. Photo-serving views are not yet present.

## Scope boundaries

Deferred: React/React Native frontend, native mobile app, ticket purchasing integrations, automated event imports, venue partnerships, verified organizer accounts, live chat, hidden invite-only groups, audio hosting, and community editing of the genre directory. Listening references are external links, not an uploaded music catalog.

Venue approval means a location record was reviewed, not that an event or organizer is guaranteed safe. Reports trigger review rather than automatic bans or removal. Location history is not part of the product.

## Project records and submission

- [ADR.md](ADR.md): required architecture decisions and their tradeoffs.
- [AI_USAGE.md](AI_USAGE.md): meaningful AI interactions and author explanations.
- [DESIGN.md](DESIGN.md): detailed agreed behavior, proposed details, and unresolved questions.
- [SCHEMA.md](SCHEMA.md): schema, relationships, constraints, target workflows, and current implementation boundary.
- [ROUTES.md](ROUTES.md): proposed step-2 URLs, forms, and handler behavior; awaiting discussion.

Deadline: **October 4, 2026, 23:59**; confirm the submission timezone in the course portal. Final deliverables also include a 4–5 page report with SDLC reasoning, SMART goals, matching architecture/schema diagrams, and the course AI-disclosure statement, plus the written comprehension check.

History requirements: at least 12 meaningful commits across at least 6 calendar days, no day exceeding 40% of all commits, pushed as work progresses. Generic “Initial commit” messages do not count. The final ADR log must contain exactly five entries spanning at least three distinct commit dates. Do not fabricate dates or defer all pushes to submission day.
