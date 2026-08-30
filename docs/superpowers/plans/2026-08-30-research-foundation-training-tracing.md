# Research Foundation, Training, and Tracing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reproducible Phase 0–6 research release: manifests, TraceBench, leakage-safe graph/features, staged detector training, bounded tracing, learned ranking, and exact-SHA evaluation evidence.

**Architecture:** A Python package owns immutable contracts and deterministic data transformations. Training stages consume frozen manifests and emit hashed model/run packages; tracing consumes frozen seeds/candidates and evaluates deterministic versus learned rankers at matched recall. No database, broker, LLM, or web UI is introduced in this plan.

**Tech Stack:** Python 3.12, uv, Pydantic 2, Polars, PyArrow, scikit-learn, LightGBM, PyTorch, PyTorch Geometric, NetworkX, pytest, Ruff, mypy.

## Global Constraints

- Core path requires 0 VND cash cost and must run locally or on free compute.
- `RELEVANT`, `CONFIRMED_BENIGN`, and `UNKNOWN` are distinct; `UNKNOWN` is never a negative.
- Features at time `t` use only events with `event_time <= t`.
- Test, held-out typology, and unseen-generator tracks are never used for tuning.
- Stochastic models run five seeds: `11, 23, 37, 53, 71`.
- GraphSAGE is mandatory; HGT/TGN/hybrid are evidence-gated.
- A failed promotion gate keeps the simpler model or records `selected_detection_model = null`.
- No DeepSeek/LLM output may create labels, scores, or promotion decisions.
- Every task follows RED → GREEN → REFACTOR and ends in a recoverable commit.

## Git Branching & PR Strategy (git-workflow / github-ops)

This implementation plan is split into **7 feature branches** and **7 Pull Requests** targeting `master`, keeping changes scoped to 2–3 tasks (~300–600 LOC) per PR with isolated git worktrees.

| Branch Name | Tasks Covered | PR Scope & Title | Target | Worktree Setup Command |
|-------------|---------------|------------------|--------|------------------------|
| `feat/phase0-bootstrap-manifests-baseline` | Tasks 1–3 | PR #1: `feat(phase0): bootstrap manifests and feasibility baseline` | `master` | `git worktree add ../fin-p0-manifests -b feat/phase0-bootstrap-manifests-baseline` |
| `feat/phase1-tracebench-data-splits` | Tasks 4–6 | PR #2: `feat(phase1): TraceBench data pipelines and scenario splits` | `master` | `git worktree add ../fin-p1-data -b feat/phase1-tracebench-data-splits` |
| `feat/phase2-graph-pit-features` | Tasks 7–8 | PR #3: `feat(phase2): point-in-time graph builder and feature extraction` | `master` | `git worktree add ../fin-p2-graph -b feat/phase2-graph-pit-features` |
| `feat/phase3-detector-baselines-gates` | Tasks 9–11 | PR #4: `feat(phase3): tabular detector baselines and promotion gates` | `master` | `git worktree add ../fin-p3-detectors -b feat/phase3-detector-baselines-gates` |
| `feat/phase4-graphsage-gnn` | Tasks 12–13 | PR #5: `feat(phase4): GraphSAGE baseline and architecture gates` | `master` | `git worktree add ../fin-p4-graphsage -b feat/phase4-graphsage-gnn` |
| `feat/phase5-bounded-tracing-ranker` | Tasks 14–15 | PR #6: `feat(phase5): bounded candidate generation and learned trace ranking` | `master` | `git worktree add ../fin-p5-tracing -b feat/phase5-bounded-tracing-ranker` |
| `feat/phase6-frozen-research-run` | Task 16 | PR #7: `feat(phase6): frozen research orchestrator and report` | `master` | `git worktree add ../fin-p6-release -b feat/phase6-frozen-research-run` |

### Commit Strategy
- **Format**: Follow Conventional Commits `<type>(<scope>): <subject>` with imperative mood (e.g. `feat(contracts): define dataset and trace manifests`).
- **Scopes**: `repo`, `contracts`, `feasibility`, `data`, `graph`, `features`, `training`, `tracing`, `release`.
- **Pre-commit Gate**: Every Step 5 commit must be verified locally with `uv run pytest -q && uv run ruff check . && uv run mypy src` before committing. No dirty/untracked files or secrets committed.
- **Milestone Tagging**: Upon completion and merge of PR #7 (`feat/phase6-frozen-research-run`), tag the master branch with `v0.1.0-alpha.research`.

## File Structure

```text
pyproject.toml
src/fincrime/
  __init__.py
  cli.py
  contracts/manifests.py
  contracts/training.py
  feasibility/resources.py
  data/tracebench.py
  data/splits.py
  graph/events.py
  graph/build.py
  features/point_in_time.py
  training/runner.py
  training/baselines.py
  training/graphsage.py
  training/gates.py
  tracing/candidates.py
  tracing/rankers.py
  evaluation/detection.py
  evaluation/tracing.py
tests/
  contracts/
  feasibility/
  data/
  graph/
  features/
  training/
  tracing/
  evaluation/
configs/research/
data/manifests/.gitkeep
data/splits/.gitkeep
research/reports/.gitkeep
```

---

### Task 1: Bootstrap the research package

**Branch:** `feat/phase0-bootstrap-manifests-baseline` | **PR:** #1

**Files:**
- Create: `pyproject.toml`
- Create: `src/fincrime/__init__.py`
- Create: `tests/test_package.py`
- Create: `.gitignore`

**Interfaces:**
- Consumes: Python 3.12 and uv.
- Produces: importable package `fincrime`; commands `uv run pytest`, `uv run ruff check .`, and `uv run mypy src`.

- [ ] **Step 1: Write the failing package test**

```python
def test_package_exports_version() -> None:
    import fincrime

    assert fincrime.__version__ == "0.1.0"
```

- [ ] **Step 2: Run the test and verify RED**

Run: `uv run pytest tests/test_package.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'fincrime'`.

- [ ] **Step 3: Add the minimal package configuration**

```toml
[project]
name = "financial-crime-intelligence-platform"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "pydantic>=2.11,<3",
  "polars>=1.30,<2",
  "pyarrow>=20,<21",
  "scikit-learn>=1.6,<2",
  "lightgbm>=4.6,<5",
  "networkx>=3.4,<4",
]

[dependency-groups]
dev = ["pytest>=8.3,<9", "ruff>=0.11,<1", "mypy>=1.15,<2"]
graph = ["torch>=2.7,<3", "torch-geometric>=2.6,<3"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/fincrime"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["fincrime"]
```

```python
# src/fincrime/__init__.py
__version__ = "0.1.0"
```

```gitignore
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.pyc
data/raw/
data/processed/
artifacts/
mlruns/
.env
```

- [ ] **Step 4: Install and verify GREEN**

Run: `uv sync --group dev && uv run pytest tests/test_package.py -v && uv run ruff check . && uv run mypy src`

Expected: one passing test; Ruff and mypy exit 0.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml uv.lock .gitignore src/fincrime/__init__.py tests/test_package.py
git commit -m "chore(repo): bootstrap research package"
```

---

### Task 2: Define immutable manifest contracts

**Branch:** `feat/phase0-bootstrap-manifests-baseline` | **PR:** #1

**Files:**
- Create: `src/fincrime/contracts/manifests.py`
- Create: `tests/contracts/test_manifests.py`

**Interfaces:**
- Consumes: JSON-compatible manifest dictionaries.
- Produces: `DatasetManifest`, `TraceGoldManifest`, `SplitManifest`, and `sha256_file(path: Path) -> str`.

- [ ] **Step 1: Write failing validation tests**

```python
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from fincrime.contracts.manifests import DatasetManifest, TraceLabel


def test_dataset_manifest_is_frozen_and_hash_is_lowercase() -> None:
    manifest = DatasetManifest(
        dataset_id="fixture-v1",
        source_url="https://example.invalid/fixture",
        license="CC-BY-4.0",
        sha256="a" * 64,
        schema_hash="b" * 64,
        created_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
    )
    with pytest.raises(ValidationError):
        manifest.dataset_id = "changed"


def test_unknown_is_a_distinct_trace_label() -> None:
    assert {item.value for item in TraceLabel} == {
        "RELEVANT",
        "CONFIRMED_BENIGN",
        "UNKNOWN",
    }
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/contracts/test_manifests.py -v`

Expected: FAIL because `fincrime.contracts.manifests` does not exist.

- [ ] **Step 3: Implement the contracts**

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TraceLabel(StrEnum):
    RELEVANT = "RELEVANT"
    CONFIRMED_BENIGN = "CONFIRMED_BENIGN"
    UNKNOWN = "UNKNOWN"


class DatasetManifest(FrozenModel):
    dataset_id: str = Field(min_length=1)
    source_url: HttpUrl
    license: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime


class TraceEdge(FrozenModel):
    edge_id: str
    source_id: str
    target_id: str
    event_time: datetime
    label: TraceLabel


class TraceGoldManifest(FrozenModel):
    dataset_id: str
    generator_version: str
    generator_seed: int
    configuration_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    case_id: str
    typology: str
    edges: tuple[TraceEdge, ...]
    mandatory_anchors: tuple[str, ...]
    visibility_boundary_ids: tuple[str, ...] = ()


class SplitManifest(FrozenModel):
    train_case_ids: tuple[str, ...]
    validation_case_ids: tuple[str, ...]
    calibration_case_ids: tuple[str, ...]
    temporal_test_case_ids: tuple[str, ...]
    heldout_typology_case_ids: tuple[str, ...]
    unseen_generator_case_ids: tuple[str, ...]


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/contracts/test_manifests.py -v && uv run mypy src`

Expected: two passing tests; mypy exits 0.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/contracts/manifests.py tests/contracts/test_manifests.py
git commit -m "feat(contracts): define dataset and trace manifests"
```

---

### Task 3: Capture the Phase 0 resource and cost baseline

**Branch:** `feat/phase0-bootstrap-manifests-baseline` | **PR:** #1

**Files:**
- Create: `src/fincrime/feasibility/resources.py`
- Create: `tests/feasibility/test_resources.py`
- Create: `src/fincrime/cli.py`

**Interfaces:**
- Consumes: workspace path and optional `nvidia-smi` availability.
- Produces: `ResourceProfile`, `collect_resource_profile(workspace: Path)`, and CLI command `resource-profile`.

- [ ] **Step 1: Write the failing resource test**

```python
from pathlib import Path

from fincrime.feasibility.resources import collect_resource_profile


def test_resource_profile_reports_positive_disk_capacity(tmp_path: Path) -> None:
    profile = collect_resource_profile(tmp_path)
    assert profile.cpu_count >= 1
    assert profile.ram_bytes > 0
    assert profile.disk_free_bytes > 0
    assert profile.actual_cash_cost_vnd == 0
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/feasibility/test_resources.py -v`

Expected: FAIL because the resources module does not exist.

- [ ] **Step 3: Implement a stdlib-only profiler and CLI**

```python
# src/fincrime/feasibility/resources.py
from __future__ import annotations

import os
import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ResourceProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    cpu_count: int
    ram_bytes: int
    disk_free_bytes: int
    docker_available: bool
    nvidia_smi_available: bool
    actual_cash_cost_vnd: int = 0


def _ram_bytes() -> int:
    if hasattr(os, "sysconf"):
        try:
            return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
        except (OSError, ValueError):
            pass
    return 1


def collect_resource_profile(workspace: Path) -> ResourceProfile:
    return ResourceProfile(
        cpu_count=os.cpu_count() or 1,
        ram_bytes=_ram_bytes(),
        disk_free_bytes=shutil.disk_usage(workspace).free,
        docker_available=shutil.which("docker") is not None,
        nvidia_smi_available=shutil.which("nvidia-smi") is not None,
    )
```

```python
# src/fincrime/cli.py
from __future__ import annotations

import argparse
from pathlib import Path

from fincrime.feasibility.resources import collect_resource_profile


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    resource = subparsers.add_parser("resource-profile")
    resource.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()
    if args.command == "resource-profile":
        print(collect_resource_profile(args.workspace).model_dump_json(indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Verify GREEN and create the first actual profile**

Run: `uv run pytest tests/feasibility/test_resources.py -v && uv run python -m fincrime.cli resource-profile --workspace .`

Expected: test passes; JSON contains CPU, RAM, disk, Docker, GPU-tool presence, and cost 0.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/feasibility/resources.py src/fincrime/cli.py tests/feasibility/test_resources.py
git commit -m "feat(feasibility): record Phase 0 resource profile"
```

---

### Task 4: Produce leak-free TraceBench public and gold projections

**Branch:** `feat/phase1-tracebench-data-splits` | **PR:** #2

**Files:**
- Create: `src/fincrime/data/tracebench.py`
- Create: `tests/data/test_tracebench.py`

**Interfaces:**
- Consumes: transaction `polars.DataFrame` and `TraceGoldManifest`.
- Produces: `public_transactions(frame) -> pl.DataFrame` and `gold_labels(manifest) -> pl.DataFrame`.

- [ ] **Step 1: Write failing projection tests**

```python
import polars as pl

from fincrime.data.tracebench import LABEL_DERIVED_COLUMNS, public_transactions


def test_public_projection_removes_all_label_derived_columns() -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [100.0],
            "scenario_id": ["s1"],
            "_aml_designations": [1],
            "split_mask": ["train"],
        }
    )
    public = public_transactions(frame)
    assert not set(LABEL_DERIVED_COLUMNS).intersection(public.columns)
    assert public.columns == ["edge_id", "source_id", "target_id", "amount"]
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/data/test_tracebench.py -v`

Expected: FAIL because `fincrime.data.tracebench` does not exist.

- [ ] **Step 3: Implement the denylist projection**

```python
from __future__ import annotations

import polars as pl

LABEL_DERIVED_COLUMNS = (
    "_aml_designations",
    "_scenario_log",
    "scenario_id",
    "case_id",
    "signal_columns",
    "split_mask",
    "In_Scenario",
    "analyst_disposition",
)


def public_transactions(frame: pl.DataFrame) -> pl.DataFrame:
    forbidden = [name for name in LABEL_DERIVED_COLUMNS if name in frame.columns]
    return frame.drop(forbidden)
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/data/test_tracebench.py -v && uv run ruff check src tests`

Expected: test passes; Ruff exits 0.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/data/tracebench.py tests/data/test_tracebench.py
git commit -m "feat(data): separate TraceBench truth from model inputs"
```

---

### Task 5: Adapt AMLSim and AMLBench into canonical events

**Branch:** `feat/phase1-tracebench-data-splits` | **PR:** #2

**Files:**
- Create: `src/fincrime/data/adapters.py`
- Create: `tests/data/test_adapters.py`

**Interfaces:**
- Consumes: AMLSim/AMLBench transaction tables with explicit source mappings.
- Produces: canonical columns `edge_id`, `source_id`, `target_id`, `amount`, `event_time`; missing source columns fail.

- [ ] **Step 1: Write failing adapter tests with tiny fixtures**

```python
from datetime import datetime, timezone

import polars as pl
import pytest

from fincrime.data.adapters import AMLSimAdapter


def test_amlsim_adapter_maps_canonical_columns() -> None:
    raw = pl.DataFrame(
        {
            "transaction_id": ["e1"],
            "orig_id": ["a"],
            "dest_id": ["b"],
            "amount": [10.0],
            "timestamp": [datetime(2026, 1, 1, tzinfo=timezone.utc)],
        }
    )
    assert AMLSimAdapter().transactions(raw).columns == [
        "edge_id", "source_id", "target_id", "amount", "event_time"
    ]


def test_adapter_fails_when_transaction_id_is_missing() -> None:
    with pytest.raises(ValueError, match="missing source columns"):
        AMLSimAdapter().transactions(pl.DataFrame({"orig_id": ["a"]}))
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/data/test_adapters.py -v`

Expected: FAIL because dataset adapters do not exist.

- [ ] **Step 3: Implement explicit schema mappings**

```python
from __future__ import annotations

import polars as pl


class AMLSimAdapter:
    mapping = {
        "transaction_id": "edge_id",
        "orig_id": "source_id",
        "dest_id": "target_id",
        "amount": "amount",
        "timestamp": "event_time",
    }

    def transactions(self, frame: pl.DataFrame) -> pl.DataFrame:
        missing = tuple(sorted(set(self.mapping) - set(frame.columns)))
        if missing:
            raise ValueError(f"missing source columns: {missing}")
        return frame.select(
            [pl.col(source).alias(target) for source, target in self.mapping.items()]
        )


class AMLBenchAdapter:
    mapping = {
        "transaction_id": "edge_id",
        "source_account_id": "source_id",
        "target_account_id": "target_id",
        "amount": "amount",
        "transaction_time": "event_time",
    }

    def transactions(self, frame: pl.DataFrame) -> pl.DataFrame:
        missing = tuple(sorted(set(self.mapping) - set(frame.columns)))
        if missing:
            raise ValueError(f"missing source columns: {missing}")
        return frame.select(
            [pl.col(source).alias(target) for source, target in self.mapping.items()]
        )
```

- [ ] **Step 4: Verify GREEN and record real-column deviations in the adapter report**

Run: `uv run pytest tests/data/test_adapters.py -v`

Expected: fixture tests pass. On first real-data run, source columns are inspected and a code change plus test is required for any deviation; no fuzzy mapping is allowed.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/data/adapters.py tests/data/test_adapters.py
git commit -m "feat(data): adapt AML datasets to canonical events"
```

---

### Task 6: Build scenario-safe splits and overlap auditing

**Branch:** `feat/phase1-tracebench-data-splits` | **PR:** #2

**Files:**
- Create: `src/fincrime/data/splits.py`
- Create: `tests/data/test_splits.py`

**Interfaces:**
- Consumes: case records with `case_id`, `typology`, `generator_seed`, entity IDs, edge IDs, and time range.
- Produces: `audit_split_overlap(records, manifest) -> OverlapReport` and `assert_split_safe(report) -> None`.

- [ ] **Step 1: Write a failing overlap test**

```python
import pytest

from fincrime.contracts.manifests import SplitManifest
from fincrime.data.splits import CaseRecord, assert_split_safe, audit_split_overlap


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
    with pytest.raises(ValueError, match="entity overlap"):
        assert_split_safe(audit_split_overlap(records, manifest))


def test_generator_seed_overlap_in_unseen_track_fails() -> None:
    records = {
        "train": CaseRecord("train", "fan_in", 11, frozenset({"a"}), frozenset({"e1"})),
        "unseen": CaseRecord("unseen", "cycle", 11, frozenset({"b"}), frozenset({"e2"})),
    }
    manifest = SplitManifest(
        train_case_ids=("train",), validation_case_ids=(), calibration_case_ids=(),
        temporal_test_case_ids=(), heldout_typology_case_ids=(),
        unseen_generator_case_ids=("unseen",),
    )
    with pytest.raises(ValueError, match="generator seed overlap"):
        assert_split_safe(audit_split_overlap(records, manifest))
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/data/test_splits.py -v`

Expected: FAIL because the split module does not exist.

- [ ] **Step 3: Implement overlap reporting**

```python
from __future__ import annotations

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
    model_config = ConfigDict(frozen=True)
    entity_overlap: tuple[str, ...]
    edge_overlap: tuple[str, ...]
    generator_seed_overlap: tuple[int, ...]


def audit_split_overlap(
    records: dict[str, CaseRecord], manifest: SplitManifest
) -> OverlapReport:
    train = [records[key] for key in manifest.train_case_ids]
    test_ids = (
        manifest.validation_case_ids
        + manifest.calibration_case_ids
        + manifest.temporal_test_case_ids
        + manifest.heldout_typology_case_ids
        + manifest.unseen_generator_case_ids
    )
    test = [records[key] for key in test_ids]
    train_entities = set().union(*(item.entity_ids for item in train)) if train else set()
    test_entities = set().union(*(item.entity_ids for item in test)) if test else set()
    train_edges = set().union(*(item.edge_ids for item in train)) if train else set()
    test_edges = set().union(*(item.edge_ids for item in test)) if test else set()
    return OverlapReport(
        entity_overlap=tuple(sorted(train_entities & test_entities)),
        edge_overlap=tuple(sorted(train_edges & test_edges)),
        generator_seed_overlap=tuple(
            sorted({item.generator_seed for item in train} & {item.generator_seed for item in test})
        ),
    )


def assert_split_safe(report: OverlapReport) -> None:
    if report.entity_overlap:
        raise ValueError(f"entity overlap: {report.entity_overlap}")
    if report.edge_overlap:
        raise ValueError(f"edge overlap: {report.edge_overlap}")
    if report.generator_seed_overlap:
        raise ValueError(f"generator seed overlap: {report.generator_seed_overlap}")
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/data/test_splits.py -v`

Expected: test passes.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/data/splits.py tests/data/test_splits.py
git commit -m "feat(data): audit scenario split leakage"
```

---

### Task 7: Build a point-in-time transaction graph

**Branch:** `feat/phase2-graph-pit-features` | **PR:** #3

**Files:**
- Create: `src/fincrime/graph/events.py`
- Create: `src/fincrime/graph/build.py`
- Create: `tests/graph/test_build.py`

**Interfaces:**
- Consumes: ordered `TransactionEvent` objects and `cutoff: datetime`.
- Produces: `build_graph(events, cutoff) -> nx.MultiDiGraph` with no future edges.

- [ ] **Step 1: Write the failing causality test**

```python
from datetime import datetime, timezone

from fincrime.graph.build import build_graph
from fincrime.graph.events import TransactionEvent


def test_future_event_is_excluded_from_graph() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=timezone.utc)
    events = (
        TransactionEvent("e1", "a", "b", 10.0, datetime(2026, 1, 1, tzinfo=timezone.utc)),
        TransactionEvent("e2", "b", "c", 9.0, datetime(2026, 1, 3, tzinfo=timezone.utc)),
    )
    graph = build_graph(events, cutoff)
    assert set(key for _, _, key in graph.edges(keys=True)) == {"e1"}
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/graph/test_build.py -v`

Expected: FAIL because graph modules do not exist.

- [ ] **Step 3: Implement immutable events and causal construction**

```python
# src/fincrime/graph/events.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TransactionEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    edge_id: str
    source_id: str
    target_id: str
    amount: float = Field(gt=0)
    event_time: datetime
```

```python
# src/fincrime/graph/build.py
from datetime import datetime

import networkx as nx

from fincrime.graph.events import TransactionEvent


def build_graph(events: tuple[TransactionEvent, ...], cutoff: datetime) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph(cutoff=cutoff.isoformat())
    for event in sorted(events, key=lambda item: (item.event_time, item.edge_id)):
        if event.event_time > cutoff:
            continue
        graph.add_edge(
            event.source_id,
            event.target_id,
            key=event.edge_id,
            amount=event.amount,
            event_time=event.event_time,
        )
    return graph
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/graph/test_build.py -v && uv run mypy src`

Expected: test passes; mypy exits 0.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/graph/events.py src/fincrime/graph/build.py tests/graph/test_build.py
git commit -m "feat(graph): build point in time transaction graph"
```

---

### Task 8: Compute point-in-time baseline features

**Branch:** `feat/phase2-graph-pit-features` | **PR:** #3

**Files:**
- Create: `src/fincrime/features/point_in_time.py`
- Create: `tests/features/test_point_in_time.py`

**Interfaces:**
- Consumes: causal graph, account ID, and cutoff.
- Produces: `AccountFeatures` and `account_features(graph, account_id) -> AccountFeatures`.

- [ ] **Step 1: Write the failing feature test**

```python
from datetime import datetime, timezone

from fincrime.features.point_in_time import account_features
from fincrime.graph.build import build_graph
from fincrime.graph.events import TransactionEvent


def test_account_features_are_amount_and_degree_aware() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=timezone.utc)
    graph = build_graph(
        (
            TransactionEvent("e1", "a", "b", 10.0, cutoff),
            TransactionEvent("e2", "b", "c", 8.0, cutoff),
        ),
        cutoff,
    )
    features = account_features(graph, "b")
    assert features.in_degree == 1
    assert features.out_degree == 1
    assert features.incoming_amount == 10.0
    assert features.outgoing_amount == 8.0
    assert features.pass_through_ratio == 0.8
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/features/test_point_in_time.py -v`

Expected: FAIL because the features module does not exist.

- [ ] **Step 3: Implement transparent baseline features**

```python
from __future__ import annotations

import networkx as nx
from pydantic import BaseModel, ConfigDict


class AccountFeatures(BaseModel):
    model_config = ConfigDict(frozen=True)
    account_id: str
    in_degree: int
    out_degree: int
    incoming_amount: float
    outgoing_amount: float
    pass_through_ratio: float


def account_features(graph: nx.MultiDiGraph, account_id: str) -> AccountFeatures:
    incoming = sum(float(data["amount"]) for *_, data in graph.in_edges(account_id, data=True))
    outgoing = sum(float(data["amount"]) for *_, data in graph.out_edges(account_id, data=True))
    return AccountFeatures(
        account_id=account_id,
        in_degree=graph.in_degree(account_id),
        out_degree=graph.out_degree(account_id),
        incoming_amount=incoming,
        outgoing_amount=outgoing,
        pass_through_ratio=0.0 if incoming == 0 else min(outgoing / incoming, 1.0),
    )
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/features/test_point_in_time.py -v`

Expected: test passes.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/features/point_in_time.py tests/features/test_point_in_time.py
git commit -m "feat(features): extract point in time baseline features"
```

---

### Task 9: Define the training run and model package contracts

**Branch:** `feat/phase3-detector-baselines-gates` | **PR:** #4

**Files:**
- Create: `src/fincrime/contracts/training.py`
- Create: `tests/contracts/test_training.py`
- Create: `configs/research/baseline.json`

**Interfaces:**
- Consumes: preregistered JSON.
- Produces: `TrainingRunSpec`, `ModelPackageManifest`, and fixed seed tuple `RESEARCH_SEEDS`.

- [ ] **Step 1: Write the failing preregistration test**

```python
from fincrime.contracts.training import RESEARCH_SEEDS, TrainingRunSpec


def test_training_run_uses_five_fixed_seeds_and_trial_cap() -> None:
    spec = TrainingRunSpec(
        run_id="baseline-001",
        hypothesis="LightGBM improves precision at K",
        model_family="lightgbm",
        dataset_manifest_hash="a" * 64,
        split_manifest_hash="b" * 64,
        feature_schema_hash="c" * 64,
        primary_metric="precision_at_k",
        alert_budget=100,
        search_trial_cap=20,
    )
    assert spec.random_seeds == RESEARCH_SEEDS
    assert spec.search_trial_cap == 20
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/contracts/test_training.py -v`

Expected: FAIL because training contracts do not exist.

- [ ] **Step 3: Implement the contracts and baseline config**

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

RESEARCH_SEEDS = (11, 23, 37, 53, 71)


class TrainingRunSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: str
    hypothesis: str
    model_family: str
    dataset_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    split_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_schema_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    primary_metric: str
    alert_budget: int = Field(gt=0)
    search_trial_cap: int = Field(gt=0, le=50)
    random_seeds: tuple[int, ...] = RESEARCH_SEEDS


class ModelPackageManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: str
    model_family: str
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    selected: bool
    limitations: tuple[str, ...]
```

```json
{
  "run_id": "baseline-001",
  "hypothesis": "LightGBM improves precision at K over deterministic rules",
  "model_family": "lightgbm",
  "dataset_manifest_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "split_manifest_hash": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "feature_schema_hash": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "primary_metric": "precision_at_k",
  "alert_budget": 100,
  "search_trial_cap": 20
}
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/contracts/test_training.py -v`

Expected: test passes.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/contracts/training.py tests/contracts/test_training.py configs/research/baseline.json
git commit -m "feat(contracts): preregister training runs"
```

---

### Task 10: Implement deterministic and tabular detector baselines

**Branch:** `feat/phase3-detector-baselines-gates` | **PR:** #4

**Files:**
- Create: `src/fincrime/training/baselines.py`
- Create: `tests/training/test_baselines.py`

**Interfaces:**
- Consumes: NumPy-compatible feature matrix and binary labels from train only.
- Produces: `fit_logistic`, `fit_lightgbm`, and `predict_scores`.

- [ ] **Step 1: Write failing baseline tests**

```python
import numpy as np

from fincrime.training.baselines import fit_logistic, predict_scores


def test_logistic_baseline_returns_probabilities() -> None:
    x = np.array([[0.0], [0.2], [0.8], [1.0]])
    y = np.array([0, 0, 1, 1])
    model = fit_logistic(x, y, seed=11)
    scores = predict_scores(model, x)
    assert scores.shape == (4,)
    assert np.all((scores >= 0.0) & (scores <= 1.0))
    assert scores[-1] > scores[0]
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/training/test_baselines.py -v`

Expected: FAIL because baseline functions do not exist.

- [ ] **Step 3: Implement minimal baseline factories**

```python
from __future__ import annotations

from typing import Protocol

import lightgbm as lgb
import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import LogisticRegression


class ProbabilityModel(Protocol):
    def predict_proba(self, x: NDArray[np.float64]) -> NDArray[np.float64]: ...


def fit_logistic(
    x: NDArray[np.float64], y: NDArray[np.int64], seed: int
) -> LogisticRegression:
    return LogisticRegression(class_weight="balanced", random_state=seed, max_iter=1000).fit(x, y)


def fit_lightgbm(
    x: NDArray[np.float64], y: NDArray[np.int64], seed: int
) -> lgb.LGBMClassifier:
    return lgb.LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        num_leaves=31,
        class_weight="balanced",
        random_state=seed,
        verbosity=-1,
    ).fit(x, y)


def predict_scores(model: ProbabilityModel, x: NDArray[np.float64]) -> NDArray[np.float64]:
    return model.predict_proba(x)[:, 1]
```

- [ ] **Step 4: Verify GREEN across five seeds**

Run: `uv run pytest tests/training/test_baselines.py -v`

Expected: test passes.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/training/baselines.py tests/training/test_baselines.py
git commit -m "feat(training): add tabular detector baselines"
```

---

### Task 11: Add detection metrics, calibration, and promotion gates

**Branch:** `feat/phase3-detector-baselines-gates` | **PR:** #4

**Files:**
- Create: `src/fincrime/evaluation/detection.py`
- Create: `src/fincrime/training/gates.py`
- Create: `tests/evaluation/test_detection.py`
- Create: `tests/training/test_gates.py`

**Interfaces:**
- Consumes: labels, scores, fixed `alert_budget`, and candidate/baseline seed metrics.
- Produces: `DetectionMetrics`, `detection_metrics`, and `promotion_decision`.

- [ ] **Step 1: Write failing metric and null-result tests**

```python
import numpy as np

from fincrime.evaluation.detection import detection_metrics, fit_score_calibrator
from fincrime.training.gates import promotion_decision


def test_precision_at_fixed_budget() -> None:
    metrics = detection_metrics(
        np.array([1, 0, 1, 0]), np.array([0.9, 0.8, 0.7, 0.1]), alert_budget=2
    )
    assert metrics.precision_at_k == 0.5


def test_failed_candidate_returns_null_selection() -> None:
    decision = promotion_decision(baseline_values=(0.7,) * 5, candidate_values=(0.69,) * 5)
    assert decision.selected_model is None


def test_calibrator_is_fit_only_from_supplied_calibration_scores() -> None:
    calibrator = fit_score_calibrator(
        np.array([0.1, 0.2, 0.8, 0.9]), np.array([0, 0, 1, 1])
    )
    calibrated = calibrator.predict(np.array([0.15, 0.85]))
    assert calibrated[1] > calibrated[0]
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/evaluation/test_detection.py tests/training/test_gates.py -v`

Expected: FAIL because evaluation/gate modules do not exist.

- [ ] **Step 3: Implement exact fixed-budget metrics and conservative gate**

```python
# src/fincrime/evaluation/detection.py
from pydantic import BaseModel, ConfigDict
import numpy as np
from numpy.typing import NDArray
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.isotonic import IsotonicRegression


class DetectionMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    pr_auc: float
    precision_at_k: float
    brier: float


def detection_metrics(
    y_true: NDArray[np.int64], scores: NDArray[np.float64], alert_budget: int
) -> DetectionMetrics:
    order = np.argsort(-scores, kind="stable")[:alert_budget]
    return DetectionMetrics(
        pr_auc=float(average_precision_score(y_true, scores)),
        precision_at_k=float(y_true[order].mean()),
        brier=float(brier_score_loss(y_true, scores)),
    )


def fit_score_calibrator(
    calibration_scores: NDArray[np.float64], calibration_labels: NDArray[np.int64]
) -> IsotonicRegression:
    return IsotonicRegression(out_of_bounds="clip").fit(
        calibration_scores, calibration_labels
    )
```

```python
# src/fincrime/training/gates.py
import numpy as np
from pydantic import BaseModel, ConfigDict


class PromotionDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    selected_model: str | None
    mean_delta: float
    ci_lower: float


def promotion_decision(
    baseline_values: tuple[float, ...], candidate_values: tuple[float, ...]
) -> PromotionDecision:
    deltas = tuple(candidate - baseline for baseline, candidate in zip(baseline_values, candidate_values))
    mean_delta = sum(deltas) / len(deltas)
    rng = np.random.default_rng(20260830)
    samples = np.array(deltas)
    bootstrap_means = np.array(
        [rng.choice(samples, size=len(samples), replace=True).mean() for _ in range(10_000)]
    )
    lower = float(np.quantile(bootstrap_means, 0.025))
    selected = (
        "candidate"
        if lower > 0 and sum(delta > 0 for delta in deltas) >= 4
        else None
    )
    return PromotionDecision(selected_model=selected, mean_delta=mean_delta, ci_lower=lower)
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/evaluation/test_detection.py tests/training/test_gates.py -v`

Expected: both tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/evaluation/detection.py src/fincrime/training/gates.py tests/evaluation/test_detection.py tests/training/test_gates.py
git commit -m "feat(training): evaluate and gate detector candidates"
```

---

### Task 12: Add the mandatory GraphSAGE baseline

**Branch:** `feat/phase4-graphsage-gnn` | **PR:** #5

**Files:**
- Create: `src/fincrime/training/graphsage.py`
- Create: `tests/training/test_graphsage.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: PyG `Data` with `x`, `edge_index`, `y`, and train mask.
- Produces: `GraphSAGEDetector` logits and `train_graphsage_epoch`.

- [ ] **Step 1: Write the failing smoke-training test**

```python
import torch
from torch_geometric.data import Data

from fincrime.training.graphsage import GraphSAGEDetector, build_neighbor_loader, train_graphsage_epoch


def test_graphsage_smoke_training_returns_finite_loss() -> None:
    data = Data(
        x=torch.tensor([[0.0], [0.2], [0.8], [1.0]]),
        edge_index=torch.tensor([[0, 1, 2], [1, 2, 3]]),
        y=torch.tensor([0, 0, 1, 1]),
        train_mask=torch.tensor([True, True, True, True]),
    )
    model = GraphSAGEDetector(in_channels=1, hidden_channels=8)
    loss = train_graphsage_epoch(model, data, learning_rate=0.01)
    assert torch.isfinite(torch.tensor(loss))


def test_neighbor_loader_keeps_seed_batch_bounded() -> None:
    data = Data(
        x=torch.rand((20, 2)),
        edge_index=torch.tensor([[i for i in range(19)], [i + 1 for i in range(19)]]),
        y=torch.zeros(20, dtype=torch.long),
    )
    batch = next(iter(build_neighbor_loader(data, torch.tensor([0, 1]), batch_size=2)))
    assert batch.batch_size == 2
```

- [ ] **Step 2: Install graph dependencies and verify RED**

Run: `uv sync --group graph --group dev && uv run pytest tests/training/test_graphsage.py -v`

Expected: FAIL because the GraphSAGE module does not exist.

- [ ] **Step 3: Implement the two-layer baseline**

```python
from __future__ import annotations

import torch
import torch.nn.functional as functional
from torch import Tensor
from torch_geometric.data import Data
from torch_geometric.loader import NeighborLoader
from torch_geometric.nn import SAGEConv


class GraphSAGEDetector(torch.nn.Module):
    def __init__(self, in_channels: int, hidden_channels: int) -> None:
        super().__init__()
        self.first = SAGEConv(in_channels, hidden_channels)
        self.second = SAGEConv(hidden_channels, 2)

    def forward(self, x: Tensor, edge_index: Tensor) -> Tensor:
        hidden = self.first(x, edge_index).relu()
        return self.second(hidden, edge_index)


def build_neighbor_loader(
    data: Data, input_nodes: Tensor, batch_size: int
) -> NeighborLoader:
    return NeighborLoader(
        data,
        input_nodes=input_nodes,
        num_neighbors=[15, 10],
        batch_size=batch_size,
        shuffle=False,
    )


def train_graphsage_epoch(
    model: GraphSAGEDetector, data: Data, learning_rate: float
) -> float:
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    optimizer.zero_grad()
    logits = model(data.x, data.edge_index)
    loss = functional.cross_entropy(logits[data.train_mask], data.y[data.train_mask])
    loss.backward()
    optimizer.step()
    return float(loss.detach())
```

- [ ] **Step 4: Verify GREEN and deterministic seed behavior**

Run: `uv run pytest tests/training/test_graphsage.py -v && uv run ruff check src tests`

Expected: smoke test passes; Ruff exits 0.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml uv.lock src/fincrime/training/graphsage.py tests/training/test_graphsage.py
git commit -m "feat(training): add mandatory GraphSAGE baseline"
```

---

### Task 13: Gate HGT, TGN, and hybrid work before implementation

**Branch:** `feat/phase4-graphsage-gnn` | **PR:** #5

**Files:**
- Create: `src/fincrime/training/advanced_gate.py`
- Create: `tests/training/test_advanced_gate.py`

**Interfaces:**
- Consumes: ontology support, GraphSAGE delta, temporal-feature gap, HGT delta, and TGN delta.
- Produces: `AdvancedModelDecision` with `next_family` equal to `hgt`, `tgn`, `hybrid`, or `JUSTIFIED_NULL`.

- [ ] **Step 1: Write failing branch-gate tests**

```python
from fincrime.training.advanced_gate import advanced_model_decision


def test_no_graphsage_gain_records_justified_null() -> None:
    result = advanced_model_decision(False, -0.01, True, 0.0, 0.0)
    assert result.next_family == "JUSTIFIED_NULL"


def test_real_heterogeneity_opens_hgt_only_after_graphsage_gain() -> None:
    result = advanced_model_decision(True, 0.04, False, 0.0, 0.0)
    assert result.next_family == "hgt"
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/training/test_advanced_gate.py -v`

Expected: FAIL because advanced gate does not exist.

- [ ] **Step 3: Implement the gate**

```python
from pydantic import BaseModel, ConfigDict


class AdvancedModelDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    next_family: str
    reason: str


def advanced_model_decision(
    heterogeneous_supported: bool,
    graphsage_delta: float,
    temporal_gap: bool,
    hgt_delta: float,
    tgn_delta: float,
) -> AdvancedModelDecision:
    if graphsage_delta <= 0:
        return AdvancedModelDecision(
            next_family="JUSTIFIED_NULL", reason="GraphSAGE did not beat tabular baseline"
        )
    if heterogeneous_supported and hgt_delta <= 0:
        return AdvancedModelDecision(next_family="hgt", reason="real heterogeneous ontology")
    if temporal_gap and tgn_delta <= 0:
        return AdvancedModelDecision(next_family="tgn", reason="unresolved temporal feature gap")
    if hgt_delta > 0 and tgn_delta > 0:
        return AdvancedModelDecision(next_family="hybrid", reason="HGT and TGN both passed")
    return AdvancedModelDecision(next_family="JUSTIFIED_NULL", reason="no advanced hypothesis passed")
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/training/test_advanced_gate.py -v`

Expected: tests pass. If result is `hgt`, `tgn`, or `hybrid`, stop execution and use `writing-plans` to create that model's focused plan before code; if `JUSTIFIED_NULL`, continue.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/training/advanced_gate.py tests/training/test_advanced_gate.py
git commit -m "feat(training): gate advanced GNN research"
```

---

### Task 14: Generate bounded trace candidates

**Branch:** `feat/phase5-bounded-tracing-ranker` | **PR:** #6

**Files:**
- Create: `src/fincrime/tracing/candidates.py`
- Create: `tests/tracing/test_candidates.py`

**Interfaces:**
- Consumes: causal graph and `TraceRequest`.
- Produces: `TraceResult` with at most four hops, 100 returned edges, deterministic ties, and truncation status.

- [ ] **Step 1: Write the failing budget test**

```python
from datetime import datetime, timezone

import networkx as nx

from fincrime.tracing.candidates import TraceRequest, generate_candidates


def test_candidate_generation_obeys_edge_budget() -> None:
    graph = nx.MultiDiGraph()
    for index in range(5):
        graph.add_edge("seed", f"n{index}", key=f"e{index}", amount=10 - index, event_time=datetime(2026, 1, 1, tzinfo=timezone.utc))
    request = TraceRequest(seed_entity="seed", max_hops=1, max_edges=2)
    result = generate_candidates(graph, request)
    assert len(result.edge_ids) == 2
    assert result.status == "TRACE_TRUNCATED"
    assert result.edge_ids == ("e0", "e1")
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/tracing/test_candidates.py -v`

Expected: FAIL because candidate module does not exist.

- [ ] **Step 3: Implement deterministic bounded best-first expansion**

```python
from __future__ import annotations

import heapq

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field


class TraceRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    seed_entity: str
    max_hops: int = Field(default=4, ge=1, le=4)
    max_edges: int = Field(default=100, ge=1, le=100)


class TraceResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    edge_ids: tuple[str, ...]
    status: str


def generate_candidates(graph: nx.MultiDiGraph, request: TraceRequest) -> TraceResult:
    queue: list[tuple[float, str, str, int]] = []
    for _, target, key, data in graph.out_edges(request.seed_entity, keys=True, data=True):
        heapq.heappush(queue, (-float(data["amount"]), str(key), target, 1))
    selected: list[str] = []
    while queue and len(selected) < request.max_edges:
        _, edge_id, target, hop = heapq.heappop(queue)
        selected.append(edge_id)
        if hop >= request.max_hops:
            continue
        for _, next_target, key, data in graph.out_edges(target, keys=True, data=True):
            heapq.heappush(queue, (-float(data["amount"]), str(key), next_target, hop + 1))
    return TraceResult(
        edge_ids=tuple(selected),
        status="TRACE_TRUNCATED" if queue else "COMPLETE",
    )
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/tracing/test_candidates.py -v`

Expected: test passes.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/tracing/candidates.py tests/tracing/test_candidates.py
git commit -m "feat(tracing): generate bounded trace candidates"
```

---

### Task 15: Train and evaluate the learned trace ranker

**Branch:** `feat/phase5-bounded-tracing-ranker` | **PR:** #6

**Files:**
- Create: `src/fincrime/tracing/rankers.py`
- Create: `src/fincrime/evaluation/tracing.py`
- Create: `tests/tracing/test_rankers.py`
- Create: `tests/evaluation/test_tracing.py`

**Interfaces:**
- Consumes: fixed candidate features and tri-state labels.
- Produces: `fit_trace_ranker`, `rank_edges`, and matched-recall `TraceMetrics`.

- [ ] **Step 1: Write failing unknown-label and metric tests**

```python
import numpy as np

from fincrime.contracts.manifests import TraceLabel
from fincrime.evaluation.tracing import trace_metrics
from fincrime.tracing.rankers import training_mask


def test_unknown_edges_are_excluded_from_ranker_training() -> None:
    labels = np.array([TraceLabel.RELEVANT, TraceLabel.UNKNOWN, TraceLabel.CONFIRMED_BENIGN])
    assert training_mask(labels).tolist() == [True, False, True]


def test_trace_metrics_report_unknown_separately() -> None:
    metrics = trace_metrics(
        returned=("e1", "e2", "e3"),
        labels={
            "e1": TraceLabel.RELEVANT,
            "e2": TraceLabel.CONFIRMED_BENIGN,
            "e3": TraceLabel.UNKNOWN,
        },
    )
    assert metrics.relevant_recall == 1.0
    assert metrics.confirmed_benign_contamination == 1 / 3
    assert metrics.unknown_inclusion_rate == 1 / 3
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/tracing/test_rankers.py tests/evaluation/test_tracing.py -v`

Expected: FAIL because ranker/evaluation modules do not exist.

- [ ] **Step 3: Implement tri-state training and metrics**

```python
# src/fincrime/tracing/rankers.py
from __future__ import annotations

import lightgbm as lgb
import numpy as np
from numpy.typing import NDArray

from fincrime.contracts.manifests import TraceLabel


def training_mask(labels: NDArray[np.object_]) -> NDArray[np.bool_]:
    return np.array([label is not TraceLabel.UNKNOWN for label in labels], dtype=bool)


def fit_trace_ranker(
    x: NDArray[np.float64], labels: NDArray[np.object_], seed: int
) -> lgb.LGBMRanker:
    mask = training_mask(labels)
    y = np.array([1 if label is TraceLabel.RELEVANT else 0 for label in labels[mask]])
    model = lgb.LGBMRanker(objective="lambdarank", random_state=seed, verbosity=-1)
    return model.fit(x[mask], y, group=[int(mask.sum())])
```

```python
# src/fincrime/evaluation/tracing.py
from pydantic import BaseModel, ConfigDict

from fincrime.contracts.manifests import TraceLabel


class TraceMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    relevant_recall: float
    confirmed_benign_contamination: float
    unknown_inclusion_rate: float


def trace_metrics(returned: tuple[str, ...], labels: dict[str, TraceLabel]) -> TraceMetrics:
    relevant_total = sum(label is TraceLabel.RELEVANT for label in labels.values())
    relevant_returned = sum(labels[item] is TraceLabel.RELEVANT for item in returned)
    benign_returned = sum(labels[item] is TraceLabel.CONFIRMED_BENIGN for item in returned)
    unknown_returned = sum(labels[item] is TraceLabel.UNKNOWN for item in returned)
    count = len(returned)
    return TraceMetrics(
        relevant_recall=0.0 if relevant_total == 0 else relevant_returned / relevant_total,
        confirmed_benign_contamination=0.0 if count == 0 else benign_returned / count,
        unknown_inclusion_rate=0.0 if count == 0 else unknown_returned / count,
    )
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/tracing/test_rankers.py tests/evaluation/test_tracing.py -v`

Expected: tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/tracing/rankers.py src/fincrime/evaluation/tracing.py tests/tracing/test_rankers.py tests/evaluation/test_tracing.py
git commit -m "feat(tracing): evaluate learned trace ranker against deterministic search"
```

---

### Task 16: Orchestrate the frozen research run and release report

**Branch:** `feat/phase6-frozen-research-run` | **PR:** #7

**Files:**
- Create: `src/fincrime/training/runner.py`
- Create: `tests/training/test_runner.py`
- Create: `research/reports/.gitkeep`
- Modify: `src/fincrime/cli.py`

**Interfaces:**
- Consumes: `TrainingRunSpec`, frozen matrices/graph references, and output directory.
- Produces: append-only `run-manifest.json`, `metrics.json`, `promotion.json`, and non-zero exit on invalid gate.

- [ ] **Step 1: Write the failing append-only run test**

```python
from pathlib import Path

import pytest

from fincrime.training.runner import TrainingRunState, TrainingStage, write_run_artifact


def test_run_artifact_refuses_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "run-manifest.json"
    write_run_artifact(target, {"run_id": "r1"})
    with pytest.raises(FileExistsError):
        write_run_artifact(target, {"run_id": "r2"})


def test_training_stages_cannot_skip_calibration() -> None:
    state = TrainingRunState(stage=TrainingStage.PREREGISTERED)
    with pytest.raises(ValueError, match="expected DATA_VERIFIED"):
        state.advance(TrainingStage.FROZEN)
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/training/test_runner.py -v`

Expected: FAIL because runner module does not exist.

- [ ] **Step 3: Implement atomic append-only artifact writing**

```python
# src/fincrime/training/runner.py
from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class TrainingStage(StrEnum):
    PREREGISTERED = "PREREGISTERED"
    DATA_VERIFIED = "DATA_VERIFIED"
    FITTED = "FITTED"
    VALIDATED = "VALIDATED"
    CALIBRATED = "CALIBRATED"
    FROZEN = "FROZEN"
    TESTED = "TESTED"
    TRACE_EVALUATED = "TRACE_EVALUATED"
    DECIDED = "DECIDED"


STAGE_ORDER = tuple(TrainingStage)


class TrainingRunState(BaseModel):
    model_config = ConfigDict(frozen=True)
    stage: TrainingStage

    def advance(self, next_stage: TrainingStage) -> "TrainingRunState":
        current_index = STAGE_ORDER.index(self.stage)
        expected = STAGE_ORDER[current_index + 1]
        if next_stage is not expected:
            raise ValueError(f"expected {expected.value}, got {next_stage.value}")
        return self.model_copy(update={"stage": next_stage})


def write_run_artifact(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as target:
        json.dump(payload, target, indent=2, sort_keys=True)
        target.write("\n")
```

Add this branch to `src/fincrime/cli.py`:

```python
run = subparsers.add_parser("write-run-artifact")
run.add_argument("--path", type=Path, required=True)
run.add_argument("--run-id", required=True)

# after parsing
if args.command == "write-run-artifact":
    from fincrime.training.runner import write_run_artifact

    write_run_artifact(args.path, {"run_id": args.run_id})
    return 0
```

- [ ] **Step 4: Run the full Research Release verification**

Run: `uv run pytest -q && uv run ruff check . && uv run mypy src && uv run python -m fincrime.cli write-run-artifact --path research/reports/smoke/run-manifest.json --run-id smoke`

Expected: all tests pass; checks exit 0; the smoke manifest is created once. Remove only the generated `research/reports/smoke/` directory after verifying it is inside the workspace and untracked.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/training/runner.py src/fincrime/cli.py tests/training/test_runner.py research/reports/.gitkeep
git commit -m "feat(release): produce immutable research run evidence"
```

## Research Release Exit Review & Tagging

After merging PR #7 (`feat/phase6-frozen-research-run`) into `master`, verify the exit criteria and tag the milestone:

```powershell
git tag -a v0.1.0-alpha.research -m "Release v0.1.0-alpha.research: Phase 0–6 Research Foundation & Tracing"
git push origin v0.1.0-alpha.research
```

Before moving to the next plan, verify:

- TraceBench truth is independent and tri-state.
- Leakage audit passes on frozen split manifests.
- Rules, Logistic, LightGBM, and GraphSAGE each have five-seed evidence.
- Advanced GNN decision is either a focused new writing plan or `JUSTIFIED_NULL`.
- Candidate generator reaches the preregistered ceiling.
- Learned ranker is compared at matched recall and fixed budget.
- Actual cost/resource fields are present.
- Negative/null results remain in the report.
