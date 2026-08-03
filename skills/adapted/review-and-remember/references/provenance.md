# Adaptation provenance

## Sources

Repository: `addyosmani/agent-skills`

Pinned commit: `7829ffd90d973b6325f5f12f1b1226dcace74443`

License observed for the repository: MIT.

Source skills:

- `code-review-and-quality`, fingerprint
  `bec431b759ff389e47b8d2c9d74e1981ff93cf5f3c36b4a3b6a71a75c250be2c`;
- `documentation-and-adrs`, fingerprint
  `b867bb80fb681257c7625ae59a0dfd849b1fc0f0a2f0338e7923f38030df9793`.

The fingerprints above are copied from Trufagent's governed import manifest.

## Adaptation decisions

Retained:

- correctness, simplicity, architecture, security, performance, and test axes;
- actionable review findings backed by evidence;
- durable decision and rationale capture;
- explicit separation between transient notes and lasting project knowledge.

Removed or relaxed:

- review of every axis at equal depth for every change;
- fixed diff-size and file-size thresholds;
- mandatory ADR creation for all decisions;
- provider- or language-specific examples;
- automatic mutation of memory or cartography before human confirmation.
