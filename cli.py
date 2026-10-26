import argparse, json
from pathlib import Path
from .selector import load_json, select_hybrid, select_coverage_only, select_full
from .experiment import run_experiment
from .events import EventProcessor
from .durable_events import DurableEventProcessor

def main():
    p = argparse.ArgumentParser(description="Change-aware regression test selector")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("recommend")
    r.add_argument("--diff", required=True)
    r.add_argument("--data", default="data")
    e = sub.add_parser("experiment")
    e.add_argument("--data", default="data")
    e.add_argument("--out", default="results/experiment_results.json")
    v = sub.add_parser("events")
    v.add_argument("--events", required=True)
    dv = sub.add_parser("durable-events")
    dv.add_argument("--events", required=True)
    dv.add_argument("--db", default="results/events.sqlite3")
    args = p.parse_args()
    if args.command == "recommend":
        d = Path(args.data)
        changed = load_json(args.diff)["changed_files"]
        out = select_hybrid(changed, load_json(d/"test_catalog.json"),
            load_json(d/"test_history.json"), load_json(d/"defect_associations.json"),
            load_json(d/"dependencies.json"))
        print(json.dumps(out, indent=2))
    elif args.command == "experiment":
        out = run_experiment(args.data)
        dest = Path(args.out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out["aggregate"], indent=2))
        print(f"Saved: {dest}")
    elif args.command == "events":
        processor = EventProcessor()
        for event in load_json(args.events):
            print(json.dumps({"input": event, "result": processor.ingest(event)}))
        print(json.dumps({"committed_state": processor.state, "pending": processor.pending,
                          "rejected": processor.rejected}, indent=2))
    elif args.command == "durable-events":
        processor = DurableEventProcessor(args.db)
        for event in load_json(args.events):
            print(json.dumps({"input": event, "result": processor.ingest(event)}))
        print(json.dumps(processor.snapshot(), indent=2))

if __name__ == "__main__":
    main()
