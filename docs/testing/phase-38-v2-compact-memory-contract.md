# Phase 38 — V2 compact memory contract

## Objective

Define the smallest useful v2 memory contract while preserving strict v1
validation and reversible compatibility.

## Contract

A v2 memory keeps only:

- identity, kind, title, project, and lifecycle state;
- creation and update timestamps;
- the human reviewer when accepted;
- an optional source commit and compact tags;
- the Markdown body.

The lifecycle is reduced to `proposed`, `accepted`, `replaced`, and `retired`.
Accepted memory requires an explicit human reviewer. Proposed memory cannot
govern behavior.

## Compatibility boundary

The existing v1 parser and repository remain unchanged. A separate compatible
reader accepts either schema and projects validated v1 documents into the
compact v2 contract. Historical v1 states map reversibly at the read boundary:

- `proposed` and `accepted` remain unchanged;
- `superseded` becomes `replaced`;
- `rejected`, `stale`, and `resolved` become `retired`.

V2 canonical writes and the simplified human operations are intentionally left
for the next increment.

## Evidence

- existing v1 fixtures still pass strict validation;
- an accepted v1 rule projects into an accepted governing v2 view;
- a native v2 document exposes only the compact schema fields;
- duplicate tags are removed;
- accepted v2 memory without a reviewer is rejected;
- unknown schemas and secret-shaped content remain rejected;
- the full project suite remains green.
