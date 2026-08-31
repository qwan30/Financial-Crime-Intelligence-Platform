from __future__ import annotations

import pytest
from pydantic import ValidationError

from fincrime.data.splits import SplitEvidence, SplitVerdict, audit_temporal_evidence


def test_missing_raw_ticks_is_not_evaluable() -> None:
    result = audit_temporal_evidence(
        "amlsim-20k", (), 10, 1, frozenset(), frozenset(), frozenset(), frozenset()
    )
    assert isinstance(result, SplitEvidence)
    assert result.verdict is SplitVerdict.NOT_EVALUABLE
    assert result.cutoff_tick == 10
    assert result.embargo_ticks == 1
    assert result.entity_overlap == ()
    assert result.edge_overlap == ()
    assert result.embargo_violations == ()


def test_ticks_missing_pre_cutoff_side_is_not_evaluable() -> None:
    result = audit_temporal_evidence(
        "amlsim-20k",
        (12, 15),
        10,
        1,
        frozenset({"a"}),
        frozenset({"b"}),
        frozenset({"e1"}),
        frozenset({"e2"}),
    )
    assert result.verdict is SplitVerdict.NOT_EVALUABLE
    assert result.entity_overlap == ()
    assert result.edge_overlap == ()
    assert result.embargo_violations == ()


def test_missing_cutoff_side_overrides_embargo_violation_as_not_evaluable() -> None:
    result = audit_temporal_evidence(
        "amlsim-20k",
        (11, 15),
        10,
        1,
        frozenset({"a"}),
        frozenset({"b"}),
        frozenset({"e1"}),
        frozenset({"e2"}),
    )
    assert result.verdict is SplitVerdict.NOT_EVALUABLE
    assert result.embargo_violations == (11,)


def test_ticks_missing_post_cutoff_side_is_not_evaluable() -> None:
    result = audit_temporal_evidence(
        "amlsim-20k",
        (1, 5, 10),
        10,
        1,
        frozenset({"a"}),
        frozenset({"b"}),
        frozenset({"e1"}),
        frozenset({"e2"}),
    )
    assert result.verdict is SplitVerdict.NOT_EVALUABLE
    assert result.entity_overlap == ()
    assert result.edge_overlap == ()
    assert result.embargo_violations == ()


@pytest.mark.parametrize(
    ("train_entities", "test_entities", "train_edges", "test_edges"),
    [
        (frozenset(), frozenset({"b"}), frozenset({"e1"}), frozenset({"e2"})),
        (frozenset({"a"}), frozenset(), frozenset({"e1"}), frozenset({"e2"})),
        (frozenset({"a"}), frozenset({"b"}), frozenset(), frozenset({"e2"})),
        (frozenset({"a"}), frozenset({"b"}), frozenset({"e1"}), frozenset()),
    ],
)
def test_absence_of_entity_or_edge_evidence_is_not_evaluable(
    train_entities: frozenset[str],
    test_entities: frozenset[str],
    train_edges: frozenset[str],
    test_edges: frozenset[str],
) -> None:
    result = audit_temporal_evidence(
        "amlsim-20k",
        (1, 15),
        10,
        1,
        train_entities,
        test_entities,
        train_edges,
        test_edges,
    )
    assert result.verdict is SplitVerdict.NOT_EVALUABLE


def test_entity_overlap_or_embargo_event_blocks_split() -> None:
    result = audit_temporal_evidence(
        "amlsim-20k",
        (1, 11),
        10,
        1,
        frozenset({"a"}),
        frozenset({"a"}),
        frozenset({"e1"}),
        frozenset({"e2"}),
    )
    assert result.verdict is SplitVerdict.BLOCKED_DATA
    assert result.entity_overlap == ("a",)
    assert result.edge_overlap == ()
    assert result.embargo_violations == (11,)


def test_edge_overlap_alone_blocks_split() -> None:
    result = audit_temporal_evidence(
        "amlsim-20k",
        (1, 15),
        10,
        1,
        frozenset({"a"}),
        frozenset({"b"}),
        frozenset({"e1"}),
        frozenset({"e1"}),
    )
    assert result.verdict is SplitVerdict.BLOCKED_DATA
    assert result.entity_overlap == ()
    assert result.edge_overlap == ("e1",)
    assert result.embargo_violations == ()


def test_embargo_event_alone_blocks_split() -> None:
    result = audit_temporal_evidence(
        "amlsim-20k",
        (5, 12, 20),
        10,
        3,
        frozenset({"a"}),
        frozenset({"b"}),
        frozenset({"e1"}),
        frozenset({"e2"}),
    )
    assert result.verdict is SplitVerdict.BLOCKED_DATA
    assert result.entity_overlap == ()
    assert result.edge_overlap == ()
    assert result.embargo_violations == (12,)


def test_embargo_window_boundaries() -> None:
    # cutoff=10, embargo=2 -> embargo window is (10, 12]
    # tick 10 is <= cutoff (safe train tick)
    # tick 13 is > cutoff + embargo (safe test tick)
    result_boundary_safe = audit_temporal_evidence(
        "amlsim-20k",
        (10, 13),
        10,
        2,
        frozenset({"a"}),
        frozenset({"b"}),
        frozenset({"e1"}),
        frozenset({"e2"}),
    )
    assert result_boundary_safe.verdict is SplitVerdict.SAFE
    assert result_boundary_safe.embargo_violations == ()

    # tick 11 is in (10, 12] (blocked)
    result_boundary_blocked_low = audit_temporal_evidence(
        "amlsim-20k",
        (10, 11, 13),
        10,
        2,
        frozenset({"a"}),
        frozenset({"b"}),
        frozenset({"e1"}),
        frozenset({"e2"}),
    )
    assert result_boundary_blocked_low.verdict is SplitVerdict.BLOCKED_DATA
    assert result_boundary_blocked_low.embargo_violations == (11,)

    # tick 12 is in (10, 12] (blocked)
    result_boundary_blocked_high = audit_temporal_evidence(
        "amlsim-20k",
        (10, 12),
        10,
        2,
        frozenset({"a"}),
        frozenset({"b"}),
        frozenset({"e1"}),
        frozenset({"e2"}),
    )
    assert result_boundary_blocked_high.verdict is SplitVerdict.BLOCKED_DATA
    assert result_boundary_blocked_high.embargo_violations == (12,)


def test_clean_split_is_safe() -> None:
    result = audit_temporal_evidence(
        "amlsim-20k",
        (1, 2, 3, 10, 15, 20),
        10,
        2,
        frozenset({"u1", "u2"}),
        frozenset({"u3", "u4"}),
        frozenset({"e1", "e2"}),
        frozenset({"e3", "e4"}),
    )
    assert result.verdict is SplitVerdict.SAFE
    assert result.entity_overlap == ()
    assert result.edge_overlap == ()
    assert result.embargo_violations == ()
    assert result.cutoff_tick == 10
    assert result.embargo_ticks == 2


def test_zero_embargo_ticks_is_supported() -> None:
    result = audit_temporal_evidence(
        "amlsim-20k",
        (1, 15),
        10,
        0,
        frozenset({"a"}),
        frozenset({"b"}),
        frozenset({"e1"}),
        frozenset({"e2"}),
    )
    assert result.verdict is SplitVerdict.SAFE
    assert result.embargo_ticks == 0
    assert result.embargo_violations == ()


def test_audit_temporal_evidence_rejects_negative_embargo_ticks() -> None:
    with pytest.raises(ValueError, match="embargo_ticks must be non-negative"):
        audit_temporal_evidence(
            "amlsim-20k",
            (1, 15),
            10,
            -1,
            frozenset({"a"}),
            frozenset({"b"}),
            frozenset({"e1"}),
            frozenset({"e2"}),
        )


def test_split_evidence_rejects_negative_embargo_ticks() -> None:
    with pytest.raises(ValidationError):
        SplitEvidence(
            source_id="amlsim-20k",
            verdict=SplitVerdict.SAFE,
            cutoff_tick=10,
            embargo_ticks=-1,
        )


def test_split_evidence_is_immutable() -> None:
    result = audit_temporal_evidence(
        "amlsim-20k",
        (1, 15),
        10,
        1,
        frozenset({"a"}),
        frozenset({"b"}),
        frozenset({"e1"}),
        frozenset({"e2"}),
    )
    with pytest.raises(ValidationError):
        result.verdict = SplitVerdict.BLOCKED_DATA  # type: ignore[misc]
