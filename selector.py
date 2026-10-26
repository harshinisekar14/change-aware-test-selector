"""Transparent change-aware regression test selection."""
from collections import defaultdict
from pathlib import Path
import json

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def dependency_neighborhood(changed_files, dependencies):
    """Return changed files plus recursively reachable dependency targets."""
    graph = defaultdict(set)
    for edge in dependencies:
        graph[edge["source"]].add(edge["target"])
    seen = set(changed_files)
    stack = list(changed_files)
    while stack:
        node = stack.pop()
        for nxt in graph.get(node, ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen

def score_tests(changed_files, catalog, history, defects, dependencies):
    neighborhood = dependency_neighborhood(changed_files, dependencies)
    history_by_id = {x["test_id"]: x for x in history}
    defects_by_test = defaultdict(list)
    for defect in defects:
        for tid in defect.get("test_ids", []):
            defects_by_test[tid].append(defect)

    scored = []
    for test in catalog:
        tid = test["test_id"]
        covered = set(test.get("covers", []))
        direct = bool(covered & set(changed_files))
        related = bool(covered & neighborhood)
        h = history_by_id.get(tid, {"runs": 0, "failures": 0})
        fail_rate = (h["failures"] / h["runs"]) if h.get("runs", 0) else 0.0
        linked = defects_by_test.get(tid, [])
        critical_links = [d for d in linked if d.get("severity") == "critical"]
        defect_score = min(1.0, 0.65 * len(critical_links) + 0.15 * len(linked))
        # Transparent weighted score, normalized to [0,1].
        score = 0.45 * float(direct) + 0.20 * float(related) + 0.15 * fail_rate + 0.20 * defect_score
        scored.append({
            "test_id": tid, "runtime_seconds": float(test["runtime_seconds"]),
            "direct_coverage": direct, "dependency_relevant": related,
            "historical_failure_rate": round(fail_rate, 4),
            "critical_defect_links": len(critical_links),
            "defect_links": len(linked), "score": round(score, 4),
            "critical": bool(test.get("critical", False)),
        })
    return sorted(scored, key=lambda x: (-x["score"], x["runtime_seconds"], x["test_id"]))

def select_hybrid(changed_files, catalog, history, defects, dependencies, threshold=0.20):
    """Hybrid ranked selection with explicit safety floor."""
    scored = score_tests(changed_files, catalog, history, defects, dependencies)
    selected = {x["test_id"] for x in scored if x["score"] >= threshold}
    changed = set(changed_files)
    neighborhood = dependency_neighborhood(changed_files, dependencies)
    known_coverage = set().union(*(set(t.get("covers", [])) for t in catalog)) if catalog else set()
    # Safety fallback: unknown changes with no mapped test coverage cannot safely narrow.
    if changed and not (neighborhood & known_coverage):
        return {"selected_tests": [t["test_id"] for t in catalog],
                "scores": scored, "total_tests": len(catalog),
                "selected_count": len(catalog),
                "estimated_seconds": round(sum(float(t["runtime_seconds"]) for t in catalog), 2),
                "reason": "safety fallback: changed files have no mapped coverage; run full regression"}
    # Safety floor 1: all tests directly covering changed files.
    for test in catalog:
        if set(test.get("covers", [])) & changed:
            selected.add(test["test_id"])
    # Safety floor 2: tests linked to critical defects whose affected files overlap
    # changed files or their dependency neighborhood.
    neighborhood = dependency_neighborhood(changed_files, dependencies)
    for defect in defects:
        if defect.get("severity") == "critical" and set(defect.get("affected_files", [])) & neighborhood:
            selected.update(defect.get("test_ids", []))
    # Unknown/empty diffs are unsafe to narrow: return full suite.
    if not changed_files:
        selected = {t["test_id"] for t in catalog}
    ordered = [x["test_id"] for x in scored if x["test_id"] in selected]
    return {"selected_tests": ordered, "scores": scored,
            "total_tests": len(catalog), "selected_count": len(ordered),
            "estimated_seconds": round(sum(float(t["runtime_seconds"]) for t in catalog if t["test_id"] in selected), 2),
            "reason": "hybrid weighted ranking plus direct-coverage and critical-defect safety floors"}

def select_coverage_only(changed_files, catalog):
    changed = set(changed_files)
    fallback = False
    if not changed:
        chosen = list(catalog)
        fallback = True
    else:
        chosen = [t for t in catalog if set(t.get("covers", [])) & changed]
        # If coverage mapping cannot select any test, do not return an unsafe empty suite.
        if not chosen:
            chosen = list(catalog)
            fallback = True
    return {"selected_tests": [t["test_id"] for t in chosen],
            "selected_count": len(chosen), "total_tests": len(catalog),
            "estimated_seconds": round(sum(float(t["runtime_seconds"]) for t in chosen), 2),
            "reason": "safety fallback: no mapped coverage; run full regression" if fallback else "baseline coverage-only selection"}

def select_full(catalog):
    return {"selected_tests": [t["test_id"] for t in catalog],
            "selected_count": len(catalog), "total_tests": len(catalog),
            "estimated_seconds": round(sum(float(t["runtime_seconds"]) for t in catalog), 2),
            "reason": "run the full regression suite"}
