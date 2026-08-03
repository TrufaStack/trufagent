---
name: end-session
description: Close the active Trufagent session with a compact handoff and reviewable memory proposals. Use for /end-session or when ending a work session.
argument-hint: "[handoff note]"
---

# End a Trufagent session

1. Run session status and obtain the active session id:

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" trufagent session status .
   ```

2. Derive a concise close request from facts observed in this session:
   `session_id`, `summary`, `completed`, `next_steps`, `decisions`, and
   `memory_proposals`. Show any memory proposals to the user before closing.
   Omit speculative or secret-bearing proposals.
3. Create the request as a temporary JSON file outside the repository, then run:

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" trufagent session end . <request.json>
   ```

4. Remove the temporary request file and report the handoff plus IDs of any
   proposed memories.

Memory proposals remain `proposed`, unreviewed, and non-governing until explicit
human acceptance. Never run git commit, push, merge, or create a release as part
of session close.
