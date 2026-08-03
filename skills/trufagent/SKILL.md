---
name: trufagent
description: Classify and prepare a development task with Trufagent before acting. Use when the user invokes /trufagent or asks Trufagent to size, route, or plan work.
argument-hint: "<task>"
---

# Trufagent task adapter

Translate the user's task into the compact Trufagent v2 contract. This skill is a thin
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
   uv run --project "${CLAUDE_PLUGIN_ROOT}" trufagent prepare <intake.json> . --harness claude
   ```

4. Remove the temporary intake file after reading the JSON result.

## Follow the result

- If `status` is `needs_input`, ask only the returned `questions`. Do not begin
  implementation.
- Otherwise, present task complexity, `model_tier`, `effort`, compact memory and
  Graphify references, selected skills, and warnings.
- Load a selected skill from its `location` only when entering the phase that
  needs it. Do not scan the complete skill catalog.
- Use the runtime's exploration, implementation, and verification effort. Do not
  turn a small change into a formal design cycle unless the result requires it.
- Execution still follows Claude Code's normal permissions and the user's
  request. A plan is not permission for unrelated changes.

The current Claude host owns coordination; never invoke a second coordinator.
Resolve `model_tier` to a concrete model with
`trufagent models resolve . --harness claude --tier <tier>` so project
overrides are honored. Do not upgrade a phase without evidence.

Graphify is structural context, not the memory store. Query only the scoped
cartography suggested by the runtime; never replace decision history with a
graph scan.
