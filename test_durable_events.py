import tempfile, unittest
from pathlib import Path
from selector.durable_events import DurableEventProcessor

class DurableEventTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=str(Path(self.tmp.name)/"events.sqlite3")
    def tearDown(self): self.tmp.cleanup()
    def test_restart_recovers_committed_and_pending(self):
        p=DurableEventProcessor(self.db)
        self.assertEqual(p.ingest({"event_id":"e2","sequence":2,"event_type":"sale"})["status"],"buffered")
        p=DurableEventProcessor(self.db)  # simulated process restart
        self.assertEqual(list(p.snapshot()["pending"]),[2])
        p.ingest({"event_id":"e1","sequence":1,"event_type":"inventory"})
        p=DurableEventProcessor(self.db)
        snap=p.snapshot()
        self.assertEqual([x["sequence"] for x in snap["state"]],[1,2])
        self.assertEqual(snap["next_sequence"],3)
    def test_duplicate_after_restart_is_not_reapplied(self):
        p=DurableEventProcessor(self.db); e={"event_id":"e1","sequence":1,"event_type":"sale"}
        p.ingest(e); p=DurableEventProcessor(self.db)
        self.assertEqual(p.ingest(e)["status"],"duplicate")
        self.assertEqual(len(p.snapshot()["state"]),1)
    def test_conflicting_sequence_preserves_first_pending(self):
        p=DurableEventProcessor(self.db)
        p.ingest({"event_id":"a2","sequence":2})
        result=p.ingest({"event_id":"b2","sequence":2})
        self.assertEqual(result["status"],"conflict")
        self.assertEqual(p.snapshot()["pending"][2]["event_id"],"a2")
    def test_invalid_event_audited(self):
        p=DurableEventProcessor(self.db); p.ingest({"event_id":"bad","sequence":0})
        self.assertEqual(p.snapshot()["rejected"][0]["reason"],"invalid envelope")
if __name__=='__main__': unittest.main()
