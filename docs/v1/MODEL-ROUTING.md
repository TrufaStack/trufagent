# Cost-aware model routing

Trufagent routes each task phase by capability tier instead of assigning one
model to the whole task:

| Effort budget | Model tier |
| --- | --- |
| `none` | `none` |
| `low` | `economy` |
| `medium` | `balanced` |
| `high` or `critical` | `frontier` |

The raw provider-neutral route retains an `economy` coordinator for a future
external orchestrator. In embedded skill mode, the current Claude/Codex host
already coordinated the deterministic runtime. `TaskPlan.coordinator_gate`
therefore changes the effective coordinator tier to `none`, preventing a
second model call that would only reinterpret the same plan.

## Validated harness profiles

| Harness | Economy | Balanced | Frontier |
| --- | --- | --- | --- |
| Codex | `gpt-5.6-luna` | `gpt-5.6-terra` | `gpt-5.6-sol` |
| Claude | `sonnet` | `sonnet` | `opus` |

Claude's economy tier intentionally resolves to Sonnet. Haiku was cheaper in
the C01 canary but failed the autonomy and no-diagnostic-command judges.

Model routing does not lower evidence requirements. A low-cost execution phase
can still be followed by frontier verification when risk, secrets, production,
or silent failure make that proportionate.

The defaults live in
`src/trufagent/infrastructure/model_profiles.py`; the domain plan contains only
portable tiers.

## Project overrides

Overrides are optional and additive in `.trufagent/config.yaml`:

```yaml
models:
  claude:
    balanced: sonnet
    frontier: opus
  codex:
    economy: gpt-5.6-luna
    balanced: gpt-5.6-terra
    frontier: gpt-5.6-sol
```

Projects only need to declare values that differ from the defaults. Existing
v1 configurations without `models` remain valid. The `none` tier is not
overridable because it is a policy decision to skip invocation.

Inspect the effective choice before delegation:

```bash
trufagent models resolve . --harness codex --tier balanced
```

The JSON response includes `source: default` or `source: project`.
