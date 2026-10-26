# How to Close the Three External Validation Gaps

This guide distinguishes implementation evidence from evidence that must come from a real reviewer, real CI run, or target deployment. Do not mark a gate complete until its evidence is saved in this repository.

## 1. Real QA/release stakeholder feedback

### Required activity
- Recruit one QA automation engineer and one release engineer (two people is preferred because their risks differ).
- Use a real code change or an approved anonymised diff from the target repository.
- Ask each reviewer to run the recommendation without step-by-step coaching.
- Ask them to explain why tests were selected, identify any risky omission, and state how they would use the result in the existing release pipeline.
- Record scores, concerns, requested changes, and retest outcome in `templates/stakeholder_feedback_record.md`.
- Save the actual anonymised record under `reports/external_evidence/` and update the acceptance checklist.

### Completion rule
This gate is complete only when the walkthrough actually happened and reviewer responses are recorded. A blank form, a simulated persona, or AI-generated feedback is not stakeholder evidence.

## 2. Real repository and CI timing measurements

### Prepare inputs
Use a clean checkout of the target repository and a real base/head commit pair. Export actual test IDs, test durations, test-to-file coverage, recent failure history, and confirmed defect-to-test links. Remove secrets and anonymise customer data. Record export date and commit SHA.

### Configure commands
Copy `templates/benchmark_commands.template.json` to a private local file. Replace every placeholder with the exact command used to execute each strategy in the target CI. Each strategy must actually execute its corresponding suite; do not use the selector's recommendation command as a substitute for running tests. Do not leave identical commands for the three strategies.

### Run fairly
- Run full regression, coverage-only, and hybrid on the same runner class and commit.
- Use equivalent dependency setup and cache policy; alternate execution order to reduce warm-cache bias.
- Run at least five successful repeats per strategy; keep failed/flaky run logs and explain exclusions.
- Save median and individual durations, runner image/hardware, commit SHA, cache state, and test-data snapshot.
- Calculate time saved as `(full median - strategy median) / full median * 100`.
- Separately measure critical-defect recall against a labelled set of known or seeded critical defects: `defects detected by selected suite / defects in validation set`. Timing alone does not establish recall.

### Completion rule
The gate is complete only when real CI logs/results and real repository metadata are attached. Local demo measurements and synthetic fixture timings must remain labelled as such.

## 3. Production deployment validation

Use a staging environment before production. Start in **shadow mode**: generate recommendations but continue running the full regression suite; compare the selector's picks with tests that actually detected failures. Do not initially skip tests based on recommendations.

### Staging test sequence
1. Verify authentication/authorisation, secret handling, least-privilege access, and retention policy.
2. Verify SQLite path is on persistent storage; restart the process and confirm committed/pending event state is recovered correctly.
3. Test duplicate, delayed, out-of-order, malformed, stale, and conflicting events; confirm no duplicate state application and audit rejected events.
4. Test concurrent writers, database locking, backup/restore, disk-full behaviour, schema migration, and recovery from corrupted/unavailable storage.
5. Test missing coverage/history, unknown changed files, empty diffs, dependency cycles, critical-defect links, and selector errors. Unknown or low-confidence cases must fall back to full regression.
6. Compare selected tests with the full suite over representative changes. Review every missed critical defect before enabling any test skipping.
7. Add metrics/alerts for selection duration, selected test count, fallback rate, unknown mappings, event lag, rejected events, and critical misses.
8. Verify kill switch and rollback: disable selection and restore full regression without requiring a code redeploy.
9. Obtain an actual release/SRE sign-off and attach logs, configuration version, test report, and rollback drill evidence.

### Safe rollout gates
- Phase 0: offline evaluation only.
- Phase 1: shadow mode; full suite still runs.
- Phase 2: limited canary on low-risk changes with full-suite fallback and human approval.
- Phase 3: expand only after agreed recall and reliability thresholds are met over a documented observation period.

Do not skip full regression on flash-sale/high-risk releases until the organisation explicitly approves thresholds and rollback criteria.

### Completion rule
Production validation is complete only after the checks run in the target staging/production-like environment and evidence is attached. A checklist by itself is a plan, not proof of deployment.

## Evidence index
Store evidence with non-sensitive identifiers in `reports/external_evidence/`. Never commit credentials, customer data, raw proprietary source, or unredacted CI logs. Reference the evidence file, commit, date, and reviewer role in the final report.
