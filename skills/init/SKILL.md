---
name: init
description: Initialize Trufagent v1 in the current project. Use for /trufagent:init or when adopting Trufagent in a repository.
argument-hint: "[project-id]"
---

# Initialize Trufagent v1

Choose a stable project id from the repository name unless the user supplied
one. Confirm it with the user if the choice is ambiguous, then run:

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" trufagent init . --project <project-id>
```

Report the created `.trufagent/config.yaml`. Initialization creates the governed
memory vault and links the personal skill catalog. It does not generate
`CLAUDE.md`, start a dashboard, rewrite product documentation, or scan secrets.

If configuration already exists, inspect it and do not overwrite a mismatch.
