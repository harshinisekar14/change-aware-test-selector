"""Local staging-style smoke checks for safety fallback and durable events.

This is a controlled local validation simulation, not a deployment to an external
company staging/production environment.
"""
import json, shutil, sqlite3, tempfile
from pathlib import Path
from .selector import load_json, select_hybrid, select_coverage_only
from .durable_events import DurableEventProcessor

def main():
    root=Path(__file__).resolve().parents[1]; data=root/'data'
    catalog=load_json(data/'test_catalog.json'); history=load_json(data/'test_history.json')
    defects=load_json(data/'defect_associations.json'); deps=load_json(data/'dependencies.json')
    checks=[]
    def record(name, condition, detail):
        checks.append({'check':name,'status':'PASS' if condition else 'FAIL','detail':detail})
        if not condition: raise AssertionError(f'{name}: {detail}')
    unknown=select_hybrid(['new_unmapped_file.py'],catalog,history,defects,deps)
    record('unknown mapping full-suite fallback',unknown['selected_count']==len(catalog),unknown['reason'])
    cov=select_coverage_only(['new_unmapped_file.py'],catalog)
    record('coverage-only empty-match fallback',cov['selected_count']==len(catalog),cov['reason'])
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/'events.sqlite3'; p=DurableEventProcessor(db)
        e2={'event_id':'stage-e2','sequence':2,'event_type':'inventory','payload':{'stock':4}}
        e1={'event_id':'stage-e1','sequence':1,'event_type':'inventory','payload':{'stock':5}}
        record('out-of-order event buffered',p.ingest(e2)['status']=='buffered','sequence 2 waits for sequence 1')
        p=DurableEventProcessor(db)
        record('pending event survives restart',2 in p.snapshot()['pending'],'reopened processor recovered sequence 2')
        p.ingest(e1); snap=p.snapshot()
        record('ordered recovery commits 1 then 2',[x['sequence'] for x in snap['state']]==[1,2],'committed order preserved')
        record('duplicate event idempotency',p.ingest(e1)['status']=='duplicate',f"committed_count={len(p.snapshot()['state'])}")
        conflict=p.ingest({'event_id':'stage-conflict','sequence':3,'event_type':'other'})
        # Sequence 3 is next and is valid, so it commits; test a collision using a buffered seq 5 instead.
        p.ingest({'event_id':'stage-e5a','sequence':5,'event_type':'sale'})
        conflict=p.ingest({'event_id':'stage-e5b','sequence':5,'event_type':'sale'})
        record('conflicting sequence rejected',conflict['status']=='conflict',str(conflict))
        bad=p.ingest({'event_id':'bad-stage','sequence':0})
        record('malformed envelope audited',bad['status']=='rejected',str(bad))
        # Use SQLite's backup API to test a consistent database backup/restore.
        backup=Path(tmp)/'backup.sqlite3'
        with sqlite3.connect(db) as src, sqlite3.connect(backup) as dst: src.backup(dst)
        restored=DurableEventProcessor(backup).snapshot()
        record('SQLite backup restore retains committed state',len(restored['state'])==3,
               f"restored_committed={len(restored['state'])}")
    report={'scope':'local staging-style simulation; not external production validation',
            'checks_passed':sum(x['status']=='PASS' for x in checks),'checks_total':len(checks),'checks':checks}
    out=root/'results'/'local_staging_validation.json'; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
