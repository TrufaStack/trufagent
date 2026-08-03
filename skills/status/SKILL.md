---
name: status
description: Show Trufagent v1 session, memory, skill-catalog, and Graphify status. Use for /trufagent:status.
---

# Trufagent status

Run these read-only checks from the project root:

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" trufagent session status .
uv run --project "${CLAUDE_PLUGIN_ROOT}" trufagent memory list .
uv run --project "${CLAUDE_PLUGIN_ROOT}" trufagent cartography status .
uv run --project "${CLAUDE_PLUGIN_ROOT}" trufagent skills list
```

The memory command requires the project id in the current CLI; read it from
`.trufagent/config.yaml` and pass `--project <id>`. Summarize:

- active or idle session and next handoff;
- accepted versus proposed memories;
- Graphify availability and freshness;
- reviewed active skills and unresolved conflicts.

All checks are read-only. Do not launch services or modify configuration.
