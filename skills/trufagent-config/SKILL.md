---
name: trufagent-config
description: Reconfigure a specific agent in the trufagent fleet — swap the model behind a role without changing anything else. Use to optimize for cost, speed, or capability. Usage: /trufagent config [agent-name]
triggers:
  - /trufagent config
  - reconfigure trufagent agent
  - change trufagent model
  - swap agent model
---

# trufagent-config

Reconfigures the model behind a specific agent role. The role stays the same — only the model changes in `~/litellm-config.yaml`.

## Usage

```
/trufagent config [agent]
```

Where `[agent]` is one of: `scout`, `runner`, `thinker`, `builder`, `writer`, `critic`

## Execution

### Step 1 — Identify target agent

If no agent name provided in the command, list all agents and ask which one to reconfigure:

```
Agentes configurados:
  scout   → gemini/gemini-2.0-flash       (Google)
  runner  → groq/llama-3.3-70b-versatile  (Groq)
  thinker → deepseek/deepseek-chat         (DeepSeek)
  builder → openrouter/qwen/...            (OpenRouter)
  writer  → openrouter/mistralai/...       (OpenRouter)
  critic  → anthropic/claude-opus-4-8      (Anthropic)

¿Cuál querés reconfigurar?
```

### Step 2 — Show current config and alternatives

For the selected agent, show:
```
THINKER — Razonamiento profundo + 1er review
Modelo actual: deepseek/deepseek-chat (DeepSeek API)

Alternativas validadas:
  1. anthropic/claude-sonnet-4-6    (Anthropic — ya tenés la key)
  2. openai/gpt-4o                  (OpenAI)
  3. google/gemini-2.5-pro          (Google)
  4. groq/llama-3.3-70b-versatile   (Groq — más rápido, menor razonamiento)
  5. Modelo custom (cualquier string LiteLLM)

Elegí una opción [1-5]:
```

### Step 3 — Handle API key

- If chosen provider already has a key in the config → skip
- If new provider → ask for API key → add to config as `os.environ/PROVIDER_API_KEY`

### Step 4 — Test connection

Run a minimal test to verify the model responds:
```bash
litellm --test --model [chosen-model] 2>&1 | tail -3
```

If test fails: show error, offer to try another model or keep current.

### Step 5 — Update ~/litellm-config.yaml

Update only the `model_name: [agent]` entry. Leave everything else untouched.

### Step 6 — Confirm

```
✓ thinker actualizado: deepseek/deepseek-chat → anthropic/claude-sonnet-4-6
  Reiniciá LiteLLM para que el cambio tome efecto:
  litellm --config ~/litellm-config.yaml
```

## Notes

- Reconfiguring `critic` to a cheaper model reduces review quality on important changes
- Reconfiguring `thinker` to a faster model (groq) reduces reasoning depth
- Any LiteLLM-compatible model string works — see https://docs.litellm.ai/docs/providers
