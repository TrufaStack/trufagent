---
name: end-session
description: Close an active Trufagent session with a compact handoff and optional reviewable memory proposals. Use when the user explicitly invokes $end-session, asks Codex to preserve session continuity, or is ending the current work period.
---

# End a Trufagent session

1. Run `trufagent session status .` and obtain the active session ID. Stop
   cleanly if no session is active.
2. Build a concise request from observed facts: `session_id`, `summary`,
   `completed`, `next_steps`, `decisions`, and `memory_proposals`.
3. Show proposed memories to the user before closing. Omit speculation and
   anything shaped like a secret. A proposal is not accepted memory.
4. Write the request to a temporary JSON file outside the repository using a
   file-writing tool. Do not interpolate its content into a shell command.
5. Run `trufagent session end . <request-path>`, then remove the temporary file.
6. Report the compact handoff and any proposed-memory IDs.

Memory proposals remain unreviewed and non-governing until explicit human
acceptance. Never run `git commit` as part of session close. Do not push, merge,
or release either.
