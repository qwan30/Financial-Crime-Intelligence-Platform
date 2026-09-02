from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

from fincrime.evidence.models import (
    EvidenceCategory,
    EvidenceItem,
    EvidencePolarity,
    compute_sha256_hex,
)
from fincrime.evidence.store import (
    EvidenceConflict,
    EvidenceNotFound,
    EvidenceStore,
)


def create_sample_item(
    evidence_id: str = "ev-001",
    summary: str = "Summary of evidence",
    category: EvidenceCategory = EvidenceCategory.OBSERVED,
) -> EvidenceItem:
    raw = {
        "evidence_id": evidence_id,
        "category": category,
        "source_reference": f"src-{evidence_id}",
        "polarity": EvidencePolarity.SUPPORTING,
        "snapshot_time": datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC),
        "generation_method_version": "v1.0.0",
        "confidence": 0.9,
        "payload_summary": summary,
    }
    h = compute_sha256_hex(raw)
    return EvidenceItem(**raw, integrity_hash=h)


def test_store_put_and_get() -> None:
    store = EvidenceStore()
    item = create_sample_item("ev-101")
    stored = store.put(item)
    assert stored == item
    fetched = store.get("ev-101")
    assert fetched == item


def test_store_put_idempotent() -> None:
    store = EvidenceStore()
    item1 = create_sample_item("ev-102", summary="First insert")
    item2 = create_sample_item("ev-102", summary="First insert")
    stored1 = store.put(item1)
    stored2 = store.put(item2)
    assert stored1 == stored2
    assert store.get("ev-102") == item1


def test_store_put_conflict() -> None:
    store = EvidenceStore()
    item1 = create_sample_item("ev-103", summary="Original summary")
    item2 = create_sample_item("ev-103", summary="Conflicting summary")
    store.put(item1)
    with pytest.raises(EvidenceConflict, match="already exists with differing canonical bytes"):
        store.put(item2)


def test_store_get_not_found() -> None:
    store = EvidenceStore()
    with pytest.raises(EvidenceNotFound, match="not found"):
        store.get("non-existent")


def test_store_get_many_success() -> None:
    store = EvidenceStore()
    item1 = create_sample_item("ev-201")
    item2 = create_sample_item("ev-202")
    item3 = create_sample_item("ev-203")
    store.put(item1)
    store.put(item2)
    store.put(item3)

    items = store.get_many(["ev-201", "ev-203", "ev-202"])
    assert items == [item1, item3, item2]


def test_store_get_many_missing_raises() -> None:
    store = EvidenceStore()
    item1 = create_sample_item("ev-301")
    store.put(item1)
    with pytest.raises(EvidenceNotFound, match="EvidenceItem 'ev-302' not found"):
        store.get_many(["ev-301", "ev-302"])


def test_store_thread_safety() -> None:
    store = EvidenceStore()
    items = [create_sample_item(f"ev-concurrent-{i}") for i in range(100)]

    def worker(item: EvidenceItem) -> EvidenceItem:
        store.put(item)
        return store.get(item.evidence_id)

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(worker, items))

    assert len(results) == 100
    all_fetched = store.get_many([f"ev-concurrent-{i}" for i in range(100)])
    assert len(all_fetched) == 100
