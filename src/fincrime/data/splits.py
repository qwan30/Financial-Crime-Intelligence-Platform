from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from fincrime.contracts.manifests import SplitManifest
from fincrime.data.provenance import NonBlank


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
            raise KeyError(
                f"Case record '{case_id}' specified in manifest was not found in records"
            )
        record = records[case_id]
        if record.case_id != case_id:
            raise ValueError(
                f"Manifest case ID '{case_id}' does not match CaseRecord.case_id '{record.case_id}'"
            )

    train_records = [records[cid] for cid in train_ids]
    non_train_records = [records[cid] for cid in non_train_ids]

    train_entities = (
        set().union(*(item.entity_ids for item in train_records)) if train_records else set()
    )
    non_train_entities = (
        set().union(*(item.entity_ids for item in non_train_records))
        if non_train_records
        else set()
    )

    train_edges = (
        set().union(*(item.edge_ids for item in train_records)) if train_records else set()
    )
    non_train_edges = (
        set().union(*(item.edge_ids for item in non_train_records)) if non_train_records else set()
    )

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


class SplitVerdict(StrEnum):
    SAFE = "SAFE"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    BLOCKED_DATA = "BLOCKED_DATA"


class SplitEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: NonBlank
    verdict: SplitVerdict
    cutoff_tick: int
    embargo_ticks: int = Field(ge=0)
    entity_overlap: tuple[str, ...] = ()
    edge_overlap: tuple[str, ...] = ()
    embargo_violations: tuple[int, ...] = ()


def audit_temporal_evidence(
    source_id: str,
    ticks: Iterable[int],
    cutoff_tick: int,
    embargo_ticks: int,
    train_entity_ids: Collection[str],
    test_entity_ids: Collection[str],
    train_edge_ids: Collection[str],
    test_edge_ids: Collection[str],
) -> SplitEvidence:
    """Audit temporal split evidence for missing ticks, entity/edge overlap, and embargo violations."""
    if embargo_ticks < 0:
        raise ValueError(f"embargo_ticks must be non-negative, got {embargo_ticks}")

    ticks_tuple = tuple(ticks)
    entity_overlap = tuple(sorted(set(train_entity_ids) & set(test_entity_ids)))
    edge_overlap = tuple(sorted(set(train_edge_ids) & set(test_edge_ids)))
    embargo_violations = tuple(
        sorted(t for t in ticks_tuple if cutoff_tick < t <= cutoff_tick + embargo_ticks)
    )

    has_pre_cutoff = any(t <= cutoff_tick for t in ticks_tuple)
    has_post_cutoff = any(t > cutoff_tick for t in ticks_tuple)
    has_evidence = (
        has_pre_cutoff
        and has_post_cutoff
        and bool(train_entity_ids)
        and bool(test_entity_ids)
        and bool(train_edge_ids)
        and bool(test_edge_ids)
    )

    if not has_evidence:
        verdict = SplitVerdict.NOT_EVALUABLE
    elif entity_overlap or edge_overlap or embargo_violations:
        verdict = SplitVerdict.BLOCKED_DATA
    else:
        verdict = SplitVerdict.SAFE

    return SplitEvidence(
        source_id=source_id,
        verdict=verdict,
        cutoff_tick=cutoff_tick,
        embargo_ticks=embargo_ticks,
        entity_overlap=entity_overlap,
        edge_overlap=edge_overlap,
        embargo_violations=embargo_violations,
    )
