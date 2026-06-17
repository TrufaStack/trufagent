---
description: Use this skill to open the trufagent configuration dashboard in the browser. Invoke with /trufagent:dashboard or when the user says "open dashboard", "open trufagent UI", "configure trufagent visually", or "show fleet status".
---

# trufagent:dashboard

Opens the local trufagent configuration UI in the browser. Launches a FastAPI server if not already running, then opens http://localhost:7433.

## Execution

### Step 1 — Check if already running

```bash
PID_FILE="$HOME/.trufagent/ui.pid"
if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "Server already running (PID $PID)"
    xdg-open http://localhost:7433 2>/dev/null || open http://localhost:7433 2>/dev/null
    exit 0
  fi
fi
```

### Step 2 — Check dependencies

```bash
python3 -c "import fastapi, uvicorn, yaml, httpx, dotenv" 2>/dev/null || {
  echo "Installing trufagent UI dependencies…"
  pip install -r "$(dirname "$0")/../ui/requirements.txt" -q
}
```

If pip install fails, inform the user:
> "Run `pip install fastapi uvicorn pyyaml httpx python-dotenv` and try again."

### Step 3 — Launch server

```bash
UI_DIR="$(find ~/.claude -name 'server.py' -path '*/trufagent/ui/*' 2>/dev/null | head -1 | xargs dirname)"
if [ -z "$UI_DIR" ]; then
  echo "Could not find trufagent UI. Re-install the plugin: claude plugins install github:TrufaStack/trufagent"
  exit 1
fi
python3 "$UI_DIR/server.py" &
```

### Step 4 — Wait for server to respond

```bash
for i in $(seq 1 15); do
  sleep 0.3
  curl -sf http://localhost:7433 > /dev/null 2>&1 && break
done
```

### Step 5 — Open browser

```bash
xdg-open http://localhost:7433 2>/dev/null || \
open http://localhost:7433 2>/dev/null || \
echo "Open http://localhost:7433 in your browser"
```

### Step 6 — Confirm to user

```
Dashboard open at http://localhost:7433

  fleet    → configure agents, models, API keys
  status   → real-time health check for all agents
  litellm  → start/stop the LiteLLM proxy
  projects → initialize and manage project context

The server runs in the background. To stop it:
  kill $(cat ~/.trufagent/ui.pid)
```
