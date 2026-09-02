from __future__ import annotations

import pytest
from pydantic import ValidationError

from fincrime.streaming.state import ReplayConflict, ReplayState


def test_empty_replay_state() -> None:
    state = ReplayState.empty()
    assert state.event_entries == ()
    assert state.partition_offsets == ()
    assert state.get_offset("tx", 0) == 0
    assert state.get_entry("evt_unknown") is None
    assert state.get_hash("evt_unknown") is None


def test_apply_contiguous_event_advances_state() -> None:
    state0 = ReplayState.empty()
    state1 = state0.apply("tx", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64)
    assert state1.get_offset("tx", 0) == 1
    assert state1.get_hash("evt_1") == "a" * 64
    assert state1.get_entry("evt_1") == ("evt_1", "tx", 0, 0, "a" * 64)

    state2 = state1.apply("tx", partition=0, offset=1, event_id="evt_2", payload_hash="b" * 64)
    assert state2.get_offset("tx", 0) == 2
    assert state2.get_hash("evt_2") == "b" * 64
    assert state2.get_entry("evt_2") == ("evt_2", "tx", 0, 1, "b" * 64)

    # Multi-partition tracking
    state3 = state2.apply("tx", partition=1, offset=0, event_id="evt_3", payload_hash="c" * 64)
    assert state3.get_offset("tx", 0) == 2
    assert state3.get_offset("tx", 1) == 1


def test_identical_event_retry_at_same_coordinate_is_true_noop() -> None:
    state1 = ReplayState.empty().apply(
        "tx", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64
    )
    state2 = state1.apply("tx", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64)
    assert state1 == state2
    assert state1 is state2


def test_conflicting_event_payload_raises_conflict() -> None:
    state = ReplayState.empty().apply(
        "tx", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64
    )
    with pytest.raises(ReplayConflict) as exc_info:
        state.apply("tx", partition=0, offset=0, event_id="evt_1", payload_hash="c" * 64)
    assert "evt_1" in str(exc_info.value)
    assert "Conflicting retry" in str(exc_info.value)


def test_duplicate_event_id_at_different_offset_raises_conflict() -> None:
    state = ReplayState.empty().apply(
        "tx", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64
    )
    with pytest.raises(ReplayConflict) as exc_info:
        state.apply("tx", partition=0, offset=1, event_id="evt_1", payload_hash="a" * 64)
    assert "evt_1" in str(exc_info.value)


def test_duplicate_event_id_at_different_partition_or_topic_raises_conflict() -> None:
    state = ReplayState.empty().apply(
        "tx", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64
    )
    with pytest.raises(ReplayConflict):
        state.apply("tx", partition=1, offset=0, event_id="evt_1", payload_hash="a" * 64)
    with pytest.raises(ReplayConflict):
        state.apply("other_topic", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64)


def test_non_contiguous_offset_jumps_raise_conflict() -> None:
    state0 = ReplayState.empty()
    with pytest.raises(ReplayConflict) as exc_info:
        state0.apply("tx", partition=0, offset=1, event_id="evt_1", payload_hash="a" * 64)
    assert "Non-contiguous offset" in str(exc_info.value)
    assert "expected 0, got 1" in str(exc_info.value)

    state1 = state0.apply("tx", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64)
    with pytest.raises(ReplayConflict) as exc_info2:
        state1.apply("tx", partition=0, offset=5, event_id="evt_2", payload_hash="b" * 64)
    assert "expected 1, got 5" in str(exc_info2.value)


def test_apply_path_validates_blank_and_negative_inputs() -> None:
    state = ReplayState.empty()
    with pytest.raises(ValueError):
        state.apply("tx", partition=-1, offset=0, event_id="evt_1", payload_hash="a" * 64)
    with pytest.raises(ValueError):
        state.apply("tx", partition=0, offset=-1, event_id="evt_1", payload_hash="a" * 64)
    with pytest.raises(ValueError):
        state.apply("", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64)
    with pytest.raises(ValueError):
        state.apply("   ", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64)
    with pytest.raises(ValueError):
        state.apply("tx", partition=0, offset=0, event_id="", payload_hash="a" * 64)
    with pytest.raises(ValueError):
        state.apply("tx", partition=0, offset=0, event_id="   ", payload_hash="a" * 64)
    with pytest.raises(ValueError):
        state.apply("tx", partition=0, offset=0, event_id="evt_1", payload_hash="A" * 64)
    with pytest.raises(ValueError):
        state.apply("tx", partition=0, offset=0, event_id="evt_1", payload_hash="short")


def test_direct_construction_invariants_enforced() -> None:
    # Duplicate event_id
    with pytest.raises(ValidationError):
        ReplayState(
            event_entries=(("evt_1", "tx", 0, 0, "a" * 64), ("evt_1", "tx", 0, 1, "a" * 64)),
            partition_offsets=(("tx", 0, 1),),
        )

    # Unsorted event_entries
    with pytest.raises(ValidationError):
        ReplayState(
            event_entries=(("evt_2", "tx", 0, 1, "b" * 64), ("evt_1", "tx", 0, 0, "a" * 64)),
            partition_offsets=(("tx", 0, 2),),
        )

    # Duplicate partition keys
    with pytest.raises(ValidationError):
        ReplayState(
            event_entries=(("evt_1", "tx", 0, 0, "a" * 64),),
            partition_offsets=(("tx", 0, 1), ("tx", 0, 2)),
        )

    # Unsorted partition_offsets
    with pytest.raises(ValidationError):
        ReplayState(
            event_entries=(),
            partition_offsets=(("tx", 1, 1), ("tx", 0, 1)),
        )

    # Blank and negative fields in direct construction
    with pytest.raises(ValidationError):
        ReplayState(
            event_entries=(("", "tx", 0, 0, "a" * 64),),
            partition_offsets=(),
        )
    with pytest.raises(ValidationError):
        ReplayState(
            event_entries=(("evt_1", "tx", -1, 0, "a" * 64),),
            partition_offsets=(),
        )
    with pytest.raises(ValidationError):
        ReplayState(
            event_entries=(("evt_1", "tx", 0, 0, "INVALID_HASH"),),
            partition_offsets=(),
        )


def test_immutability_and_forbid_extra() -> None:
    state = ReplayState.empty()
    with pytest.raises(ValidationError):
        state.event_entries = ()

    with pytest.raises(ValidationError):
        ReplayState(extra="forbidden")  # type: ignore[call-arg]
