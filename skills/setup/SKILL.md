---
description: Use this skill to set up the trufagent framework globally on this machine — installs LiteLLM, copies agent files, configures hooks, and opens the dashboard for fleet configuration. Run once per machine. Invoke with /trufagent:setup or when the user says "setup trufagent", "configure trufagent", or "install trufagent fleet".
---

# trufagent:setup

Sets up the trufagent framework on this machine. Safe to re-run to reconfigure.

## What this skill does

1. Installs LiteLLM proxy (with visible progress)
2. Installs dashboard dependencies (with visible progress)
3. Writes `~/litellm-config.yaml` base template
4. Writes `~/.claude/CLAUDE.md` with fleet rules
5. Copies agent files to `~/.claude/agents/`
6. Configures PostToolUse and PreCompact hooks in `~/.claude/settings.json`
7. Opens the dashboard for fleet and API key configuration

API keys and model choices are configured in the dashboard — not here.

## Step 1 — Install LiteLLM proxy

```bash
pip show litellm 2>/dev/null | head -1
```

If not installed or version is outdated, install it with visible output:

```bash
echo "Installing LiteLLM proxy — this may take a few minutes…"
pip install "litellm[proxy]"
echo "LiteLLM installed."
```

Do NOT use `-q`. The user needs to see progress since this can take 2–5 minutes.

## Step 2 — Install dashboard dependencies

```bash
python3 -c "import fastapi, uvicorn, yaml, httpx, dotenv" 2>/dev/null
```

If any import fails:

```bash
echo "Installing dashboard dependencies…"
pip install fastapi uvicorn pyyaml httpx python-dotenv
echo "Dashboard dependencies installed."
```

Do NOT use `-q`.

## Step 3 — Write ~/litellm-config.yaml

Read `templates/litellm-config.yaml` from the plugin directory and write it to `~/litellm-config.yaml`.

If the file already exists, ask: "A litellm-config.yaml already exists. Overwrite it? [y/N]". Only overwrite if the user confirms.

## Step 4 — Write ~/.claude/CLAUDE.md

Read `templates/global-claude.md` and write to `~/.claude/CLAUDE.md`.
If a CLAUDE.md already exists with other content, append the trufagent section below it.

## Step 5 — Copy agent files to ~/.claude/agents/

```bash
mkdir -p ~/.claude/agents
```

Copy all `.md` files from the plugin's `agents/` directory to `~/.claude/agents/`.

## Step 6 — Configure hooks in ~/.claude/settings.json

Read current `~/.claude/settings.json`, add or merge:

```json
"hooks": {
  "PostToolUse": [
    {
      "matcher": "Bash",
      "hooks": [{"type": "command", "command": "echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; d=json.load(sys.stdin); exit(0 if 'git commit' in d.get('command','') else 1)\" 2>/dev/null && PENDING=\"$PWD/docs/context/pending-updates.md\" && [ -f \"$PENDING\" ] && printf '## [%s] commit: %s\\nMessage: %s\\nFiles: %s\\n---\\n' \"$(date '+%Y-%m-%d %H:%M')\" \"$(git log -1 --format='%h' 2>/dev/null)\" \"$(git log -1 --format='%s' 2>/dev/null)\" \"$(git diff-tree --no-commit-id -r --name-only HEAD 2>/dev/null | head -10 | tr '\\n' ',')\" >> \"$PENDING\" || true"}]
    },
    {
      "matcher": "Edit|Write",
      "hooks": [{"type": "command", "command": "FILE=$(echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; d=json.load(sys.stdin); print(d.get('file_path',''))\" 2>/dev/null); if [[ \"$FILE\" == *.ts || \"$FILE\" == *.tsx ]]; then PROJ=\"$PWD\"; while [ \"$PROJ\" != \"/\" ] && [ ! -f \"$PROJ/package.json\" ]; do PROJ=$(dirname \"$PROJ\"); done; [ -f \"$PROJ/package.json\" ] && cd \"$PROJ\" && timeout 30 npx tsc --noEmit 2>&1 | grep 'error TS' | head -5; fi || true"}]
    }
  ],
  "PreCompact": [
    {
      "hooks": [{"type": "command", "command": "PENDING=\"$PWD/docs/context/pending-updates.md\"; [ -f \"$PENDING\" ] && printf '## [COMPACTION %s] — context saved before compaction\\n---\\n' \"$(date '+%Y-%m-%d %H:%M')\" >> \"$PENDING\" || true"}]
    }
  ]
}
```

## Step 7 — Open dashboard

Tell the user:

```
trufagent installed. Opening dashboard to configure your fleet and API keys…
```

Then execute all steps from the dashboard skill inline:

1. Check if server is already running (read `~/.trufagent/ui.pid`, test with `kill -0`)
2. If not running, find the `server.py` path:
   ```bash
   UI_DIR="$(find ~/.claude -name 'server.py' -path '*/trufagent/ui/*' 2>/dev/null | head -1 | xargs dirname)"
   ```
3. Launch the server in the background:
   ```bash
   python3 "$UI_DIR/server.py" &
   ```
4. Wait for it to respond (poll up to 15 × 0.3s):
   ```bash
   for i in $(seq 1 15); do sleep 0.3; curl -sf http://localhost:7433 > /dev/null 2>&1 && break; done
   ```
5. Open the browser:
   ```bash
   xdg-open http://localhost:7433 2>/dev/null || open http://localhost:7433 2>/dev/null || echo "Open http://localhost:7433 in your browser"
   ```

Final message:

```
Dashboard open at http://localhost:7433

  fleet    → configure agents and API keys
  status   → real-time health check for all agents
  litellm  → start/stop the LiteLLM proxy
  projects → initialize and manage project context

Next: cd into your project and run /trufagent:init
```
