# TASK-002 — immutable manifest contracts

## Scope

- Starting candidate: `94c563626c284884b78b2815e17cb60444a74116`.
- Final merged candidate: `ca2f4cc848f6a7e74ed64b40a0aa49b5618ab737`.
- Branch: `feat/phase0-bootstrap-manifests-baseline`.
- The initial implementation followed Research Plan Task 2 in `src/fincrime/contracts/manifests.py` and `tests/contracts/test_manifests.py`; independent security and quality review then deliberately hardened validation and expanded tests in those same files.
- Confirmed by repository search that no existing manifest contract, type, helper, or import served this purpose.
- The final candidate remains within the Task 2 manifest-contract boundary, but it is not an exact-plan-only implementation because it includes the review-driven integrity hardening below.

## Initial TDD evidence

1. Added the two plan-specified tests before production code.
2. RED: `uv run pytest tests/contracts/test_manifests.py -v` exited 1 during collection with `ModuleNotFoundError: No module named 'fincrime.contracts'`.
3. GREEN: added the minimal plan-specified immutable Pydantic contracts, trace labels, and streaming `sha256_file` helper.
4. `uv run pytest tests/contracts/test_manifests.py -v` then passed both tests.
5. Ruff identified `timezone.utc` in the plan test as incompatible with the configured Python 3.12 rule; replacing it with the equivalent `datetime.UTC` alias preserved behavior and made the gate pass.

## Independent review hardening

Independent security and quality review produced follow-up commits `7fb6dab51c28581a2418452d0c98a2f26065b8ad` and `ca2f4cc848f6a7e74ed64b40a0aa49b5618ab737`. They added deliberate integrity checks beyond the plan's illustrative two-test minimum:

- reject whitespace-only dataset, trace-edge, case, anchor, visibility-boundary, and split case identifiers;
- reject empty or whitespace-only dataset licenses, generator versions, and typology provenance;
- require timezone-aware dataset creation and trace-edge event timestamps;
- require a strict integer generator seed, rejecting booleans;
- explicitly reject uppercase values for dataset, schema, and configuration SHA-256 fields;
- verify a complete trace-gold manifest and preservation of all split tracks;
- verify `sha256_file` against a known content digest; and
- retain explicit immutability and distinct `UNKNOWN` trace-label coverage.

The final focused suite contains 31 tests after parameter expansion: frozen-model behavior (1), dataset/schema hash casing (2), dataset ID (1), license provenance (2), dataset timestamp awareness (1), trace-label values (1), trace-edge IDs (3), trace-edge timestamp awareness (1), complete trace-gold provenance (1), configuration-hash casing (1), trace-gold IDs (2), generator-version/typology provenance (4), nested anchor/boundary IDs (2), strict generator seed (1), split-track preservation (1), split case IDs (6), and file hashing (1).

## Delivered contract

- Frozen Pydantic models reject undeclared fields and mutation.
- `DatasetManifest` validates non-blank identifiers and license provenance, lowercase 64-character SHA-256 strings, and an aware creation timestamp.
- `TraceLabel` keeps `UNKNOWN` distinct from relevant and confirmed-benign labels.
- `TraceEdge` requires non-blank identifiers and an aware event timestamp.
- `TraceGoldManifest` requires non-blank provenance and identifiers, a strict integer seed, a lowercase configuration hash, and non-blank nested identifiers.
- `SplitManifest` preserves collection immutability with tuples and rejects blank case identifiers across every track.
- `sha256_file` hashes files incrementally in 1 MiB chunks.
- No dataset schema, package-level re-export, dependency, or API outside the Task 2 manifest-contract boundary was added.

## Verification

- Baseline `uv run pytest -q`: 1 passed.
- Initial RED focused pytest: expected import failure, exit 1.
- Initial GREEN focused pytest: 2 passed.
- Final candidate `uv run pytest tests/contracts/test_manifests.py -q`: 31 passed.
- Final candidate `uv run pytest -q`: 32 passed.
- Final candidate `uv run ruff check .`: all checks passed.
- Final candidate `uv run mypy src`: success, no issues in 2 source files.
- Final candidate `git diff --check`: passed.

## Concerns

- None. The review-driven additions intentionally strengthen manifest provenance and type integrity; they should not be represented as exact-plan-only scope.
