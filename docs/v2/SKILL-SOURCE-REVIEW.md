# Trufagent v2 — Skill Source Review

Review performed against the local catalog and remote registry observed on
2026-08-03. A static signal is evidence for inspection, not proof of malicious
behavior. `reviewed` means the exact local fingerprint was inspected; it does
not transfer to later versions.

## Local blocked-signal review

Approved exact local variants:

- `brainstorming`: already reviewed; deletion is restricted to an ephemeral
  `/tmp` session directory;
- `hookify-rules`: destructive strings are regex examples used to create
  protective hooks;
- `perl-security`: destructive strings appear only in explicitly bad injection
  examples;
- `safety-guard`: destructive strings are patterns the guard is designed to
  intercept.

Held for later or rejected from automatic selection:

- `configure-ecc`: clones and recursively replaces a fixed `/tmp` directory;
- `continuous-learning-v2`: installs hooks and background/session behavior that
  is broader than Trufagent's essential cycle;
- `frontend-slides`: installs Playwright/Chromium at runtime and executes a
  sizeable export bundle;
- `gateguard`: installs a hook and imposes a denial-first workflow globally;
- `rules-distill`: scans and rewrites rule libraries;
- `skill-stocktake`: duplicates the catalog/audit responsibility now owned by
  Trufagent and includes its own subagent workflow;
- `subagent-driven-development`: prescribes recursive workspace deletion and a
  delegation policy outside the essential cycle;
- `tdd-workflow`: the dangerous command is a prohibition example, but the skill
  also mandates coverage and commit checkpoints too rigidly for automatic use.

## Anthropic pilot

No Anthropic skill should enter the essential Trufagent surface in this pass:

- `frontend-design` is already present with the same fingerprint;
- `skill-creator` overlaps the installed system skill;
- `template-skill` is not a usable capability;
- document, design, MCP and testing skills remain optional domain capabilities.

Useful optional candidates for future project-scoped installation are
`doc-coauthoring`, `mcp-builder`, `webapp-testing`, `pdf`, `pptx`, `docx` and
`xlsx`. Their licenses must be checked per directory because the repository
contains both open-source and source-available material.

## Addy Osmani pilot

The repository is relevant, but its workflows are intentionally more rigid
than the Trufagent v2 brief. Do not install the full suite or copy these skills
unchanged into the essential surface.

Use the following as reviewed adaptation inputs:

- `spec-driven-development`: retain explicit outcomes, assumptions and open
  questions; drop mandatory repository paths and approval after every phase;
- `planning-and-task-breakdown`: retain dependency order, vertical slices and
  verification; let Trufagent complexity choose whether a written plan exists;
- `test-driven-development`: retain reproduction-first fixes and RED/GREEN proof;
  do not impose a universal coverage percentage or a single test stack;
- `incremental-implementation`: retain small verified slices and scope discipline;
  do not mandate a commit after every increment;
- `code-review-and-quality`: retain correctness, simplicity, architecture,
  security and performance axes as a post-implementation check;
- `documentation-and-adrs`: retain durable decision capture and feed only
  reviewable facts into Trufagent's memory-update proposal.

Do not import these overlapping responsibilities:

- `debugging-and-error-recovery`: `systematic-debugging` is already reviewed;
- `using-agent-skills`: Trufagent owns discovery and routing;
- `context-engineering`: Trufagent owns economical context loading;
- `git-workflow-and-versioning`: repository policy must remain project-specific.

## Minimal capability target

The six adaptation inputs collapse into four Trufagent behaviors rather than six
always-on skills:

1. clarify only when uncertainty or open decisions justify it;
2. plan and slice only when complexity justifies it;
3. implement with task-appropriate tests and incremental verification;
4. review the change, then propose compact memory/cartography updates.

This preserves the useful procedural knowledge without returning to the
premature specificity that v2 is intended to remove.

## First import plan

The governed import pilot is recorded in
`~/.trufagent/skills/import-plan.json`:

- direct `anthropics/skills:doc-coauthoring`: held as `needs-review`; the pinned
  directory contains only `SKILL.md`, while the repository does not declare a
  single SPDX license. Do not copy it until redistribution terms are explicit;
- adapt `code-review-and-quality`: candidate, MIT;
- adapt `documentation-and-adrs`: candidate, MIT, with a non-critical sensitive
  configuration reference;
- adapt `test-driven-development`: candidate, MIT;
- adapt `incremental-implementation`: candidate, MIT, with a non-critical
  sensitive configuration reference.

No item was installed. The four MIT sources should be collapsed into two small
Trufagent skills—implementation evidence and post-change review/memory—rather
than copied as four always-on workflows.

## Adaptations materialized

The four MIT sources were subsequently adapted into two concise, versioned
skills under `skills/adapted/`:

- `implement-with-evidence` combines proportional behavior proof and small
  verified increments;
- `review-and-remember` combines task-sized review with governed memory and
  post-confirmation Graphify updates.

Both keep detailed source commits, fingerprints, license, retained principles,
and removed constraints in a lazily loaded `references/provenance.md`. Their
operational `SKILL.md` files deliberately omit fixed coverage targets, mandatory
commit cadence, universal gates, provider-specific examples, and automatic
memory mutation. They were validated, installed in the Codex catalog, reviewed
by exact fingerprint, and routed automatically only for fixes and features.
