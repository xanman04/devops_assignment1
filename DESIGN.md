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
- Group name, description, capacity, and one optional uploaded photo. Use a default image when absent; validate type/size and store files in the configured data directory, paths in SQLite.
- Prevent duplicate memberships and exceeding capacity. Members can leave. The owner counts toward capacity. One membership per user per event; switching uses an atomic operation.
- Only members read/post messages. Text-only messages have author and timestamp; no live updates, message notifications, attachments, or read receipts. Event-change and group-offer notifications are separate.
- Owner departure transfers ownership by membership seniority; empty groups are deleted. Removal permits rejoining, bans prevent it. Authors may edit/delete their messages; admins may remove messages. Approved private requests are offers without reserved spaces. The exact post-start joining cutoff remains an implementation follow-up.

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
- Today's delivery is documentation and ADR-3 only. Django skeleton/models/migrations are the next chunk.
