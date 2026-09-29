# Detailed design context

Updated: September 27, 2026. SCHEMA.md is authoritative for the subsequently agreed data design. This file preserves the design interview; it is not evidence that features are implemented. The README is the overview; ADR.md contains the five required decision topics, not every UI choice.

## Product intent

Music comes first, rather than appearance, reputation, or social popularity. Help people find smaller or niche events across genres and understand what the music sounds like. Group discovery supports attendance rather than replacing the music focus. The author originated the map/genre idea and may develop it into a personal product after the assignment.

The professor approved the proposal according to the author. That does not imply every later feature or external provider has been separately approved. No application code existed when these documents were created.

## Agreed: map and filtering

- Browser requests current location on opening, subject to permission. If declined/unavailable, use a default city (city still undecided).
- Users can pan/zoom freely. Do not snap back to their position; a locate-me control recenters intentionally.
- Refresh pins automatically after movement stops, retaining current filters. Ignore stale search responses. Exact delay is an implementation detail still to choose.
- Default date window: next 14 days. Date shortcuts and a custom range are planned; exact timezone, end-boundary, and ongoing-event semantics need definition.
- Genre matching supports ANY/OR and ALL/AND. Default ANY; no selection shows all.
- One pin per venue. Count only matching events; show a count when more than one matches. Ombre combines their genre colors; selecting the pin opens matching events ordered by date.
- Use a subdued charcoal/grey basemap with readable roads/labels so genre colors stand out. Retain textual genre labels and adequate pin contrast.
- Leaflet selected. Alidade Smooth Dark was shown as a visual reference, not a finalized provider contract. Provider, access configuration, attribution, usage terms, and asset distribution still need verification.
- Do not save user location history. Viewport bounds support map browsing; exact distance-filter controls remain to be specified.

## Agreed: genres and music

- Genres share one admin-managed name/color/description system across pins, tags, and Explore Genres.
- Curated reference artists, tracks, and sets explain each genre. Event creators can attach event-specific listening links, including for eclectic DJs.
- References can carry multiple genre tags. Artist references must not be confused with the actual event lineup.
- Event tempo is derived from optional admin-curated category/tag BPM ranges, labeled as an estimate. No event-creator BPM entry; unknown ranges display “Varies”.
- Use external listening links; uploads/streaming of music are out of scope. Events require at least one category and allow multiple tags; reference fields are specified in SCHEMA.md.

## Agreed: accounts, events, venues, reports

- Django username/password accounts; public browsing, authenticated publishing and participation.
- Creators edit their own event listings. Event fields include name/title, description, time, venue, genres, derived tempo estimates, listening links, and ticket link.
- Select an existing approved venue or propose one by name and placing a map pin, with optional written address. No geocoding provider is required for this flow.
- Proposed new locations require admin review; their events remain nonpublic until approved. Approved coordinates cannot be changed by ordinary users without review.
- Approval records location review, not a safety guarantee or verification of each organizer/event. A false claim about an established venue remains possible.
- Listings at approved venues publish immediately after input validation. Automated keyword/AI screening and universal event preapproval were discussed but superseded by reports plus new-location review.
- Posting rules establish expectations. Reporting reasons: incorrect information, spam/scam, safety concern, other; optional explanatory text.
- Reports enter an admin queue without automatic removal. Admins can dismiss reports, hide listings, or deactivate offending accounts.
- Safe text rendering and field/link validation remain necessary independently of moderation policy.

## Agreed: groups and communication

- “Going alone?” presents group cards associated with an event, with a create-group action.
- All groups are discoverable. Public means immediate joining; private means approval required, not hidden.
- Private join requests can be approved or declined by the creator. Hidden invite-only groups are explicitly out of scope.
- Group name, description (up to 2,000 characters), capacity, and one optional uploaded photo. Use a default image when absent. Accept JPG/PNG/WebP up to 5 MiB and 20 megapixels, reject animation, resize to a maximum 1,600-pixel edge, and re-encode to JPEG without metadata. Store files in the configured data directory, paths in SQLite.
- Prevent duplicate memberships and exceeding capacity. Members can leave. The owner counts toward capacity. One membership per user per event; switching uses an atomic operation.
- Only current members read/post messages. Text-only messages have author and timestamp, with a 4,000-character maximum; no live updates, message notifications, attachments, or read receipts. The board supports simple coordination, including arranging an external chat group.
- Creators count as members: one group per person per event, including groups they create. Owner departure transfers ownership by membership seniority; empty groups are deleted. Removal permits rejoining, bans prevent it. Authors may edit/delete their messages; admins may remove messages. Approved private requests are offers without reserved spaces. New participation closes at event start.
- Owners may edit name, description, photo, joining mode, and capacity, but not below current membership. Changing mode preserves existing members and unresolved requests. Only admins may disband a populated group.
- Notify owners of new requests and applicants of approval/rejection. Also notify members of removal, bans, and ownership transfer. Ordinary messages do not generate notices.

## Agreed: implementation direction

- Django, SQLite ORM/migrations, built-in auth/admin, templates, CSS, plain browser JavaScript, built-in JSON responses, Leaflet.
- One project with discovery and groups apps; shared identity, one database/process. No React, Node build pipeline, Django REST Framework, background worker, or actual service split.
- Models define storage; request handlers deal with HTTP; domain functions implement rules. Exact service/helper names and schema are not yet selected.
- Future frontend reuse motivates separation of business logic from templates, not building a full external API now.

## Proposed page structure (not separately confirmed)

Map landing page with event previews; full event page with music and groups; group page with membership/message controls; Explore Genres; submit/edit event; My Activity for own listings/groups/requests. Separate detail pages were recommended immediately before documentation was requested. Treat the exact navigation as a proposal.

## Still to decide during implementation

- Implement the agreed SCHEMA.md design and reconcile it with real models/migrations and the final report diagram (ADR-3 recorded September 27).
- Runtime versions, root manifest, image handling dependency, local asset delivery, tile provider.
- Startup server and command, environment variables/defaults, exact SQLite/media paths, and noninteractive admin provisioning. Account administration must not block clean startup.
- Testing approach (explicitly deferred by the author), actual coverage command/scope/result (ADR-4). At least 70% core coverage is still required.
- SDLC model, SMART goals, report, and final acceptance checks.
- Feature sequencing if the agreed scope pressures the deadline; discuss reductions instead of silently dropping agreed behavior.

## Assignment evidence

Deadline October 4, 2026 at 23:59; submission timezone not specified in the supplied instructions. At least 12 meaningful commits over 6 days; no day over 40%; push timestamps are checked. Exactly five ADR entries over at least three commit dates. Maintain AI_USAGE.md while work happens. A 4–5 page report and closed-book comprehension check remain required.

Do not author Docker/Compose, CI workflows, IaC, or publicly deploy this assignment. Keep dependencies near the suggested soft cap of 12 and aim for understandable code rather than adding optional features at the expense of required evidence.

## Reference documentation consulted in the discussion

- [Django migrations](https://docs.djangoproject.com/en/6.0/topics/migrations/)
- [Leaflet API](https://leafletjs.com/reference)
- [Alidade Smooth Dark](https://docs.stadiamaps.com/map-styles/alidade-smooth-dark/)
- [Expo web support](https://docs.expo.dev/workflow/web/) (considered, deferred)
- [Resident Advisor event submission](https://support.ra.co/article/12-submitting-events) and [Eventbrite transparency report](https://www.eventbrite.com/blog/wp-content/uploads/2026/02/Eventbrite_Transparency_Report_2025.pdf) informed moderation discussion, not an assumption that every platform uses the same workflow.

## September 27 schema decisions

See [SCHEMA.md](SCHEMA.md) for the complete field-level specification and relationship diagram.

- Optional private email and display name alongside Django username/password; no recovery or verification functionality.
- Required event start/end times, reusable approved venues, independent event venue references, cancellation separate from moderation hiding.
- Broad categories own pin colors; detailed tags belong to categories. Events may select multiple categories/tags even at a single-event venue.
- App-generated typical tempo estimates use curated ranges; artist/AI classification is future work.
- Event follows are independent of attendance and groups. In-app notifications cover venue/time/cancellation changes and private-group offers; phone/banner push, deals, and ticket prices remain future work.
- Groups are optional under “Attending alone?”. One membership per event; private approval offers require acceptance and a fresh capacity check without reserving space.
- Owner departure transfers ownership by seniority, or deletes the empty group. Removal and bans are separate. Authors edit/delete their own messages.
- Shared accounts/notification modules supplement the two feature domains without introducing services.
- The earlier September 27 documentation/ADR-3 batch was committed separately. The subsequent Django skeleton implements models/migrations and row constraints. September 28 discovery/group services, admin moderation, map JSON, and the approved public request handlers/forms/templates are implemented (see README, SCHEMA, and ROUTES.md).

## September 28 discovery implementation details for review

- Discovery operations are in services.py and reused by admin forms. No automatic moderation or public write API was added.
- Creator edits preserve admin hiding. Public queries exclude pending/rejected locations; creators/admins can inspect their unpublished records. Existing rejected-venue events can be corrected or cancelled, but new assignments to rejected venues are rejected.
- Used subgenre tags cannot be moved between categories without explicitly reclassifying their references; creating a new tag avoids silently corrupting event selections.
- Map windows use aware datetimes and overlap rules; default next 14 days. API supports viewport/date/ANY-ALL category/tag filters. More than 1,000 results requires a narrower query rather than partial counts.
- Notifications are persisted in the edit transaction. Summaries contain changed field names and pending-location warnings, not private coordinates/text; before/after snapshots remain restricted to admin history. The recipient-only inbox UI is implemented.
- Venue-local datetime input was approved and implemented in event admin forms. UTC remains the storage format; moving an event reinterprets entered times in the destination venue's timezone, with DST ambiguity/gap validation.
- No real event fixtures or changes to user data were made. Fifty isolated tests pass; full measured core coverage and ADR-4 are still outstanding.

### Lifecycle clarification

Event creators can change their own category/tag selections without deleting the event. The restriction concerns moving a shared tag into a new parent category, which could invalidate other events and curated references.

Cancelled events disappear from the map and generate tracked-event notifications; records remain. Retention-based purging is a future possibility with no agreed duration or deletion policy; no purge job is implemented. Group services enforce closure of creation, joins, requests, and offer acceptance at event start. Existing memberships continue and members can use the message board during and after the event, including after cancellation. 101 backend/HTTP tests pass; measured coverage remains to establish.

## September 28: approved public routes and first interface

Implemented Django pages/forms for accounts, venue proposals, event submission/editing/references/reports/tracking, optional group creation/settings/joining/request review/switching, messages, checked photos, notifications, and My Activity. All writes are POST with CSRF; services enforce domain permissions and transactions. Public group cards remain visible while boards are member-only. Successful writes redirect; invalid forms retain errors and lock failures ask for a retry.

The first interface uses black/gray layouts with genre accents and a grayscale Leaflet/OpenStreetMap map. Browser location centers the map, falling back to Paris; panning or filtering refreshes JSON automatically. Gradient venue pins combine category colors and show counts for multiple matching events. Browser dates describe local-midnight intervals; detail/form dates use venue-local time. Listening examples are external links. CDN library and tiles require internet access and visible attribution; no new package manifest or server process was introduced.

Local Waitress page/asset checks and 101 automated tests pass. JavaScript syntax and migration consistency were checked. Visual browser inspection was attempted but the computer-use runtime failed to start; review layout, map interactions, and accessibility in a normal browser next. Existing long-running app processes need restarting to load the new URLs.

## Desktop UI prototype decisions

The author's UI_mock_inspo.png establishes a dark full-height sidebar and a map-dominant canvas. Agreed navigation: Near me (map only), Discover, My events (tracked events/own listings), Groups (My groups/Requests, including approved requests), and Profile. Other destinations replace the map; returning restores map position, dates, and genre filters. Date controls sit above a genre filter button. A searchable panel accommodates many umbrella genres with expandable subgenre tags, ANY matching by default and optional ALL. Selected chips invert to genre-colored fills with gray text; the sidebar shows a compact selection summary. Genre taxonomy remains undecided.

A selected pin opens a floating panel showing only title, venue, local date/time, and genre tags. Show more reveals other details and actions. Multiple events at a venue get an event list. Desktop is the current design target; mobile adaptation follows later. The standalone static/prototype files implement clickable visual states with placeholder labels/geometry, no live data and no backend writes. The optional /ui/ route opens this preview, while existing functional routes remain available. JS syntax/config checks passed; browser visual review remains unverified because the available browser blocked local file navigation.

## September 29: desktop preview refinement

The September 29 UI review increases markers to 48 × 62 pixel teardrops with tips anchored to map locations, preserving gradients and event counts. A larger floating preview has stronger typography, contrast, and a genre-colored accent. Selecting another marker replaces the preview immediately; expanded details are nonmodal and close when switching markers. Placeholder A/B/C labels make switching visible without connecting real data. Larger labeled sidebar items replace the previous compact spacing; Profile appears only in navigation. Local HTTP browser inspection verified the layout and direct switching, including from expanded details. Restart the static-serving app after asset edits because WhiteNoise caches file metadata at startup.

Further UI review adds trackpad Ctrl+wheel pinch, mouse-wheel zoom, and two-pointer touch pinch with midpoint anchoring and pan continuity when a finger lifts. Drag/pinch gestures suppress unintended pin clicks. Existing zoom limits remain 0.75–2.2. Date and genre buttons now have 64-pixel minimum heights, larger icons/text, and more surrounding space. Filters follow navigation after a fixed gap rather than sitting at the bottom of a growing empty area. The sidebar scrolls on short windows or when selections require more room. Browser review confirms the default sidebar fits a 1280 × 720 viewport and wheel zoom updates the map; simulated input checks cover pinch math and lifecycle. Physical gesture testing remains for the author. Icon-only navigation and colored hover banners were discussed, but remain undecided; the current experiment keeps visible labels and neutral navigation accents so genre colors retain their meaning.

## September 29: demo fixtures without genre decisions

Genre taxonomy remains for the author to curate after discussion with other music listeners. The explicit seed_demo command creates five regular demo users and five synthetic Paris-area venues labeled as fictional. Three approved, one pending, and one rejected venue illustrate fixture review states; no actual location verification is claimed. No genres/tags are created or edited. Without a selected existing category, events/groups are skipped. Later, --category ID enables event/group/request/message/follow scenarios through domain services. Unchanged reruns preserve profiles, passwords, venue edits, and membership/request activity. --refresh-dates explicitly moves fixture events forward with normal tracked-event notices. Runtime fixture data stays local and ignored by Git. The full suite now passes 108 tests.
