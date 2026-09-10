from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from fincrime.data.artifacts import write_public_artifact
from fincrime.data.provenance import sha256_file
from fincrime.tracing.candidates import generate_candidates
from fincrime.tracing.models import (
    AccountSeed,
    TraceLabError,
    TraceRequest,
    TransactionSeed,
)
from fincrime.tracing.snapshots import TraceSnapshot, load_trace_snapshot


def create_snapshot_from_events(
    tmp_path: Path,
    events: list[dict[str, object]],
    cutoff: datetime,
    sub_dir: str = "snap",
) -> TraceSnapshot:
    """Create a temporary canonical artifact and load it via load_trace_snapshot."""
    out_dir = tmp_path / sub_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = out_dir / "transactions.parquet"
    manifest_path = out_dir / "transactions.manifest.json"

    df = pl.DataFrame(
        events,
        schema={
            "edge_id": pl.String,
            "source_id": pl.String,
            "target_id": pl.String,
            "amount": pl.Float64,
            "event_time": pl.Datetime(time_zone="UTC"),
        },
    )

    conversion_params = (("time_basis", "EVENT_TIME"),)
    raw_hash = sha256_file(parquet_path) if parquet_path.exists() else "0" * 64

    manifest = write_public_artifact(
        frame=df,
        output_path=parquet_path,
        source_id="test-source",
        parent_raw_sha256=raw_hash,
        adapter_name="TestAdapter",
        adapter_version="1.0",
        conversion_parameters=conversion_params,
    )
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    return load_trace_snapshot(parquet_path, manifest_path, cutoff=cutoff)


def test_scenario_1_causal_reversal(tmp_path: Path) -> None:
    """1. Causal reversal: A->B at 10:00, B->C at 09:00, B->D at 10:05.
    Account A forward returns A->B->D, never A->B->C; rejected transition cites prefix and TEMPORAL_ORDER_VIOLATION.
    """
    cutoff = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    events = [
        {
            "edge_id": "e_ab",
            "source_id": "A",
            "target_id": "B",
            "amount": 100.0,
            "event_time": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        },
        {
            "edge_id": "e_bc",
            "source_id": "B",
            "target_id": "C",
            "amount": 50.0,
            "event_time": datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        },
        {
            "edge_id": "e_bd",
            "source_id": "B",
            "target_id": "D",
            "amount": 50.0,
            "event_time": datetime(2026, 1, 1, 10, 5, tzinfo=UTC),
        },
    ]
    snap = create_snapshot_from_events(tmp_path, events, cutoff, "s1")

    req = TraceRequest(
        seed=AccountSeed(account_id="A"),
        direction="forward",
        window_start=datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        max_hops=3,
        max_edges=10,
    )
    res = generate_candidates(snap, req)

    assert "e_ab" in res.edge_ids
    assert "e_bd" in res.edge_ids
    assert "e_bc" not in res.edge_ids

    # Check path contains A->B->D
    path_edges = [p.edge_ids for p in res.paths]
    assert ("e_ab", "e_bd") in path_edges
    assert not any("e_bc" in p.edge_ids for p in res.paths)

    # Exclusions cite TEMPORAL_ORDER_VIOLATION for e_bc
    assert res.excluded_transition_counts["TEMPORAL_ORDER_VIOLATION"] >= 1
    bc_exclusions = [ex for ex in res.excluded_transition_examples if ex.edge_id == "e_bc"]
    assert len(bc_exclusions) == 1
    assert bc_exclusions[0].reason == "TEMPORAL_ORDER_VIOLATION"


def test_scenario_2_backward_and_anchor_semantics(tmp_path: Path) -> None:
    """2. Backward and anchor semantics: S->A at 09:50, anchor A->B at 10:00, B->D at 10:05, unrelated A->X at 09:55.
    Anchor both returns [S->A, anchor] and [anchor, B->D] in money-transfer order,
    no concatenated source-to-destination claim, no A->X path, anchor counted once toward edge budget.
    """
    cutoff = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    events = [
        {
            "edge_id": "e_sa",
            "source_id": "S",
            "target_id": "A",
            "amount": 100.0,
            "event_time": datetime(2026, 1, 1, 9, 50, tzinfo=UTC),
        },
        {
            "edge_id": "e_anchor",
            "source_id": "A",
            "target_id": "B",
            "amount": 100.0,
            "event_time": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        },
        {
            "edge_id": "e_bd",
            "source_id": "B",
            "target_id": "D",
            "amount": 100.0,
            "event_time": datetime(2026, 1, 1, 10, 5, tzinfo=UTC),
        },
        {
            "edge_id": "e_ax",
            "source_id": "A",
            "target_id": "X",
            "amount": 10.0,
            "event_time": datetime(2026, 1, 1, 9, 55, tzinfo=UTC),
        },
    ]
    snap = create_snapshot_from_events(tmp_path, events, cutoff, "s2")

    req = TraceRequest(
        seed=TransactionSeed(edge_id="e_anchor"),
        direction="both",
        window_start=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        max_hops=2,
        max_edges=10,
    )
    res = generate_candidates(snap, req)

    assert "e_anchor" in res.edge_ids
    assert "e_sa" in res.edge_ids
    assert "e_bd" in res.edge_ids
    assert "e_ax" not in res.edge_ids
    assert res.edge_ids == ("e_anchor", "e_bd", "e_sa")

    # Find backward path and forward path
    backward_paths = [p for p in res.paths if p.direction == "backward" and len(p.edge_ids) > 1]
    forward_paths = [p for p in res.paths if p.direction == "forward" and len(p.edge_ids) > 1]

    assert len(backward_paths) == 1
    # Money transfer order for backward: S->A then anchor
    assert backward_paths[0].edge_ids == ("e_sa", "e_anchor")
    steps = backward_paths[0].steps
    assert steps[0].edge_id == "e_sa"
    assert steps[0].previous_edge_id is None
    assert steps[1].edge_id == "e_anchor"
    assert steps[1].previous_edge_id == "e_sa"
    assert "ANCHOR_TRANSACTION" in steps[1].reason_codes
    assert "TEMPORAL_ORDER" in steps[1].reason_codes

    assert len(forward_paths) == 1
    assert forward_paths[0].edge_ids == ("e_anchor", "e_bd")


def test_scenario_3_breadth_counterparty_fairness(tmp_path: Path) -> None:
    """3. Breadth/counterparty fairness: seed->large has three parallel transfers with high amounts,
    seed->small has one small transfer, and large->deep exists. With max_edges=2, select one edge to large
    and one to small; no deep edge. With 3 distinct direct counterparties and budget 2, cover only two in
    lexical branch order and explicitly truncate.
    """
    cutoff = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    events = [
        {
            "edge_id": "e_l1",
            "source_id": "seed",
            "target_id": "large",
            "amount": 1000.0,
            "event_time": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        },
        {
            "edge_id": "e_l2",
            "source_id": "seed",
            "target_id": "large",
            "amount": 1000.0,
            "event_time": datetime(2026, 1, 1, 10, 1, tzinfo=UTC),
        },
        {
            "edge_id": "e_l3",
            "source_id": "seed",
            "target_id": "large",
            "amount": 1000.0,
            "event_time": datetime(2026, 1, 1, 10, 2, tzinfo=UTC),
        },
        {
            "edge_id": "e_s1",
            "source_id": "seed",
            "target_id": "small",
            "amount": 1.0,
            "event_time": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        },
        {
            "edge_id": "e_deep",
            "source_id": "large",
            "target_id": "deep",
            "amount": 500.0,
            "event_time": datetime(2026, 1, 1, 10, 5, tzinfo=UTC),
        },
    ]
    snap = create_snapshot_from_events(tmp_path, events, cutoff, "s3")

    req = TraceRequest(
        seed=AccountSeed(account_id="seed"),
        direction="forward",
        window_start=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        max_hops=2,
        max_edges=2,
    )
    res = generate_candidates(snap, req)

    # Must pick one to large and one to small
    assert "e_l1" in res.edge_ids
    assert "e_s1" in res.edge_ids
    assert "e_deep" not in res.edge_ids
    assert len(res.edge_ids) == 2
    assert "EDGE_BUDGET" in res.stop_reasons
    assert res.status == "TRUNCATED"

    # Now test 3 distinct direct counterparties (c1, c2, c3) with max_edges=2
    events3 = [
        {
            "edge_id": "e_c1",
            "source_id": "seed",
            "target_id": "c1",
            "amount": 10.0,
            "event_time": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        },
        {
            "edge_id": "e_c2",
            "source_id": "seed",
            "target_id": "c2",
            "amount": 10.0,
            "event_time": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        },
        {
            "edge_id": "e_c3",
            "source_id": "seed",
            "target_id": "c3",
            "amount": 10.0,
            "event_time": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        },
    ]
    snap3 = create_snapshot_from_events(tmp_path, events3, cutoff, "s3_3")
    res3 = generate_candidates(snap3, req)
    assert res3.edge_ids == ("e_c1", "e_c2")
    assert res3.status == "TRUNCATED"
    assert "EDGE_BUDGET" in res3.stop_reasons


def test_scenario_4_alternative_arrivals_and_determinism(tmp_path: Path) -> None:
    """4. Alternative arrivals: seed->X at 08:00->B at 10:00 vs seed->Y at 08:30->B at 09:00; B->C at 09:30.
    Preserve both histories to B and admit C only from the earlier arrival.
    Shuffling event insertion order produces identical results.
    """
    cutoff = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    events_order_a = [
        {
            "edge_id": "e_sx",
            "source_id": "seed",
            "target_id": "X",
            "amount": 10.0,
            "event_time": datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
        },
        {
            "edge_id": "e_xb",
            "source_id": "X",
            "target_id": "B",
            "amount": 10.0,
            "event_time": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        },
        {
            "edge_id": "e_sy",
            "source_id": "seed",
            "target_id": "Y",
            "amount": 10.0,
            "event_time": datetime(2026, 1, 1, 8, 30, tzinfo=UTC),
        },
        {
            "edge_id": "e_yb",
            "source_id": "Y",
            "target_id": "B",
            "amount": 10.0,
            "event_time": datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        },
        {
            "edge_id": "e_bc",
            "source_id": "B",
            "target_id": "C",
            "amount": 10.0,
            "event_time": datetime(2026, 1, 1, 9, 30, tzinfo=UTC),
        },
    ]
    snap_a = create_snapshot_from_events(tmp_path, events_order_a, cutoff, "s4_a")

    req = TraceRequest(
        seed=AccountSeed(account_id="seed"),
        direction="forward",
        window_start=datetime(2026, 1, 1, 7, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        max_hops=3,
        max_edges=10,
    )
    res_a = generate_candidates(snap_a, req)

    # Both histories to B are admitted
    path_edges = [p.edge_ids for p in res_a.paths]
    assert ("e_sx", "e_xb") in path_edges
    assert ("e_sy", "e_yb") in path_edges

    # e_bc is admitted from the e_yb arrival (09:00 -> 09:30), but NOT from e_xb (10:00 -> 09:30)
    assert ("e_sy", "e_yb", "e_bc") in path_edges
    assert ("e_sx", "e_xb", "e_bc") not in path_edges

    # Reverse insertion order of events in the snapshot
    events_order_b = list(reversed(events_order_a))
    snap_b = create_snapshot_from_events(tmp_path, events_order_b, cutoff, "s4_b")
    res_b = generate_candidates(snap_b, req)

    assert res_a.edge_ids == res_b.edge_ids
    assert [p.edge_ids for p in res_a.paths] == [p.edge_ids for p in res_b.paths]


def test_scenario_5_ties_and_gap_boundaries(tmp_path: Path) -> None:
    """5. Ties and gap boundaries: equal-time consecutive edges stay with SAME_TIMESTAMP_ORDER_UNKNOWN;
    exactly max gap stays, one microsecond over does not.
    Subsecond cutoffs produce different snapshot IDs.
    """
    cutoff = datetime(2026, 1, 1, 12, 0, 0, 500000, tzinfo=UTC)
    t0 = datetime(2026, 1, 1, 10, 0, 0, 0, tzinfo=UTC)
    t_equal = datetime(2026, 1, 1, 10, 0, 0, 0, tzinfo=UTC)
    t_gap_exact = t0 + timedelta(microseconds=500)
    t_gap_over = t0 + timedelta(microseconds=501)

    events = [
        {
            "edge_id": "e_0",
            "source_id": "seed",
            "target_id": "mid1",
            "amount": 10.0,
            "event_time": t0,
        },
        {
            "edge_id": "e_equal",
            "source_id": "mid1",
            "target_id": "t1",
            "amount": 10.0,
            "event_time": t_equal,
        },
        {
            "edge_id": "e_exact",
            "source_id": "mid1",
            "target_id": "t2",
            "amount": 10.0,
            "event_time": t_gap_exact,
        },
        {
            "edge_id": "e_over",
            "source_id": "mid1",
            "target_id": "t3",
            "amount": 10.0,
            "event_time": t_gap_over,
        },
    ]
    snap = create_snapshot_from_events(tmp_path, events, cutoff, "s5")

    req = TraceRequest(
        seed=AccountSeed(account_id="seed"),
        direction="forward",
        window_start=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        max_gap_microseconds=500,
        max_hops=2,
        max_edges=10,
    )
    res = generate_candidates(snap, req)

    assert "e_equal" in res.edge_ids
    assert "e_exact" in res.edge_ids
    assert "e_over" not in res.edge_ids

    # Check reason codes on e_equal
    path_equal = next(p for p in res.paths if p.edge_ids == ("e_0", "e_equal"))
    assert "SAME_TIMESTAMP_ORDER_UNKNOWN" in path_equal.steps[1].reason_codes
    assert "WITHIN_GAP" in path_equal.steps[1].reason_codes

    # Check e_over rejection
    assert res.excluded_transition_counts["GAP_EXCEEDED"] >= 1
    over_exclusions = [ex for ex in res.excluded_transition_examples if ex.edge_id == "e_over"]
    assert len(over_exclusions) == 1
    assert over_exclusions[0].reason == "GAP_EXCEEDED"

    # Subsecond cutoff produces different snapshot IDs
    cutoff1 = datetime(2026, 1, 1, 12, 0, 0, 100000, tzinfo=UTC)
    cutoff2 = datetime(2026, 1, 1, 12, 0, 0, 200000, tzinfo=UTC)
    snap1 = create_snapshot_from_events(tmp_path, events, cutoff1, "s5_c1")
    snap2 = create_snapshot_from_events(tmp_path, events, cutoff2, "s5_c2")
    assert snap1.descriptor.snapshot_id != snap2.descriptor.snapshot_id


def test_scenario_6_cycles_and_budgets(tmp_path: Path) -> None:
    """6. Cycles and budgets: A->B->A includes closing edge once and stops prefix (CYCLE_CLOSED).
    Unresolved hop frontier reports HOP_LIMIT.
    Exhausted frontier exactly at max_edges does not spuriously report EDGE_BUDGET.
    Dense parallel-path fixture proves at most 1000 admitted states, 10000 examinations, 200 examples.
    """
    cutoff = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    events = [
        {
            "edge_id": "e_ab",
            "source_id": "A",
            "target_id": "B",
            "amount": 10.0,
            "event_time": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        },
        {
            "edge_id": "e_ba",
            "source_id": "B",
            "target_id": "A",
            "amount": 10.0,
            "event_time": datetime(2026, 1, 1, 10, 1, tzinfo=UTC),
        },
        {
            "edge_id": "e_ax",
            "source_id": "A",
            "target_id": "X",
            "amount": 10.0,
            "event_time": datetime(2026, 1, 1, 10, 2, tzinfo=UTC),
        },
    ]
    snap = create_snapshot_from_events(tmp_path, events, cutoff, "s6_cycle")

    # A->B->A
    req_cycle = TraceRequest(
        seed=AccountSeed(account_id="A"),
        direction="forward",
        window_start=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        max_hops=4,
        max_edges=10,
    )
    res_cycle = generate_candidates(snap, req_cycle)
    cycle_path = next(p for p in res_cycle.paths if p.edge_ids == ("e_ab", "e_ba"))
    assert cycle_path.terminal_reason == "CYCLE_CLOSED"
    # No path continues from e_ba to e_ax
    assert not any(p.edge_ids == ("e_ab", "e_ba", "e_ax") for p in res_cycle.paths)

    # Hop limit
    req_hop = TraceRequest(
        seed=AccountSeed(account_id="A"),
        direction="forward",
        window_start=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        max_hops=1,
        max_edges=10,
    )
    res_hop = generate_candidates(snap, req_hop)
    assert res_hop.status == "TRUNCATED"
    assert "HOP_LIMIT" in res_hop.stop_reasons
    p_ab = next(p for p in res_hop.paths if p.edge_ids == ("e_ab",))
    p_ax = next(p for p in res_hop.paths if p.edge_ids == ("e_ax",))
    assert p_ab.terminal_reason == "HOP_LIMIT"
    assert p_ax.terminal_reason == "DEAD_END"

    # Exhausted frontier exactly at max_edges does NOT spuriously report EDGE_BUDGET
    # Graph has 3 edges: e_ab, e_ba, e_ax. With max_edges=3, all 3 are admitted, and frontier is exhausted
    req_exact = TraceRequest(
        seed=AccountSeed(account_id="A"),
        direction="forward",
        window_start=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        max_hops=3,
        max_edges=3,
    )
    res_exact = generate_candidates(snap, req_exact)
    assert len(res_exact.edge_ids) == 3
    assert "EDGE_BUDGET" not in res_exact.stop_reasons
    assert res_exact.status == "EXHAUSTED_WITHIN_LIMITS"

    # Dense parallel-path fixture
    dense_events = []
    base_t = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)
    for i in range(1200):
        dense_events.append(
            {
                "edge_id": f"e_dense_{i}",
                "source_id": "seed",
                "target_id": f"dst_{i}",
                "amount": 10.0,
                "event_time": base_t + timedelta(seconds=i),
            }
        )
    snap_dense = create_snapshot_from_events(tmp_path, dense_events, cutoff, "s6_dense")
    req_dense = TraceRequest(
        seed=AccountSeed(account_id="seed"),
        direction="forward",
        window_start=datetime(2026, 1, 1, 7, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        max_hops=2,
        max_edges=100,  # capped at 100
    )
    res_dense = generate_candidates(snap_dense, req_dense)
    assert len(res_dense.edge_ids) <= 100
    assert res_dense.admitted_path_states <= 1000
    assert res_dense.examined_transitions <= 10000
    assert len(res_dense.excluded_transition_examples) <= 200


def test_scenario_7_missing_empty_invalid(tmp_path: Path) -> None:
    """7. Missing/empty/invalid: absent account/anchor returns SEED_NOT_FOUND,
    valid but window-isolated seed yields empty exhausted result,
    anchor outside window raises INVALID_REQUEST,
    reversed window raises ValueError,
    window_end > cutoff raises TraceLabError INVALID_REQUEST.
    """
    cutoff = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    events = [
        {
            "edge_id": "e1",
            "source_id": "A",
            "target_id": "B",
            "amount": 10.0,
            "event_time": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        },
    ]
    snap = create_snapshot_from_events(tmp_path, events, cutoff, "s7")

    # Absent account -> SEED_NOT_FOUND
    req_missing_acc = TraceRequest(
        seed=AccountSeed(account_id="UNKNOWN"),
        direction="forward",
        window_start=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
    )
    res_missing_acc = generate_candidates(snap, req_missing_acc)
    assert res_missing_acc.status == "SEED_NOT_FOUND"
    assert res_missing_acc.edge_ids == ()

    # Absent anchor -> SEED_NOT_FOUND
    req_missing_anc = TraceRequest(
        seed=TransactionSeed(edge_id="UNKNOWN_EDGE"),
        direction="forward",
        window_start=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
    )
    res_missing_anc = generate_candidates(snap, req_missing_anc)
    assert res_missing_anc.status == "SEED_NOT_FOUND"
    assert res_missing_anc.edge_ids == ()

    # Window-isolated seed -> EXHAUSTED_WITHIN_LIMITS with 0 edges
    req_isolated = TraceRequest(
        seed=AccountSeed(account_id="A"),
        direction="forward",
        window_start=datetime(2026, 1, 1, 6, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 7, 0, tzinfo=UTC),
    )
    res_isolated = generate_candidates(snap, req_isolated)
    assert res_isolated.status == "EXHAUSTED_WITHIN_LIMITS"
    assert res_isolated.edge_ids == ()
    assert res_isolated.excluded_transition_counts["OUTSIDE_WINDOW"] >= 1

    # Anchor outside window -> TraceLabError INVALID_REQUEST
    req_anc_outside = TraceRequest(
        seed=TransactionSeed(edge_id="e1"),
        direction="forward",
        window_start=datetime(2026, 1, 1, 6, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 7, 0, tzinfo=UTC),
    )
    with pytest.raises(TraceLabError) as exc_info:
        generate_candidates(snap, req_anc_outside)
    assert exc_info.value.code == "INVALID_REQUEST"

    # Reversed window -> ValueError from TraceRequest model
    with pytest.raises(ValueError, match="window_start must be <= window_end"):
        TraceRequest(
            seed=AccountSeed(account_id="A"),
            direction="forward",
            window_start=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
            window_end=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )

    # Window end > cutoff -> TraceLabError INVALID_REQUEST
    req_beyond_cutoff = TraceRequest(
        seed=AccountSeed(account_id="A"),
        direction="forward",
        window_start=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
    )
    with pytest.raises(TraceLabError) as exc_cutoff:
        generate_candidates(snap, req_beyond_cutoff)
    assert exc_cutoff.value.code == "INVALID_REQUEST"


def test_large_date_adjacent_microsecond_ordering(tmp_path: Path) -> None:
    """Large-date adjacent-microsecond ordering: floats collapse adjacent microseconds on large timestamps.
    Exact integer arithmetic preserves strict ordering and exact 1-microsecond deltas.
    """
    # Year 2060 timestamp (large float value where float64 microsecond precision degrades)
    t_base = datetime(2060, 6, 15, 12, 0, 0, 0, tzinfo=UTC)
    t1 = t_base
    t2 = t_base + timedelta(microseconds=1)
    t3 = t_base + timedelta(microseconds=2)
    cutoff = datetime(2060, 12, 31, 23, 59, 59, tzinfo=UTC)

    events = [
        {
            "edge_id": "e_upstream1",
            "source_id": "X1",
            "target_id": "A",
            "amount": 10.0,
            "event_time": t1,
        },
        {
            "edge_id": "e_upstream2",
            "source_id": "X2",
            "target_id": "A",
            "amount": 10.0,
            "event_time": t2,
        },
        {
            "edge_id": "e_anchor",
            "source_id": "A",
            "target_id": "B",
            "amount": 10.0,
            "event_time": t3,
        },
    ]
    snap = create_snapshot_from_events(tmp_path, events, cutoff, "s_large_date")

    # Backward query from anchor e_anchor:
    # Backward traversal explores incoming edges to A:
    # Between e_upstream1 (t1) and e_upstream2 (t2), backward order MUST examine/order e_upstream2 before e_upstream1!
    req_back = TraceRequest(
        seed=TransactionSeed(edge_id="e_anchor"),
        direction="backward",
        window_start=t_base - timedelta(days=1),
        window_end=t_base + timedelta(days=1),
        max_hops=2,
        max_edges=10,
    )
    res_back = generate_candidates(snap, req_back)

    # Both paths admitted in money-transfer order
    paths = {p.edge_ids: p for p in res_back.paths}
    assert ("e_upstream2", "e_anchor") in paths
    assert ("e_upstream1", "e_anchor") in paths

    p2 = paths[("e_upstream2", "e_anchor")]
    # Delta between t2 and t3 (t3 - t2) is EXACTLY 1 microsecond
    assert p2.steps[1].delta_microseconds == 1
    assert "TEMPORAL_ORDER" in p2.steps[1].reason_codes
    assert "SAME_TIMESTAMP_ORDER_UNKNOWN" not in p2.steps[1].reason_codes

    p1 = paths[("e_upstream1", "e_anchor")]
    # Delta between t1 and t3 (t3 - t1) is EXACTLY 2 microseconds
    assert p1.steps[1].delta_microseconds == 2


def test_long_gap_equality_and_one_microsecond_over(tmp_path: Path) -> None:
    """Long gap equality and 1-microsecond-over: 100 days gap (8_640_000_000_000 usec).
    Exactly max gap stays (WITHIN_GAP); exactly 1 microsecond over is rejected (GAP_EXCEEDED).
    """
    t0 = datetime(2050, 1, 1, 0, 0, 0, 0, tzinfo=UTC)
    exact_delta = timedelta(days=100)
    over_delta = timedelta(days=100, microseconds=1)
    max_gap_usec = 100 * 86_400_000_000  # 8,640,000,000,000 us

    t_exact = t0 + exact_delta
    t_over = t0 + over_delta
    cutoff = datetime(2050, 12, 31, tzinfo=UTC)

    events = [
        {
            "edge_id": "e_start",
            "source_id": "A",
            "target_id": "B",
            "amount": 100.0,
            "event_time": t0,
        },
        {
            "edge_id": "e_exact",
            "source_id": "B",
            "target_id": "C",
            "amount": 100.0,
            "event_time": t_exact,
        },
        {
            "edge_id": "e_over",
            "source_id": "B",
            "target_id": "D",
            "amount": 100.0,
            "event_time": t_over,
        },
    ]
    snap = create_snapshot_from_events(tmp_path, events, cutoff, "s_long_gap")

    req = TraceRequest(
        seed=AccountSeed(account_id="A"),
        direction="forward",
        window_start=t0 - timedelta(days=1),
        window_end=t_over + timedelta(days=1),
        max_gap_microseconds=max_gap_usec,
        max_hops=2,
        max_edges=10,
    )
    res = generate_candidates(snap, req)

    assert "e_exact" in res.edge_ids
    assert "e_over" not in res.edge_ids

    p_exact = next(p for p in res.paths if p.edge_ids == ("e_start", "e_exact"))
    assert p_exact.steps[1].delta_microseconds == max_gap_usec
    assert "WITHIN_GAP" in p_exact.steps[1].reason_codes

    assert res.excluded_transition_counts["GAP_EXCEEDED"] >= 1
    over_ex = [ex for ex in res.excluded_transition_examples if ex.edge_id == "e_over"]
    assert len(over_ex) == 1
    assert over_ex[0].reason == "GAP_EXCEEDED"
