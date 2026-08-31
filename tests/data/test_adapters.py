from datetime import UTC, datetime
from typing import Any

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from fincrime.data.adapters import AMLBenchAdapter, AMLSimAdapter


def test_amlsim_adapter_maps_canonical_columns() -> None:
    raw = pl.DataFrame(
        {
            "transaction_id": ["e1"],
            "orig_id": ["a"],
            "dest_id": ["b"],
            "amount": [10.0],
            "timestamp": [datetime(2026, 1, 1, tzinfo=UTC)],
        }
    )

    result = AMLSimAdapter().transactions(raw)
    expected = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [10.0],
            "event_time": [datetime(2026, 1, 1, tzinfo=UTC)],
        }
    )

    assert result.columns == [
        "edge_id",
        "source_id",
        "target_id",
        "amount",
        "event_time",
    ]
    assert_frame_equal(result, expected)


def test_amlbench_adapter_maps_canonical_columns() -> None:
    raw = pl.DataFrame(
        {
            "transaction_id": ["e2"],
            "source_account_id": ["c"],
            "target_account_id": ["d"],
            "amount": [20.0],
            "transaction_time": [datetime(2026, 1, 2, tzinfo=UTC)],
        }
    )

    result = AMLBenchAdapter().transactions(raw)
    expected = pl.DataFrame(
        {
            "edge_id": ["e2"],
            "source_id": ["c"],
            "target_id": ["d"],
            "amount": [20.0],
            "event_time": [datetime(2026, 1, 2, tzinfo=UTC)],
        }
    )

    assert result.columns == [
        "edge_id",
        "source_id",
        "target_id",
        "amount",
        "event_time",
    ]
    assert_frame_equal(result, expected)


@pytest.mark.parametrize(
    "adapter_cls",
    [AMLSimAdapter, AMLBenchAdapter],
)
def test_adapter_mappings_are_immutable(
    adapter_cls: type[AMLSimAdapter | AMLBenchAdapter],
) -> None:
    adapter = adapter_cls()
    with pytest.raises(TypeError):
        adapter_cls.mapping["injected_col"] = "label"  # type: ignore[index]
    with pytest.raises(TypeError):
        adapter.mapping["injected_col"] = "label"  # type: ignore[index]
    with pytest.raises(TypeError):
        del adapter_cls.mapping["transaction_id"]  # type: ignore[attr-defined]



@pytest.mark.parametrize(
    ("adapter", "frame"),
    [
        (AMLSimAdapter(), pl.DataFrame({"orig_id": ["a"]})),
        (AMLBenchAdapter(), pl.DataFrame({"source_account_id": ["a"]})),
    ],
)
def test_adapter_fails_when_required_source_columns_are_missing(
    adapter: AMLSimAdapter | AMLBenchAdapter, frame: pl.DataFrame
) -> None:
    with pytest.raises(ValueError, match="missing source columns"):
        adapter.transactions(frame)


@pytest.mark.parametrize("blank_value", ["", "   "])
@pytest.mark.parametrize("id_col", ["transaction_id", "orig_id", "dest_id"])
def test_amlsim_adapter_rejects_blank_identifiers(blank_value: str, id_col: str) -> None:
    raw = pl.DataFrame(
        {
            "transaction_id": ["e1"],
            "orig_id": ["a"],
            "dest_id": ["b"],
            "amount": [10.0],
            "timestamp": [datetime(2026, 1, 1, tzinfo=UTC)],
        }
    ).with_columns(pl.lit(blank_value).alias(id_col))

    with pytest.raises(ValueError, match="blank identifier"):
        AMLSimAdapter().transactions(raw)


@pytest.mark.parametrize("id_col", ["transaction_id", "orig_id", "dest_id"])
def test_amlsim_adapter_rejects_null_identifiers(id_col: str) -> None:
    raw = pl.DataFrame(
        {
            "transaction_id": ["e1"],
            "orig_id": ["a"],
            "dest_id": ["b"],
            "amount": [10.0],
            "timestamp": [datetime(2026, 1, 1, tzinfo=UTC)],
        }
    ).with_columns(pl.lit(None, dtype=pl.String).alias(id_col))

    with pytest.raises(ValueError, match="null identifier"):
        AMLSimAdapter().transactions(raw)


@pytest.mark.parametrize("id_col", ["transaction_id", "source_account_id", "target_account_id"])
def test_amlbench_adapter_rejects_non_string_identifiers(id_col: str) -> None:
    raw = pl.DataFrame(
        {
            "transaction_id": ["e2"],
            "source_account_id": ["c"],
            "target_account_id": ["d"],
            "amount": [20.0],
            "transaction_time": [datetime(2026, 1, 2, tzinfo=UTC)],
        }
    ).with_columns(pl.lit(12345).alias(id_col))

    with pytest.raises(ValueError, match="identifier columns must be string"):
        AMLBenchAdapter().transactions(raw)


@pytest.mark.parametrize(
    ("amount_val", "expected_match"),
    [
        (None, "null amount"),
        (float("nan"), "non-finite amount"),
        (float("inf"), "non-finite amount"),
        (float("-inf"), "non-finite amount"),
    ],
)
def test_adapter_rejects_non_finite_amounts(
    amount_val: Any, expected_match: str
) -> None:
    raw = pl.DataFrame(
        {
            "transaction_id": ["e1"],
            "orig_id": ["a"],
            "dest_id": ["b"],
            "amount": [amount_val],
            "timestamp": [datetime(2026, 1, 1, tzinfo=UTC)],
        },
        schema_overrides={"amount": pl.Float64},
    )

    with pytest.raises(ValueError, match=expected_match):
        AMLSimAdapter().transactions(raw)


def test_adapter_rejects_non_numeric_amount() -> None:
    raw = pl.DataFrame(
        {
            "transaction_id": ["e1"],
            "orig_id": ["a"],
            "dest_id": ["b"],
            "amount": ["not_a_number"],
            "timestamp": [datetime(2026, 1, 1, tzinfo=UTC)],
        }
    )

    with pytest.raises(ValueError, match="amount must be numeric"):
        AMLSimAdapter().transactions(raw)


def test_adapter_rejects_naive_datetime_event_time() -> None:
    raw = pl.DataFrame(
        {
            "transaction_id": ["e1"],
            "orig_id": ["a"],
            "dest_id": ["b"],
            "amount": [10.0],
            "timestamp": [datetime(2026, 1, 1)],  # noqa: DTZ001
        }
    )

    with pytest.raises(ValueError, match="event_time must be timezone-aware"):
        AMLSimAdapter().transactions(raw)



def test_adapter_rejects_string_event_time() -> None:
    raw = pl.DataFrame(
        {
            "transaction_id": ["e1"],
            "orig_id": ["a"],
            "dest_id": ["b"],
            "amount": [10.0],
            "timestamp": ["2026-01-01T00:00:00Z"],
        }
    )

    with pytest.raises(ValueError, match="event_time must be datetime type"):
        AMLSimAdapter().transactions(raw)


def test_adapter_rejects_null_event_time() -> None:
    raw = pl.DataFrame(
        {
            "transaction_id": ["e1"],
            "orig_id": ["a"],
            "dest_id": ["b"],
            "amount": [10.0],
            "timestamp": [None],
        },
        schema_overrides={"timestamp": pl.Datetime("us", "UTC")},
    )

    with pytest.raises(ValueError, match="null event_time"):
        AMLSimAdapter().transactions(raw)


def test_adapter_rejection_does_not_leak_row_content() -> None:
    sensitive_source = "SECRET_ACCOUNT_ACC_998877"
    sensitive_target = "SECRET_ACCOUNT_BEN_112233"
    raw = pl.DataFrame(
        {
            "transaction_id": ["e1"],
            "orig_id": [sensitive_source],
            "dest_id": [sensitive_target],
            "amount": [float("nan")],
            "timestamp": [datetime(2026, 1, 1, tzinfo=UTC)],
        }
    )

    with pytest.raises(ValueError) as exc_info:
        AMLSimAdapter().transactions(raw)

    err_msg = str(exc_info.value)
    assert sensitive_source not in err_msg
    assert sensitive_target not in err_msg
