---
description: Use this skill to reconfigure the model behind a specific agent role in the trufagent fleet. Invoke with /trufagent:config [agent] or when the user says "change [agent] model", "swap [agent] to [model]", "reconfigure [agent]", or "optimize [agent] for cost/speed".
---

# trufagent:config

Reconfigures the model behind a specific agent role. Only `~/litellm-config.yaml` changes — agent `.md` files stay the same.

## Step 1 — Identify target agent

If no agent specified, show current fleet and ask which to reconfigure:

```
Configured agents:
!`cat ~/litellm-config.yaml 2>/dev/null | grep "model_name:" | grep -v "claude-sonnet" | sed 's/.*model_name: /  /'`

Which agent do you want to reconfigure?
```

## Step 2 — Show alternatives

```
[AGENT] — [role description]
Current model: [current model]

Validated alternatives:
  1. [alternative 1]  ([provider])
  2. [alternative 2]  ([provider])
  3. Custom model (any valid LiteLLM model string)
```

Alternatives by role:
- **scout**: `anthropic/claude-haiku-4-5`, `openai/gpt-4o-mini`
- **runner**: `anthropic/claude-haiku-4-5`, `openai/gpt-4o-mini`, `google/gemini-2.0-flash`
- **thinker**: `anthropic/claude-sonnet-4-6`, `openai/gpt-4o`, `google/gemini-2.5-pro`
- **builder**: `deepseek/deepseek-chat`, `openai/gpt-4o`, `mistral/codestral-latest`
- **writer**: `anthropic/claude-haiku-4-5`, `openai/gpt-4o-mini`
- **critic**: `anthropic/claude-sonnet-4-6` (cheaper, less powerful), `openai/gpt-4o`

## Step 3 — Handle API key

If the chosen provider already has a key in config → skip.
If new provider → ask for key → add as `os.environ/PROVIDER_API_KEY`.

## Step 4 — Update ~/litellm-config.yaml

Update only the matching `model_name: [agent]` entry. Leave all other entries untouched.

## Step 5 — Confirm

```
[agent] updated: [old model] → [new model]
Restart LiteLLM for the change to take effect:
  litellm --config ~/litellm-config.yaml
```

## Notes

- Reconfiguring `critic` to a cheaper model reduces review quality on high-stakes changes
- Reconfiguring `thinker` to a faster model (groq) reduces reasoning depth
- Any LiteLLM-compatible model string works — see https://docs.litellm.ai/docs/providers
