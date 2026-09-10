from __future__ import annotations

import json
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import networkx as nx  # type: ignore[import-untyped]
import polars as pl

from fincrime.data.adapters import CANONICAL_COLUMNS, AMLSimSampleAdapter
from fincrime.data.artifacts import write_public_artifact
from fincrime.data.provenance import DerivedArtifactManifest, sha256_file
from fincrime.evidence.models import compute_sha256_hex
from fincrime.graph.build import build_graph
from fincrime.graph.events import TransactionEvent
from fincrime.tracing.models import (
    SnapshotDescriptor,
    TraceLabError,
    datetime_to_descending_usec,
    duration_microseconds,
    format_iso_datetime,
)


@dataclass(frozen=True)
class TraceSnapshot:
    descriptor: SnapshotDescriptor
    _graph: nx.MultiDiGraph
    _events_by_id: dict[str, TransactionEvent]
    _edge_endpoints: dict[str, tuple[str, str]]
    _forward_adj: dict[str, dict[str, tuple[str, ...]]]
    _backward_adj: dict[str, dict[str, tuple[str, ...]]]
    _accounts: frozenset[str]

    @property
    def cutoff(self) -> datetime:
        return self.descriptor.cutoff

    def has_account(self, account_id: str) -> bool:
        return account_id in self._accounts

    def has_edge(self, edge_id: str) -> bool:
        return edge_id in self._events_by_id

    def get_event(self, edge_id: str) -> TransactionEvent | None:
        return self._events_by_id.get(edge_id)

    def get_endpoints(self, edge_id: str) -> tuple[str, str]:
        endpoints = self._edge_endpoints.get(edge_id)
        if endpoints is None:
            raise KeyError(f"Edge {edge_id} not found in snapshot")
        return endpoints

    def get_forward_counterparties(self, account_id: str) -> tuple[str, ...]:
        adj = self._forward_adj.get(account_id)
        if not adj:
            return ()
        return tuple(sorted(adj.keys()))

    def get_forward_edges(self, account_id: str, counterparty_id: str) -> tuple[str, ...]:
        adj = self._forward_adj.get(account_id)
        if not adj:
            return ()
        return adj.get(counterparty_id, ())

    def get_backward_counterparties(self, account_id: str) -> tuple[str, ...]:
        adj = self._backward_adj.get(account_id)
        if not adj:
            return ()
        return tuple(sorted(adj.keys()))

    def get_backward_edges(self, account_id: str, counterparty_id: str) -> tuple[str, ...]:
        adj = self._backward_adj.get(account_id)
        if not adj:
            return ()
        return adj.get(counterparty_id, ())

    def get_incident_edge_count(self, account_id: str, direction: str) -> int:
        if direction == "forward":
            adj = self._forward_adj.get(account_id)
            if not adj:
                return 0
            return sum(len(edges) for edges in adj.values())
        if direction == "backward":
            adj = self._backward_adj.get(account_id)
            if not adj:
                return 0
            return sum(len(edges) for edges in adj.values())
        return 0


def validate_contained_path(raw: str | Path) -> Path:
    """Validate that path resolves to an absolute path within allowed filesystem boundaries."""
    resolved = Path(raw).resolve()
    cwd = Path.cwd().resolve()
    allowed_roots: list[Path] = [
        cwd,
        *cwd.parents,
        Path(tempfile.gettempdir()).resolve(),
    ]

    anchor = Path(resolved.anchor).resolve()
    if anchor.exists():
        allowed_roots.append(anchor)

    for root in allowed_roots:
        try:
            if resolved.is_relative_to(root):
                return resolved
        except (ValueError, TypeError):
            continue

    allowed_desc = " or ".join(str(r) for r in allowed_roots[:3])
    raise ValueError(f"Path {str(raw)!r} resolves outside allowed boundaries: {allowed_desc}")


def import_amlsim_snapshot(
    archive_path: Path,
    manifest_path: Path,
    output_path: Path,
    *,
    observation_start: datetime,
    tick_duration: timedelta,
) -> DerivedArtifactManifest:
    """Import AMLSim sample archive into canonical Parquet and write lineage manifest."""
    archive_path = validate_contained_path(archive_path)
    manifest_path = validate_contained_path(manifest_path)
    output_path = validate_contained_path(output_path)
    lineage_path = validate_contained_path(output_path.with_suffix(".manifest.json"))
    if output_path.exists() or lineage_path.exists():
        raise TraceLabError(
            "OUTPUT_EXISTS",
            f"Target output path or manifest already exists: {output_path}",
        )

    if not manifest_path.exists():
        raise TraceLabError("IO_ERROR", f"Manifest file does not exist: {manifest_path}")
    if not archive_path.exists():
        raise TraceLabError("IO_ERROR", f"Archive file does not exist: {archive_path}")
    try:
        manifest_raw = manifest_path.read_text(encoding="utf-8")
        manifest_data = json.loads(manifest_raw)
    except Exception as err:
        raise TraceLabError("INVALID_SOURCE", f"Failed to read/parse manifest: {err}") from err

    if manifest_data.get("dataset_id") != "amlsim-20k-fanin200":
        raise TraceLabError(
            "INVALID_SOURCE",
            f"Expected dataset_id 'amlsim-20k-fanin200', got {manifest_data.get('dataset_id')!r}",
        )
    if manifest_data.get("schema_header") != "sourceNodeId,targetNodeId,value,time":
        raise TraceLabError(
            "INVALID_SOURCE",
            f"Expected schema_header 'sourceNodeId,targetNodeId,value,time', got {manifest_data.get('schema_header')!r}",
        )

    expected_sha256 = manifest_data.get("sha256")
    actual_archive_sha256 = sha256_file(archive_path)
    if actual_archive_sha256 != expected_sha256:
        raise TraceLabError(
            "SOURCE_HASH_MISMATCH",
            f"Archive SHA256 mismatch: expected {expected_sha256}, got {actual_archive_sha256}",
        )

    try:
        with tarfile.open(archive_path, "r:*") as tar:
            csv_members = [
                m for m in tar.getmembers() if Path(m.name).name == "transactions.csv" and m.isreg()
            ]
            if len(csv_members) != 1:
                raise TraceLabError(
                    "INVALID_SOURCE",
                    f"Expected exactly 1 regular 'transactions.csv' in archive, found {len(csv_members)}",
                )
            member = csv_members[0]
            member_f = tar.extractfile(member)
            if member_f is None:
                raise TraceLabError("INVALID_SOURCE", "Could not extract transactions.csv member")
            source_df = pl.read_csv(member_f)
    except TraceLabError:
        raise
    except Exception as err:
        raise TraceLabError("INVALID_SOURCE", f"Failed reading archive: {err}") from err

    adapter = AMLSimSampleAdapter(
        observation_start=observation_start,
        tick_duration=tick_duration,
        edge_id_prefix="amlsim:",
    )
    try:
        canonical_df = adapter.transactions(source_df)
    except Exception as err:
        raise TraceLabError("INVALID_SOURCE", f"Adapter transformation failed: {err}") from err

    expected_count = manifest_data.get("transactions_count")
    if expected_count is not None and canonical_df.height != expected_count:
        raise TraceLabError(
            "INVALID_SOURCE",
            f"Transaction count mismatch: expected {expected_count}, got {canonical_df.height}",
        )

    source_manifest_sha256 = sha256_file(manifest_path)
    tick_usec = duration_microseconds(tick_duration)
    obs_start_str = format_iso_datetime(observation_start)

    conversion_params: tuple[tuple[str, str], ...] = (
        ("archive_member", member.name),
        ("edge_id_prefix", "amlsim:"),
        ("observation_start", obs_start_str),
        ("source_manifest_sha256", source_manifest_sha256),
        ("tick_duration_microseconds", str(tick_usec)),
        ("time_basis", "SYNTHETIC_TICKS"),
    )

    created_paths: list[Path] = []
    try:
        lineage = write_public_artifact(
            frame=canonical_df,
            output_path=output_path,
            source_id=manifest_data.get("dataset_id", "amlsim-20k-fanin200"),
            parent_raw_sha256=actual_archive_sha256,
            adapter_name="AMLSimSampleAdapter",
            adapter_version="1.0",
            conversion_parameters=conversion_params,
        )
        created_paths.append(output_path)
        lineage_json = json.dumps(
            lineage.model_dump(mode="python"),
            indent=2,
            sort_keys=True,
        )
        lineage_path.write_text(lineage_json, encoding="utf-8")
        created_paths.append(lineage_path)
        return lineage
    except Exception as err:
        for p in created_paths:
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
        if isinstance(err, TraceLabError):
            raise
        if isinstance(err, FileExistsError):
            raise TraceLabError("OUTPUT_EXISTS", str(err)) from err
        raise TraceLabError("IO_ERROR", f"Failed writing artifact/manifest: {err}") from err


def load_trace_snapshot(
    artifact_path: Path,
    lineage_path: Path,
    *,
    cutoff: datetime,
) -> TraceSnapshot:
    """Load an immutable trace snapshot index from canonical Parquet and lineage manifest."""
    artifact_path = validate_contained_path(artifact_path)
    lineage_path = validate_contained_path(lineage_path)
    if not artifact_path.exists():
        raise TraceLabError("IO_ERROR", f"Artifact file does not exist: {artifact_path}")
    if not lineage_path.exists():
        raise TraceLabError("IO_ERROR", f"Lineage file does not exist: {lineage_path}")

    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise TraceLabError("INVALID_REQUEST", "Cutoff datetime must be timezone-aware")
    cutoff_utc = cutoff.astimezone(UTC)

    try:
        lineage_bytes = lineage_path.read_bytes()
        lineage_data = json.loads(lineage_bytes.decode("utf-8"))
        lineage = DerivedArtifactManifest.model_validate(lineage_data)
    except Exception as err:
        raise TraceLabError(
            "INVALID_SOURCE", f"Failed to read/validate lineage manifest: {err}"
        ) from err

    actual_artifact_sha256 = sha256_file(artifact_path)
    if actual_artifact_sha256 != lineage.output_sha256:
        raise TraceLabError(
            "SOURCE_HASH_MISMATCH",
            f"Artifact SHA256 mismatch: expected {lineage.output_sha256}, got {actual_artifact_sha256}",
        )
    lineage_sha256 = sha256_file(lineage_path)

    try:
        df = pl.read_parquet(artifact_path)
    except Exception as err:
        raise TraceLabError("INVALID_SOURCE", f"Failed to read parquet artifact: {err}") from err

    if lineage.public_columns != CANONICAL_COLUMNS:
        raise TraceLabError(
            "INVALID_SOURCE",
            f"Lineage public_columns mismatch: expected {CANONICAL_COLUMNS}, got {lineage.public_columns}",
        )
    if tuple(df.columns) != lineage.public_columns:
        raise TraceLabError(
            "INVALID_SOURCE",
            f"Parquet columns do not match lineage public_columns: expected {lineage.public_columns}, got {tuple(df.columns)}",
        )
    if df.height != lineage.row_count:
        raise TraceLabError(
            "INVALID_SOURCE",
            f"Parquet row count ({df.height}) does not match lineage row count ({lineage.row_count})",
        )

    # Validate canonical column types and values
    for col_name in ("edge_id", "source_id", "target_id"):
        if df.schema[col_name].base_type() not in (pl.String, pl.Utf8):
            raise TraceLabError(
                "INVALID_SOURCE",
                f"Canonical column '{col_name}' must be string type, got {df.schema[col_name]}",
            )
        if df[col_name].null_count() > 0:
            raise TraceLabError(
                "INVALID_SOURCE",
                f"Canonical column '{col_name}' contains null identifier",
            )
        if df.height > 0 and (df[col_name].str.strip_chars() == "").any():
            raise TraceLabError(
                "INVALID_SOURCE",
                f"Canonical column '{col_name}' contains blank identifier",
            )

    if not df.schema["amount"].is_numeric():
        raise TraceLabError(
            "INVALID_SOURCE",
            f"Canonical column 'amount' must be numeric type, got {df.schema['amount']}",
        )
    if df["amount"].null_count() > 0:
        raise TraceLabError(
            "INVALID_SOURCE",
            "Canonical column 'amount' contains null values",
        )
    if df.schema["amount"].is_float() and df.height > 0 and not df["amount"].is_finite().all():
        raise TraceLabError(
            "INVALID_SOURCE",
            "Canonical column 'amount' contains non-finite values",
        )
    if df.height > 0 and (df["amount"] <= 0).any():
        raise TraceLabError(
            "INVALID_SOURCE",
            "Canonical column 'amount' must be strictly positive",
        )

    dt_dtype = df.schema["event_time"]
    if dt_dtype.base_type() != pl.Datetime:
        raise TraceLabError(
            "INVALID_SOURCE",
            f"Canonical column 'event_time' must be datetime type, got {dt_dtype}",
        )
    if (
        not isinstance(dt_dtype, pl.Datetime)
        or dt_dtype.time_zone is None
        or dt_dtype.time_zone == ""
    ):
        raise TraceLabError(
            "INVALID_SOURCE",
            "Canonical column 'event_time' must be timezone-aware",
        )
    if df["event_time"].null_count() > 0:
        raise TraceLabError(
            "INVALID_SOURCE",
            "Canonical column 'event_time' contains null values",
        )

    # Validate parameters from lineage
    params_dict = dict(lineage.conversion_parameters)
    time_basis_str = params_dict.get("time_basis")
    obs_start: datetime | None = None
    tick_usec: int | None = None

    if lineage.adapter_name == "AMLSimSampleAdapter" or time_basis_str == "SYNTHETIC_TICKS":
        if (
            "observation_start" not in params_dict
            or "tick_duration_microseconds" not in params_dict
        ):
            raise TraceLabError(
                "INVALID_SOURCE",
                "Lineage for synthetic ticks artifact missing required time parameters",
            )
        try:
            obs_start = datetime.fromisoformat(params_dict["observation_start"]).astimezone(UTC)
            tick_usec = int(params_dict["tick_duration_microseconds"])
            if tick_usec <= 0:
                raise ValueError("tick_duration_microseconds must be > 0")
        except Exception as err:
            raise TraceLabError(
                "INVALID_SOURCE",
                f"Malformed synthetic time parameters in lineage: {err}",
            ) from err
        time_basis = "SYNTHETIC_TICKS"
    else:
        time_basis = "EVENT_TIME"

    # Construct strict TransactionEvent objects
    events: list[TransactionEvent] = []
    seen_ids: set[str] = set()
    edge_ids = df["edge_id"].to_list()
    source_ids = df["source_id"].to_list()
    target_ids = df["target_id"].to_list()
    amounts = df["amount"].to_list()
    time_usecs = df["event_time"].dt.timestamp("us").to_list()

    for edge_id, src, dst, amt, ts_usec in zip(
        edge_ids, source_ids, target_ids, amounts, time_usecs, strict=True
    ):
        if ts_usec is None:
            raise TraceLabError(
                "INVALID_SOURCE", f"Transaction row '{edge_id}' has null event_time"
            )
        sec, usec = divmod(ts_usec, 1_000_000)
        dt = datetime.fromtimestamp(sec, tz=UTC).replace(microsecond=usec)
        try:
            event = TransactionEvent(
                edge_id=edge_id,
                source_id=src,
                target_id=dst,
                amount=float(amt),
                event_time=dt,
            )
        except Exception as err:
            raise TraceLabError("INVALID_SOURCE", f"Malformed transaction row: {err}") from err

        if event.edge_id in seen_ids:
            raise TraceLabError("INVALID_SOURCE", f"Duplicate edge_id: {event.edge_id}")
        seen_ids.add(event.edge_id)
        events.append(event)

    # Build point-in-time graph
    try:
        graph = build_graph(events, cutoff_utc)
    except Exception as err:
        raise TraceLabError(
            "INVALID_SOURCE", f"Failed building point-in-time graph: {err}"
        ) from err
    nx.freeze(graph)

    events_by_id: dict[str, TransactionEvent] = {}
    edge_endpoints: dict[str, tuple[str, str]] = {}
    forward_adj: dict[str, dict[str, list[tuple[datetime, str]]]] = {}
    backward_adj: dict[str, dict[str, list[tuple[datetime, str]]]] = {}
    accounts: set[str] = set()

    for event in events:
        ev_time = event.event_time.astimezone(UTC)
        if ev_time > cutoff_utc:
            continue
        events_by_id[event.edge_id] = event
        edge_endpoints[event.edge_id] = (event.source_id, event.target_id)
        accounts.add(event.source_id)
        accounts.add(event.target_id)

        # Forward adjacency: source -> target
        if event.source_id not in forward_adj:
            forward_adj[event.source_id] = {}
        if event.target_id not in forward_adj[event.source_id]:
            forward_adj[event.source_id][event.target_id] = []
        forward_adj[event.source_id][event.target_id].append((ev_time, event.edge_id))

        # Backward adjacency: target -> source
        if event.target_id not in backward_adj:
            backward_adj[event.target_id] = {}
        if event.source_id not in backward_adj[event.target_id]:
            backward_adj[event.target_id][event.source_id] = []
        backward_adj[event.target_id][event.source_id].append((ev_time, event.edge_id))

    # Sort forward edge IDs by (event_time ASC, edge_id ASC)
    frozen_forward: dict[str, dict[str, tuple[str, ...]]] = {}
    for src, cparties in forward_adj.items():
        frozen_forward[src] = {}
        for dst, edge_list in cparties.items():
            edge_list.sort(key=lambda item: (item[0], item[1]))
            frozen_forward[src][dst] = tuple(e_id for _, e_id in edge_list)

    # Sort backward edge IDs by (event_time DESC, edge_id ASC)
    frozen_backward: dict[str, dict[str, tuple[str, ...]]] = {}
    for dst, cparties in backward_adj.items():
        frozen_backward[dst] = {}
        for src, edge_list in cparties.items():
            # For backward traversal, most recent first, with edge_id tie-break ascending
            edge_list.sort(key=lambda item: (datetime_to_descending_usec(item[0]), item[1]))
            frozen_backward[dst][src] = tuple(e_id for _, e_id in edge_list)

    # Compute snapshot_id: SHA256 of canonical bytes for {artifact_sha256,lineage_sha256,cutoff}
    cutoff_iso = format_iso_datetime(cutoff_utc)
    id_payload = {
        "artifact_sha256": actual_artifact_sha256,
        "cutoff": cutoff_iso,
        "lineage_sha256": lineage_sha256,
    }
    snapshot_id = compute_sha256_hex(id_payload)

    descriptor = SnapshotDescriptor(
        snapshot_id=snapshot_id,
        source_id=lineage.source_id,
        artifact_sha256=actual_artifact_sha256,
        lineage_sha256=lineage_sha256,
        cutoff=cutoff_utc,
        transaction_count=len(events_by_id),
        time_basis=time_basis,
        observation_start=obs_start,
        tick_duration_microseconds=tick_usec,
    )

    return TraceSnapshot(
        descriptor=descriptor,
        _graph=graph,
        _events_by_id=events_by_id,
        _edge_endpoints=edge_endpoints,
        _forward_adj=frozen_forward,
        _backward_adj=frozen_backward,
        _accounts=frozenset(accounts),
    )
