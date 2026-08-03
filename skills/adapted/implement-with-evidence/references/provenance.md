# Adaptation provenance

## Sources

Repository: `addyosmani/agent-skills`

Pinned commit: `7829ffd90d973b6325f5f12f1b1226dcace74443`

License observed for the repository: MIT.

Source skills:

- `test-driven-development`, fingerprint
  `71fdddb96c2c54041fcfbfdaef3c172b202fb9240b609e658d9d82edbed6cad1`;
- `incremental-implementation`, fingerprint
  `f3336e581a5247d9a6a58096f0015dbbfb7673a35e71aebd39491c55662a1906`.

The fingerprints above are copied from Trufagent's governed import manifest.

## Adaptation decisions

Retained:

- behavior-first proof;
- reproduction-first bug fixes when feasible;
- repository-specific test discovery;
- small coherent increments;
- explicit verification and honest evidence reporting.

Removed or relaxed:

- universal TDD for non-behavioral changes;
- fixed coverage percentages and test pyramids;
- JavaScript-specific examples;
- mandatory commits after each increment;
- mandatory feature flags and fixed line-count thresholds;
- automatic subagent or browser requirements.
