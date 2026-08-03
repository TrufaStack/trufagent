# Phase 14 — cost-aware routing

Date: 2026-07-30

## Purpose

Validate whether the smallest casebook task can use cheaper coordinator models
without weakening Trufagent's contract.

Adoption required all 11 live judges, including no implementation, no
diagnostic command, correct autonomy, and an unchanged repository.

## C01 results

| Harness/model | Result | Time | Cost/tokens | Decision |
| --- | --- | ---: | --- | --- |
| Codex GPT-5.6-Luna, low | 11/11 | 24.844 s | 70,880 input; 51,200 cached | Adopt |
| Codex GPT-5.6-Sol baseline | 11/11 | 29.044 s | 89,396 input; 66,560 cached | Frontier baseline |
| Claude Haiku, low | 9/11 | 42.105 s | USD 0.051696 | Reject |
| Claude Sonnet baseline | 11/11 | 27.140 s | USD 0.142701 | Retain |

Luna reduced Codex input tokens by 20.7% and elapsed time by 14.5% while
preserving every judge. Haiku was 63.8% cheaper than Sonnet, but returned
`user_action=confirm` when the runtime said `proceed` and ran a prohibited
diagnostic command. Cost alone therefore did not qualify it.

## Resulting policy

- Plans expose portable per-phase tiers in `model_route`.
- Codex economy resolves to GPT-5.6-Luna.
- Claude economy is promoted to Sonnet until a cheaper model passes the same
  contract.
- `none` means no model invocation for that phase.
- High and critical effort reserve frontier models; routing never relaxes
  verification evidence.

Live result JSON remains under ignored `.trufagent/state/live-eval/`.
