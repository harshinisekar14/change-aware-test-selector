"""Small deterministic event processor resilient to duplicate/stale/out-of-order events."""
from dataclasses import dataclass, field

@dataclass
class EventProcessor:
    """Apply only contiguous sequence numbers; ignore duplicates and stale events.

    `state` is a list of applied event records, useful for an auditable demo.
    Production systems should persist inbox IDs, sequence checkpoints, and state
    transactionally in a database/outbox or equivalent durable store.
    """
    next_sequence: int = 1
    seen_event_ids: set = field(default_factory=set)
    pending: dict = field(default_factory=dict)
    state: list = field(default_factory=list)
    rejected: list = field(default_factory=list)

    def ingest(self, event):
        event_id = event.get("event_id")
        seq = event.get("sequence")
        if not event_id or not isinstance(seq, int) or seq < 1:
            self.rejected.append({"event": event, "reason": "invalid envelope"})
            return {"status": "rejected", "reason": "invalid envelope"}
        if event_id in self.seen_event_ids:
            return {"status": "duplicate", "event_id": event_id}
        if seq < self.next_sequence:
            self.seen_event_ids.add(event_id)
            return {"status": "stale", "event_id": event_id}
        if seq in self.pending:
            # Same sequence with different ID is a conflict; keep the first event
            # and record the conflict rather than silently overwrite state.
            self.seen_event_ids.add(event_id)
            self.rejected.append({"event": event, "reason": "sequence conflict"})
            return {"status": "conflict", "sequence": seq}
        self.seen_event_ids.add(event_id)
        self.pending[seq] = event
        applied = []
        while self.next_sequence in self.pending:
            current = self.pending.pop(self.next_sequence)
            self.state.append({"event_id": current["event_id"],
                               "sequence": current["sequence"],
                               "event_type": current.get("event_type"),
                               "payload": current.get("payload", {})})
            applied.append(current["event_id"])
            self.next_sequence += 1
        return {"status": "applied" if applied else "buffered", "applied": applied,
                "next_sequence": self.next_sequence, "pending_sequences": sorted(self.pending)}
