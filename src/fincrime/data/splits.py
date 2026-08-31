from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from fincrime.contracts.manifests import SplitManifest


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    typology: str
    generator_seed: int
    entity_ids: frozenset[str]
    edge_ids: frozenset[str]


class OverlapReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    entity_overlap: tuple[str, ...]
    edge_overlap: tuple[str, ...]
    generator_seed_overlap: tuple[int, ...]


def audit_split_overlap(
    records: Mapping[str, CaseRecord], manifest: SplitManifest
) -> OverlapReport:
    """Audit train cases against all non-train tracks for leakage and overlap."""
    train_ids = manifest.train_case_ids
    non_train_ids = (
        manifest.validation_case_ids
        + manifest.calibration_case_ids
        + manifest.temporal_test_case_ids
        + manifest.heldout_typology_case_ids
        + manifest.unseen_generator_case_ids
    )

    for case_id in (*train_ids, *non_train_ids):
        if case_id not in records:
            raise KeyError(f"Case record '{case_id}' specified in manifest was not found in records")
        record = records[case_id]
        if record.case_id != case_id:
            raise ValueError(
                f"Manifest case ID '{case_id}' does not match CaseRecord.case_id '{record.case_id}'"
            )

    train_records = [records[cid] for cid in train_ids]
    non_train_records = [records[cid] for cid in non_train_ids]

    train_entities = set().union(*(item.entity_ids for item in train_records)) if train_records else set()
    non_train_entities = (
        set().union(*(item.entity_ids for item in non_train_records)) if non_train_records else set()
    )

    train_edges = set().union(*(item.edge_ids for item in train_records)) if train_records else set()
    non_train_edges = set().union(*(item.edge_ids for item in non_train_records)) if non_train_records else set()

    train_seeds = {item.generator_seed for item in train_records}
    non_train_seeds = {item.generator_seed for item in non_train_records}

    return OverlapReport(
        entity_overlap=tuple(sorted(train_entities & non_train_entities)),
        edge_overlap=tuple(sorted(train_edges & non_train_edges)),
        generator_seed_overlap=tuple(sorted(train_seeds & non_train_seeds)),
    )


def assert_split_safe(report: OverlapReport) -> None:
    """Assert that an overlap report contains no entity, edge, or seed leakage."""
    if report.entity_overlap:
        raise ValueError(f"entity overlap: {report.entity_overlap}")
    if report.edge_overlap:
        raise ValueError(f"edge overlap: {report.edge_overlap}")
    if report.generator_seed_overlap:
        raise ValueError(f"generator seed overlap: {report.generator_seed_overlap}")
