# Detection Pilot Data Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AMLSim and a future bounded AMLBench slice reproducible detection/graph pilot inputs, with executable provenance, capacity, extraction, public-artifact, and evidence gates.

**Architecture:** Keep the existing immutable `DatasetManifest` contract unchanged. Add pilot-specific source and derived-artifact records, then route every source through capacity admission, checksum verification, safe extraction, source-specific canonicalization, public-field allowlisting, and evidence writing. AMLSim stays synthetic-relative detection/graph data; AMLBench acquisition is refused locally until its exact archive and resource preflight are admissible.

**Tech Stack:** Python 3.12, stdlib `zipfile`/`hashlib`/`pathlib`, Pydantic 2, Polars, pytest, Ruff, MyPy.

## Global Constraints

- Raw and processed datasets stay under ignored `data/raw/` and `data/processed/`; never commit payloads.
- All source and derived byte hashes are lowercase SHA-256 strings.
- Use only HTTPS source URLs pinned by revision and checksum.
- A capacity decision must be `READY` before any remote archive download or extraction; otherwise return `SKIPPED_BY_RESOURCE` without downloading.
- AMLBench full archives are prohibited on the current disk; only a future, pinned, resource-admitted small slice may be acquired.
- Public model frames contain only `edge_id`, `source_id`, `target_id`, `amount`, and `event_time`.
- Raw rows are never silently coerced or dropped; accepted and rejected row counts must reconcile to the raw input count.
- `isFraud`, `fraudStep`, scenario/case fields, source labels, and split masks are denied from public/model artifacts.
- AMLSim 20K exact duplicates are reported but retained because it has no stable source transaction ID; outliers are profile-only.
- AMLSim relative ticks require explicit synthetic epoch and duration and must never be described as source-observed calendar time.
- `UNKNOWN` is never a negative; no pilot artifact may claim learned-tracing or Research Release evidence.
- Every task follows RED → GREEN → REFACTOR and ends in a recoverable commit after `uv run pytest -q`, `uv run ruff check .`, `uv run mypy src`, and `git diff --check`.

---

### Task 1: Define executable source and derived-artifact manifests

**Files:**
- Create: `src/fincrime/data/provenance.py`
- Create: `tests/data/test_provenance.py`

**Interfaces:**
- Produces `SourceManifest`, `DerivedArtifactManifest`, `sha256_header(header: str) -> str`, and `sha256_file(path: Path) -> str`.
- `SourceManifest` records source ID, HTTPS URL, revision, license, retrieval timestamp, raw hash, schema hash, extraction selector, intended use, prohibited claims, and limitations.
- `DerivedArtifactManifest` records parent raw hash, adapter name/version, conversion parameters, output hash, row count, and public columns.

- [ ] **Step 1: Write failing source-manifest tests**

```python
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fincrime.data.provenance import SourceManifest


def test_source_manifest_rejects_non_https_and_non_hash_values() -> None:
    with pytest.raises(ValidationError):
        SourceManifest(
            source_id="amlsim-20k-fanin200",
            source_url="http://example.invalid/data",
            revision="7338a4b",
            license="Apache-2.0",
            retrieved_at=datetime(2026, 8, 31, tzinfo=UTC),
            raw_sha256="not-a-hash",
            schema_sha256="b" * 64,
            extraction_selector="sample/20K_fanin200.tgz",
            intended_use="detection_graph_pilot",
            prohibited_claims=("learned_tracing",),
            limitations=("synthetic",),
        )
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/data/test_provenance.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'fincrime.data.provenance'`.

- [ ] **Step 3: Implement immutable provenance records**

```python
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, HttpUrl, StringConstraints, field_validator

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class SourceManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_id: NonBlank
    source_url: HttpUrl
    revision: NonBlank
    license: NonBlank
    retrieved_at: AwareDatetime
    raw_sha256: Hash
    schema_sha256: Hash
    extraction_selector: NonBlank
    intended_use: NonBlank
    prohibited_claims: tuple[NonBlank, ...]
    limitations: tuple[NonBlank, ...]

    @field_validator("source_url")
    @classmethod
    def require_https(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("source_url must use HTTPS")
        return value


class DerivedArtifactManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_id: NonBlank
    parent_raw_sha256: Hash
    adapter_name: NonBlank
    adapter_version: NonBlank
    conversion_parameters: tuple[tuple[NonBlank, NonBlank], ...]
    output_sha256: Hash
    row_count: int = Field(ge=0)
    public_columns: tuple[NonBlank, ...]


def sha256_header(header: str) -> str:
    return sha256(header.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/data/test_provenance.py -v && uv run mypy src`

Expected: source records reject invalid URLs/hashes and are immutable.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/data/provenance.py tests/data/test_provenance.py
git commit -m "feat(data): record immutable pilot provenance"
```

### Task 2: Add capacity admission before acquisition

**Files:**
- Create: `src/fincrime/data/capacity.py`
- Create: `tests/data/test_capacity.py`

**Interfaces:**
- Consumes `disk_free_bytes`, `archive_bytes`, `extraction_bytes`, `processed_bytes`, `temporary_bytes`, and `safety_headroom_bytes`.
- Produces `CapacityDecision(status: Literal["READY", "SKIPPED_BY_RESOURCE"], required_bytes: int, available_bytes: int)`.

- [ ] **Step 1: Write failing capacity test**

```python
from fincrime.data.capacity import capacity_decision


def test_capacity_decision_skips_oversized_archive_before_download() -> None:
    result = capacity_decision(
        disk_free_bytes=9_000,
        archive_bytes=7_000,
        extraction_bytes=7_000,
        processed_bytes=2_000,
        temporary_bytes=1_000,
        safety_headroom_bytes=1_000,
    )
    assert result.status == "SKIPPED_BY_RESOURCE"
    assert result.required_bytes == 18_000
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/data/test_capacity.py -v`

Expected: FAIL with missing module.

- [ ] **Step 3: Implement the pure capacity gate**

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CapacityDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    status: Literal["READY", "SKIPPED_BY_RESOURCE"]
    required_bytes: int = Field(ge=0)
    available_bytes: int = Field(ge=0)


def capacity_decision(
    *, disk_free_bytes: int, archive_bytes: int, extraction_bytes: int,
    processed_bytes: int, temporary_bytes: int, safety_headroom_bytes: int,
) -> CapacityDecision:
    values = (disk_free_bytes, archive_bytes, extraction_bytes, processed_bytes,
              temporary_bytes, safety_headroom_bytes)
    if any(value < 0 for value in values):
        raise ValueError("capacity values must be non-negative")
    required = archive_bytes + extraction_bytes + processed_bytes + temporary_bytes + safety_headroom_bytes
    return CapacityDecision(
        status="READY" if disk_free_bytes >= required else "SKIPPED_BY_RESOURCE",
        required_bytes=required,
        available_bytes=disk_free_bytes,
    )
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/data/test_capacity.py -v`

Expected: `READY` and `SKIPPED_BY_RESOURCE` cases pass without filesystem writes.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/data/capacity.py tests/data/test_capacity.py
git commit -m "feat(data): gate acquisition on local capacity"
```

### Task 3: Verify archives and safely extract a selected member

**Files:**
- Create: `src/fincrime/data/archive.py`
- Create: `tests/data/test_archive.py`

**Interfaces:**
- Consumes a local ZIP archive, expected archive SHA-256, allowed member names, and byte/file-count caps.
- Produces `extract_verified_members(...) -> tuple[Path, ...]`.
- Rejects checksum mismatch, absolute/traversal members, unexpected members, file-count overflow, and extracted-byte overflow before writing outside `destination`.

- [ ] **Step 1: Write failing traversal test**

```python
from hashlib import sha256
import zipfile
from pathlib import Path

import pytest

from fincrime.data.archive import extract_verified_members


def test_extract_rejects_path_traversal_member(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../escape.csv", "x")
    with pytest.raises(ValueError, match="unsafe archive member"):
        extract_verified_members(
            archive,
            sha256(archive.read_bytes()).hexdigest(),
            {"transactions.csv"},
            tmp_path / "out",
            1,
            1024,
        )
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/data/test_archive.py -v`

Expected: FAIL with missing module.

- [ ] **Step 3: Implement safe member validation**

```python
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZipInfo

from fincrime.data.provenance import sha256_file


def extract_verified_members(
    archive: Path,
    expected_sha256: str,
    allowed_members: set[str],
    destination: Path,
    max_files: int,
    max_bytes: int,
) -> tuple[Path, ...]:
    if sha256_file(archive) != expected_sha256:
        raise ValueError("archive checksum mismatch")
    with ZipFile(archive) as source:
        members = [member for member in source.infolist() if not member.is_dir()]
        if len(members) > max_files or sum(member.file_size for member in members) > max_bytes:
            raise ValueError("archive exceeds extraction quota")
        safe_members: list[tuple[PurePosixPath, ZipInfo]] = []
        for member in members:
            name = PurePosixPath(member.filename)
            if name.is_absolute() or ".." in name.parts:
                raise ValueError("unsafe archive member")
            if name.as_posix() not in allowed_members:
                raise ValueError("unexpected archive member")
            safe_members.append((name, member))
        root = destination.resolve()
        root.mkdir(parents=True, exist_ok=True)
        outputs: list[Path] = []
        for name, member in safe_members:
            output = (root / name).resolve()
            if root not in output.parents:
                raise ValueError("unsafe archive member")
            output.parent.mkdir(parents=True, exist_ok=True)
            with source.open(member) as input_file, output.open("xb") as output_file:
                output_file.write(input_file.read())
            outputs.append(output)
        return tuple(outputs)
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/data/test_archive.py -v && uv run ruff check src tests`

Expected: traversal, checksum, unexpected-member, and quota fixtures fail closed; a permitted tiny member extracts.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/data/archive.py tests/data/test_archive.py
git commit -m "feat(data): safely extract verified source members"
```

### Task 4: Freeze public pilot artifacts and lineage

**Files:**
- Create: `src/fincrime/data/artifacts.py`
- Create: `tests/data/test_artifacts.py`

**Interfaces:**
- Consumes a canonical Polars frame, `SourceManifest`, adapter name/version, and conversion parameters.
- Produces an ignored Parquet artifact and `DerivedArtifactManifest`.
- Public artifacts always call existing `public_transactions(frame)` before writing.

- [ ] **Step 1: Write failing lineage test**

```python
from pathlib import Path

import polars as pl

from fincrime.data.artifacts import write_public_artifact


def test_public_artifact_excludes_labels_and_records_output_hash(tmp_path: Path) -> None:
    frame = pl.DataFrame({"edge_id": ["e1"], "source_id": ["a"], "target_id": ["b"],
                          "amount": [1.0], "event_time": ["2026-01-01T00:00:00Z"],
                          "scenario_id": ["hidden"]})
    manifest = write_public_artifact(frame, tmp_path / "public.parquet", "amlsim", "raw", "adapter", "1", ())
    assert manifest.row_count == 1
    assert manifest.public_columns == ("edge_id", "source_id", "target_id", "amount", "event_time")
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/data/test_artifacts.py -v`

Expected: FAIL with missing module.

- [ ] **Step 3: Implement one-write public artifact creation**

Implement `write_public_artifact` to reject an existing output path, apply `public_transactions`, write Parquet once, hash the written file with `sha256_file`, and return `DerivedArtifactManifest`. Preserve `CANONICAL_COLUMNS` order, and reject frames that cannot supply all five canonical columns.

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/data/test_artifacts.py -v && uv run mypy src`

Expected: label-derived and unknown columns are absent from the Parquet artifact; the manifest hashes its exact bytes.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/data/artifacts.py tests/data/test_artifacts.py
git commit -m "feat(data): freeze public pilot artifacts"
```

### Task 5: Add pilot evidence and source-admission CLI

**Files:**
- Modify: `src/fincrime/cli.py`
- Create: `src/fincrime/data/pilot.py`
- Create: `tests/data/test_pilot.py`

**Interfaces:**
- `pilot_admission(...) -> PilotEvidence` combines capacity decision, source manifest, and optional derived artifact manifest.
- CLI command: `pilot-admission --workspace PATH --archive-bytes N --extraction-bytes N --processed-bytes N --temporary-bytes N --headroom-bytes N`.
- `PilotEvidence.verdict` is exactly `detection_only`; it never reports a research release or tracing approval.

- [ ] **Step 1: Write failing CLI/evidence test**

```python
from fincrime.data.pilot import pilot_admission


def test_insufficient_capacity_returns_detection_only_skipped_evidence() -> None:
    evidence = pilot_admission("amlbench-slice", 1, 9, 9, 1, 1)
    assert evidence.capacity.status == "SKIPPED_BY_RESOURCE"
    assert evidence.verdict == "detection_only"
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/data/test_pilot.py -v`

Expected: FAIL with missing module.

- [ ] **Step 3: Implement evidence without acquisition side effects**

Implement immutable `PilotEvidence` with source ID, `CapacityDecision`, and `verdict: Literal["detection_only"]`. The CLI serializes `PilotEvidence.model_dump_json(indent=2)` and performs no download or extraction. Add parser arguments exactly matching the interface.

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/data/test_pilot.py -v && uv run python -m fincrime.cli pilot-admission --workspace . --archive-bytes 7560000000 --extraction-bytes 7560000000 --processed-bytes 2000000000 --temporary-bytes 1000000000 --headroom-bytes 1000000000`

Expected: test passes; the local command returns `SKIPPED_BY_RESOURCE` and `detection_only` without downloading AMLBench.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/cli.py src/fincrime/data/pilot.py tests/data/test_pilot.py
git commit -m "feat(data): emit detection pilot admission evidence"
```

### Task 6: Produce source-quality evidence and restricted AMLSim labels

**Files:**
- Create: `src/fincrime/data/quality.py`
- Create: `src/fincrime/data/labels.py`
- Modify: `src/fincrime/data/tracebench.py`, `src/fincrime/data/artifacts.py`
- Create: `tests/data/test_quality.py`, `tests/data/test_labels.py`

**Interfaces:**
- `profile_amlsim_rows(frame: pl.DataFrame, raw_sha256: str) -> QualityReport` returns immutable schema/profile, accepted/rejected/duplicate counts, and sorted reason counts.
- `account_labels(nodes: pl.DataFrame) -> pl.DataFrame` returns exactly `account_id`, `is_fraud`, `label_provenance`.
- `write_clean_artifact(...) -> DerivedArtifactManifest` writes accepted canonical rows once and includes the quality-report hash in `conversion_parameters`.

- [ ] **Step 1: Write failing quality and label-isolation tests**

```python
import polars as pl

from fincrime.data.labels import account_labels
from fincrime.data.quality import profile_amlsim_rows
from fincrime.data.tracebench import public_transactions


def test_quality_counts_reconcile_and_duplicates_are_retained() -> None:
    report = profile_amlsim_rows(
        pl.DataFrame({"sourceNodeId": ["a", "a", ""], "targetNodeId": ["b", "b", "c"],
                      "value": [1.0, 1.0, -1.0], "time": [1, 1, 2]}), "a" * 64,
    )
    assert (report.input_rows, report.accepted_rows, report.rejected_rows, report.duplicate_rows) == (3, 2, 1, 1)
    assert report.input_rows == report.accepted_rows + report.rejected_rows


def test_node_labels_cannot_enter_public_transactions() -> None:
    labels = account_labels(pl.DataFrame({"nodeid": ["a"], "isFraud": [1], "fraudStep": [7]}))
    assert labels.columns == ["account_id", "is_fraud", "label_provenance"]
    public = public_transactions(pl.DataFrame({"edge_id": ["e"], "source_id": ["a"], "target_id": ["b"],
                                                 "amount": [1.0], "event_time": ["2026-01-01T00:00:00Z"],
                                                 "isFraud": [1], "fraudStep": [7]}))
    assert {"isFraud", "fraudStep"}.isdisjoint(public.columns)
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/data/test_quality.py tests/data/test_labels.py -v`

Expected: FAIL because the quality and label modules do not exist.

- [ ] **Step 3: Implement the smallest source-specific cleaner**

Define frozen `QualityReport` with source/raw hash/schema fingerprint/counts/reason counts. Reject only missing or blank IDs, non-finite/non-positive amounts, and null/negative/non-integer ticks into a reason-coded quarantine frame with raw row ordinal. Count exact raw-row duplicates without removing them; do not clip outliers. `account_labels` validates the three `nodes.csv` columns and preserves `fraudStep` only as `label_provenance`. Extend the existing `LABEL_DERIVED_COLUMNS` denylist before writing public artifacts.

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/data/test_quality.py tests/data/test_labels.py -v && uv run ruff check . && uv run mypy src`

Expected: counts reconcile; accepted duplicate rows remain; public artifacts contain no source labels.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/data/quality.py src/fincrime/data/labels.py src/fincrime/data/tracebench.py src/fincrime/data/artifacts.py tests/data/test_quality.py tests/data/test_labels.py
git commit -m "feat(data): add AMLSim quality and label isolation"
```

### Task 7: Gate source-specific temporal split evidence

**Files:**
- Modify: `src/fincrime/data/splits.py`
- Create: `tests/data/test_temporal_splits.py`

**Interfaces:**
- `audit_temporal_evidence(source_id, ticks, cutoff_tick, embargo_ticks, train_entity_ids, test_entity_ids, train_edge_ids, test_edge_ids) -> SplitEvidence`.
- `SplitEvidence.verdict` is `SAFE`, `NOT_EVALUABLE`, or `BLOCKED_DATA`.

- [ ] **Step 1: Write failing split-evidence tests**

```python
from fincrime.data.splits import SplitVerdict, audit_temporal_evidence


def test_missing_raw_ticks_is_not_evaluable() -> None:
    result = audit_temporal_evidence("amlsim-20k", (), 10, 1, frozenset(), frozenset(), frozenset(), frozenset())
    assert result.verdict is SplitVerdict.NOT_EVALUABLE


def test_entity_overlap_or_embargo_event_blocks_split() -> None:
    result = audit_temporal_evidence("amlsim-20k", (1, 11), 10, 1,
                                     frozenset({"a"}), frozenset({"a"}), frozenset({"e1"}), frozenset({"e2"}))
    assert result.verdict is SplitVerdict.BLOCKED_DATA
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/data/test_temporal_splits.py -v`

Expected: FAIL because `SplitVerdict` and `audit_temporal_evidence` do not exist.

- [ ] **Step 3: Implement evidence-only split gating**

Use a frozen Pydantic `SplitEvidence`. Empty ticks return `NOT_EVALUABLE`; entity/edge overlap or any event in `(cutoff_tick, cutoff_tick + embargo_ticks]` returns `BLOCKED_DATA`; otherwise return `SAFE`. This gate records evidence only: it does not fabricate calendar times, create a split, or claim scenario/typology separation for AMLSim 20K.

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/data/test_temporal_splits.py -v && uv run ruff check . && uv run mypy src`

Expected: unavailable time evidence is not promoted; overlap and embargo failures block the pilot.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/data/splits.py tests/data/test_temporal_splits.py
git commit -m "feat(data): gate temporal split evidence"
```

## Plan self-review

- Spec coverage: Tasks 1–7 cover source records, capacity admission, safe extraction, public artifacts, detection-only evidence, AMLSim quality/labels, and temporal split gating. They intentionally exclude full AMLBench download, trace truth, learned-tracing claims, and release tagging.
- Completeness scan: every task has a concrete implementation and verification step. The AMLBench schema is deliberately not invented; Task 3 accepts only a named, verified member after real archive inspection.
- Type consistency: every task uses `SourceManifest`, `DerivedArtifactManifest`, `CapacityDecision`, and the five-column public artifact contract defined in earlier tasks.
