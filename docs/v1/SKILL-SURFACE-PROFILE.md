# Trufagent skill surface profile

## STACK

- Python 3.12 package managed with uv.
- Pydantic and YAML domain/configuration models.
- Pytest and Ruff verification.
- Graphify 0.9.30 structural cartography.
- Claude Code and Codex runtime adapters.

Repository evidence: 52 Python files, 54 Markdown files, `pyproject.toml`,
`uv.lock`, pytest configuration, and no active frontend application in v1.

## DAILY

Codex user surface:

- `trufagent` — required entry point for task sizing.
- `start-session` — required continuity entry point.
- `end-session` — required continuity entry point.
- `ui-ux-pro-max` — explicitly reviewed personal skill.

OpenAI system skills remain managed by Codex and are outside this profile.

## LIBRARY

349 installed Codex skills are retained but disabled from initial discovery.
They are not deleted. Most are unreviewed, off-stack, or useful only for a
specific task.

When the Trufagent runtime selects a reviewed skill, the Codex adapter reads the
selected location on demand. This preserves progressive disclosure without
making every library entry DAILY.

Claude currently exposes ten user skills plus plugin skills. It needs a
separate profile mechanism because its loading and authentication controls
differ from Codex.

## INSTALL PLAN

The command below plans the surface without changing configuration:

```text
trufagent skills profile --platform codex
```

Add `--apply` to atomically replace the managed block in
`~/.codex/config.toml`. The block uses documented `[[skills.config]]` entries
with `enabled = false`; user configuration outside the markers is preserved.

Source directories remain in place and the personal Trufagent catalog remains
the inventory and review authority.

## VERIFICATION

- Planned counts: 4 DAILY, 349 LIBRARY.
- Managed configuration loads under `codex --strict-config`.
- Reapplying the block is idempotent in tests.
- C01 passed before and after profile application.
- Codex input tokens fell from 110,654 to 89,396 on the matched C01 canary.
- The damaged Codex state database discovered during testing was moved to
  recoverable `.corrupt-20260730` files and regenerated successfully.

Codex must be restarted after profile changes, as required by its skill
configuration contract.
