from __future__ import annotations

import threading
from collections.abc import Sequence

from fincrime.evidence.models import (
    EvidenceItem,
    canonical_json_bytes,
)


class EvidenceConflict(Exception):
    pass


class EvidenceNotFound(Exception):
    pass


class EvidenceStore:
    def __init__(self) -> None:
        self._items: dict[str, EvidenceItem] = {}
        self._bytes: dict[str, bytes] = {}
        self._lock = threading.Lock()

    def put(self, item: EvidenceItem) -> EvidenceItem:
        dumped = item.model_dump(mode="python", by_alias=False)
        item_bytes = canonical_json_bytes(dumped)
        with self._lock:
            if item.evidence_id in self._items:
                if self._bytes[item.evidence_id] == item_bytes:
                    return self._items[item.evidence_id]
                raise EvidenceConflict(
                    f"EvidenceItem '{item.evidence_id}' already exists with differing canonical bytes."
                )
            self._items[item.evidence_id] = item
            self._bytes[item.evidence_id] = item_bytes
            return item

    def get(self, evidence_id: str) -> EvidenceItem:
        with self._lock:
            if evidence_id not in self._items:
                raise EvidenceNotFound(f"EvidenceItem '{evidence_id}' not found.")
            return self._items[evidence_id]

    def get_many(self, evidence_ids: Sequence[str]) -> list[EvidenceItem]:
        with self._lock:
            results: list[EvidenceItem] = []
            for eid in evidence_ids:
                if eid not in self._items:
                    raise EvidenceNotFound(f"EvidenceItem '{eid}' not found.")
                results.append(self._items[eid])
            return results
