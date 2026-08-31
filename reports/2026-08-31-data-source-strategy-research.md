# Data-source strategy research — 2026-08-31

## Decision

Use **AMLBench/AusAML only as the primary, version-pinned source for a small
complete scenario/time slice**. Use **IBM AMLSim only for separately reported,
controlled stress scenarios**. Do not acquire the full AMLBench repository on
the current machine, do not use AMLBench's producer masks as an evaluation
split, and do not mix the two sources into one training population.

This follows the graph AML specification's distinct primary-data and simulator
roles, provenance separation, and chronological evaluation policy
([Dataset Strategy](../.superpower/specs/2026-08-27-financial-crime-intelligence-platform-design.md#L123),
[Temporal Evaluation Policy](../.superpower/specs/2026-08-27-financial-crime-intelligence-platform-design.md#L155)).
It also preserves the research plan's frozen manifests, label-derived-column
denylist, explicit adapter mappings, and split-overlap audit
([plan](../docs/superpowers/plans/2026-08-30-research-foundation-training-tracing.md#L192),
[plan](../docs/superpowers/plans/2026-08-30-research-foundation-training-tracing.md#L439),
[plan](../docs/superpowers/plans/2026-08-30-research-foundation-training-tracing.md#L521),
[plan](../docs/superpowers/plans/2026-08-30-research-foundation-training-tracing.md#L627)).

No archive, dataset payload, or simulator sample archive was downloaded for
this research. External findings below are limited to the official IBM GitHub
repository and the Hugging Face repository's public metadata/card.

## Primary-source inventory

| Source | Access and license evidence | Size and content evidence | Strategy implication |
|---|---|---|---|
| [IBM AMLSim repository](https://github.com/IBM/AMLSim) at retrieved `master` commit [`7338a4b`](https://github.com/IBM/AMLSim/commit/7338a4bcb1af9bcfea2201ad7daccfe2a4d569ca) | Public GitHub repository. Its [LICENSE](https://github.com/IBM/AMLSim/blob/master/LICENSE) is Apache-2.0. The [README](https://github.com/IBM/AMLSim/blob/master/README.md) asks publication users to cite the listed papers. | The README describes a configurable multi-agent simulator that generates transaction CSVs, then emits accounts, transactions, alerts, SAR accounts, and logs. The official repository tree includes small checked-in `paramFiles/1K`, `sample/outputs`, and roughly 1.3 MB `sample/20K_*.tgz` fixtures; it does not establish a fixed benchmark corpus size. | Good for repeatable, configuration/seed-pinned stress scenarios; not the main population for model fitting. |
| [DVK2026/AMLBench metadata API](https://huggingface.co/api/datasets/DVK2026/AMLBench) at retrieved revision `0ce65bbd0b65718c1a40acbc71f59a7e2d6eb5d2` and [dataset card](https://huggingface.co/datasets/DVK2026/AMLBench/blob/main/README.md) | Public and ungated at retrieval. The card metadata declares `cc-by-4.0`; preserve attribution and the exact revision in every derived manifest. | API `usedStorage` is **45,057,280,916 bytes** (45.06 GB decimal; 41.96 GiB). The card declares 35,554,888 transactions, 50,000 primary customers, 112,620 accounts, a seven-month range, and four bank archives plus `AusAML-Small-Dataset.zip`. It says all PII is synthetic. | This is the primary source, but only a complete, bounded derivative is locally viable. Do not assume the small archive's schema, labels, or byte size before a later acquisition/manifest inspection. |

## Source-specific constraints

### AMLBench/AusAML

- The card says `labels.json` holds scenario boundaries, signal columns, node
  labels, and producer masks. It also says every one of the 297 scenarios is
  assigned to `train`: the seven-month window is insufficient for its own
  held-out temporal split. Therefore those masks are **not** evidence of
  generalisation and cannot be the project's validation/holdout contract.
- Define the project split after acquisition from complete scenarios and time
  windows; preserve causal availability and run entity, edge, and generator
  overlap checks. Do not take random rows from the 35.6M transactions.
- Treat `labels.json`, `_aml_designations`, `_scenario_log`, `scenario_id`,
  split masks, and analogous signal fields as gold/provenance material, not
  model inputs. The card's own examples make these label-bearing artefacts
  visible, so a denylist projection is required before training or scoring.
- The card limits intended use to research/benchmarking AML models, explicitly
  excludes systems intended to evade AML controls or launder money, and notes
  that the data is synthetic. Results must consequently be described as
  synthetic-data research evidence, not bank-production performance.

### IBM AMLSim

- The README requires Java 8 and Python 3.7, lists legacy dependencies
  including `networkx==1.11`, and describes a manual MASON JAR step even with
  Maven. Keep this generator outside the planned Python 3.12 application
  environment; use an isolated, disposable generator environment.
- Pin the repository commit, `conf.json`, parameter files, random seed,
  generator commands, output-file hashes, and schema hash in the stress-run
  manifest. The README makes all of those output/configuration seams explicit.
- The inspected sources license the **repository Work** under Apache-2.0 but
  do not state a separate license for generated datasets. Do not assert one;
  retain source attribution and obtain a legal/owner decision before any
  redistribution of generated outputs beyond the project's allowed use.

## Local feasibility at this worktree

Read-only spot checks on 2026-08-31 found 15.19 GiB RAM, 8.97 GiB free on
`D:`, and an RTX 4050 Laptop GPU with 6,141 MiB reported VRAM. The complete
AMLBench storage figure alone is about 4.7 times the free disk capacity, before
extraction, Parquet derivatives, indexes, or run evidence. Full AMLBench
acquisition is therefore **NOT FEASIBLE on the current disk**.

AMLSim's small repository fixtures are compatible with local adapter and
controlled-scenario work in principle, but its actual generator runtime has
not been measured here. A full graph/GNN run is also **not established** by
these checks; it needs the plan's measured resource profile and scaling
evidence, not a GPU-memory assumption.

## Smallest viable source plan

1. **Do not download AMLBench now.** Free or attach sufficient storage first,
   then record the actual resource profile and cost as required by the
   [research plan](../docs/superpowers/plans/2026-08-30-research-foundation-training-tracing.md#L321).
2. At acquisition time, inspect and hash only the named
   `AusAML-Small-Dataset.zip` first. Accept it only if its manifest confirms a
   transaction table plus the ground-truth material needed to construct a
   complete scenario/time subset. If it does not, acquire the smallest
   one-bank source that does; the public metadata does not give per-archive
   byte sizes, so no smaller choice can yet be evidenced.
3. Derive a **100k–500k-event complete scenario/time slice** from that primary
   source. Record dataset revision, archive SHA-256, schema hash, CC-BY-4.0
   label, transformation version, retained scenario IDs, and split manifest.
   Keep its gold labels out of the model frame. Promote to 500k–2M only after
   the end-to-end rules/tabular/trace path and resource profile succeed.
4. Independently run AMLSim's small, seed-pinned configuration for a single
   stress typology. Hash the generator source/configuration/output and report
   it as `stress`, never as pooled primary training data. Add further AMLSim
   mutations only after this one scenario is reproducible.
5. Report `NOT_RUN`/`SKIPPED_BY_DEPENDENCY` for any unavailable storage,
   legacy-generator dependency, or unmeasured full-graph run. Do not convert
   an access or capacity gap into an unsupported benchmark claim.

## Required future provenance record

For each acquired or generated input, retain: direct source URL; source
revision/commit; retrieval time; declared license; raw-byte SHA-256; schema
hash; generator version/configuration/seed where applicable; transformation
version; exact included scenarios/time range; split manifest; and the
resource/cost profile. This is the minimum evidence needed to distinguish
primary training, calibration, validation, sealed holdout, and AMLSim stress
results.
