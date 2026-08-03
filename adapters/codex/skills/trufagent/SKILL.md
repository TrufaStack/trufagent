---
name: trufagent
description: Prepare development work with Trufagent's governed memory, Graphify cartography, skill catalog, and task-sized effort policy. Use when the user explicitly invokes $trufagent or asks Codex to classify, size, route, or plan a coding task before acting.
---

# Prepare work with Trufagent

Keep this adapter thin. Let the runtime select effort, context, skills, and
verification.

1. Confirm the current directory is the intended project root and
   `.trufagent/config.yaml` exists. If absent, stop and offer initialization.
2. Write a temporary JSON file outside the repository with the user's complete
   wording:

   ```json
   {"task": "<task>", "signal_overrides": {}}
   ```

   Do not invent signal overrides. Use a file-writing tool; do not interpolate
   the task into a shell command. Add `required_symbols` only when the user or
   an approved plan explicitly names them; never invent targets to trigger
   Graphify-first.
3. Run `trufagent plan prepare <intake-path> .`.
4. Remove the temporary file after parsing the JSON result.
5. If `ready_to_plan` is false, ask only the returned `questions` and pause.
6. Otherwise, state the strategy and apply its exploration, execution, and
   verification budgets. Surface relevant memories, Graphify scope, selected
   skills, `model_route`, warnings, and autonomy boundary compactly.
7. For each selected skill, read only its first accessible `locations` path
   when entering the phase that needs it. The runtime has already enforced
   review status. Do not enable or scan the full skill library.

The current Codex host owns coordination; a prepared embedded plan returns
`coordinator=none`, so never spawn a second coordinator. Treat remaining model
tiers as routing recommendations: economy maps to GPT-5.6-Luna,
balanced to GPT-5.6-Terra, and frontier to GPT-5.6-Sol unless project
configuration overrides them. Resolve the concrete choice with
`trufagent models resolve . --harness codex --tier <tier>`. Never upgrade a
phase merely because a stronger model exists.

Automatic multi-model execution is not enabled yet. If inspecting a proposed
delegation, compile it with `trufagent delegation compile` and enforce its
serial, single-writer boundaries; do not spawn delegates merely because the
protocol exists. `trufagent delegation dry-run` with scripted handoffs is the
only generally enabled executor. A read-only shadow adapter exists for
supervised evaluation only; it is not delegation authority.

Treat accepted governing memory as constraints. Label proposed memory as
unreviewed context. Use Graphify for scoped structural retrieval, not as a
replacement for decision memory. Do not inflate small changes or treat a plan
as authorization for unrelated actions.
