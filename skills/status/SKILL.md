---
description: Use this skill to show the current trufagent fleet status — configured agents, models, LiteLLM health, and context system state. Invoke with /trufagent:status or when the user asks "trufagent status", "is litellm running", "what agents are configured", or "show fleet".
---

# trufagent:status

Shows the current state of the trufagent fleet and context system.

## LiteLLM status
!`curl -s http://localhost:4000/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('running')" 2>/dev/null || echo "not running — start with: litellm --config ~/litellm-config.yaml"`

## Fleet configuration
!`cat ~/litellm-config.yaml 2>/dev/null | grep -A2 "model_name:" | grep -v "^--$" || echo "~/litellm-config.yaml not found — run /trufagent:setup"`

## Agent files
!`ls ~/.claude/agents/ 2>/dev/null | sed 's/\.md//' || echo "No agents found in ~/.claude/agents/"`

## Context system
!`[ -f CLAUDE.md ] && echo "CLAUDE.md found" || echo "CLAUDE.md missing — run /trufagent:init"`
!`[ -f docs/context/state.md ] && echo "state.md found" || echo "state.md missing — run /trufagent:init"`
!`[ -f docs/context/pending-updates.md ] && wc -l docs/context/pending-updates.md | awk '{if($1>0) print $1 " lines in pending-updates.md — review at session start"; else print "pending-updates.md empty"}' || echo "pending-updates.md missing — run /trufagent:init"`

## Instructions

Format the above data as a clean status report:

```
trufagent — Fleet Status
────────────────────────────────────────────
Infrastructure
  LiteLLM: [running on :4000 | not running]

Fleet
  scout    [model]   [provider]
  runner   [model]   [provider]
  thinker  [model]   [provider]
  builder  [model]   [provider]
  writer   [model]   [provider]
  critic   [model]   [provider]  [optional]

Context
  CLAUDE.md:         [found | missing]
  state.md:          [found | missing]
  pending-updates:   [empty | N lines pending]
────────────────────────────────────────────
```
