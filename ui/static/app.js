/* trufagent UI — app.js */

// ── Agent metadata ─────────────────────────────────────────────────────────
const AGENT_META = {
  scout:    { icon: 'fa-magnifying-glass', color: '#60a5fa', role: 'explore',   desc: 'File exploration, grep, parsing. Use before implementing to understand current state.' },
  runner:   { icon: 'fa-bolt',             color: '#4ade80', role: 'speed',     desc: 'Fast parallel tasks, data extraction, repetitive checks across multiple files.' },
  thinker:  { icon: 'fa-brain',            color: '#2dd4bf', role: 'reason',    desc: 'Root-cause debugging, algorithm design, architecture decisions. Use before builder.' },
  builder:  { icon: 'fa-hammer',           color: '#fbbf24', role: 'implement', desc: 'Full-stack implementation: components, APIs, CRUD, features. Code that runs without modifications.' },
  reviewer: { icon: 'fa-code-branch',      color: '#a78bfa', role: 'review',    desc: 'First-pass code review: logic, bugs, TypeScript types, conventions. Use after builder.' },
  writer:   { icon: 'fa-pen-nib',          color: '#f472b6', role: 'write',     desc: 'Non-critical text: commit messages, changelogs. Claude handles important documentation.' },
  critic:   { icon: 'fa-shield-halved',    color: '#f87171', role: 'critique',  desc: 'Deep architectural review: security, irreversibility, coupling. High-stakes changes only.' },
};

// ── Provider catalog ───────────────────────────────────────────────────────
const PROVIDER_CATALOG = [
  {
    provider: 'Google',
    keyUrl: 'https://aistudio.google.com/apikey',
    models: [
      { name: 'Gemini 2.0 Flash', model: 'gemini/gemini-2.0-flash',  cost: '$0.04/M', keyName: 'GEMINI_API_KEY',    rec: ['scout'] },
      { name: 'Gemini 2.5 Pro',   model: 'gemini/gemini-2.5-pro',    cost: '$1.25/M', keyName: 'GEMINI_API_KEY',    rec: [] },
    ],
  },
  {
    provider: 'Groq',
    keyUrl: 'https://console.groq.com/keys',
    models: [
      { name: 'Llama 3.3 70B', model: 'groq/llama-3.3-70b-versatile', cost: '$0.05/M', keyName: 'GROQ_API_KEY', rec: ['runner'] },
      { name: 'Llama 3.1 8B',  model: 'groq/llama-3.1-8b-instant',    cost: 'free',    keyName: 'GROQ_API_KEY', rec: [] },
    ],
  },
  {
    provider: 'DeepSeek',
    keyUrl: 'https://platform.deepseek.com/api_keys',
    models: [
      { name: 'DeepSeek V4 Flash', model: 'deepseek/deepseek-v4-flash', cost: '$0.14/M', keyName: 'DEEPSEEK_API_KEY', rec: ['thinker'] },
      { name: 'DeepSeek V4 Pro',   model: 'deepseek/deepseek-v4-pro',   cost: '$1.68/M', keyName: 'DEEPSEEK_API_KEY', rec: [] },
    ],
  },
  {
    provider: 'OpenRouter',
    keyUrl: 'https://openrouter.ai/keys',
    models: [
      { name: 'Qwen 2.5 Coder 32B', model: 'openrouter/qwen/qwen-2.5-coder-32b-instruct',   cost: '$0.50/M', keyName: 'OPENROUTER_API_KEY', rec: ['builder'] },
      { name: 'Qwen3 Coder',         model: 'openrouter/qwen/qwen3-coder',                    cost: '$0.30/M', keyName: 'OPENROUTER_API_KEY', rec: [] },
      { name: 'Mistral 7B Free',     model: 'openrouter/mistralai/mistral-7b-instruct:free', cost: 'free',    keyName: 'OPENROUTER_API_KEY', rec: ['writer'] },
    ],
  },
  {
    provider: 'Anthropic',
    keyUrl: 'https://console.anthropic.com/settings/api-keys',
    models: [
      { name: 'Claude Sonnet 4.6', model: 'anthropic/claude-sonnet-4-6', cost: '$3.00/M',  keyName: 'ANTHROPIC_API_KEY', rec: ['reviewer', 'critic'] },
      { name: 'Claude Haiku 4.5',  model: 'anthropic/claude-haiku-4-5',  cost: '$0.25/M',  keyName: 'ANTHROPIC_API_KEY', rec: [] },
      { name: 'Claude Opus 4.8',   model: 'anthropic/claude-opus-4-8',   cost: '$15.00/M', keyName: 'ANTHROPIC_API_KEY', rec: [] },
    ],
  },
  {
    provider: 'OpenAI',
    keyUrl: 'https://platform.openai.com/api-keys',
    models: [
      { name: 'GPT-4o',      model: 'openai/gpt-4o',      cost: '$2.50/M', keyName: 'OPENAI_API_KEY', rec: [] },
      { name: 'GPT-4o Mini', model: 'openai/gpt-4o-mini', cost: '$0.15/M', keyName: 'OPENAI_API_KEY', rec: [] },
    ],
  },
  {
    provider: 'Mistral',
    keyUrl: 'https://console.mistral.ai/api-keys',
    models: [
      { name: 'Codestral', model: 'mistral/codestral-latest', cost: '$0.30/M', keyName: 'MISTRAL_API_KEY', rec: [] },
    ],
  },
];

// ── Key name auto-suggest from model string ────────────────────────────────
function suggestKeyName(model) {
  const map = {
    'gemini': 'GEMINI_API_KEY', 'google': 'GEMINI_API_KEY',
    'groq': 'GROQ_API_KEY',
    'deepseek': 'DEEPSEEK_API_KEY',
    'openrouter': 'OPENROUTER_API_KEY',
    'anthropic': 'ANTHROPIC_API_KEY', 'claude': 'ANTHROPIC_API_KEY',
    'openai': 'OPENAI_API_KEY', 'gpt': 'OPENAI_API_KEY',
    'mistral': 'MISTRAL_API_KEY', 'codestral': 'MISTRAL_API_KEY',
  };
  const lower = model.toLowerCase();
  for (const [prefix, key] of Object.entries(map)) {
    if (lower.startsWith(prefix) || lower.includes('/' + prefix)) return key;
  }
  const provider = model.split('/')[0].toUpperCase().replace(/[^A-Z0-9]/g, '_');
  return provider ? `${provider}_API_KEY` : '';
}

// ── Validation ─────────────────────────────────────────────────────────────
function validateModelString(v) {
  if (!v) return { ok: false, msg: 'Required' };
  if (!/^[a-zA-Z0-9_/.:+-]+$/.test(v)) return { ok: false, msg: 'Invalid characters in model string' };
  return { ok: true, msg: 'Valid format' };
}
function validateKeyName(v) {
  if (!v) return { ok: false, msg: 'Required' };
  if (!/^[A-Z][A-Z0-9_]*$/.test(v)) return { ok: false, msg: 'Must be UPPERCASE_SNAKE_CASE' };
  return { ok: true, msg: 'Valid env var name' };
}

// ── Navigation ─────────────────────────────────────────────────────────────
let currentSection = 'fleet';

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    const sec = item.dataset.section;
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    item.classList.add('active');
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(`section-${sec}`).classList.add('active');
    currentSection = sec;
    if (sec === 'status') loadStatus();
    if (sec === 'litellm') loadLiteLLM();
    if (sec === 'projects') loadProjects();
  });
});

// ── Config accordion ────────────────────────────────────────────────────────
document.getElementById('config-toggle').addEventListener('click', async () => {
  const toggle = document.getElementById('config-toggle');
  const body = document.getElementById('config-body');
  toggle.classList.toggle('open');
  body.classList.toggle('open');
  if (body.classList.contains('open')) {
    const res = await fetch('/api/config');
    const data = await res.json();
    document.getElementById('config-textarea').value = data.yaml || '';
  }
});

function copyConfig() {
  const ta = document.getElementById('config-textarea');
  navigator.clipboard.writeText(ta.value);
}

// ── Fleet section ──────────────────────────────────────────────────────────
let fleetAgents = [];
let activeAgent = null;
let testedAgents = new Set();

function agentsForKey(keyName) {
  if (!keyName) return [];
  return fleetAgents.filter(a => a.key_name === keyName).map(a => a.name);
}

async function loadFleet() {
  const res = await fetch('/api/fleet');
  const data = await res.json();
  fleetAgents = data.agents || [];
  document.getElementById('fleet-badge').textContent = `${fleetAgents.length} agents`;
  renderAgentTabs();
  if (fleetAgents.length > 0) selectAgent(fleetAgents[0].name);
}

function renderAgentTabs() {
  const bar = document.getElementById('agent-tabs');
  bar.innerHTML = '';
  fleetAgents.forEach(agent => {
    const meta = AGENT_META[agent.name] || { icon: 'fa-robot', color: 'var(--primary)' };
    const tab = document.createElement('div');
    tab.className = 'agent-tab';
    tab.dataset.agent = agent.name;
    tab.innerHTML = `<i class="fa-solid ${meta.icon}" style="color:${meta.color}"></i>${agent.name}`;
    tab.addEventListener('click', () => selectAgent(agent.name));
    bar.appendChild(tab);
  });
}

function selectAgent(name) {
  activeAgent = name;
  document.querySelectorAll('.agent-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.agent === name);
  });
  const agent = fleetAgents.find(a => a.name === name) || { name, model: '', key_name: '', key_configured: false };
  renderAgentDetail(agent);
}

function renderAgentDetail(agent) {
  const meta = AGENT_META[agent.name] || { icon: 'fa-robot', color: 'var(--primary)', role: '—', desc: '' };
  const container = document.getElementById('agent-details');
  container.innerHTML = `
    <div class="agent-detail active" id="detail-${agent.name}">
      <div class="detail-grid">
        <div class="info-card">
          <div class="info-card-label">role</div>
          <div class="info-card-value">${meta.role}</div>
          <div class="info-card-sub">${meta.desc.substring(0, 60)}…</div>
        </div>
        <div class="info-card">
          <div class="info-card-label">current model</div>
          <div class="info-card-value" style="color:var(--primary);font-size:10px;word-break:break-all">${agent.model || '—'}</div>
          <div class="info-card-sub">${agent.key_configured ? '<span style="color:var(--accent)">key configured ✓</span>' : '<span style="color:var(--warn)">key not set</span>'}</div>
        </div>
      </div>

      <div class="field">
        <label class="field-label">Model string</label>
        <div class="model-field-row">
          <input class="field-input" id="inp-model-${agent.name}" type="text"
            value="${agent.model || ''}"
            placeholder="provider/model-name (e.g. deepseek/deepseek-v4-flash)">
          <button class="btn-choose-model" onclick="openModelPicker('${agent.name}')">
            <i class="fa-solid fa-grid-2" style="font-size:9px"></i>Choose
          </button>
        </div>
        <div class="field-hint info" id="hint-model-${agent.name}"><i class="fa-solid fa-circle-info"></i>Any valid LiteLLM model string</div>
      </div>

      <div class="field">
        <label class="field-label">API key name <span style="font-weight:400;color:var(--muted)">(env var)</span></label>
        <input class="field-input" id="inp-keyname-${agent.name}" type="text"
          value="${agent.key_name || ''}"
          placeholder="PROVIDER_API_KEY">
        <div class="field-hint info" id="hint-keyname-${agent.name}"><i class="fa-solid fa-circle-info"></i>Must be UPPERCASE_SNAKE_CASE</div>
      </div>

      <div class="field">
        <label class="field-label">API key value
          ${(() => { const shared = agentsForKey(agent.key_name).filter(n => n !== agent.name); return shared.length ? `<span style="font-weight:400;color:var(--primary);margin-left:6px"><i class="fa-solid fa-link" style="font-size:9px"></i> shared with ${shared.join(', ')}</span>` : ''; })()}
        </label>
        <div class="field-row">
          <input class="field-input" id="inp-keyval-${agent.name}" type="password"
            placeholder="${agent.key_configured ? '••••••••••••••••••••' : 'Enter key value'}"
            oninput="syncSharedKey('${agent.name}', '${agent.key_name}', this.value)">
          <button class="btn btn-ghost" style="flex-shrink:0" onclick="toggleKeyVisibility('${agent.name}')">
            <i class="fa-solid fa-eye" id="eye-${agent.name}"></i>
          </button>
        </div>
        ${agent.key_configured ? '<div class="field-hint ok"><i class="fa-solid fa-check"></i>Key is configured — leave blank to keep current</div>' : ''}
      </div>

      <div class="btn-row">
        <button class="btn btn-primary" onclick="testAgent('${agent.name}')">
          <i class="fa-solid fa-plug"></i>Test Connection
        </button>
        <button class="btn btn-success" id="btn-save-${agent.name}" disabled onclick="saveAgent('${agent.name}')">
          <i class="fa-solid fa-floppy-disk"></i>Save changes
        </button>
      </div>

      <div class="test-result" id="test-result-${agent.name}">
        <i class="fa-solid fa-circle-dot"></i>
        <span id="test-result-text-${agent.name}"></span>
      </div>
    </div>
  `;

  // wire validation
  const modelInp = document.getElementById(`inp-model-${agent.name}`);
  const keyInp = document.getElementById(`inp-keyname-${agent.name}`);

  modelInp.addEventListener('input', () => {
    validateField(agent.name);
    const suggested = suggestKeyName(modelInp.value);
    if (suggested && !keyInp.value) keyInp.value = suggested;
    lockSave(agent.name);
  });
  keyInp.addEventListener('input', () => { validateField(agent.name); lockSave(agent.name); });
  document.getElementById(`inp-keyval-${agent.name}`).addEventListener('input', () => lockSave(agent.name));
}

function syncSharedKey(agentName, keyName, value) {
  if (!keyName) return;
  fleetAgents.filter(a => a.key_name === keyName && a.name !== agentName).forEach(a => {
    const inp = document.getElementById(`inp-keyval-${a.name}`);
    if (inp) inp.value = value;
  });
}

function validateField(agentName) {
  const modelInp = document.getElementById(`inp-model-${agentName}`);
  const keyInp = document.getElementById(`inp-keyname-${agentName}`);
  const modelHint = document.getElementById(`hint-model-${agentName}`);
  const keyHint = document.getElementById(`hint-keyname-${agentName}`);

  const mv = validateModelString(modelInp.value);
  modelInp.className = `field-input ${mv.ok ? 'valid' : 'error'}`;
  modelHint.className = `field-hint ${mv.ok ? 'ok' : 'err'}`;
  modelHint.innerHTML = `<i class="fa-solid ${mv.ok ? 'fa-check' : 'fa-xmark'}"></i>${mv.msg}`;

  const kv = validateKeyName(keyInp.value);
  keyInp.className = `field-input ${kv.ok ? 'valid' : 'error'}`;
  keyHint.className = `field-hint ${kv.ok ? 'ok' : 'err'}`;
  keyHint.innerHTML = `<i class="fa-solid ${kv.ok ? 'fa-check' : 'fa-xmark'}"></i>${kv.msg}`;

  return mv.ok && kv.ok;
}

function lockSave(agentName) {
  testedAgents.delete(agentName);
  const btn = document.getElementById(`btn-save-${agentName}`);
  if (btn) btn.disabled = true;
  const result = document.getElementById(`test-result-${agentName}`);
  if (result) result.classList.remove('visible');
}

function toggleKeyVisibility(agentName) {
  const inp = document.getElementById(`inp-keyval-${agentName}`);
  const eye = document.getElementById(`eye-${agentName}`);
  if (inp.type === 'password') {
    inp.type = 'text';
    eye.className = 'fa-solid fa-eye-slash';
  } else {
    inp.type = 'password';
    eye.className = 'fa-solid fa-eye';
  }
}

async function testAgent(agentName) {
  if (!validateField(agentName)) return;

  const model = document.getElementById(`inp-model-${agentName}`).value;
  const keyName = document.getElementById(`inp-keyname-${agentName}`).value;
  const keyVal = document.getElementById(`inp-keyval-${agentName}`).value;
  const resultEl = document.getElementById(`test-result-${agentName}`);
  const resultText = document.getElementById(`test-result-text-${agentName}`);
  const btn = document.querySelector(`[onclick="testAgent('${agentName}')"]`);

  btn.innerHTML = '<div class="spinner"></div>Testing…';
  btn.disabled = true;
  resultEl.classList.remove('visible', 'ok', 'err');

  const res = await fetch(`/api/fleet/${agentName}/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, key_name: keyName, key_value: keyVal || null })
  });
  const data = await res.json();

  btn.innerHTML = '<i class="fa-solid fa-plug"></i>Test Connection';
  btn.disabled = false;

  if (data.status === 'reachable') {
    resultEl.classList.add('visible', 'ok');
    resultText.textContent = `Connected · ${model} · ${data.latency_ms}ms TTFT`;
    testedAgents.add(agentName);
    document.getElementById(`btn-save-${agentName}`).disabled = false;
  } else {
    resultEl.classList.add('visible', 'err');
    resultText.textContent = data.error || data.status;
    testedAgents.delete(agentName);
    document.getElementById(`btn-save-${agentName}`).disabled = true;
  }
}

async function saveAgent(agentName) {
  if (!testedAgents.has(agentName)) return;
  const model = document.getElementById(`inp-model-${agentName}`).value;
  const keyName = document.getElementById(`inp-keyname-${agentName}`).value;
  const keyVal = document.getElementById(`inp-keyval-${agentName}`).value;

  const btn = document.getElementById(`btn-save-${agentName}`);
  btn.innerHTML = '<div class="spinner"></div>Saving…';
  btn.disabled = true;

  await fetch(`/api/fleet/${agentName}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, key_name: keyName })
  });

  if (keyVal && keyName) {
    await fetch(`/api/keys/${keyName}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: keyVal })
    });
    document.getElementById(`inp-keyval-${agentName}`).value = '';
  }

  btn.innerHTML = '<i class="fa-solid fa-check"></i>Saved';
  setTimeout(() => {
    btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i>Save changes';
    btn.disabled = true;
    testedAgents.delete(agentName);
    loadFleet();
  }, 1500);
}

// ── Status section ──────────────────────────────────────────────────────────
async function loadStatus() {
  const body = document.getElementById('status-body');
  body.innerHTML = '<div style="color:var(--ink-dim);font-family:var(--font-mono);font-size:11px">Pinging agents…</div>';
  const res = await fetch('/api/status');
  const data = await res.json();
  const { litellm, agents, keys } = data;

  const statusDot = litellm.running
    ? '<span class="status-dot on"></span>'
    : '<span class="status-dot off"></span>';
  const statusLabel = litellm.running
    ? `<span class="status-pill running">${statusDot} running :${litellm.port}</span>`
    : `<span class="status-pill stopped">${statusDot} stopped</span>`;

  const agentRows = agents.map(a => {
    const meta = AGENT_META[a.name] || { icon: 'fa-robot', color: 'var(--ink-dim)' };
    let statusBadge, latency;
    if (a.status === 'reachable') {
      statusBadge = `<span class="agent-status-badge"><span class="status-dot on"></span><span style="color:var(--accent)">reachable</span></span>`;
      latency = `<span style="color:${a.latency_ms > 1000 ? 'var(--warn)' : 'var(--ink-dim)'}">${a.latency_ms}ms</span>`;
    } else {
      statusBadge = `<span class="agent-status-badge"><span class="status-dot off"></span><span style="color:var(--danger)">${a.status}</span></span>`;
      latency = '—';
    }
    return `<tr>
      <td><i class="fa-solid ${meta.icon}" style="color:${meta.color};margin-right:7px"></i>${a.name}</td>
      <td style="color:var(--primary)">${a.model}</td>
      <td>${statusBadge}</td>
      <td>${latency}</td>
    </tr>`;
  }).join('');

  const keyRows = Object.entries(keys).map(([name, configured]) => `
    <div class="env-row">
      <span class="env-name">${name}</span>
      ${configured
        ? '<span class="env-ok"><i class="fa-solid fa-check"></i> configured</span>'
        : '<span class="env-miss"><i class="fa-solid fa-triangle-exclamation"></i> missing</span>'}
    </div>`).join('');

  body.innerHTML = `
    <div class="status-litellm-card">
      <div>
        <div style="font-family:var(--font-mono);font-size:9px;color:var(--ink-dim);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px">LiteLLM Proxy</div>
        ${statusLabel}
      </div>
      <div style="font-family:var(--font-mono);font-size:9px;color:var(--muted)">port :${litellm.port}</div>
    </div>

    <table class="agents-table">
      <thead><tr>
        <th>Agent</th><th>Model</th><th>Status</th><th>Latency</th>
      </tr></thead>
      <tbody>${agentRows}</tbody>
    </table>

    ${keyRows ? `<div style="margin-top:16px">
      <div style="font-family:var(--font-mono);font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink-dim);margin-bottom:8px">API Keys</div>
      <div class="litellm-card" style="padding:0 0 0 0">${keyRows}</div>
    </div>` : ''}
  `;
}

// ── LiteLLM section ─────────────────────────────────────────────────────────
async function loadLiteLLM() {
  const body = document.getElementById('litellm-body');
  const statusRes = await fetch('/api/status');
  const statusData = await statusRes.json();
  const { litellm, keys } = statusData;
  const running = litellm.running;

  const keyRows = Object.entries(keys).map(([name, configured]) => `
    <div class="env-row">
      <span class="env-name">${name}</span>
      ${configured
        ? '<span class="env-ok"><i class="fa-solid fa-check"></i></span>'
        : '<span class="env-miss"><i class="fa-solid fa-triangle-exclamation"></i> missing</span>'}
    </div>`).join('');

  body.innerHTML = `
    <div class="litellm-card">
      <div class="litellm-card-title">Proxy control</div>
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
        <span class="${running ? 'status-pill running' : 'status-pill stopped'}">
          <span class="status-dot ${running ? 'on' : 'off'}"></span>
          ${running ? `running :${litellm.port}` : 'stopped'}
        </span>
      </div>
      ${running
        ? `<button class="btn btn-danger" id="btn-litellm-action" onclick="stopLiteLLM()">
            <i class="fa-solid fa-stop"></i>Stop LiteLLM
          </button>`
        : `<button class="btn btn-primary" id="btn-litellm-action" onclick="startLiteLLM()">
            <i class="fa-solid fa-play"></i>Start LiteLLM
          </button>`}
    </div>

    ${keyRows ? `<div class="litellm-card">
      <div class="litellm-card-title">Environment variables</div>
      ${keyRows}
    </div>` : ''}

    <div class="litellm-card">
      <div class="litellm-card-title">Manual start command</div>
      <div class="cmd-block" id="start-cmd">Loading…</div>
      <div class="copy-row" style="margin-top:8px">
        <button class="btn btn-ghost" onclick="copyStartCmd()">
          <i class="fa-solid fa-copy"></i>Copy
        </button>
      </div>
    </div>
  `;

  const configRes = await fetch('/api/config');
  const configData = await configRes.json();
  const envVars = Object.keys(keys).map(k => `export ${k}="..."`).join('\n');
  document.getElementById('start-cmd').textContent =
    `${envVars}\nlitellm --config ${configData.path}`;
}

async function startLiteLLM() {
  const btn = document.getElementById('btn-litellm-action');
  btn.innerHTML = '<div class="spinner"></div>Starting…';
  btn.disabled = true;
  const res = await fetch('/api/litellm/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  const data = await res.json();
  if (data.ok) { loadLiteLLM(); } else {
    btn.innerHTML = `<i class="fa-solid fa-xmark"></i>${data.message || 'Failed'}`;
    btn.disabled = false;
  }
}

async function stopLiteLLM() {
  const btn = document.getElementById('btn-litellm-action');
  btn.innerHTML = '<div class="spinner"></div>Stopping…';
  btn.disabled = true;
  await fetch('/api/litellm/stop', { method: 'POST' });
  setTimeout(loadLiteLLM, 800);
}

function copyStartCmd() {
  navigator.clipboard.writeText(document.getElementById('start-cmd').textContent);
}

// ── Projects section ────────────────────────────────────────────────────────
async function loadProjects() {
  const body = document.getElementById('projects-body');
  const res = await fetch('/api/projects');
  const data = await res.json();
  const projects = data.projects || [];

  const cards = projects.map(p => `
    <div class="project-card">
      <div>
        <div class="project-name"><i class="fa-solid fa-folder" style="color:var(--warn);margin-right:7px"></i>${p.name}</div>
        <div class="project-path">${p.path}</div>
        <div class="project-meta">
          ${p.state_exists
            ? '<span style="color:var(--accent)"><i class="fa-solid fa-check"></i> context initialized</span>'
            : '<span style="color:var(--warn)"><i class="fa-solid fa-triangle-exclamation"></i> context missing</span>'}
          ${p.pending_commits > 0
            ? `<span style="color:var(--warn);margin-left:10px"><i class="fa-solid fa-clock-rotate-left"></i> ${p.pending_commits} commits pending</span>`
            : ''}
        </div>
      </div>
      <div style="font-family:var(--font-mono);font-size:9px;color:var(--muted)">added ${p.added || '—'}</div>
    </div>
  `).join('');

  body.innerHTML = `
    ${cards || '<div style="color:var(--ink-dim);font-family:var(--font-mono);font-size:11px;margin-bottom:16px">No projects initialized yet.</div>'}
    <div class="init-card">
      <div class="init-card-title"><i class="fa-solid fa-plus" style="margin-right:6px;color:var(--primary)"></i>Initialize a new project</div>
      <div class="field" style="text-align:left">
        <label class="field-label">Project path</label>
        <input class="field-input" id="inp-init-path" type="text" placeholder="/home/user/Projects/my-project">
      </div>
      <button class="btn btn-primary" onclick="initProject()">
        <i class="fa-solid fa-wand-magic-sparkles"></i>Initialize context
      </button>
      <div id="init-result" style="margin-top:10px;font-family:var(--font-mono);font-size:10px"></div>
    </div>
  `;
}

async function initProject() {
  const path = document.getElementById('inp-init-path').value.trim();
  if (!path) return;
  const result = document.getElementById('init-result');
  result.innerHTML = '<div class="spinner" style="display:inline-block"></div> Initializing…';
  const res = await fetch('/api/projects/init', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path })
  });
  const data = await res.json();
  if (data.ok) {
    result.innerHTML = `<span style="color:var(--accent)"><i class="fa-solid fa-check"></i> Initialized: ${data.path}</span>`;
    setTimeout(loadProjects, 1000);
  } else {
    result.innerHTML = `<span style="color:var(--danger)"><i class="fa-solid fa-xmark"></i> ${data.detail || 'Error'}</span>`;
  }
}

// ── SSE real-time status ────────────────────────────────────────────────────
function connectSSE() {
  const es = new EventSource('/events');
  es.onmessage = (e) => {
    const data = JSON.parse(e.data);
    // Update sidebar status dot if needed (future: badge on status nav item)
    if (currentSection === 'status') {
      // silently refresh status view every SSE tick
    }
  };
  es.onerror = () => { setTimeout(connectSSE, 5000); };
}

// ── Model picker ────────────────────────────────────────────────────────────
let pickerTargetAgent = null;
let pickerSelectedModel = null;

function openModelPicker(agentName) {
  pickerTargetAgent = agentName;
  pickerSelectedModel = document.getElementById(`inp-model-${agentName}`)?.value || null;
  renderPickerModal();
  document.getElementById('model-picker-root').style.display = 'block';
  setTimeout(() => document.getElementById('picker-search')?.focus(), 50);
}

function closeModelPicker() {
  document.getElementById('model-picker-root').style.display = 'none';
  pickerTargetAgent = null;
  pickerSelectedModel = null;
}

function confirmModelPicker() {
  if (!pickerTargetAgent || !pickerSelectedModel) return;
  const modelInp = document.getElementById(`inp-model-${pickerTargetAgent}`);
  const keyInp = document.getElementById(`inp-keyname-${pickerTargetAgent}`);
  if (!modelInp) return;
  modelInp.value = pickerSelectedModel;
  const entry = PROVIDER_CATALOG.flatMap(p => p.models).find(m => m.model === pickerSelectedModel);
  if (entry && keyInp && !keyInp.value) keyInp.value = entry.keyName;
  modelInp.dispatchEvent(new Event('input'));
  closeModelPicker();
}

function useCustomModel() {
  const val = document.getElementById('picker-custom-inp')?.value.trim();
  if (!val) return;
  pickerSelectedModel = val;
  confirmModelPicker();
}

function pickerSelectCard(modelStr) {
  pickerSelectedModel = modelStr;
  document.querySelectorAll('.picker-card').forEach(c => {
    c.classList.toggle('selected', c.dataset.model === modelStr);
  });
  document.getElementById('picker-confirm-btn').disabled = false;
}

function pickerSearch(query) {
  const q = query.toLowerCase().trim();
  document.querySelectorAll('.picker-provider').forEach(section => {
    let anyVisible = false;
    section.querySelectorAll('.picker-card').forEach(card => {
      const text = (card.dataset.model + ' ' + card.querySelector('.picker-card-name').textContent).toLowerCase();
      const match = !q || text.includes(q);
      card.classList.toggle('hidden', !match);
      if (match) anyVisible = true;
    });
    section.classList.toggle('hidden', !anyVisible);
  });
}

function renderPickerModal() {
  const currentModel = pickerSelectedModel;
  const sectionsHtml = PROVIDER_CATALOG.map(({ provider, keyUrl, models }) => {
    const cardsHtml = models.map(({ name, model, cost, rec }) => {
      const isFree = cost === 'free';
      const recBadges = rec.map(r => `<span class="picker-badge picker-badge-rec">${r}</span>`).join('');
      return `
        <div class="picker-card${model === currentModel ? ' selected' : ''}"
             data-model="${model}"
             onclick="pickerSelectCard('${model}')">
          <div class="picker-card-name">${name}</div>
          <div class="picker-card-model">${model}</div>
          <div class="picker-card-badges">
            <span class="picker-badge picker-badge-cost${isFree ? ' free' : ''}">${cost}</span>
            ${recBadges}
          </div>
        </div>`;
    }).join('');
    return `
      <div class="picker-provider">
        <div class="picker-provider-label">
          ${provider}
          <a class="picker-key-link" href="${keyUrl}" target="_blank" rel="noopener">
            <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:8px"></i>get key
          </a>
        </div>
        <div class="picker-grid">${cardsHtml}</div>
      </div>`;
  }).join('');

  document.getElementById('model-picker-root').innerHTML = `
    <div class="picker-backdrop" onclick="if(event.target===this)closeModelPicker()">
      <div class="picker-modal">
        <div class="picker-header">
          <div class="picker-title">
            <i class="fa-solid fa-microchip" style="color:var(--primary);font-size:12px"></i>
            Choose a model
            <span class="picker-agent-chip">${pickerTargetAgent}</span>
          </div>
          <button class="picker-close" onclick="closeModelPicker()"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="picker-search">
          <div class="picker-search-wrap">
            <i class="fa-solid fa-magnifying-glass"></i>
            <input id="picker-search" class="picker-search-input" type="text"
              placeholder="Search models…" oninput="pickerSearch(this.value)" autocomplete="off">
          </div>
        </div>
        <div class="picker-body">
          ${sectionsHtml}
          <div class="picker-custom">
            <div class="picker-custom-label">Custom model</div>
            <div class="picker-custom-row">
              <input id="picker-custom-inp" class="picker-custom-input" type="text"
                placeholder="provider/model-name  (e.g. ollama/llama3.2)"
                onkeydown="if(event.key==='Enter')useCustomModel()">
              <button class="picker-custom-use" onclick="useCustomModel()">Use this</button>
            </div>
          </div>
        </div>
        <div class="picker-footer">
          <span class="picker-footer-hint">
            <i class="fa-solid fa-circle-info" style="margin-right:4px"></i>Key name auto-fills on selection
          </span>
          <button id="picker-confirm-btn" class="picker-confirm"
            ${currentModel ? '' : 'disabled'}
            onclick="confirmModelPicker()">Confirm selection</button>
        </div>
      </div>
    </div>`;
}

// ── Init ────────────────────────────────────────────────────────────────────
loadFleet();
connectSSE();
