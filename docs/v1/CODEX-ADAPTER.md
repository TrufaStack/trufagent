# Codex adapter

## Purpose

The Codex adapter exposes Trufagent v1 as three native skills while keeping
classification, effort sizing, memory, Graphify retrieval, skill selection, and
session state inside the shared runtime.

| Codex skill | Runtime operation | Safety boundary |
| --- | --- | --- |
| `$trufagent` | `plan prepare` | Pauses on unresolved intake questions |
| `$start-session` | `session start` | Reads only the compact prior handoff |
| `$end-session` | `session end` | Never commits; proposals need human review |

The source skills live in `adapters/codex/skills/`. Their
`agents/openai.yaml` files provide UI labels and starter prompts without adding
workflow text to the always-loaded skill metadata.

## Installation

For personal use, copy each source directory into `~/.codex/skills/`. The
editable `trufagent` uv tool remains the single executable dependency.

The task and close adapters write structured inputs to temporary JSON files.
They do not interpolate user text, environment values, or secrets into shell
commands and do not assume a particular shell.

## Relationship to Claude Code

Claude Code and Codex use different discovery metadata, but both adapters call
the same CLI. Behavior changes belong in the runtime and its tests, not in
parallel prompt implementations.
