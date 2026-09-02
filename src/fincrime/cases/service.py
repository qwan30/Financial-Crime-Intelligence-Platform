from __future__ import annotations

import threading

from fincrime.cases.models import (
    AnalystFeedbackEvent,
    CaseSnapshot,
)
from fincrime.evidence.models import canonical_json_bytes
from fincrime.evidence.store import EvidenceStore


class CaseConflict(Exception):
    pass


class FeedbackConflict(Exception):
    pass


class CaseNotFound(Exception):
    pass


class CaseService:
    def __init__(self, evidence_store: EvidenceStore | None = None) -> None:
        self._evidence_store = evidence_store or EvidenceStore()
        self._cases: dict[str, CaseSnapshot] = {}
        self._case_bytes: dict[str, bytes] = {}
        self._feedback: dict[str, AnalystFeedbackEvent] = {}
        self._feedback_bytes: dict[str, bytes] = {}
        self._lock = threading.Lock()

    def create(
        self, case: CaseSnapshot, evidence_store: EvidenceStore | None = None
    ) -> CaseSnapshot:
        store = evidence_store or self._evidence_store
        # Revalidate that every evidence_id exists in EvidenceStore
        for eid in case.evidence_ids:
            store.get(eid)

        case_bytes = canonical_json_bytes(case.model_dump(mode="python", by_alias=False))
        with self._lock:
            if case.case_id in self._cases:
                if self._case_bytes[case.case_id] == case_bytes:
                    return self._cases[case.case_id]
                raise CaseConflict(
                    f"Case '{case.case_id}' already exists with differing canonical bytes."
                )
            self._cases[case.case_id] = case
            self._case_bytes[case.case_id] = case_bytes
            return case

    def get(self, case_id: str) -> CaseSnapshot:
        with self._lock:
            if case_id not in self._cases:
                raise CaseNotFound(f"Case '{case_id}' not found.")
            return self._cases[case_id]

    def append_feedback(self, event: AnalystFeedbackEvent) -> AnalystFeedbackEvent:
        event_bytes = canonical_json_bytes(event.model_dump(mode="python", by_alias=False))
        with self._lock:
            if event.case_id not in self._cases:
                raise CaseNotFound(f"Case '{event.case_id}' not found.")
            if event.event_id in self._feedback:
                if self._feedback_bytes[event.event_id] == event_bytes:
                    return self._feedback[event.event_id]
                raise FeedbackConflict(
                    f"Feedback event '{event.event_id}' already exists with differing canonical bytes."
                )
            self._feedback[event.event_id] = event
            self._feedback_bytes[event.event_id] = event_bytes
            return event
