import unittest
from selector.events import EventProcessor
class EventTests(unittest.TestCase):
    def test_out_of_order_events_buffer_then_drain(self):
        p=EventProcessor()
        self.assertEqual(p.ingest({"event_id":"e2","sequence":2,"event_type":"b"})["status"],"buffered")
        result=p.ingest({"event_id":"e1","sequence":1,"event_type":"a"})
        self.assertEqual(result["applied"],["e1","e2"])
        self.assertEqual([x["sequence"] for x in p.state],[1,2])
    def test_duplicate_event_id_not_applied_twice(self):
        p=EventProcessor()
        e={"event_id":"e1","sequence":1,"event_type":"a"}
        p.ingest(e); result=p.ingest(e)
        self.assertEqual(result["status"],"duplicate")
        self.assertEqual(len(p.state),1)
    def test_stale_event_ignored(self):
        p=EventProcessor()
        p.ingest({"event_id":"e1","sequence":1,"event_type":"a"})
        result=p.ingest({"event_id":"late","sequence":1,"event_type":"late"})
        self.assertEqual(result["status"],"stale")
        self.assertEqual(len(p.state),1)
    def test_sequence_conflict_does_not_overwrite_pending(self):
        p=EventProcessor()
        p.ingest({"event_id":"e2a","sequence":2,"event_type":"first"})
        result=p.ingest({"event_id":"e2b","sequence":2,"event_type":"second"})
        self.assertEqual(result["status"],"conflict")
        self.assertEqual(p.pending[2]["event_id"],"e2a")
    def test_invalid_envelope_rejected(self):
        p=EventProcessor()
        self.assertEqual(p.ingest({"event_id":"bad","sequence":0})["status"],"rejected")
if __name__=="__main__": unittest.main()
