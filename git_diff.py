"""Optional adapter to extract changed paths from a Git diff."""
import subprocess

def changed_paths(base_ref="HEAD~1", head_ref="HEAD", repo="."):
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base_ref}...{head_ref}"],
        cwd=repo, check=True, capture_output=True, text=True
    )
    return sorted({line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()})

def write_diff_json(paths, destination):
    import json
    from pathlib import Path
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"changed_files": paths}, indent=2), encoding="utf-8")
