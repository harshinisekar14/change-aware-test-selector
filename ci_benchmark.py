"""Measure real wall-clock time for user-supplied CI commands.

Input JSON maps approach names to argv arrays. Commands are executed without a
shell. The script measures actual local/CI wall-clock elapsed time; it does not
infer critical-defect recall, which must be recorded from a labelled test run.
"""
import argparse, json, statistics, subprocess, time
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--commands', required=True, help='JSON: approach -> argv list')
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--out', default='results/real_ci_benchmark.json')
    args=p.parse_args()
    if args.repeats < 1: p.error('--repeats must be >= 1')
    commands=json.loads(Path(args.commands).read_text(encoding='utf-8'))
    required={'full_regression','coverage_only','hybrid_selector'}
    if set(commands) < required: p.error(f'commands JSON must include {sorted(required)}')
    results={}
    for name in ('full_regression','coverage_only','hybrid_selector'):
        argv=commands[name]
        if not isinstance(argv,list) or not argv or not all(isinstance(x,str) for x in argv):
            p.error(f'{name} must be a non-empty argv array of strings')
        durations=[]; codes=[]
        for run in range(args.repeats):
            start=time.perf_counter()
            proc=subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            elapsed=round(time.perf_counter()-start,3)
            durations.append(elapsed); codes.append(proc.returncode)
            if proc.returncode:
                print(proc.stdout[-4000:])
                raise SystemExit(f'{name} run {run+1} failed with exit code {proc.returncode}; no benchmark claimed')
        results[name]={'command':argv,'runs_seconds':durations,'median_seconds':round(statistics.median(durations),3),'return_codes':codes}
    base=results['full_regression']['median_seconds']
    for name in results:
        t=results[name]['median_seconds']
        results[name]['time_saved_seconds_vs_full']=round(base-t,3)
        results[name]['time_saved_percent_vs_full']=round((base-t)/base*100,2) if base else 0
    output={'measurement_type':'wall-clock command measurements','repeats':args.repeats,
            'machine_and_environment':'Record CI runner image, hardware class, cache state, and commit in accompanying notes.',
            'critical_defect_recall':'NOT measured by this timing harness; calculate from labelled defect/test cases separately.',
            'results':results}
    dest=Path(args.out); dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps(output,indent=2)); print(f'Saved {dest}')
if __name__=='__main__': main()
