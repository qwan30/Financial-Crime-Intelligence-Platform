# TASK-002 — immutable manifest contracts

## Scope

- Starting candidate: `94c563626c284884b78b2815e17cb60444a74116`.
- Branch: `feat/phase0-bootstrap-manifests-baseline`.
- Implemented only Research Plan Task 2 in `src/fincrime/contracts/manifests.py` and `tests/contracts/test_manifests.py`.
- Confirmed by repository search that no existing manifest contract, type, helper, or import served this purpose.

## TDD evidence

1. Added the two plan-specified tests before production code.
2. RED: `uv run pytest tests/contracts/test_manifests.py -v` exited 1 during collection with `ModuleNotFoundError: No module named 'fincrime.contracts'`.
3. GREEN: added the minimal plan-specified immutable Pydantic contracts, trace labels, and streaming `sha256_file` helper.
4. `uv run pytest tests/contracts/test_manifests.py -v` then passed both tests.
5. Ruff identified `timezone.utc` in the plan test as incompatible with the configured Python 3.12 rule; replacing it with the equivalent `datetime.UTC` alias preserved behavior and made the gate pass.

## Delivered contract

- Frozen Pydantic models reject undeclared fields and mutation.
- `DatasetManifest` validates non-empty identifiers/license values and lowercase 64-character SHA-256 strings.
- `TraceLabel` keeps `UNKNOWN` distinct from relevant and confirmed-benign labels.
- `TraceGoldManifest` and `SplitManifest` preserve collection immutability with tuples.
- `sha256_file` hashes files incrementally in 1 MiB chunks.
- No dataset schema, package-level re-export, dependency, or API beyond Task 2 was added.

## Verification

- Baseline `uv run pytest -q`: 1 passed.
- RED focused pytest: expected import failure, exit 1.
- GREEN focused pytest: 2 passed.
- Final `uv run pytest -q`: 3 passed.
- Final `uv run ruff check .`: all checks passed.
- Final `uv run mypy src`: success, no issues in 2 source files.
- Final `git diff --check`: passed.

## Concerns

- None. The implementation intentionally follows the stated contract without introducing additional manifest schema or exports.
