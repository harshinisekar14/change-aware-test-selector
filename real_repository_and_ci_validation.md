# Real Repository, CI Benchmark, and Stakeholder Validation Runbook

## Status and integrity statement
This package now includes a Git-diff adapter, a SQLite durable event processor, restart-recovery tests, and a wall-clock benchmark runner. **No real company repository, CI credentials, private test history, or real stakeholder was supplied in this workspace.** Therefore the package does not invent stakeholder approval or label synthetic fixture timings as production measurements. The steps below are the final external evidence needed to close those validation items.

## A. Connect a real repository
1. Run inside a clean checkout with the same Python/runtime used by CI.
2. Confirm the base/head commit refs exist: `git rev-parse BASE_REF` and `git rev-parse HEAD_REF`.
3. Generate changed-file input: `python -c "from selector.git_diff import changed_paths,write_diff_json; write_diff_json(changed_paths('BASE_REF','HEAD_REF'), 'data/live_diff.json')"` (replace `BASE_REF` with the actual merge-base/base ref).
4. Export test catalogue, measured durations, coverage map, failure history, and defect-to-test associations from the actual CI system. Keep identifiers anonymised if needed. Do not use synthetic values for the final validation run.
5. Run `python -m selector.cli recommend --diff data/live_diff.json --data data` and archive the output with commit SHA, data-export date, and selector version.
6. Review any missing file-to-test mappings. Unknown/low-confidence mappings must trigger the full-suite fallback rather than silently omit tests.

## B. Measure actual pipeline time
The included `selector/ci_benchmark.py` measures wall-clock durations of real commands and refuses to count failed runs as successful measurements. Copy `data/benchmark_commands.example.json` to a private local file and replace the three command arrays with commands that execute the full suite, coverage-only suite, and hybrid-selected suite respectively. The example currently repeats the same command intentionally as a safe format example; **it is not a valid comparative experiment until the commands are replaced.**

Run: `python -m selector.ci_benchmark --commands data/benchmark_commands.local.json --repeats 5 --out results/real_ci_benchmark.json`

Run all approaches on the same runner class and commit, with equivalent dependency/cache setup. Alternate execution order or randomise order to reduce warm-cache bias. Record runner image, CPU/memory, commit, cache state, test data snapshot, and repeat count. If tests are flaky, investigate and rerun under a documented policy rather than dropping inconvenient runs.

### Critical defect detection metric
Timing alone does not prove preservation of critical defect detection. Create a labelled validation set from historical incidents or seeded defects. For each critical defect, record the known detecting test IDs and whether the selected suite includes at least one validated detector. Report recall as `critical defects detected by selected suite / critical defects in validation set`. Include false omissions and unknown mappings. Do not use the fixture oracle as production truth.

## C. Stakeholder usability walkthrough
Invite at least one QA automation engineer and one release engineer. In a 15–20 minute walkthrough:
1. Give them a real (or approved anonymised) code diff and ask them to run the recommendation without coaching.
2. Ask them to explain why the top tests were selected and identify any risky omission.
3. Ask whether the output can fit the existing pipeline and what fallback they expect for low-confidence data.
4. Capture task completion, rationale clarity (1–5), actionability (1–5), omissions, requested changes, and retest evidence in `stakeholder_validation_template.md`.
5. Record role and date, not personal details unless consented. Obtain sign-off only if the reviewer actually gives it. Until completed, mark stakeholder validation **pending**.

## D. Durable event state and restart recovery
The SQLite-backed `DurableEventProcessor` uses transactions, unique event IDs, ordered sequence commits, persistent pending events, and an audit table for rejected/conflicting messages. Run:

`python -m unittest discover -s tests -v`

`python -m selector.cli durable-events --events data/sample_events.json --db results/events.sqlite3`

Restart recovery is tested by constructing a second processor against the same SQLite database in `tests/test_durable_events.py`. This validates local single-writer restart recovery, not multi-region durability. Before production: use a managed database or durable queue, backup/restore drills, retention controls, metrics/alerts, access control, schema migration, and concurrent-writer testing. Keep database files outside ephemeral containers or on persistent volumes.

## E. Acceptance gates
- [ ] Real repository diff and actual CI exports processed.
- [ ] Full / coverage-only / hybrid commands measured on equivalent runners (minimum 5 successful repeats recommended).
- [ ] Critical defect recall calculated against labelled real/seeded defects; false omissions reviewed.
- [ ] QA and release stakeholder forms completed with actual feedback and retest evidence.
- [x] SQLite persistence and restart recovery implemented and unit-tested locally.
- [ ] Production storage, monitoring, backups, permissions, load/concurrency tests, and rollback tested in target environment.

Do not describe all items as complete until the unchecked external gates have evidence attached.
