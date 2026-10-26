"""Reproducible experiment comparing baseline and selectors."""
from .selector import select_full, select_coverage_only, select_hybrid, load_json

def run_experiment(data_dir):
    from pathlib import Path
    d = Path(data_dir)
    catalog = load_json(d / "test_catalog.json")
    history = load_json(d / "test_history.json")
    defects = load_json(d / "defect_associations.json")
    deps = load_json(d / "dependencies.json")
    diffs = load_json(d / "experiment_diffs.json")
    results = []
    all_critical = {x["defect_id"] for x in defects if x["severity"] == "critical"}
    for case in diffs:
        changed = case["changed_files"]
        full = select_full(catalog)
        coverage = select_coverage_only(changed, catalog)
        hybrid = select_hybrid(changed, catalog, history, defects, deps)
        # Fixture oracle: defect considered detected if any associated test is selected.
        critical_for_change = {x["defect_id"] for x in defects
            if x["severity"] == "critical" and set(x.get("affected_files", [])) & set(changed)}
        def detected(selection):
            ids = set(selection["selected_tests"])
            return sorted(x["defect_id"] for x in defects
                if x["severity"] == "critical" and x["defect_id"] in critical_for_change
                and ids.intersection(x.get("test_ids", [])))
        full_detected = detected(full)
        cov_detected = detected(coverage)
        hyb_detected = detected(hybrid)
        base_time = full["estimated_seconds"]
        def pack(name, sel, detected_ids):
            return {"approach": name, "selected_tests": sel["selected_tests"],
                    "selected_count": sel["selected_count"], "estimated_seconds": sel["estimated_seconds"],
                    "time_saved_seconds": round(base_time-sel["estimated_seconds"], 2),
                    "time_saved_percent": round(100*(base_time-sel["estimated_seconds"])/base_time, 2) if base_time else 0,
                    "critical_defects_detected": detected_ids,
                    "critical_detection_recall": round(len(detected_ids)/len(critical_for_change), 4) if critical_for_change else 1.0}
        results.append({"case_id": case["case_id"], "description": case["description"],
            "changed_files": changed, "critical_defects_in_scope": sorted(critical_for_change),
            "full_regression": pack("full_regression", full, full_detected),
            "coverage_only": pack("coverage_only", coverage, cov_detected),
            "hybrid_selector": pack("hybrid_selector", hybrid, hyb_detected)})
    # Aggregate average time saving relative to full regression and mean critical recall.
    aggregate = {}
    for name in ("full_regression", "coverage_only", "hybrid_selector"):
        vals = [r[name] for r in results]
        aggregate[name] = {
            "mean_selected_tests": round(sum(x["selected_count"] for x in vals)/len(vals), 2),
            "mean_estimated_seconds": round(sum(x["estimated_seconds"] for x in vals)/len(vals), 2),
            "mean_time_saved_percent": round(sum(x["time_saved_percent"] for x in vals)/len(vals), 2),
            "mean_critical_detection_recall": round(sum(x["critical_detection_recall"] for x in vals)/len(vals), 4)
        }
    return {"experiment_type": "deterministic synthetic fixture experiment",
            "runtime_seconds_are": "estimated fixture durations, not live CI measurements",
            "cases": results, "aggregate": aggregate,
            "interpretation": "Use real CI data before production decisions; the fixture oracle is not proof of real-world detection."}
