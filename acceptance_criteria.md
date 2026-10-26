# Acceptance Criteria and Evidence

## Local prototype acceptance
- [x] CLI recommends a test suite for a supplied diff.
- [x] Full regression baseline is available.
- [x] Coverage-only baseline is available.
- [x] Hybrid selector uses coverage, dependencies, test history, and defect links.
- [x] Empty diff triggers full-suite fallback.
- [x] Critical defect-associated tests are retained when relevant.
- [x] Event processor deduplicates event IDs.
- [x] Event processor buffers out-of-order events and drains in sequence.
- [x] Stale, conflicting, and malformed events are handled without overwriting committed state.
- [x] Experiment produces per-case and aggregate metrics.
- [x] Automated tests pass locally.
- [x] CI workflow is included to rerun tests on GitHub pushes and pull requests.

## External acceptance — must be completed by the project team
- [ ] Run against a real repository diff and current coverage export.
- [ ] Compare selector recommendations against full regression outcomes for historical changes.
- [ ] Obtain QA/release-engineer walkthrough feedback.
- [ ] Approve acceptable critical-defect recall and runtime-saving thresholds.
- [ ] Run shadow mode and document release sign-off.
- [ ] Add durable event storage and restart recovery before production use.

The first section establishes that the included prototype package works. The second section requires external evidence that cannot be truthfully fabricated inside a generated ZIP.
