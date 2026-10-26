# Prototype Walkthrough — Reproducible Self-Test

**Type:** Developer self-test of the packaged demo, not independent stakeholder validation.

1. Recommendation command: `python -m selector.cli recommend --diff data/sample_diff.json --data data`
   - Expected: JSON output with selected test IDs, scores, counts, and estimated runtime.
2. Experiment command: `python -m selector.cli experiment --data data --out results/experiment_results.json`
   - Expected: five scenarios and three approaches per scenario.
3. Event recovery command: `python -m selector.cli events --events data/sample_events.json`
   - Expected: committed sequence order is 1, 2, 3, 4, with duplicate event ignored.
4. Test command: `python -m unittest discover -s tests -v`
   - Expected: all unit tests pass.

For real stakeholder validation, use `stakeholder_validation_template.md` and record actual feedback without inventing reviewer names or sign-off.
