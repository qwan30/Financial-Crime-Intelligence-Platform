from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from fincrime.contracts.manifests import SplitManifest
from fincrime.data.splits import CaseRecord, OverlapReport, assert_split_safe, audit_split_overlap


def test_entity_overlap_between_train_and_test_fails() -> None:
    records = {
        "train": CaseRecord("train", "fan_in", 11, frozenset({"a"}), frozenset({"e1"})),
        "test": CaseRecord("test", "cycle", 23, frozenset({"a"}), frozenset({"e2"})),
    }
    manifest = SplitManifest(
        train_case_ids=("train",),
        validation_case_ids=(),
        calibration_case_ids=(),
        temporal_test_case_ids=("test",),
        heldout_typology_case_ids=(),
        unseen_generator_case_ids=(),
    )
    report = audit_split_overlap(records, manifest)
    assert report.entity_overlap == ("a",)
    assert report.edge_overlap == ()
    assert report.generator_seed_overlap == ()
    with pytest.raises(ValueError, match="entity overlap"):
        assert_split_safe(report)


def test_edge_overlap_between_train_and_validation_fails() -> None:
    records = {
        "train": CaseRecord("train", "fan_in", 11, frozenset({"a"}), frozenset({"e1"})),
        "val": CaseRecord("val", "cycle", 23, frozenset({"b"}), frozenset({"e1"})),
    }
    manifest = SplitManifest(
        train_case_ids=("train",),
        validation_case_ids=("val",),
        calibration_case_ids=(),
        temporal_test_case_ids=(),
        heldout_typology_case_ids=(),
        unseen_generator_case_ids=(),
    )
    report = audit_split_overlap(records, manifest)
    assert report.entity_overlap == ()
    assert report.edge_overlap == ("e1",)
    assert report.generator_seed_overlap == ()
    with pytest.raises(ValueError, match="edge overlap"):
        assert_split_safe(report)


def test_generator_seed_overlap_in_unseen_track_fails() -> None:
    records = {
        "train": CaseRecord("train", "fan_in", 11, frozenset({"a"}), frozenset({"e1"})),
        "unseen": CaseRecord("unseen", "cycle", 11, frozenset({"b"}), frozenset({"e2"})),
    }
    manifest = SplitManifest(
        train_case_ids=("train",),
        validation_case_ids=(),
        calibration_case_ids=(),
        temporal_test_case_ids=(),
        heldout_typology_case_ids=(),
        unseen_generator_case_ids=("unseen",),
    )
    report = audit_split_overlap(records, manifest)
    assert report.entity_overlap == ()
    assert report.edge_overlap == ()
    assert report.generator_seed_overlap == (11,)
    with pytest.raises(ValueError, match="generator seed overlap"):
        assert_split_safe(report)


def test_clean_splits_pass_audit() -> None:
    records = {
        "train": CaseRecord("train", "fan_in", 11, frozenset({"a", "b"}), frozenset({"e1"})),
        "val": CaseRecord("val", "fan_out", 12, frozenset({"c"}), frozenset({"e2"})),
        "calib": CaseRecord("calib", "cycle", 13, frozenset({"d"}), frozenset({"e3"})),
        "temporal": CaseRecord(
            "temporal", "scatter_gather", 14, frozenset({"e"}), frozenset({"e4"})
        ),
        "heldout": CaseRecord("heldout", "smurfing", 15, frozenset({"f"}), frozenset({"e5"})),
        "unseen": CaseRecord("unseen", "peeling_chain", 16, frozenset({"g"}), frozenset({"e6"})),
    }
    manifest = SplitManifest(
        train_case_ids=("train",),
        validation_case_ids=("val",),
        calibration_case_ids=("calib",),
        temporal_test_case_ids=("temporal",),
        heldout_typology_case_ids=("heldout",),
        unseen_generator_case_ids=("unseen",),
    )
    report = audit_split_overlap(records, manifest)
    assert report.entity_overlap == ()
    assert report.edge_overlap == ()
    assert report.generator_seed_overlap == ()
    # Should not raise
    assert_split_safe(report)


def test_all_non_train_tracks_are_audited_against_train() -> None:
    manifest_fields = (
        ("validation_case_ids", "val"),
        ("calibration_case_ids", "calib"),
        ("temporal_test_case_ids", "temp"),
        ("heldout_typology_case_ids", "held"),
        ("unseen_generator_case_ids", "unseen"),
    )
    for field_name, case_id in manifest_fields:
        records = {
            "train": CaseRecord(
                "train", "fan_in", 100, frozenset({"shared_entity"}), frozenset({"e_train"})
            ),
            case_id: CaseRecord(
                case_id, "cycle", 200, frozenset({"shared_entity"}), frozenset({"e_non_train"})
            ),
        }
        kwargs = {
            "train_case_ids": ("train",),
            "validation_case_ids": (),
            "calibration_case_ids": (),
            "temporal_test_case_ids": (),
            "heldout_typology_case_ids": (),
            "unseen_generator_case_ids": (),
        }
        kwargs[field_name] = (case_id,)
        manifest = SplitManifest(**kwargs)
        report = audit_split_overlap(records, manifest)
        assert report.entity_overlap == ("shared_entity",)
        with pytest.raises(ValueError, match="entity overlap"):
            assert_split_safe(report)


def test_missing_record_id_fails_clearly_without_leakage() -> None:
    records = {
        "train": CaseRecord("train", "fan_in", 11, frozenset({"a"}), frozenset({"e1"})),
    }
    manifest = SplitManifest(
        train_case_ids=("train",),
        validation_case_ids=("missing_val_case",),
        calibration_case_ids=(),
        temporal_test_case_ids=(),
        heldout_typology_case_ids=(),
        unseen_generator_case_ids=(),
    )
    with pytest.raises(KeyError, match="missing_val_case"):
        audit_split_overlap(records, manifest)


def test_missing_train_record_id_fails_clearly() -> None:
    records = {
        "val": CaseRecord("val", "cycle", 12, frozenset({"b"}), frozenset({"e2"})),
    }
    manifest = SplitManifest(
        train_case_ids=("missing_train_case",),
        validation_case_ids=("val",),
        calibration_case_ids=(),
        temporal_test_case_ids=(),
        heldout_typology_case_ids=(),
        unseen_generator_case_ids=(),
    )
    with pytest.raises(KeyError, match="missing_train_case"):
        audit_split_overlap(records, manifest)


def test_manifest_id_mismatch_with_case_record_fails_clearly() -> None:
    records = {
        "train_alias": CaseRecord(
            "different_case_id", "fan_in", 11, frozenset({"a"}), frozenset({"e1"})
        ),
    }
    manifest = SplitManifest(
        train_case_ids=("train_alias",),
        validation_case_ids=(),
        calibration_case_ids=(),
        temporal_test_case_ids=(),
        heldout_typology_case_ids=(),
        unseen_generator_case_ids=(),
    )
    with pytest.raises(
        ValueError,
        match="Manifest case ID 'train_alias' does not match CaseRecord.case_id 'different_case_id'",
    ):
        audit_split_overlap(records, manifest)


def test_immutability_of_case_record() -> None:
    record = CaseRecord("c1", "typology_a", 42, frozenset({"node1"}), frozenset({"edge1"}))
    with pytest.raises(FrozenInstanceError):
        record.case_id = "c2"


def test_immutability_of_overlap_report() -> None:
    report = OverlapReport(
        entity_overlap=("node1",),
        edge_overlap=(),
        generator_seed_overlap=(),
    )
    with pytest.raises(ValidationError):
        report.entity_overlap = ()
