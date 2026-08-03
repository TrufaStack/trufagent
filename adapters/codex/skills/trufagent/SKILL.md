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
3. Run `trufagent prepare <intake-path> . --harness codex`.
4. Remove the temporary file after parsing the JSON result.
5. If `status` is `needs_input`, ask only the returned `questions` and pause.
6. Otherwise, state the task complexity and follow `model_tier` and the
   exploration, implementation, and verification `effort` values. Surface the
   compact memory and Graphify references, selected skills, and warnings.
7. Load a selected skill from its `location` only when entering the phase that
   needs it. Do not enable or scan the full skill library.

The current Codex host owns coordination; never spawn a second coordinator.
Treat `model_tier` as a routing recommendation: economy maps to GPT-5.6-Luna
with maximum reasoning effort; balanced and frontier map to GPT-5.6-Sol with
low reasoning effort unless project configuration overrides the model. Resolve with
`trufagent models resolve . --harness codex --tier <tier>`. Never upgrade a
phase merely because a stronger model exists.

Use Graphify for scoped structural retrieval, not as a replacement for decision
memory. Do not inflate small changes or treat preparation as authorization for
unrelated actions.
