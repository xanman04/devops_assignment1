# Repository workflow

The project owner authorized automatic commits and pushes on September 28, 2026.

## Commits

- After completing a substantial, coherent change, review the diff, run the checks relevant to that change, commit with a descriptive message, and push to the current branch's configured upstream. Do not ask again for routine commits or pushes within the requested work.
- Group closely related code and documentation together. Separate independent substantial changes when each commit is coherent. Do not create empty commits or split trivial edits just to increase the count.
- Check the remote before pushing. Use ordinary pushes; never force-push, rewrite published history, or backdate commits to manufacture assignment cadence. If pushing fails, retain the local commits and report the failure.
- Stage only reviewed project changes. Keep virtual environments, runtime databases, uploads, generated secrets, caches, scratch scripts, and local environment files out of Git.
- The assignment allows no more than 40% of all commits on one calendar day and checks push timestamps. Before committing, count today's local commits against the total; distinguish that evidence from unverified push timestamps. More commits on an already concentrated day raise its share: keep commits coherent rather than padding the count, and never falsify dates.

## AI usage log (`AI_USAGE.md`)

The log is kept **per commit, not per prompt**. One row describes the AI-assisted work that one commit contains, however many prompts it took.

The owner chose this workflow on October 4, 2026 to make author review practical. It differs from the assignment's explicit requirement of one row per meaningful interaction. Preserve relevant interactions in each commit summary, disclose the grouping, and do not claim the workflow change overrides the course requirement or guarantees compliance.

- Add or update the row in the same commit as the change. Columns follow the assignment: Date/commit, Tool, Prompt, Disposition (Accepted/Modified/Rejected), What changed & why, In my own words.
- **Date/commit:** the date and the commit's subject line. A commit cannot contain its own hash, so add the short hash to the row in the next commit that touches `AI_USAGE.md`; do not create an extra commit just for that.
- **Tool:** name the tool(s) that did the work, for example Claude or Codex.
- **Prompt:** a short summary of the request(s) behind the commit, in the author's words where possible. It does not need to quote every prompt.
- **Disposition and What changed & why:** state what was accepted, modified or rejected, based on what actually happened. If it is unclear, leave it for the author to confirm; never guess.
- **In my own words:** one explanation per commit, written by the author using the real function and variable names. The agent leaves it as `TODO` and does not write it. The author fills it in when reviewing the commit, not after each prompt.
- Update design and schema documentation (`README.md`, `DESIGN.md`, `SCHEMA.md`, `ROUTES.md`, `ADR.md`) when the change makes them wrong.
- Preserve existing historical records until the owner requests their restructuring. Never invent author explanations or imply they were completed earlier.
- The joint Claude/ChatGPT audit and coordination conversation is outside project scope by the owner's instruction. Keep its artifacts outside the repository and exclude that conversation from project AI documentation.

This is an agent workflow instruction, not a scheduled job or a Git hook. Commit and push completed work during active task sessions; do not commit unfinished work on a timer. The assignment's distinct-day requirements still require actual work and pushes on those days.
