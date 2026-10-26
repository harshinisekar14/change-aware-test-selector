# Final Project Report: Change-Aware Test Selector for Flash-Sale E-Commerce

## 1. Executive summary
This project implements a runnable change-aware regression test selector for an e-commerce flash-sale workflow. It accepts changed source files and uses a test catalogue, historical execution outcomes, file dependency relationships, and defect-to-test associations to recommend a smaller regression suite. It compares a full-regression baseline, a coverage-only strategy, and a hybrid risk-ranked strategy. A separate event processor demonstrates recovery from delayed/out-of-order, duplicated, stale, conflicting, and malformed events.

**Completion statement:** All planned prototype components, fixture datasets, command-line flows, automated tests, experiment output, report, and deployment checklist are included in this package. The prototype is complete as a reproducible academic/demo implementation. It is not yet validated against a live company repository or production CI; fixture runtimes and outcomes are synthetic and must not be represented as real-world measurements.

## 2. Scenario definition
During flash-sale releases, release windows are short and uptime targets are strict. Running every automated test can increase pipeline duration, but selecting too few tests may miss payment, inventory, pricing, order, or webhook regressions. The operational goal is to recommend the smallest defensible suite for a particular change while keeping a full-suite fallback and making each selection explainable.

### Scope
- Input: list of changed file paths, test metadata, coverage mapping, test histories, dependencies, and defect associations.
- Output: selected test IDs, scores, selection rationale, count, and estimated execution time.
- Non-goals: replacing CI orchestration, generating tests, proving absence of defects, or autonomously deploying a release.

## 3. Requirements and completion mapping
| Requirement | Implementation evidence |
|---|---|
| Scenario and baseline | Full regression strategy in `selector/selector.py` |
| At least two approaches | Full regression, coverage-only, and hybrid weighted selector |
| Diffs, histories, coverage, defects | `data/` fixtures and selector inputs |
| End-to-end working prototype | CLI commands in `selector/cli.py` |
| Three or more edge/failure cases | `tests/test_events.py` and `tests/test_selector.py` |
| Delayed/duplicate/out-of-order recovery | Sequence buffer, event-ID deduplication, stale/conflict handling in `selector/events.py` |
| Measurable experiment | Five repeatable change scenarios in `data/experiment_diffs.json` |
| Performance results and error analysis | `results/experiment_results.json` and section 8 |
| Usability walkthrough | Section 9 |
| Ethics note | Section 10 |
| Deployment checklist | Section 11 |

## 4. Technical approaches compared
### Approach A — Full regression (baseline)
Run every test on every change. It has the strongest available suite coverage but costs the sum of all test runtimes. It is simple and remains the safe fallback for unknown diffs, high-risk releases, or selector/data outages.

### Approach B — Coverage-only selection
Select tests whose coverage maps intersect changed files. It is fast and easy to explain, but it ignores historical flakiness/failure signals, dependencies, and tests associated with known critical defects. Indirect dependencies and defects outside direct coverage can be missed.

### Approach C — Hybrid risk-ranked selection (chosen)
The selected design scores tests using direct coverage, dependency relevance, historical failure rate, and linked defects, then applies a safety floor:
- all tests directly covering changed files are retained;
- tests associated with critical defects whose affected files overlap the change/dependency neighborhood are retained;
- an empty diff causes full-suite fallback.

The hybrid is the best fit for the stated need because it is transparent, data-driven, and conservative about critical paths while still allowing a smaller suite. Scores are explicit and tunable rather than a black-box model. The prototype intentionally avoids machine-learning complexity because the available sample is small and labels are synthetic.

## 5. System design and data flow
1. CI or a developer supplies a changed-file list.
2. The selector loads the test catalogue, coverage map, test histories, dependency edges, and defect associations.
3. The dependency neighborhood is calculated using graph traversal.
4. Each test receives a score from normalized weighted signals.
5. Direct coverage and critical-defect safety rules are applied.
6. The CLI returns selected tests, scores, counts, and estimated runtime.
7. The experiment harness evaluates all approaches across five change scenarios.
8. The event processor demonstrates sequence-aware ingestion of pipeline events.

### Scoring formula
`score = 0.45 × direct_coverage + 0.20 × dependency_relevance + 0.15 × historical_failure_rate + 0.20 × defect_score`

`defect_score = min(1, 0.65 × critical_link_count + 0.15 × all_link_count)`

Direct and dependency signals are Boolean; historical failure rate is failures/runs; defect score is capped at 1.0. The threshold defaults to 0.20. The safety floor overrides the threshold when required. This scoring is intentionally interpretable and can be calibrated with production data.

## 6. Baseline, target, and measured results
The packaged experiment uses eight tests with fixture durations totaling 117 seconds and five representative diffs. The experiment output is reproducible by running `python -m selector.cli experiment --data data --out results/experiment_results.json`.

**Important measurement qualification:** these are deterministic synthetic estimates, not timings captured from a live CI pipeline. The experiment computes critical-defect detection from the supplied defect associations and selected test IDs; that is a fixture oracle, not proof of real-world recall.

- **Baseline:** full regression, 100% of fixture suite run, 0% time saved by definition.
- **Target:** reduce estimated regression runtime by at least 25% while preserving all in-scope critical-defect associations in the fixture scenarios.
- **Measured result:** see `results/experiment_results.json` for the generated aggregate values and per-case details. Do not replace or manually reinterpret those values without rerunning the experiment.
- **Acceptance rule:** hybrid mean time saved should be positive, and critical-defect recall should be compared with full regression on each scenario. If any in-scope critical defect loses coverage, the selector must fail closed to a wider suite or full regression.

## 7. Error analysis and edge/failure cases
1. **Empty diff:** treated as unknown scope; full suite is selected rather than returning an empty suite.
2. **Critical defect association:** linked tests are retained if the defect's affected files intersect the changed dependency neighborhood.
3. **Delayed/out-of-order event:** future sequence is buffered; when missing earlier sequence arrives, contiguous pending events drain in order.
4. **Duplicate event ID:** ignored; committed state does not grow twice.
5. **Stale event:** an event with sequence lower than the next expected sequence is ignored.
6. **Conflicting event sequence:** first pending event remains; second event with same sequence but different ID is recorded as conflict rather than overwriting state.
7. **Malformed envelope:** rejected and recorded without changing committed state.
8. **Missing history:** score uses zero historical failure rate; production deployment should flag low-confidence metadata and consider a conservative fallback.
9. **Incomplete coverage map:** could create false negatives; use coverage freshness checks and fail closed if coverage is missing/stale for changed critical files.
10. **Flaky tests:** historical failures can raise ranking but failure rate does not distinguish product defects from flaky infrastructure. Track flakiness separately in production.

## 8. Performance metrics and interpretation
Primary metric: pipeline time saved relative to full regression.

`time_saved_seconds = full_suite_estimated_seconds - selected_suite_estimated_seconds`

`time_saved_percent = 100 × time_saved_seconds / full_suite_estimated_seconds`

Critical-defect recall is the fraction of in-scope critical defects linked to at least one selected test. The full regression approach is the reference. Per-case data reports selected test count, estimated seconds, time saved, detected critical defects, and recall for each strategy.

The selected strategy should be judged on a two-dimensional trade-off:
- **Efficiency:** mean estimated runtime reduction and selected test count.
- **Safety:** critical-defect recall, with no unexplained loss against the full-suite reference.

If real measurements show a recall loss, lower the threshold, improve associations/coverage, add a safety rule, or use full regression for the affected change category. Do not optimize time saved in isolation.

## 9. Usability walkthrough / stakeholder validation
### Walkthrough
1. Run `python -m selector.cli recommend --diff data/sample_diff.json --data data`.
2. Review `selected_tests`, each test's score, direct coverage, dependency relevance, history failure rate, and critical links.
3. Run `python -m selector.cli experiment --data data --out results/experiment_results.json`.
4. Compare the three approaches in the JSON output.
5. Run `python -m unittest discover -s tests -v`.
6. Run `python -m selector.cli events --events data/sample_events.json` and confirm event sequence 1–4 appears once and in order.

### Validation status
The package includes a developer-facing walkthrough and automated acceptance tests. No real user/stakeholder interview was conducted for this generated prototype. For a genuine validation sign-off, ask at least one QA engineer and one release engineer to complete the walkthrough, record task completion time, perceived explanation quality, missing workflow steps, and whether the selected tests are actionable. Store date, role (not personal data), feedback, and resulting changes in `reports/stakeholder_validation_template.md`.

## 10. Ethics, security, and operational safeguards
- False negatives can cause production incidents; selection must be advisory until validated.
- Do not use selection as the only release gate for payment, inventory, pricing, or other critical paths without explicit risk approval.
- Protect test histories and defect records as internal engineering data; avoid customer identifiers and production payment data in fixtures.
- Explain why tests were selected and log the selector version, input diff hash, data freshness, scores, and override decisions.
- Monitor critical-defect escapes, test selection rate, runtime saved, metadata coverage, and fallback frequency.
- Keep human override and full-regression options.
- Avoid treating historical failure frequency as a direct proxy for code quality; flakiness and infrastructure failures must be separated.

## 11. Deployment checklist
- [ ] Replace synthetic test catalogue with CI's real test inventory and stable IDs.
- [ ] Export accurate coverage maps and verify freshness for each build.
- [ ] Import historical test outcomes and separate product failures from infrastructure flakes.
- [ ] Link confirmed defects to tests and affected files; review critical severity with QA.
- [ ] Calibrate weights/threshold on held-out historical changes, not the same cases used to tune them.
- [ ] Run in shadow mode for at least one release cycle; compare recommendation with actual full-suite outcomes.
- [ ] Define fail-closed conditions for missing diff, stale coverage, unknown tests, or data-source failure.
- [ ] Add CI adapter and persist selection audit logs.
- [ ] Add transactional durable event storage, retry policy, dead-letter handling, and alerting.
- [ ] Set target metrics and alert thresholds with QA/SRE.
- [ ] Require human approval for high-risk flash-sale releases.
- [ ] Document rollback: disable selector and restore full regression.
- [ ] Review access controls, retention, and data minimization.
- [ ] Obtain QA, release engineering, and SRE sign-off before enforcement.

## 12. Limitations and future work
The current prototype uses JSON fixtures and estimated test runtimes, not live CI telemetry. Dependency edges are manually curated. Defect associations may be incomplete or biased toward previously discovered bugs. Event state is in-memory and resets on process restart; a production version needs durable transactional persistence. Future improvements include adapters for Git diff and CI APIs, coverage import, calibrated weights, per-service risk policies, parallel runtime estimation, and drift monitoring.

## 13. Final conclusion
The deliverable is a complete, runnable prototype and experiment package. It demonstrates the requested selection logic, baseline comparisons, edge-case recovery, measurable fixture experiment, report, ethics considerations, and deployment readiness checklist. It is **100% complete as the defined prototype package**, while production readiness remains conditional on replacing synthetic inputs, running shadow validation, and obtaining stakeholder sign-off.

## Additional durability and validation work
A SQLite-backed event processor was added to persist inbox records, pending out-of-order events, committed events, sequence checkpoints, and rejected/conflicting event audit records. Transactions protect sequence advancement and committed-state changes. Automated restart tests demonstrate that a buffered event survives constructing a new processor against the same database and is committed exactly once after its predecessor arrives. The local test suite now contains 18 tests and passes.

A real-command benchmark harness was added to measure wall-clock duration for full regression, coverage-only, and hybrid commands. It requires distinct commands from the target repository and records successful run times; it does not infer defect recall. A real repository/CI/stakeholder runbook defines how to collect actual diffs, coverage, test histories, defect labels, repeated timings, and QA/release-engineer feedback.

**Validation status:** SQLite persistence/restart recovery is implemented and locally tested. Actual company CI timing, critical-defect recall against a labelled real validation set, stakeholder sign-off, and production environment readiness remain unverified because no company repository, CI runner/data, or real reviewers were provided. These are external validation gates, not evidence that may ethically be fabricated.


## Final local validation (26 October 2026)

The final package was re-tested after adding a full-suite fallback for unmapped changed files. All 18 unit tests passed. A local CI-like benchmark ran five fixture change scenarios, three strategies, and five repetitions per strategy using distinct selection logic and real Python assertions with a documented synthetic runtime scale. The mean of case median wall-clock times was 0.352479 seconds for full regression, 0.095360 seconds for coverage-only (72.94% saved), and 0.138829 seconds for hybrid selection (60.62% saved). Critical-defect recall was 100% against the synthetic fixture oracle. These are local fixture measurements, not real company CI timings.

A local staging-style validation script passed 9/9 checks for safety fallback, out-of-order buffering, restart recovery, ordered commit, duplicate idempotency, conflict handling, malformed event auditing, and SQLite backup/restore. The assistant heuristic usability walkthrough is documented separately and is not represented as a human stakeholder interview.
