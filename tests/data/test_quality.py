from __future__ import annotations

import polars as pl
import pytest
from pydantic import ValidationError

from fincrime.data.quality import QualityReport, clean_amlsim_rows, profile_amlsim_rows


def test_quality_counts_reconcile_and_duplicates_are_retained() -> None:
    raw = pl.DataFrame(
        {
            "sourceNodeId": ["a", "a", ""],
            "targetNodeId": ["b", "b", "c"],
            "value": [1.0, 1.0, -1.0],
            "time": [1, 1, 2],
        }
    )
    report = profile_amlsim_rows(raw, "a" * 64)
    assert (
        report.input_rows,
        report.accepted_rows,
        report.rejected_rows,
        report.duplicate_rows,
    ) == (3, 2, 1, 1)
    assert report.input_rows == report.accepted_rows + report.rejected_rows


def test_quality_profile_quarantines_invalid_identifiers() -> None:
    raw = pl.DataFrame(
        {
            "sourceNodeId": [None, "a", "   ", "valid_source"],
            "targetNodeId": ["b", None, "c", "valid_target"],
            "value": [10.0, 20.0, 30.0, 40.0],
            "time": [1, 2, 3, 4],
        }
    )
    accepted, quarantine, report = clean_amlsim_rows(raw, "b" * 64)
    assert report.input_rows == 4
    assert report.accepted_rows == 1
    assert report.rejected_rows == 3
    assert accepted.height == 1
    assert quarantine.height == 3
    assert quarantine["row_ordinal"].to_list() == [0, 1, 2]
    assert all(reason == "missing_or_blank_identifier" for reason in quarantine["reason_code"])


def test_quality_profile_quarantines_invalid_amounts() -> None:
    raw = pl.DataFrame(
        {
            "sourceNodeId": ["s1", "s2", "s3", "s4", "s5"],
            "targetNodeId": ["t1", "t2", "t3", "t4", "t5"],
            "value": [-10.0, 0.0, float("nan"), float("inf"), 50.0],
            "time": [1, 2, 3, 4, 5],
        }
    )
    accepted, quarantine, report = clean_amlsim_rows(raw, "c" * 64)
    assert report.input_rows == 5
    assert report.accepted_rows == 1
    assert report.rejected_rows == 4
    assert accepted["value"].to_list() == [50.0]
    assert all(
        reason == "non_positive_or_non_finite_amount" for reason in quarantine["reason_code"]
    )


def test_quality_profile_quarantines_invalid_ticks() -> None:
    raw = pl.DataFrame(
        {
            "sourceNodeId": ["s1", "s2", "s3", "s4"],
            "targetNodeId": ["t1", "t2", "t3", "t4"],
            "value": [10.0, 20.0, 30.0, 40.0],
            "time": [-1.0, 1.5, None, 10.0],
        }
    )
    accepted, quarantine, report = clean_amlsim_rows(raw, "d" * 64)
    assert report.input_rows == 4
    assert report.accepted_rows == 1
    assert report.rejected_rows == 3
    assert accepted["time"].to_list() == [10.0]
    assert all(reason == "negative_or_invalid_tick" for reason in quarantine["reason_code"])


def test_quality_profile_retains_duplicates_without_deletion() -> None:
    raw = pl.DataFrame(
        {
            "sourceNodeId": ["acc_1", "acc_1", "acc_1"],
            "targetNodeId": ["acc_2", "acc_2", "acc_2"],
            "value": [100.0, 100.0, 100.0],
            "time": [5, 5, 5],
        }
    )
    accepted, quarantine, report = clean_amlsim_rows(raw, "e" * 64)
    assert report.input_rows == 3
    assert report.accepted_rows == 3
    assert report.rejected_rows == 0
    assert report.duplicate_rows == 2
    assert accepted.height == 3
    assert quarantine.height == 0


def test_quality_profile_does_not_clip_outliers() -> None:
    raw = pl.DataFrame(
        {
            "sourceNodeId": ["acc_1", "acc_2"],
            "targetNodeId": ["acc_2", "acc_3"],
            "value": [1.0, 999_999_999_999.0],
            "time": [0, 1],
        }
    )
    report = profile_amlsim_rows(raw, "f" * 64)
    assert report.accepted_rows == 2
    assert report.rejected_rows == 0


def test_quality_profile_rejects_missing_columns() -> None:
    raw = pl.DataFrame({"sourceNodeId": ["a"], "value": [1.0]})
    with pytest.raises(ValueError, match="missing required columns"):
        profile_amlsim_rows(raw, "a" * 64)


def test_quality_report_validation_and_immutability() -> None:
    with pytest.raises(ValidationError):
        QualityReport(
            source_id="",
            raw_sha256="not-valid-hash",
            schema_sha256="b" * 64,
            input_rows=1,
            accepted_rows=1,
            rejected_rows=0,
            duplicate_rows=0,
            reason_counts=(),
        )

    report = QualityReport(
        source_id="amlsim-20k",
        raw_sha256="a" * 64,
        schema_sha256="b" * 64,
        input_rows=2,
        accepted_rows=1,
        rejected_rows=1,
        duplicate_rows=0,
        reason_counts=(("missing_or_blank_identifier", 1),),
    )
    with pytest.raises(ValidationError):
        report.input_rows = 10  # type: ignore[misc]

    assert len(report.report_sha256()) == 64
