"""SQLite-backed event inbox with durable ordering and restart recovery.

This is a reference implementation for a single-writer local prototype. For
multi-replica production use, apply equivalent transactional semantics in the
organisation's managed database/queue and define retention/backup policies.
"""
import json
import sqlite3
from pathlib import Path

class DurableEventProcessor:
    def __init__(self, db_path="results/events.sqlite3"):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS inbox (
              event_id TEXT PRIMARY KEY,
              sequence INTEGER NOT NULL,
              event_type TEXT,
              payload_json TEXT NOT NULL,
              status TEXT NOT NULL,
              received_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );
            CREATE TABLE IF NOT EXISTS committed_events (
              sequence INTEGER PRIMARY KEY,
              event_id TEXT NOT NULL UNIQUE,
              event_type TEXT,
              payload_json TEXT NOT NULL,
              committed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );
            CREATE TABLE IF NOT EXISTS rejected_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              event_id TEXT,
              sequence INTEGER,
              event_json TEXT NOT NULL,
              reason TEXT NOT NULL,
              received_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT OR IGNORE INTO metadata(key,value) VALUES('next_sequence','1');
            """)

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def ingest(self, event):
        event_id, seq = event.get("event_id"), event.get("sequence")
        if not event_id or not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
            with self._connect() as db:
                db.execute("INSERT INTO rejected_events(event_id,sequence,event_json,reason) VALUES(?,?,?,?)",
                           (str(event_id) if event_id else None, seq if isinstance(seq,int) else None,
                            json.dumps(event, sort_keys=True), "invalid envelope"))
            return {"status":"rejected", "reason":"invalid envelope"}
        payload = json.dumps(event.get("payload", {}), sort_keys=True)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                existing = db.execute("SELECT 1 FROM inbox WHERE event_id=? UNION SELECT 1 FROM committed_events WHERE event_id=?",
                                      (event_id,event_id)).fetchone()
                if existing:
                    db.execute("COMMIT")
                    return {"status":"duplicate", "event_id":event_id}
                next_seq = int(db.execute("SELECT value FROM metadata WHERE key='next_sequence'").fetchone()[0])
                if seq < next_seq:
                    db.execute("INSERT INTO inbox(event_id,sequence,event_type,payload_json,status) VALUES(?,?,?,?,?)",
                               (event_id,seq,event.get("event_type"),payload,"stale"))
                    db.execute("COMMIT")
                    return {"status":"stale", "event_id":event_id}
                collision = db.execute("SELECT event_id FROM inbox WHERE sequence=? AND status='pending'",(seq,)).fetchone()
                if collision:
                    db.execute("INSERT INTO rejected_events(event_id,sequence,event_json,reason) VALUES(?,?,?,?)",
                               (event_id,seq,json.dumps(event,sort_keys=True),"sequence conflict"))
                    db.execute("COMMIT")
                    return {"status":"conflict", "sequence":seq, "kept_event_id":collision['event_id']}
                db.execute("INSERT INTO inbox(event_id,sequence,event_type,payload_json,status) VALUES(?,?,?,?,?)",
                           (event_id,seq,event.get("event_type"),payload,"pending"))
                applied=[]
                while True:
                    nxt=int(db.execute("SELECT value FROM metadata WHERE key='next_sequence'").fetchone()[0])
                    row=db.execute("SELECT * FROM inbox WHERE sequence=? AND status='pending'",(nxt,)).fetchone()
                    if not row: break
                    db.execute("INSERT INTO committed_events(sequence,event_id,event_type,payload_json) VALUES(?,?,?,?)",
                               (row['sequence'],row['event_id'],row['event_type'],row['payload_json']))
                    db.execute("UPDATE inbox SET status='committed' WHERE event_id=?",(row['event_id'],))
                    db.execute("UPDATE metadata SET value=? WHERE key='next_sequence'",(str(nxt+1),))
                    applied.append(row['event_id'])
                next_seq=int(db.execute("SELECT value FROM metadata WHERE key='next_sequence'").fetchone()[0])
                pending=[r[0] for r in db.execute("SELECT sequence FROM inbox WHERE status='pending' ORDER BY sequence")]
                db.execute("COMMIT")
                return {"status":"applied" if applied else "buffered", "applied":applied,
                        "next_sequence":next_seq, "pending_sequences":pending}
            except Exception:
                db.execute("ROLLBACK")
                raise

    def snapshot(self):
        with self._connect() as db:
            next_seq=int(db.execute("SELECT value FROM metadata WHERE key='next_sequence'").fetchone()[0])
            state=[{"event_id":r['event_id'],"sequence":r['sequence'],"event_type":r['event_type'],
                    "payload":json.loads(r['payload_json'])} for r in db.execute("SELECT * FROM committed_events ORDER BY sequence")]
            pending={r['sequence']:{"event_id":r['event_id'],"sequence":r['sequence'],"event_type":r['event_type'],
                    "payload":json.loads(r['payload_json'])} for r in db.execute("SELECT * FROM inbox WHERE status='pending' ORDER BY sequence")}
            rejected=[{"event_id":r['event_id'],"sequence":r['sequence'],"reason":r['reason']} for r in db.execute("SELECT * FROM rejected_events ORDER BY id")]
            return {"next_sequence":next_seq,"state":state,"pending":pending,"rejected":rejected}
