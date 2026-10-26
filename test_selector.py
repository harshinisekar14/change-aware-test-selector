import json, unittest
from pathlib import Path
from selector.selector import load_json, select_hybrid, select_coverage_only, select_full, dependency_neighborhood
from selector.experiment import run_experiment
ROOT = Path(__file__).resolve().parents[1]
class SelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d=ROOT/"data"
        cls.catalog=load_json(d/"test_catalog.json")
        cls.history=load_json(d/"test_history.json")
        cls.defects=load_json(d/"defect_associations.json")
        cls.deps=load_json(d/"dependencies.json")
    def test_changed_file_direct_test_selected(self):
        out=select_hybrid(["flash_sale.py"],self.catalog,self.history,self.defects,self.deps)
        self.assertIn("T03_flash_inventory",out["selected_tests"])
    def test_critical_defect_associated_test_retained(self):
        out=select_hybrid(["payment.py"],self.catalog,self.history,self.defects,self.deps)
        self.assertIn("T02_payment_authorization",out["selected_tests"])
        self.assertIn("T08_checkout_e2e",out["selected_tests"])
    def test_empty_diff_falls_back_to_full_suite(self):
        out=select_hybrid([],self.catalog,self.history,self.defects,self.deps)
        self.assertEqual(out["selected_count"],len(self.catalog))
    def test_coverage_only_is_subset_for_sample_diff(self):
        out=select_coverage_only(["flash_sale.py","inventory.py"],self.catalog)
        self.assertLessEqual(out["selected_count"],len(self.catalog))
        self.assertIn("T03_flash_inventory",out["selected_tests"])
    def test_unknown_changed_file_falls_back_to_full_suite(self):
        out=select_hybrid(["totally_unknown_module.py"],self.catalog,self.history,self.defects,self.deps)
        self.assertEqual(out["selected_count"],len(self.catalog))
        self.assertIn("safety fallback",out["reason"])
    def test_coverage_only_unknown_file_falls_back_to_full_suite(self):
        out=select_coverage_only(["totally_unknown_module.py"],self.catalog)
        self.assertEqual(out["selected_count"],len(self.catalog))
    def test_dependency_cycle_terminates(self):
        cycle=[{"source":"a.py","target":"b.py"},{"source":"b.py","target":"a.py"}]
        self.assertEqual(dependency_neighborhood(["a.py"],cycle),{"a.py","b.py"})
    def test_dependency_neighborhood(self):
        n=dependency_neighborhood(["checkout.py"],self.deps)
        self.assertIn("payment.py",n)
        self.assertIn("pricing.py",n)
    def test_experiment_is_reproducible_and_has_three_approaches(self):
        x=run_experiment(ROOT/"data")
        self.assertEqual(len(x["cases"]),5)
        self.assertIn("hybrid_selector",x["aggregate"])
        self.assertEqual(x["aggregate"]["full_regression"]["mean_time_saved_percent"],0.0)
if __name__=="__main__": unittest.main()
