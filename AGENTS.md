# Repository workflow

The project owner authorized automatic commits and pushes on September 28, 2026.

- After completing a substantial, coherent change, review the diff, run the checks relevant to that change, commit with a descriptive message, and push to the current branch's configured upstream. Do not ask again for routine commits or pushes within the requested work.
- Group closely related code and documentation together. Separate independent substantial changes when each commit is coherent. Do not create empty commits or split trivial edits just to increase the count.
- Check the remote before pushing. Use ordinary pushes; never force-push, rewrite published history, or backdate commits to manufacture assignment cadence. If pushing fails, retain the local commits and report the failure.
- Stage only reviewed project changes. Keep virtual environments, runtime databases, uploads, generated secrets, caches, and local environment files out of Git.
- Update design/schema documentation and AI_USAGE.md when relevant. Leave the author's own-word explanations for the author to write.

This is an agent workflow instruction, not a scheduled job or a Git hook. Commit and push completed work during active task sessions; do not commit unfinished work on a timer. The assignment's distinct-day requirements still require actual work and pushes on those days.
