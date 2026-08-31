# Detection Pilot Data Intake Design

**Goal:** Establish a reproducible, local detection/graph data pilot with source-specific quality evidence, using the downloaded AMLSim 20K sample and a future small AMLBench slice, without claiming TraceBench truth or a Research Release.

## Scope

The pilot covers source registration, safe acquisition, verification, canonicalization, public-model artifact creation, and split/leakage evidence. It does not download full AMLBench, generate learned-tracing metrics, create trace gold, or tag a research release.

## Source roles

| Source | Role | Allowed claim |
| --- | --- | --- |
| AMLSim 20K fan-in sample | Local synthetic adapter, cleaning, and graph smoke data | Adapter, quality, graph, and detection-pipeline smoke evidence only; a temporal split needs explicit raw-tick evidence |
| Instrumented AMLSim | Future TraceBench source | Tracing only after separately generated hidden edge-level gold is verified; outside this detection pilot |
| AMLBench/AusAML pinned slice | Detection and heterogeneous graph benchmark | Detection/graph pilot evidence only |

AMLSim relative ticks become timestamps only through a caller-supplied synthetic epoch and duration. Those timestamps are non-source-provenance. AMLSim has no independent edge-level tri-state trace gold, so it cannot support learned-tracing release claims.

## Intake flow

`source declaration → capacity preflight → secure acquisition → raw/member checksums → raw profile → reason-coded quarantine → source-specific clean artifact → restricted label artifact → public artifact → frozen manifest → split/leakage audit → pilot evidence`

Each source declaration records immutable upstream URL/revision, license, terms/access date, archive and extracted-member hashes, schema hash, row count, extraction selector, intended use, prohibited claims, and known limitations. Derived artifacts record parent hashes, adapter version, conversion parameters, and output hash. A quality manifest additionally binds raw hash/schema, cleaner policy version, input/accepted/rejected/duplicate counts, reason-code report hash, clean/label artifact hashes, and admission evidence; hashes never contain local absolute paths.

## Capacity policy

The preflight estimates raw archive bytes, extraction bytes, processed artifact bytes, temporary workspace, and a fixed safety headroom. It returns `READY` only when all fit on local disk; otherwise it returns `SKIPPED_BY_RESOURCE` with no download. The current machine must not download or extract AMLBench's 7.56 GB archive until adequate free disk exists. The AMLBench selector must target a documented, small source subset rather than the full archive.

## Safety and leakage rules

- Acquire only authenticated HTTPS sources pinned by revision/checksum.
- Validate archive paths and extraction sizes before consuming members; reject traversal and unsupported members.
- Raw and processed data remain ignored by Git.
- Canonical public artifacts use source-specific allowlists; label/scenario/split fields never reach model inputs.
- Raw records are immutable: missing/invalid identifiers, non-finite or non-positive amount, invalid tick/time, and missing required columns are quarantined with a reason code and raw-row locator, never silently coerced or dropped.
- Exact duplicate raw rows are reported. Without a stable source transaction ID, they are retained; `(source, target, amount, tick)` is never used as a deduplication key.
- Outliers are profile-only in this pilot; they are neither removed nor winsorized.
- AMLSim `nodes.csv.isFraud` is a restricted account-level target artifact, not a transaction label or model feature. `isFraud`, `fraudStep`, scenario/case fields, source labels, and split masks are denied from public/model artifacts; any training label join is explicit and occurs after split construction.
- Error reports contain source identifiers and hashes, not transaction values or local absolute paths.
- Split evidence proves pairwise track exclusivity, declared temporal boundaries/purge policy, and typology/generator boundaries when present. AMLSim 20K is `NOT_EVALUABLE` when raw-tick cutoff, embargo, and entity/edge-overlap evidence are absent; synthetic calendar mapping alone is insufficient.

## Validation

- Unit tests cover manifest parsing, checksum mismatch, capacity decisions, unsafe archive members, canonical schema allowlists, deterministic source conversion, quality-count reconciliation, reason-coded quarantine, duplicate reporting, label isolation, and blocked temporal evidence.
- Integration tests use tiny synthetic source fixtures only; no large remote download runs in CI.
- A local pilot records its input and output hashes, resource profile, and a `detection_only` verdict.

## Done criteria

The pilot is complete when AMLSim and a pinned AMLBench slice have independently verifiable source manifests, canonical public artifacts, frozen lineage evidence, and a passing leakage/split audit. The final report must state that tracing claims and the Research Release are not enabled unless independent edge-level gold truth and all release gates exist.
