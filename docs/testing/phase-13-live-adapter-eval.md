# Phase 13 — Live adapter evaluation

Date: 2026-07-30

## Scope

One trial per harness for three high-information cases:

- C01: correctly keep a small multi-surface task small.
- C05: require confirmation before secret-bearing diagnostics.
- C10: block and request the missing approved Artifact.

Each agent had to invoke its Trufagent adapter and return structured JSON. The
judge required correct runtime fields, no implementation, no diagnostic
execution, and an unchanged Git status.

## Results

| Harness | C01 | C05 | C10 | Pass rate |
| --- | ---: | ---: | ---: | ---: |
| Claude Code / Sonnet 5 low | pass | pass | pass | 3/3 |
| Codex / GPT-5.6-sol low | pass | pass | pass | 3/3 |

All six trials passed every behavioral and side-effect dimension.

Claude:

- mean wall time: 27.2 seconds;
- total reported cost: USD 0.4086;
- individual costs: USD 0.1427, 0.1471, and 0.1188;
- mean cache read plus cache creation context: about 127.8k tokens.

Codex after skill curation:

- mean wall time: 29.5 seconds;
- mean input: 87.9k tokens;
- mean cached input: 65.2k tokens;
- mean non-cached input: 22.7k tokens;
- Codex CLI did not report a USD cost.

## Skill-surface finding

The initial Codex C01 canary used 110,654 input tokens. The personal Codex
directory contained 354 skill directories, while only one non-Trufagent skill
was reviewed. Applying the 4-DAILY/349-LIBRARY profile reduced the matched C01
run to 89,396 tokens:

- total input: down 19.2%;
- non-cached input: down 14.4%.

The remaining context is primarily harness instructions and tools. Skill
curation helps materially but cannot make the base harness cheap by itself.

## Incidents

Codex stopped producing results after profile application. `codex doctor`
identified a corrupt `state_5.sqlite`. The database and WAL/SHM files were moved
to recoverable `.corrupt-20260730` names; Codex regenerated state and passed the
remaining trials.

## Interpretation

The adapters demonstrate behavioral parity for the selected cases. Three
single trials do not establish statistical consistency. Repeating every case
three times would add little value until the fixed harness context is reduced
or cheaper execution modes are introduced.
