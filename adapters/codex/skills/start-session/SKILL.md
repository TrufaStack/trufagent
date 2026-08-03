---
name: start-session
description: Start or resume a Trufagent work session from its compact governed handoff. Use when the user explicitly invokes $start-session, begins a continued project session, or asks Codex to recover the prior Trufagent handoff.
---

# Start a Trufagent session

1. Confirm the current directory is the intended project root and
   `.trufagent/config.yaml` exists. If absent, stop and offer initialization.
2. Run `trufagent session start .`. Add `--objective "<objective>"` only when
   the user supplied an objective; pass it as one safely quoted argument.
3. Report whether the session was created or resumed, its objective, and the
   compact previous handoff.
4. If a task is known, invoke `$trufagent` for that task.

Read only the runtime handoff. Do not sweep old journals, duplicate state in a
parallel context directory, or promote notes into governing memory.
