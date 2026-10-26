"""Repeated in-process local CI-like benchmark across all fixture diffs.

Measures wall-clock time for actual Python assertions plus configurable synthetic
runtime delays. It is local synthetic-suite evidence, not company CI performance.
"""
import argparse, json, platform, statistics, sys, time
from datetime import datetime, timezone
from pathlib import Path
from .selector import load_json, select_full, select_coverage_only, select_hybrid
from .demo_ci_runner import CHECKS

STRATEGIES=('full_regression','coverage_only','hybrid_selector')

def execute(strategy, changed, data, scale):
    catalog=load_json(data/'test_catalog.json')
    if strategy=='full_regression': selection=select_full(catalog)
    elif strategy=='coverage_only': selection=select_coverage_only(changed,catalog)
    else: selection=select_hybrid(changed,catalog,load_json(data/'test_history.json'),
                                  load_json(data/'defect_associations.json'),load_json(data/'dependencies.json'))
    started=time.perf_counter(); passed=[]
    for test in catalog:
        tid=test['test_id']
        if tid in selection['selected_tests']:
            CHECKS[tid](); passed.append(tid); time.sleep(float(test['runtime_seconds'])*scale)
    elapsed=time.perf_counter()-started
    defects=load_json(data/'defect_associations.json')
    in_scope=[x for x in defects if x.get('severity')=='critical' and set(x.get('affected_files',[])) & set(changed)]
    detected=[x['defect_id'] for x in in_scope if set(x.get('test_ids',[])) & set(passed)]
    recall=len(detected)/len(in_scope) if in_scope else 1.0
    return {'selected_tests':selection['selected_tests'],'tests_passed':passed,
            'selected_count':len(passed),'total_tests':len(catalog),'elapsed_wall_seconds':round(elapsed,6),
            'critical_defects_in_scope':[x['defect_id'] for x in in_scope],
            'critical_defects_detected':detected,'critical_defect_recall':round(recall,4),
            'selection_reason':selection.get('reason','full suite')}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',default='data'); p.add_argument('--repeats',type=int,default=5)
    p.add_argument('--runtime-scale',type=float,default=0.003); p.add_argument('--out',default='results/local_ci_validation.json')
    args=p.parse_args()
    if args.repeats<1: p.error('--repeats must be >= 1')
    root=Path(__file__).resolve().parents[1]; data=Path(args.data)
    if not data.is_absolute(): data=root/data
    diffs=json.loads((data/'experiment_diffs.json').read_text(encoding='utf-8')); results=[]
    for case in diffs:
        per={}
        for strategy in STRATEGIES:
            durations=[]; outputs=[]
            for _ in range(args.repeats):
                start=time.perf_counter(); out=execute(strategy,case['changed_files'],data,args.runtime_scale)
                durations.append(round(time.perf_counter()-start,6)); outputs.append(out)
            per[strategy]={'repeat_count':args.repeats,'wall_clock_seconds_each_run':durations,
                'median_wall_clock_seconds':round(statistics.median(durations),6),
                'selected_tests':outputs[-1]['selected_tests'],'critical_defect_recall':outputs[-1]['critical_defect_recall'],
                'critical_defects_in_scope':outputs[-1]['critical_defects_in_scope'],
                'critical_defects_detected':outputs[-1]['critical_defects_detected'],
                'all_runs_passed':all(len(x['tests_passed'])==x['selected_count'] for x in outputs)}
        baseline=per['full_regression']['median_wall_clock_seconds']
        for row in per.values():
            row['time_saved_seconds_vs_full']=round(baseline-row['median_wall_clock_seconds'],6)
            row['time_saved_percent_vs_full']=round((baseline-row['median_wall_clock_seconds'])/baseline*100,2) if baseline else 0.0
        results.append({'case_id':case['case_id'],'description':case['description'],'changed_files':case['changed_files'],'approaches':per})
    aggregate={}
    for strategy in STRATEGIES:
        rows=[x['approaches'][strategy] for x in results]
        aggregate[strategy]={'mean_median_wall_clock_seconds':round(statistics.mean(x['median_wall_clock_seconds'] for x in rows),6),
            'mean_time_saved_percent':round(statistics.mean(x['time_saved_percent_vs_full'] for x in rows),2),
            'mean_critical_defect_recall':round(statistics.mean(x['critical_defect_recall'] for x in rows),4),
            'all_selected_tests_passed':all(x['all_runs_passed'] for x in rows)}
    report={'created_utc':datetime.now(timezone.utc).isoformat(),
        'measurement_scope':'actual local wall-clock timings for repeated execution of real Python assertions with simulated runtime delays over a synthetic suite; not company CI or production application timings',
        'environment':{'python':sys.version,'platform':platform.platform(),'repeats_per_strategy_per_case':args.repeats,'runtime_scale':args.runtime_scale},
        'case_count':len(results),'strategies':list(STRATEGIES),'cases':results,'aggregate':aggregate,
        'interpretation':'This is a reproducible local end-to-end comparison of distinct strategy-selected suites. Replace fixture tests/data with the target repository before making company CI claims.'}
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'aggregate':aggregate,'output':str(out),'case_count':len(results)},indent=2))
if __name__=='__main__': main()
