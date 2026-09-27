# Music Event Discovery

A music-first event discovery application: find nearby events by genre and date, hear what their music sounds like through listening references, and find people to attend with.

The idea comes from difficulty discovering smaller and niche events. It covers music broadly, including electronic music, rock, and jazz. Attendees and independent event organizers are the intended users.

**Status:** planning and documentation only; no working application yet. The project proposal has been approved by the professor, as reported by the author on September 24, 2026. Features below describe the planned implementation, not completed functionality. Product name is provisional.

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

Dependency versions, image-processing library, server package, and testing tools are not selected yet. There will be one root Python dependency manifest; frontend asset delivery must not introduce another package manifest.

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

Proposed layout (application folders do not exist yet):

```text
README.md
ADR.md
AI_USAGE.md
DESIGN.md
SCHEMA.md
requirements.txt
manage.py
config/                # Django settings, URL configuration, startup integration
accounts/              # Django-based user model
notifications/         # Shared in-app notifications
discovery/             # Models, views, business rules, migrations
groups/                # Models, views, business rules, migrations
templates/             # Pages and reusable fragments
static/                # CSS, JavaScript, frontend assets
```

## Running the application

Not available yet. Exact installation/start commands and supported Python version will be documented after implementation and verification.

The startup implementation must satisfy the assignment contract: one documented command, one running process, binding to `0.0.0.0`, an environment-configured port with a default, automatic noninteractive database setup, and readiness within a few seconds. SQLite and uploaded images will live under a configurable data directory; exact paths/defaults remain to be defined. Configuration must not require source edits or a `.env` file.

No self-authored Dockerfile, Compose configuration, CI workflow, IaC, external database/cache/queue, or public deployment belongs in this assignment.

## Testing status

Testing-tool selection is deferred. No tests have run and no coverage result is available. The assignment requires automated tests covering core business logic in both domains at **at least 70% coverage**; the verified command, measurement scope, and actual result must be added here before submission.

## Scope boundaries

Deferred: React/React Native frontend, native mobile app, ticket purchasing integrations, automated event imports, venue partnerships, verified organizer accounts, live chat, hidden invite-only groups, audio hosting, and community editing of the genre directory. Listening references are external links, not an uploaded music catalog.

Venue approval means a location record was reviewed, not that an event or organizer is guaranteed safe. Reports trigger review rather than automatic bans or removal. Location history is not part of the product.

## Project records and submission

- [ADR.md](ADR.md): required architecture decisions and their tradeoffs.
- [AI_USAGE.md](AI_USAGE.md): meaningful AI interactions and author explanations.
- [DESIGN.md](DESIGN.md): detailed agreed behavior, proposed details, and unresolved questions.
- [SCHEMA.md](SCHEMA.md): September 27 field-level schema, relationships, constraints, state transitions, and planning diagram; not yet implemented.

Deadline: **October 4, 2026, 23:59**; confirm the submission timezone in the course portal. Final deliverables also include a 4–5 page report with SDLC reasoning, SMART goals, matching architecture/schema diagrams, and the course AI-disclosure statement, plus the written comprehension check.

History requirements: at least 12 meaningful commits across at least 6 calendar days, no day exceeding 40% of all commits, pushed as work progresses. Generic “Initial commit” messages do not count. The final ADR log must contain exactly five entries spanning at least three distinct commit dates. Do not fabricate dates or defer all pushes to submission day.
