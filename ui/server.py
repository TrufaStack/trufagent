"""
trufagent UI — FastAPI backend
Manages litellm-config.yaml, API keys, LiteLLM subprocess, and project context.
Binds to 127.0.0.1 only.
"""
import asyncio
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import AsyncGenerator, Optional

import httpx
import yaml
from dotenv import dotenv_values, set_key
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Paths ─────────────────────────────────────────────────────────────────────
HOME = Path.home()
LITELLM_CONFIG = HOME / "litellm-config.yaml"
ENV_FILE = HOME / ".trufagent" / ".env"
PID_FILE = HOME / ".trufagent" / "ui.pid"
PROJECTS_INDEX = HOME / ".trufagent" / "projects.json"

ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
if not ENV_FILE.exists():
    ENV_FILE.touch()

# ── State ──────────────────────────────────────────────────────────────────────
_litellm_process: Optional[subprocess.Popen] = None

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="trufagent UI", docs_url=None, redoc_url=None)

# ── Helpers ───────────────────────────────────────────────────────────────────

def read_config() -> dict:
    if not LITELLM_CONFIG.exists():
        return {"model_list": [], "litellm_settings": {"drop_params": True, "request_timeout": 60}, "general_settings": {"master_key": "sk-litellm-local", "port": 4000}}
    with open(LITELLM_CONFIG) as f:
        return yaml.safe_load(f) or {}


def write_config(config: dict) -> None:
    with open(LITELLM_CONFIG, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def get_agents(config: dict) -> list[dict]:
    orchestrator_names = {"claude-sonnet-4-6", "claude-haiku-4-5", "claude-opus-4-8"}
    agents = []
    for entry in config.get("model_list", []):
        name = entry.get("model_name", "")
        if name in orchestrator_names:
            continue
        params = entry.get("litellm_params", {})
        model = params.get("model", "")
        api_key_ref = params.get("api_key", "")
        key_name = api_key_ref.replace("os.environ/", "") if api_key_ref.startswith("os.environ/") else ""
        agents.append({"name": name, "model": model, "key_name": key_name})
    return agents


def upsert_agent(config: dict, agent_name: str, model: str, key_name: str) -> dict:
    model_list = config.get("model_list", [])
    for entry in model_list:
        if entry.get("model_name") == agent_name:
            entry["litellm_params"]["model"] = model
            entry["litellm_params"]["api_key"] = f"os.environ/{key_name}" if key_name else ""
            return config
    model_list.append({
        "model_name": agent_name,
        "litellm_params": {
            "model": model,
            "api_key": f"os.environ/{key_name}" if key_name else ""
        }
    })
    config["model_list"] = model_list
    return config


def read_keys() -> dict:
    return dotenv_values(ENV_FILE)


def key_is_set(key_name: str) -> bool:
    keys = read_keys()
    return bool(keys.get(key_name, "").strip())


def litellm_port() -> int:
    config = read_config()
    return config.get("general_settings", {}).get("port", 4000)


def litellm_is_running() -> bool:
    global _litellm_process
    if _litellm_process and _litellm_process.poll() is None:
        return True
    port = litellm_port()
    try:
        import socket
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


async def ping_agent(agent_name: str, model: str) -> dict:
    if not litellm_is_running():
        return {"name": agent_name, "model": model, "status": "litellm_offline", "latency_ms": None}
    port = litellm_port()
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    payload = {
        "model": agent_name,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1
    }
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload, headers={"Authorization": "Bearer sk-litellm-local"})
        latency = round((time.monotonic() - start) * 1000)
        if resp.status_code in (200, 201):
            return {"name": agent_name, "model": model, "status": "reachable", "latency_ms": latency}
        detail = resp.json().get("error", {}).get("message", resp.text)[:120]
        return {"name": agent_name, "model": model, "status": "error", "latency_ms": latency, "error": detail}
    except httpx.TimeoutException:
        return {"name": agent_name, "model": model, "status": "timeout", "latency_ms": None}
    except Exception as e:
        return {"name": agent_name, "model": model, "status": "unreachable", "latency_ms": None, "error": str(e)[:80]}

# ── Models ────────────────────────────────────────────────────────────────────

class AgentUpdate(BaseModel):
    model: str
    key_name: str

class AgentTest(BaseModel):
    model: str
    key_name: str
    key_value: Optional[str] = None

class KeySet(BaseModel):
    value: str

class ProjectInit(BaseModel):
    path: str

class LiteLLMStart(BaseModel):
    config_path: Optional[str] = None

# ── Fleet endpoints ───────────────────────────────────────────────────────────

@app.get("/api/fleet")
async def get_fleet():
    config = read_config()
    agents = get_agents(config)
    keys = read_keys()
    for agent in agents:
        agent["key_configured"] = bool(keys.get(agent["key_name"], "").strip()) if agent["key_name"] else False
    return {"agents": agents}


@app.get("/api/fleet/{agent_name}")
async def get_agent(agent_name: str):
    config = read_config()
    agents = get_agents(config)
    for a in agents:
        if a["name"] == agent_name:
            a["key_configured"] = key_is_set(a["key_name"]) if a["key_name"] else False
            return a
    raise HTTPException(404, f"Agent '{agent_name}' not found")


@app.patch("/api/fleet/{agent_name}")
async def update_agent(agent_name: str, body: AgentUpdate):
    if not re.match(r"^[a-zA-Z0-9_/.:+-]+$", body.model):
        raise HTTPException(422, "Invalid model string format")
    if body.key_name and not re.match(r"^[A-Z][A-Z0-9_]*$", body.key_name):
        raise HTTPException(422, "Key name must be UPPERCASE_SNAKE_CASE")
    config = read_config()
    config = upsert_agent(config, agent_name, body.model, body.key_name)
    write_config(config)
    return {"ok": True}


@app.post("/api/fleet/{agent_name}/test")
async def test_agent(agent_name: str, body: AgentTest):
    if body.key_value and body.key_name:
        set_key(str(ENV_FILE), body.key_name, body.key_value)
        os.environ[body.key_name] = body.key_value
    result = await ping_agent(agent_name, body.model)
    return result


@app.get("/api/config")
async def get_raw_config():
    if not LITELLM_CONFIG.exists():
        return {"yaml": "", "path": str(LITELLM_CONFIG)}
    content = LITELLM_CONFIG.read_text()
    return {"yaml": content, "path": str(LITELLM_CONFIG)}

# ── Keys endpoints ────────────────────────────────────────────────────────────

@app.get("/api/keys/{key_name}")
async def check_key(key_name: str):
    return {"name": key_name, "configured": key_is_set(key_name)}


@app.put("/api/keys/{key_name}")
async def set_key_value(key_name: str, body: KeySet):
    if not re.match(r"^[A-Z][A-Z0-9_]*$", key_name):
        raise HTTPException(422, "Key name must be UPPERCASE_SNAKE_CASE")
    set_key(str(ENV_FILE), key_name, body.value)
    os.environ[key_name] = body.value
    return {"ok": True}

# ── Status endpoint ───────────────────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    config = read_config()
    agents = get_agents(config)
    running = litellm_is_running()
    port = litellm_port()
    results = await asyncio.gather(*[ping_agent(a["name"], a["model"]) for a in agents])
    keys = read_keys()
    key_names = {a["key_name"] for a in agents if a["key_name"]}
    key_status = {k: bool(keys.get(k, "").strip()) for k in key_names}
    return {
        "litellm": {"running": running, "port": port},
        "agents": list(results),
        "keys": key_status
    }

# ── LiteLLM endpoints ─────────────────────────────────────────────────────────

@app.post("/api/litellm/start")
async def start_litellm(body: LiteLLMStart):
    global _litellm_process
    if litellm_is_running():
        return {"ok": True, "message": "Already running"}
    config_path = body.config_path or str(LITELLM_CONFIG)
    env = {**os.environ, **read_keys()}
    try:
        _litellm_process = subprocess.Popen(
            ["litellm", "--config", config_path],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        for _ in range(15):
            await asyncio.sleep(0.5)
            if litellm_is_running():
                return {"ok": True, "pid": _litellm_process.pid}
        return {"ok": False, "message": "LiteLLM started but not responding after 7.5s"}
    except FileNotFoundError:
        raise HTTPException(500, "litellm command not found — run: pip install litellm[proxy]")


@app.post("/api/litellm/stop")
async def stop_litellm():
    global _litellm_process
    if _litellm_process and _litellm_process.poll() is None:
        _litellm_process.send_signal(signal.SIGTERM)
        try:
            _litellm_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _litellm_process.kill()
        _litellm_process = None
        return {"ok": True}
    return {"ok": False, "message": "No managed process found"}

# ── Projects endpoints ────────────────────────────────────────────────────────

@app.get("/api/projects")
async def list_projects():
    if not PROJECTS_INDEX.exists():
        return {"projects": []}
    data = json.loads(PROJECTS_INDEX.read_text())
    enriched = []
    for p in data.get("projects", []):
        path = Path(p["path"])
        state_file = path / "docs" / "context" / "state.md"
        pending_file = path / "docs" / "context" / "pending-updates.md"
        p["state_exists"] = state_file.exists()
        p["pending_commits"] = pending_file.read_text().count("## [") if pending_file.exists() else 0
        enriched.append(p)
    return {"projects": enriched}


@app.post("/api/projects/init")
async def init_project(body: ProjectInit):
    path = Path(body.path).expanduser().resolve()
    if not path.exists():
        raise HTTPException(404, f"Path not found: {path}")
    context_dir = path / "docs" / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    (context_dir / "pending-updates.md").touch(exist_ok=True)
    for subdir in ["technical", "lessons", "preferences", "goals"]:
        (context_dir / "decisions" / subdir).mkdir(parents=True, exist_ok=True)
    index = json.loads(PROJECTS_INDEX.read_text()) if PROJECTS_INDEX.exists() else {"projects": []}
    existing_paths = [p["path"] for p in index["projects"]]
    if str(path) not in existing_paths:
        index["projects"].append({"path": str(path), "name": path.name, "added": time.strftime("%Y-%m-%d")})
        PROJECTS_INDEX.write_text(json.dumps(index, indent=2))
    return {"ok": True, "path": str(path)}

# ── SSE stream ────────────────────────────────────────────────────────────────

async def status_stream() -> AsyncGenerator[str, None]:
    while True:
        config = read_config()
        agents = get_agents(config)
        running = litellm_is_running()
        port = litellm_port()
        results = await asyncio.gather(*[ping_agent(a["name"], a["model"]) for a in agents])
        payload = json.dumps({
            "litellm": {"running": running, "port": port},
            "agents": list(results),
            "ts": int(time.time())
        })
        yield f"data: {payload}\n\n"
        await asyncio.sleep(10)


@app.get("/events")
async def sse_events(request: Request):
    async def generator():
        async for chunk in status_stream():
            if await request.is_disconnected():
                break
            yield chunk
    return StreamingResponse(generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ── Static files + SPA fallback ───────────────────────────────────────────────

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    try:
        uvicorn.run(app, host="127.0.0.1", port=7433, log_level="warning")
    finally:
        PID_FILE.unlink(missing_ok=True)
