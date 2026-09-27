# Architecture Decision Record

Entries record decisions actually made, not implementation completion. Initial decisions recorded September 24, 2026; schema decision added September 27, 2026. No commit or push is implied by the dates below.

The final assignment requires exactly five entries across at least three distinct commit dates. Entry 3 (schema) is now recorded. Entry 4 (testing approach) remains unwritten because that decision is not yet settled. Complete them as real decisions on subsequent workdays, not by backdating. Numbering follows the required topics, not insertion order.

## [1]. Use Django with server-rendered pages and built-in authentication
Date: 2026-09-24
Status: Decided
Context: Python is the author's strongest language, and attendees need persistent username/password accounts. Admins need to curate genres, review proposed locations and reports, and manage accounts.
Decision: Use Django with its authentication, admin, ORM, and migrations, serving HTML templates, plain CSS, and JavaScript from the same application. Use built-in Django JSON responses for map queries rather than adding a REST framework.
Alternatives considered: Flask was considered for its smaller core, but would require assembling more account and administration functionality. React Native/Expo and React were considered for future portability, but add unfamiliar frontend tooling and complicate the one-manifest requirement; plain HTML/CSS matches current experience.
Consequences: Django's integrated features have concrete uses, while one Python application remains the runtime boundary. The author must learn and explain Django conventions; a later React frontend would replace presentation code while reusing suitably separated business logic.

## [2]. Separate discovery from attendance groups inside one monolith
Date: 2026-09-24
Status: Decided
Context: The product helps people find music events and optionally find company, and the assignment requires two distinct SQLite-backed domains. Map display alone is not an independent backend domain.
Decision: Use a discovery app for genres, venues, events, listening references, review/report flows, and filtering, and a groups app for groups, join requests, memberships, photos, and messages. Keep business rules separate from HTTP rendering, with groups obtaining event identity and necessary event information through a small discovery interface.
Alternatives considered: Events and a basic venue directory were considered as the two domains, but groups offers a more distinct user purpose. A single undifferentiated application module would make responsibilities and a future separation harder to explain; separately deployed services are prohibited now.
Consequences: Both domains share Django authentication and one SQLite database but have distinct data ownership and responsibilities. A future service split would need explicit handling of shared identity, event references, and consistency; the module split alone does not solve those issues.

## [3]. Separate reusable music and venue data from event and group state
Date: 2026-09-27
Status: Decided
Context: Events can share approved venues while having different genre tags, times, and groups, so editing one event must not change another. Users also need tracked-event updates and one group membership per event.
Decision: Use the relational schema in SCHEMA.md: event-to-venue references, category/tag link tables, separate curated and event listening references, event follows/change records, and group membership/request/ban/message records. Derive tempo from admin-curated category/tag ranges, and use transactional domain operations for membership switches, ownership transfer, and notification creation.
Alternatives considered: Copying venue details into every event would duplicate approval state; editing the shared venue when moving an event would affect other events. Event BPM input was rejected in favor of curated estimates, while a single membership status record was rejected in favor of separate current memberships and request history.
Consequences: Reusable records keep location review and genre colors consistent, while event-specific relationships preserve independent edits and optional group participation. Cross-record rules cannot all be expressed as simple row constraints and need guarded transactional operations; the schema and diagram must be reconciled with actual migrations during implementation.
## [5]. Defer real-time chat and external ticket purchasing integrations
Date: 2026-09-24
Status: Decided
Context: Attendees need basic coordination and access to tickets, but the assignment deadline and single-process constraints favor a limited first version. The user chose an in-app message board and external listening/ticket references.
Decision: Provide a members-only text message board that loads on page opening or refresh and ordinary external ticket links. Do not build real-time chat, push/email notifications, ticket checkout integrations, or hosted audio in this version.
Alternatives considered: An external group-chat link would be simpler but moves coordination outside the app. Live messaging and integrated ticket purchasing would offer richer interaction but add protocols, third-party dependencies, and implementation work beyond the current need.
Consequences: Groups can coordinate through persisted messages without real-time infrastructure, and ticket purchases remain with external providers. Users must refresh to see new messages and leave the app to buy tickets or listen to linked music.

September 27 scope clarification: in-app notifications for tracked-event changes and group offers are now included; live delivery and push/email remain deferred. This amendment preserves the earlier decision date rather than creating a sixth ADR entry.
