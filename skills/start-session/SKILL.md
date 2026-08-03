---
name: start-session
description: Start or resume a governed Trufagent work session and load its compact handoff. Use for /start-session or when beginning continued project work.
argument-hint: "[objective]"
---

# Start a Trufagent session

1. Work from the intended project root. If `.trufagent/config.yaml` is absent,
   stop and recommend `/trufagent:init`.
2. Run the following, adding `--objective "<objective>"` only when the user
   supplied one:

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" trufagent session start .
   ```

3. Summarize whether the session was created or resumed, its objective, and the
   compact previous handoff. Do not sweep old journals or the repository.
4. If a task is already known, continue through `/trufagent <task>`.

The runtime owns session state. Do not create a parallel context directory or
promote previous notes into governing memory.
