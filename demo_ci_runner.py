"""Runnable synthetic CI test runner used to measure real local wall-clock time.

The assertions are real Python checks over a self-contained demo domain model.
They are not tests from a real e-commerce company's application. Runtime scaling
makes the example repeatable and short enough for local verification.
"""
import argparse, json, time
from pathlib import Path
from .selector import load_json, select_full, select_coverage_only, select_hybrid

# Each callable is a real assertion for a small flash-sale behaviour fixture.
def _cart_total():
    items = [(2, 100), (1, 50)]
    total = sum(q * price for q, price in items)
    assert total == 250

def _payment_authorization():
    amount, authorized = 250, 250
    assert amount == authorized and amount > 0

def _flash_inventory():
    stock, requested = 3, 2
    remaining = stock - requested
    assert remaining >= 0 and remaining == 1

def _coupon_rules():
    price, percent, max_discount = 250, 20, 30
    discount = min(price * percent / 100, max_discount)
    assert discount == 30

def _order_webhook():
    seen = set()
    event_id = "evt-100"
    seen.add(event_id)
    duplicate_applied = event_id not in seen
    assert duplicate_applied is False

def _search_catalog():
    catalog = {"SKU-1": "available", "SKU-2": "sold-out"}
    assert catalog.get("SKU-1") == "available"

def _user_login():
    stored_hash, supplied_hash = "demo-hash", "demo-hash"
    assert stored_hash == supplied_hash

def _checkout_e2e():
    cart_total, authorized_amount, stock, quantity = 250, 250, 3, 2
    assert cart_total == authorized_amount and stock - quantity >= 0

CHECKS = {
    "T01_cart_total": _cart_total,
    "T02_payment_authorization": _payment_authorization,
    "T03_flash_inventory": _flash_inventory,
    "T04_coupon_rules": _coupon_rules,
    "T05_order_webhook": _order_webhook,
    "T06_search_catalog": _search_catalog,
    "T07_user_login": _user_login,
    "T08_checkout_e2e": _checkout_e2e,
}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--strategy', choices=['full_regression','coverage_only','hybrid_selector'], required=True)
    p.add_argument('--diff', required=True)
    p.add_argument('--data', default='data')
    p.add_argument('--runtime-scale', type=float, default=0.003)
    args = p.parse_args()
    if args.runtime_scale < 0:
        p.error('--runtime-scale must be >= 0')
    d = Path(args.data)
    changed = load_json(args.diff).get('changed_files', [])
    catalog = load_json(d/'test_catalog.json')
    if args.strategy == 'full_regression':
        selection = select_full(catalog)
    elif args.strategy == 'coverage_only':
        selection = select_coverage_only(changed, catalog)
    else:
        selection = select_hybrid(changed, catalog, load_json(d/'test_history.json'),
                                  load_json(d/'defect_associations.json'), load_json(d/'dependencies.json'))
    started = time.perf_counter()
    passed = []
    for test in catalog:
        tid = test['test_id']
        if tid not in selection['selected_tests']:
            continue
        CHECKS[tid]()
        passed.append(tid)
        time.sleep(float(test['runtime_seconds']) * args.runtime_scale)
    elapsed = round(time.perf_counter()-started, 6)
    defects = load_json(d/'defect_associations.json')
    in_scope = [x for x in defects if x.get('severity') == 'critical' and set(x.get('affected_files', [])) & set(changed)]
    detected = [x['defect_id'] for x in in_scope if set(x.get('test_ids', [])) & set(passed)]
    recall = len(detected)/len(in_scope) if in_scope else 1.0
    print(json.dumps({
        'runner_type':'local synthetic CI-like execution; real assertions, simulated duration scaling',
        'strategy':args.strategy, 'changed_files':changed, 'selected_tests':selection['selected_tests'],
        'tests_passed':passed, 'selected_count':len(passed), 'total_tests':len(catalog),
        'elapsed_wall_seconds':elapsed, 'critical_defects_in_scope':[x['defect_id'] for x in in_scope],
        'critical_defects_detected':detected, 'critical_defect_recall':round(recall,4),
        'selection_reason':selection.get('reason','full suite')
    }, sort_keys=True))

if __name__ == '__main__': main()
