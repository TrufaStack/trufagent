# Bounded delegation protocol

Trufagent compiles `model_route` into a provider-specific but non-executing
protocol:

```text
coordinator (read-only)
  → exploration (read-only)
  → execution (worktree-write)
  → verification (read-only)
```

Every phase is unique, ordered, serial, and limited to one attempt. A `none`
tier remains present as an explicit skipped phase with no model.

## Compile

Create a JSON request containing the active session, harness, route returned by
the task plan, required evidence, and optional budget:

```json
{
  "session_id": "ses_example",
  "harness": "codex",
  "model_route": {
    "coordinator": "economy",
    "exploration": "balanced",
    "execution": "economy",
    "verification": "frontier"
  },
  "evidence_required": ["regression-test"],
  "budget_limit_usd": "0.50"
}
```

Then compile it:

```bash
trufagent delegation compile . request.json
```

Compilation resolves project model overrides but never invokes a model.

## Phase handoffs and gates

Every invoked phase returns a compact `PhaseHandoff`:

- `status`: `success`, `warning`, or `error`;
- one-line `summary`;
- `next_actions`;
- artifact references and named evidence;
- whether the worktree changed;
- for errors only: root-cause hint, safe retry, and explicit stop condition.

The executor rejects a phase mismatch, a worktree change outside execution, or
missing verification evidence. Warnings and errors stop later phases and return
control to the coordinator. There is no automatic retry.

Handoffs compact context at phase boundaries. They do not contain hidden
reasoning or full transcripts.

## Dry-run executor

A scripted adapter can exercise the complete state machine without invoking a
model:

```bash
trufagent delegation dry-run protocol.json handoffs.json
```

The handoff script maps phase names to typed handoff objects. Skipped phases do
not need an entry. The response always includes `status`, `summary`,
`next_actions`, `artifacts`, accepted handoffs, and the phase where execution
stopped. Warning and error results return a non-zero exit status.

## Shadow provider boundary

The experimental Codex shadow adapter is narrower than the protocol executor:
it accepts only coordinator or exploration steps with read-only scope. A
content fingerprint covers tracked, untracked, and ignored sensitive files
before and after the provider process. Explicit state and cache directories are
excluded.

Provider output must validate as a handoff. Usage is append-only once a
structured result exists. Process and validation failures expose only safe
error categories, never provider stdout or stderr. The adapter is available to
the evaluation script only; it is not automatic delegation authority.

## Graphify-first value gate

Model exploration is eligible to become `none` when the task is a known
structural change or approved implementation without open decisions; the graph
snapshot matches current content; explicit required symbols were declared; and
every target appears with structural evidence.

A truncated query may pass only when it is target-complete. Architecture,
research, visual design, unknown-cause bugs, open decisions, and requests
without explicit symbols never use this shortcut.

Shadow fallback is opt-in in evaluation. A failed gate returns
`shadow-required` and zero invocations unless `--allow-shadow` is explicit.
Task signals are evaluated before querying Graphify. Ineligible work therefore
reports `graph_queries: 0` as well as `model_invocations: 0`.

The read-only shadow workflow remains an explicit canary rather than a default
runtime path:

```bash
uv run python scripts/run_shadow_canary.py \
  --root . \
  --session <active-session-id> \
  --task "Diagnose the reported failure" \
  --signals /path/to/task-signals.json \
  --required-symbol RelevantSymbol \
  --output /tmp/trufagent-shadow.json
```

This command stops at `shadow-required`. Adding `--allow-shadow` is the sole
provider opt-in. The compiled protocol still assigns tier `none` to execution
and verification, and the adapter enforces a read-only worktree fingerprint.

The promoted CLI surface uses the same boundary:

```bash
trufagent delegation shadow . \
  --session <active-session-id> \
  --task "Diagnose the failure" \
  --signals /path/to/task-signals.json \
  --required-symbol RelevantSymbol \
  --budget-limit-usd 0.50 \
  --estimated-cost-usd 0.10
```

Without `--confirm-provider`, this is a preparation command: it reports the
route with zero provider invocations. A first attempt requires
`--confirm-provider`. A second attempt additionally requires `--attempt 2`,
and `--confirm-retry`. Its prior failure class, attempt count, and worktree
fact are read from the create-only attempt ledger rather than command-line
assertions. Invalid responses, acceptance failures, worktree changes, and
budget failures are not retryable.

```bash
trufagent delegation attempts . <session-id>
```

This returns safe attempt metadata only: IDs, task digest, phase, attempt
number, timestamps, terminal classification, and whether protected worktree
content remained unchanged. Prompts, responses, process output, and secrets are
never stored.

Budget authorization is prospective and fails closed when an earlier recorded
invocation has unknown monetary cost. The CLI does not interpret missing cost
data as zero.

## Usage ledger

Each completed invocation may append a `trufagent.usage.v1` JSON event:

```bash
trufagent delegation usage append . usage.json
trufagent delegation usage status . <session-id> --budget-limit-usd 0.50
```

Ledgers live under `.trufagent/state/usage/<session-id>.jsonl`. They contain no
prompt or response content. Duplicate invocation IDs are rejected, costs may be
explicitly unknown, and the in-memory ledger is immutable.

Budget authorization is prospective: callers must submit an estimated cost to
`UsageLedger.authorize()` before invoking a model. Recording a call after it
already exceeded the budget would be too late to act as a guardrail.

## Non-goals in this phase

- invoking Claude or Codex from the core runtime;
- parallel delegates;
- automatic retry;
- allowing verification to repair implementation;
- treating usage telemetry as decision memory.
