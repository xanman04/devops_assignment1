# Bassline

A music-first event discovery application: find nearby events by genre and date, hear what their music sounds like through listening references, and find people to attend with.

The idea comes from difficulty discovering smaller and niche events. It covers music broadly, including electronic music, rock, and jazz. Attendees and independent event organizers are the intended users.

**Status:** discovery/group services and Django workflows are implemented. The map and browsing layout are now connected to Django at `/`, `/discover/`, `/my-events/`, and `/groups/`. The professor approved the proposal, as reported by the author on September 24. Bassline is the current working title.

## Planned features

### Desktop UI prototype

The functional desktop interface is at **http://localhost:8000/**. The earlier standalone visual prototype is still available at **http://localhost:8000/ui/** as a design reference; it has placeholder content and no database/API connection.

Click the sidebar to visit Near me, Discover, My events, Groups, and Profile. Near me has an illustrative draggable/zoomable map, placeholder pins, date controls, and a searchable/collapsible genre filter panel. Selected genre chips invert to colored fills; generic genre labels are not taxonomy decisions. Map position/date/genre state survives navigation and, where permitted, refresh within the same browser tab using sessionStorage. Pin previews contain only title, venue, local date/time, and genre tags; Show more opens a detail layout. Groups contains only My groups and Requests. Search, profile edits, and event creation demonstrate layouts without saving real data; tracking a placeholder changes only prototype state. Mobile layout work remains deferred.

Pins now use larger teardrops anchored at their tips. Selecting another pin replaces the floating preview, including when expanded details are open. The map supports trackpad pinch, two-finger touch pinch, mouse-wheel zoom, and dragging. Zoom follows the gesture position. The 310px sidebar uses labeled navigation and a single Profile destination. Date/genre controls sit toward the bottom with more space above than below; their button/icon sizes are preserved. Short desktop windows can scroll the sidebar when needed.

Discover displays an Upcoming events poster gallery, a compact Playing near me lineup, colored Genres, and an Artists & DJs directory. Its main title and short intro lead into single-line section headings without numbers or extra subtitles. Event posters appear at their full portrait proportions with captions below on a dark framed backdrop. Search also shows matching subgenres with links to their expanded descriptions. Rows without matches disappear, and a single no-results message appears when nothing matches. The nearby row uses browser location permission to find linked performers at public events within 30 km in the next two weeks; it shows a location-access message when permission is unavailable. Each performer appears once, linked to their profile. My events displays Tracked events and Your listings together; Groups displays My groups and Requests together. Scroll each carousel or use its previous/next buttons; horizontal scrolling stops at the row's ends and the scrollbars stay hidden.

The live Discover page also has seven curated real DJ profiles with locally bundled, credited photos. After adding the existing genre categories, run `.\.venv\Scripts\python.exe manage.py seed_djs` to populate them on a fresh local database. The command can be rerun safely. [DJ_SOURCES.md](DJ_SOURCES.md) records the artist and image sources.

The Django home page uses the approved dark sidebar and MapLibre vector map. Date controls and searchable category/subgenre chips feed the existing public map API. Multiple genres match either or both; selecting subgenres narrows their selected parent genre, while other selected genres remain included. Subgenres show only those under selected categories, or all when no category is selected. Clicking a venue pin opens a floating panel with real matching events. The sidebar search routes to Discover on every page and searches public events, venues, performers, broad genres, subgenre names and descriptions, and curated listening references. Discover reads those records; My events reads the signed-in user's follows/listings; Groups reads their memberships/requests. The full activity page remains available for older records. Your 65px filter bottom padding is preserved. Restart `app.py` after static-file edits because WhiteNoise caches file metadata; when using `manage.py runserver`, run `manage.py collectstatic --noinput` before restarting.

The live map keeps additional tile zoom levels in memory and retains pending lower-detail tiles during zooming so revisiting an area can render more smoothly. New areas still depend on tile-provider and network response times.

The interface bundles the Funnel Display variable font in `static/fonts/`, with its SIL Open Font License beside the font file. Change the `font-family` in `static/app.css` to trial another typeface; the standalone `/ui/` prototype has a separate setting in `static/prototype/style.css`.

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

In Django admin, enter each broad category color as `#RRGGBB` text and supply a typical numeric BPM minimum and maximum for categories and subgenre tags. BPM maxima may exceed 200. A selected tag's range replaces its parent category's broad range for that component. With multiple tags or categories, the displayed estimate spans the lowest minimum to highest maximum. Updating a curated range updates existing events automatically; event BPM is never stored or entered by organizers. Tags imported without a fixed BPM range use their parent category range; classifications without either range display “Varies”.
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
| Map | MapLibre GL JS 6.3.0, OpenFreeMap Dark vector style | Smooth vector panning/zooming and custom genre markers; visible attribution and normal browser tile caching |
| Files | Local group images; file paths in SQLite | Keep data inside the application's configurable data directory |

Dependencies are pinned in the single root `requirements.txt`: Django 5.2.17 LTS, Pillow for image-field support, Waitress for a single-process Windows-compatible server, WhiteNoise for static assets, tzdata for Windows timezones, and Django's transitive dependencies. Verified with Python 3.13.1. Frontend assets must not introduce another package manifest.

## Planned architecture

One Django project runs as one process, with two logical domain apps sharing one SQLite database:

- **`discovery`:** categories/tags, venues, events, listening references, venue review, event reports, follows/change history, and map filtering.
- **`groups`:** attendance groups, join requests, memberships, photos, and messages.

Django authentication supplies shared accounts with display names and optional private email; shared notifications support event-change updates and group offers. Request handlers handle HTTP; domain business rules remain separate from page rendering and map JSON responses. Groups references events by identity and obtains necessary event information through a small discovery interface. A future service split would also need to address shared accounts and database relationships; it is not part of this assignment.

```text
Browser: templates + CSS + JavaScript + MapLibre GL JS
              |
       Django pages / JSON
          /           \
     discovery       groups
          \           /
       Django ORM + SQLite
       Local image storage

Browser also requests basemap tiles from the selected provider.
```

Current layout:

```text
README.md
ADR.md
AI_USAGE.md
DESIGN.md
SCHEMA.md
ROUTES.md              # Implemented URL and request-handler contract
AGENTS.md              # Automatic commit/push workflow during active sessions
requirements.txt
manage.py
app.py                 # Automatic migration/static setup and single-process server
config/                # Django settings, URL configuration, startup integration
accounts/              # Django-based user model
notifications/         # Shared in-app notifications
discovery/             # Models, services, admin forms, map JSON view, tests, migrations
groups/                # Models, membership/message services, photos, tests, admin, migrations
test_schema.py         # Focused persistence/integrity checks
test_web.py            # HTTP form/workflow, permission, privacy, and CSRF checks
templates/             # Shared layout and discovery/group/account/inbox pages
static/                # Plain CSS and MapLibre map integration JavaScript
```

## Running the application

From the repository root, using Python 3.13 (verified on 3.13.1):

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe app.py
```

On Linux/macOS use `.venv/bin/python` instead. Open http://localhost:8000/ for map discovery. Startup applies committed migrations and collects static assets automatically, then starts Waitress on `0.0.0.0` in one process, without a reloader or frontend server. Restart the process after code changes; it does not auto-reload.

Create an account through the public navigation. Use admin to curate genres and approve proposed venues; then list events and use optional groups through the public pages. Map JavaScript requests browser location permission and falls back to Paris when unavailable/declined. Pan to explore another area. Map results refresh automatically; the server-rendered upcoming-events list is also usable without JavaScript. Browser date filters span local midnight through the selected end date exclusively; event detail/form times use the venue timezone. No location history is saved to accounts.

The live map uses MapLibre GL JS 6.3.0 directly with [OpenFreeMap's Dark vector style](https://openfreemap.org/quick_start/), adjusted in the browser to a clearer charcoal palette. Map vectors move continuously while the event endpoint refreshes after movement; existing pins remain visible until replacement results arrive. Main navigation keeps the map mounted across Near me, Discover, My events, Groups, Notifications, and Profile, so returning to Near me restores the same view without recreating the WebGL map. Other detail/form links remain normal page loads; the last map center and zoom are kept in session storage for those returns. The map library and tiles require internet access; no API key, Node runtime, or frontend package manifest is needed. Browser geolocation draws only a small dot, and the center control animates back to it. The bottom label contains only the matching event and venue counts. The map position is not saved to accounts. Tile requests reveal the viewed map area to the provider; no offline download or prefetch is provided. The list panel closes with X, Escape, a second click on List, or a map click.

| Environment variable | Default / purpose |
|---|---|
| `PORT` | `8000` |
| `DATA_DIR` | Repository `data/`; SQLite at `DATA_DIR/db.sqlite3`, images at `DATA_DIR/media/groups/`, collected assets at `DATA_DIR/static/` |
| `DJANGO_SECRET_KEY` | If absent, a generated local key is persisted in `DATA_DIR/.django-secret-key`; set explicitly for future deployment |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]`; add the real hostname/IP for access from another device |
| `DJANGO_DEBUG` | `0`; use `1` only for local debugging |

No `.env` file or source edit is required. Runtime data and the virtual environment are ignored by Git. Group photos and uploaded event posters are served through visibility-checked routes; raw media directories are not public.

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

`notifications/services.py` supplies recipient-scoped `inbox` and `mark_read` operations. Relevant edits produce one EventChange with before/after snapshots and one notification per active follower, inside the edit transaction. Failed notification writes roll back the edit. No alerts are generated for unchanged saves or title-only changes. Notification summaries omit coordinates and private event text; raw snapshots remain admin-only history. Public pages provide event tracking/report forms and a recipient-only inbox.

Read-only map endpoint: `GET /api/map/events/`. Optional query parameters:

- `start`, `end`: ISO datetimes with timezone, e.g. `2026-10-01T00:00:00Z`; default is now through the next 14 days.
- `categories`, `tags`: comma-separated IDs; empty means unrestricted.
- `match`: `any` (default) or `all`, applied across the selected category/tag IDs.
- `bounds`: `south,west,north,east`; west greater than east handles a viewport crossing the date line.

Example: `/api/map/events/?bounds=48,2,49,3&match=any`. Results contain venue coordinates, distinct category colors, counts, and matching event cards ordered by start time. Only approved-venue, unhidden, uncancelled, categorized events overlapping the requested interval appear. The interval is start-inclusive/end-exclusive; ongoing events match. Cancelled events remain available through authorized detail pages but not the map. Invalid queries return 400; queries over 1,000 events ask for narrower filters rather than returning misleading partial pin counts. Templates escape text, and JavaScript builds popup/card text using DOM text nodes.

Admins with user-delete permission can delete unreferenced accounts through Django's confirmation page. Referenced accounts remain protected: Django lists blocking event/group/message records rather than cascading deletion. Deactivate those accounts when their history should remain.

No self-authored Dockerfile, Compose configuration, CI workflow, IaC, external database/cache/queue, or public deployment belongs in this assignment.

## Curated electronic subgenres

The supplied `discovery/fixtures/electronic_subgenres_v1.csv` contains 251 subgenre tags. Import it into the 22 existing broad categories after setting those categories up in admin:

```powershell
.venv/Scripts/python.exe manage.py import_subgenres --dry-run
.venv/Scripts/python.exe manage.py import_subgenres
```

The importer uses each CSV `pitch` as the tag description and its BPM columns as curated tempo references. It maps the CSV label `EBM / Industrial` to the existing `Industrial / EBM` category, preserves all six ranges whose maxima exceed 200, and leaves Drone's unspecified tempo blank so its parent Ambient / Experimental range applies. The Hard Dance / Hardcore broad category remains at 150–200 BPM. It does not create categories, change their colors, or copy research-source notes into the database. A repeat run leaves matching tags untouched and stops if an existing tag has been edited; `--update` explicitly replaces those edits with CSV values. The supplied classifications and descriptions have not been independently fact-checked.

## Optional demo data

```powershell
.venv/Scripts/python.exe manage.py seed_demo
```

Adds five fictional users (`demo_organizer`, `demo_alex`, `demo_sam`, `demo_jo`, `demo_morgan`) and five clearly labeled fictional Paris-area venues: three approved fixture states, one pending, and one rejected. These are synthetic locations, not real venue recommendations or verification. New demo accounts have password `Demo-music-2026!` and no staff/admin permissions. The command is explicit and never runs automatically at startup.

`seed_demo` never creates or changes genres or subgenre tags. Without a category selection, no events/groups are created, so venues alone do not produce map pins. After curating a genre in admin, select its existing ID:

```powershell
.venv/Scripts/python.exe manage.py seed_demo --category 1
# Repeat --category for mixed-category examples, using actual existing IDs.
# Explicitly refresh this fixture's event dates later if needed:
.venv/Scripts/python.exe manage.py seed_demo --category 1 --refresh-dates
```

Optional scenarios include six listings (four public/upcoming, one awaiting venue approval, one cancelled), overlapping events, two groups, a pending request, an approved switch offer, messages, follows, and notifications. Event/group transitions use domain services. Synthetic venue review states and account fixtures use direct validated model creation; they do not claim a real review occurred. Genre references/BPM/colors remain unchanged.

Unchanged reruns create no duplicates, reset no passwords, and preserve demo profiles, venue edits, memberships, and requests. Reserved usernames require their original `@example.invalid` demo email marker; conflicting accounts abort without changes. Renaming/removing fixtures or editing those markers can require manual reconciliation. No reset/deletion command is included. `--refresh-dates` updates matching fixture event times with normal follower notices; classification/cancellation remain unchanged. All seed writes roll back together on failure. SQLite demo data stays ignored by Git.

### Madrid classroom listings

After running `seed_demo` and importing the curated electronic subgenres, run:

```powershell
.venv/Scripts/python.exe manage.py seed_madrid_demo
# Later, explicitly move existing fixture dates into the upcoming two weeks:
.venv/Scripts/python.exe manage.py seed_madrid_demo --refresh-dates
```

This adds **24 fictional events at 14 real Madrid venues**. The command uses the five existing `demo_*` accounts as organizers; it creates no users, genres, tags, ticket links, or real-event copies. It also creates fictional performer profiles for the demo lineups and links them to their event records, without replacing existing profiles or event edits. It assigns organizers deterministically so reruns do not change ownership. Existing venue edits and passwords are preserved, and reruns add no duplicate listings. The `--refresh-dates` option uses the normal event service, so followers receive ordinary date-change notifications. Events are placed on typical late-night, early-evening and Sunday listening slots, all in `Europe/Madrid`. Event titles, lineups, descriptions and 24 bundled fictional flyers are original. Four venues have one single-category event each, producing solid-color pins alongside blended multi-genre pins. The in-app demo labels are hidden so the interface can be evaluated as a realistic product; these nights are still invented, and nobody should travel to a venue expecting one. The map opens on Madrid if there is no saved camera or usable browser location; normal near-me centering still takes precedence when available.

On rerun, descriptions carrying the old in-app disclaimer are replaced with the clean fixture description. Other event edits are preserved.

Venue names and addresses were checked against the [RA Madrid club directory](https://ra.co/clubs/es/madrid), [Madrid tourism listings](https://www.esmadrid.com/noche/clamores), and [Goya Social Club](https://goyasocialclub.com/contact/) and [Lula Club](https://lula.club/contact) venue pages. Coordinates came from [OpenStreetMap Nominatim](https://nominatim.openstreetmap.org/) venue matches or street-address matches on September 30, 2026. Street-address coordinates can differ from the actual entrance. These records are approved only as classroom fixtures; that status does not imply organizer affiliation, a real event, or a safety assessment. No RA/Fever listing text, lineup, ticket URL, or poster was imported. Four original backgrounds were made with the built-in image-generation tool, then `tools/build_demo_posters.py` added the invented titles and lineups to produce 24 compressed WebP flyers. `Event.demo_poster` retains the bundled artwork path for these fixtures. Event creators and admins can now upload a JPG, PNG, or WebP poster (maximum 5 MiB); the app converts it to a metadata-free JPEG, shows it in preference to the demo artwork, and supports replacement/removal.

## Testing status

```powershell
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
.venv/Scripts/python.exe manage.py test groups discovery test_schema test_web
```

**129 tests pass** across schema, discovery, groups, HTTP, and demo data. These cover permissions, rollback, filters, timezone/DST, notifications, membership switching, offers/capacity, bans/ownership, messages, image processing and replacement, private event posters, performer deduplication and nearby selection, separate-connection SQLite races, CSRF, forged form fields, private venue/message access, and automatic tempo recalculation. Migration consistency and live public page/static asset responses were also checked. No coverage percentage has been measured; the **70% core-logic coverage** requirement and ADR-4 remain outstanding.

Database constraints guard row-level invariants. Both domains' services validate and use transactions; raw ORM writes can bypass these rules and are not a supported interface. SQLite uses IMMEDIATE transactions and a timeout; handlers translate competing lock failures into retry responses. Pages use GET for reads, POST plus CSRF for writes, and redirects after successful saves. Visual polish, a browser interaction review, measured coverage, and the remaining submission records/report are still outstanding.

### Group services

`groups/services.py` implements group creation/settings, public joining, private requests/review/acceptance/cancellation, confirmed switching, leaving with seniority ownership handover, admin-only populated-group deletion, removal/bans, member-only messages, and checked photo access. A creator is a member: one group per user per event applies to creating and joining alike. Groups remain optional social coordination, never an attendance record.

New groups, joins, requests, and offer acceptance close at event start and freeze on cancellation/hiding. Existing members may coordinate during/after the event or cancellation; former members lose message access. Offers reserve no capacity; public/private mode changes retain existing members and pending requests. Request approval/rejection, owner transfer, removal/ban, and new requests generate in-app notices; messages do not.

Photos accept JPG/PNG/WebP up to 5 MiB and 20 megapixels, reject animation/invalid contents, resize to a maximum 1,600-pixel edge, and save a fresh JPEG without input metadata. Group descriptions allow 2,000 characters and messages 4,000. Old images delete after commit; newly written files are removed on a failed service write. Database and filesystem are not one transaction: callers respect the service boundary, and production maintenance must handle crash-orphaned files. Photo views check group visibility and disable shared caching.

## Scope boundaries

Deferred: React/React Native frontend, native mobile app, ticket purchasing integrations, automated event imports, venue partnerships, verified organizer accounts, live chat, hidden invite-only groups, audio hosting, and community editing of the genre directory. Listening references are external links, not an uploaded music catalog.

Venue approval means a location record was reviewed, not that an event or organizer is guaranteed safe. Reports trigger review rather than automatic bans or removal. Location history is not part of the product.

## Project records and submission

- [ADR.md](ADR.md): required architecture decisions and their tradeoffs.
- [AI_USAGE.md](AI_USAGE.md): meaningful AI interactions and author explanations.
- [DESIGN.md](DESIGN.md): detailed agreed behavior, proposed details, and unresolved questions.
- [SCHEMA.md](SCHEMA.md): schema, relationships, constraints, target workflows, and current implementation boundary.
- [ROUTES.md](ROUTES.md): implemented step-2 URLs, forms, and handler behavior.

Deadline: **October 4, 2026, 23:59**; confirm the submission timezone in the course portal. Final deliverables also include a 4–5 page report with SDLC reasoning, SMART goals, matching architecture/schema diagrams, and the course AI-disclosure statement, plus the written comprehension check.

History requirements: at least 12 meaningful commits across at least 6 calendar days, no day exceeding 40% of all commits, pushed as work progresses. Generic “Initial commit” messages do not count. The final ADR log must contain exactly five entries spanning at least three distinct commit dates. Do not fabricate dates or defer all pushes to submission day.
