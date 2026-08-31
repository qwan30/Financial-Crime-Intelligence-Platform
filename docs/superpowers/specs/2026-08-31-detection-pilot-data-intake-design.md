# Detection Pilot Data Intake Design

**Goal:** Establish a reproducible, local detection/graph data pilot using the downloaded AMLSim 20K sample and a future small AMLBench slice, without claiming TraceBench truth or a Research Release.

## Scope

The pilot covers source registration, safe acquisition, verification, canonicalization, public-model artifact creation, and split/leakage evidence. It does not download full AMLBench, generate learned-tracing metrics, create trace gold, or tag a research release.

## Source roles

| Source | Role | Allowed claim |
| --- | --- | --- |
| AMLSim 20K fan-in sample | Local synthetic adapter and graph smoke data | Adapter, graph, and detection-pipeline smoke evidence only |
| AMLBench/AusAML pinned slice | Detection and heterogeneous graph benchmark | Detection/graph pilot evidence only |

AMLSim relative ticks become timestamps only through a caller-supplied synthetic epoch and duration. Those timestamps are non-source-provenance. AMLSim has no independent edge-level tri-state trace gold, so it cannot support learned-tracing release claims.

## Intake flow

`source declaration → capacity preflight → secure acquisition → raw/member checksums → source-specific schema validation → canonical public artifact → frozen manifest → split/leakage audit → pilot evidence`

Each source declaration records immutable upstream URL/revision, license, terms/access date, archive and extracted-member hashes, schema hash, row count, extraction selector, intended use, prohibited claims, and known limitations. Derived artifacts record parent hashes, adapter version, conversion parameters, and output hash.

## Capacity policy

The preflight estimates raw archive bytes, extraction bytes, processed artifact bytes, temporary workspace, and a fixed safety headroom. It returns `READY` only when all fit on local disk; otherwise it returns `SKIPPED_BY_RESOURCE` with no download. The current machine must not download or extract AMLBench's 7.56 GB archive until adequate free disk exists. The AMLBench selector must target a documented, small source subset rather than the full archive.

## Safety and leakage rules

- Acquire only authenticated HTTPS sources pinned by revision/checksum.
- Validate archive paths and extraction sizes before consuming members; reject traversal and unsupported members.
- Raw and processed data remain ignored by Git.
- Canonical public artifacts use source-specific allowlists; label/scenario/split fields never reach model inputs.
- Error reports contain source identifiers and hashes, not transaction values or local absolute paths.
- Split evidence proves pairwise track exclusivity, declared temporal boundaries/purge policy, and typology/generator boundaries when present.

## Validation

- Unit tests cover manifest parsing, checksum mismatch, capacity decisions, unsafe archive members, canonical schema allowlists, and deterministic source conversion.
- Integration tests use tiny synthetic source fixtures only; no large remote download runs in CI.
- A local pilot records its input and output hashes, resource profile, and a `detection_only` verdict.

## Done criteria

The pilot is complete when AMLSim and a pinned AMLBench slice have independently verifiable source manifests, canonical public artifacts, frozen lineage evidence, and a passing leakage/split audit. The final report must state that tracing claims and the Research Release are not enabled unless independent edge-level gold truth and all release gates exist.
