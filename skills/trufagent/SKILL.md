---
name: trufagent
description: Classify and prepare a development task with Trufagent before acting. Use when the user invokes /trufagent or asks Trufagent to size, route, or plan work.
argument-hint: "<task>"
---

# Trufagent task adapter

Translate the user's task into the Trufagent v1 runtime. This skill is a thin
Claude Code adapter: do not invent effort rules, memory rules, skill selection,
or model personas here.

## Prepare

1. Confirm the current directory is the intended project root and that
   `.trufagent/config.yaml` exists. If it does not, stop and recommend
   `/trufagent:init`.
2. Create a temporary JSON file outside the repository containing:

   ```json
   {"task": "<the user's complete task>", "signal_overrides": {}}
   ```

   Preserve the user's wording. Do not invent signal overrides. Add
   `required_symbols` only when the user or an approved plan explicitly names
   them; never invent targets to trigger Graphify-first.
3. Run:

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" trufagent plan prepare <intake.json> . 
   ```

4. Remove the temporary intake file after reading the JSON result.

## Follow the result

- If `ready_to_plan` is false, ask only the returned `questions`. Do not begin
  implementation.
- If it is true, present the selected strategy, effort level, relevant memories,
  cartography scope, skills, `model_route`, and verification depth compactly.
- Treat accepted governing memory as constraints. Proposed memory is context
  only and must be labelled as unreviewed.
- Use the runtime's exploration, execution, and verification budgets. Do not
  turn a small change into a formal design cycle unless the result requires it.
- Execution still follows Claude Code's normal permissions and the user's
  request. A plan is not permission for unrelated changes.

The current Claude host owns coordination; a prepared embedded plan returns
`coordinator=none`, so never invoke a second coordinator. Follow the remaining
phase model tiers when delegation is available; resolve a concrete model with
`trufagent models resolve . --harness claude --tier <tier>` so project
overrides are honored. Do not upgrade a phase without evidence.

Automatic multi-model execution is not enabled yet. If inspecting a proposed
delegation, compile it with `trufagent delegation compile` and enforce its
serial, single-writer boundaries; do not invoke delegates merely because the
protocol exists. `trufagent delegation dry-run` with scripted handoffs is the
only generally enabled executor. A read-only shadow adapter exists for
supervised evaluation only; it is not delegation authority.

Graphify is structural context, not the memory store. Query only the scoped
cartography suggested by the runtime; never replace decision history with a
graph scan.
