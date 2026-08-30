# Spec Review — PR #1: Remediated End-to-End Design Specification

**Date:** 2026-08-28
**PR under review:** [qwan30/Financial-Crime-Intelligence-Platform#1](https://github.com/qwan30/Financial-Crime-Intelligence-Platform/pull/1) — *docs: remediated end-to-end design specification for Financial Crime Intelligence Platform*
**File reviewed:** `.superpower/specs/2026-08-27-financial-crime-intelligence-platform-design.md` (**PR head of branch `docs/spec-remediation`**)
**Review method:** Three independent reviewer agents (AML/ML research, systems/architecture, product/governance & spec quality), each with a narrow scope contract, findings consolidated by the orchestrator.
**Status:** 🔶 **Request changes** — no architectural rework required; one Critical research-validity gap, one Critical contract contradiction, and a set of Important specification gaps must be fixed before merge.

---

## 1. Executive Summary

The PR-head spec is an unusually disciplined document: RFC-2119 requirement language, a "Product Truth Boundary" that honestly disclaims all unproven claims, preregistered content-hashed gate manifests with PROCEED/STOP/SKIPPED_BY_DEPENDENCY outcomes, a purged scenario-grouped temporal split, a sealed final-test regime, a first-class null-champion path, deterministic replay/activation contracts, a hash-chained audit log, and a read-only evidence-grounded AI investigator. The three reviewers independently rated it above typical design-doc quality.

However, the review found:

- **2 Critical findings** — missing numeric label-support floors that would let evaluation gates pass on statistically meaningless sets (C1), and a genuine contradiction in case-reopen review authority (C2).
- **~14 Important findings** — undefined mechanisms the spec depends on (checkpoints, completeness watermarks, calibrator support), a multi-entity/cross-partition scoring ambiguity, cutover fence semantics, missing infrastructure baselines, a segregation-of-duties inconsistency, and under-specified AI grounding/prompt-injection predicates.
- **~13 Minor findings** — undefined terms, readability, metric-support phrasing, and one **merge-hygiene issue of a different kind**: the local working copy of the spec diverges from the PR head (see C3 / §2).

### PR recommendation

> **Request changes — do not merge yet.** Resolve C1, C2, C3 and the Important findings below in a single remediation commit. No Critical systems-architecture flaws were found; the streaming core (replay, activation cutover, fail-closed semantics) is correct as written and must not be weakened while fixing the rest.

---

## 2. Critical Findings

### C1. No minimum label-support floors for evaluation sets — gates are satisfiable on vacuous data
**Source:** AML/ML review · **Spec refs:** §6.3 (item 7), §8.1–8.5, §8.4
- The protocol demands six disjoint sets (train, validation, calibration, final temporal test, unknown-typology, AMLSim stress), but the only numeric support floor in the whole spec is the isotonic-calibration rule (≥100 positives / ≥100 negatives). Platt scaling — the **default** — has no minimum, and the Phase 0 split gate only requires sets to be "non-empty".
- With ~5% account prevalence over 7 months, a calibration set with a handful of positives makes fitted calibration, bootstrap CIs, and frozen promotion gates statistically meaningless — while every *stated* gate still passes. This defeats the spec's own truth-boundary purpose.
- **Recommendation:** Preregister explicit minimums per set: minimum positive scenario groups and positive accounts (including calibration and final test), minimum calendar span per temporal set, minimum scenario-group count for the unknown-typology family. Failure of any floor → Phase 0 REVISE/STOP. Report per-set positive counts in the split manifest and bind them to the floors.

### C2. Contradiction in case-reopen review authority (§15.1 vs §15.3)
**Source:** Product/governance review · **Spec refs:** §15.1 lifecycle command matrix vs §15.3 last paragraph
- §15.1 enumerates the V1 lifecycle commands *exhaustively*; `REOPEN_CASE` is authorized only for a **Reviewer**. But §15.3 says an invalidated terminal disposition "MUST transition to `REOPENED` through **Reviewer or approved quality-control authorization**" — a principal that exists nowhere in §18's roles, has no command, and no definition.
- The spec claims its lifecycle matrix is deterministic and actor-authorized; as written there are two valid readings of the highest-sensitivity transition in the system (reopening a closed suspicious case).
- **Recommendation:** Either delete "approved quality-control authorization" from §15.3, or define the role in §18 and add the corresponding command to the §15.1 matrix.

### C3. (Orchestrator / process) The local working copy diverges from the PR head
**Source:** Orchestrator pre-review diff (merge hygiene, not spec text)
- The untracked local file `.superpower/specs/2026-08-27-financial-crime-intelligence-platform-design.md` is an **older draft** (Status: "Approved design / ready for implementation planning", no phase structure) while the PR head is the remediated version (Status: "Draft / remediated; pending user approval and Phase 0 feasibility", RFC-2119 language, Phases 0–13). The two share a filename but differ substantially.
- **Why it matters:** Anyone reviewing or working from the local copy reads a different contract than the PR contains; a careless commit could regress the PR.
- **Recommendation:** Align the working tree with the PR head (`git checkout docs/spec-remediation` / restore the file from the branch) or clearly rename the stale local draft. Never keep two divergent documents under the same path.

---

## 3. Important Findings

### AML / ML research (reviewer: `aml-ml-reviewer`)

| ID | Refs | Finding | Recommendation |
|---|---|---|---|
| I1 | §5, §8.1, §8.3, §8.5, §9.4 | Unknown-typology set has no access policy, no temporal placement rule, and no threshold-freeze rule — §8.3's single-access/freeze regime covers only the final temporal test, leaving the flagship experiment's set unprotected from leakage/peeking. | Extend sealed-access and threshold-freeze rules to the unknown-typology set; define its temporal placement relative to train/validation/calibration. |
| I2–I7 | §8, §9 (various) | Gaps around ablation definition, heterogeneity-dependent branch gating, and gate-manifest cross-references (e.g., heterogeneity-conditioned branches lack a defined fallback when Phase 0 mapping cannot support heterogeneous entity types). | Define ablation units and metric expectations per branch; specify the fallback/degraded branch and its own gates for heterogeneity-dependent paths. |
| I8 | §9.4 → §8.6 | Candidate-path `SKIPPED_BY_DEPENDENCY` cross-references §8.6, whose skip categories were written for the sealed-null path ("dependence on sealed final-test data" cannot apply when the final test is not sealed). | Enumerate candidate-path skip categories explicitly in §9.4, each requiring a content-hashed decision citing mapping evidence. |

### Systems / architecture (reviewer: `systems-arch-reviewer`) — *no Critical findings*

| ID | Refs | Finding | Recommendation |
|---|---|---|---|
| I-1 | §12.1, §11.4, §10.1 | Multi-entity transactions: per-entity commands route to different partitions, but nothing gates risk-decision emission on counterpart completeness — a graph/counterparty-dependent component could silently score incomplete state, breaking evidence reconstructability (§14) and replay equivalence (§12.4). | Classify each scoring component as partition-local vs cross-entity; cross-entity components score only when the (to-be-defined) completeness watermark covers the event's counterpart set, else apply the predeclared abstention rule. Define the watermark's computation and home. |
| I-2 | §12.4 | Partition-scoped cutover vs. global activation pointer is ambiguous: per-partition flips create a mixed-generation window (partition A scores G₂ while B mutates G₁); multi-partition fence semantics are unspecified. | State explicitly whether the compare-and-set flips one global pointer after all affected partitions are fenced; define fencing across multiple partitions. |
| I-3 | §12.3–12.5 | The recovery story leans on **checkpoints** the spec never contracts: no format, ownership, frequency, placement, or restore-validation requirement. | Add a checkpoint contract (owner, cadence, storage, integrity check, restore drill) to §12. |
| I-4 | §13, §15 (latency) | The headline latency target lacks a pinned measurement definition (percentiles, warm/cold, what counts as scored, workload mix); the throughput gate is similarly unpinned. | Define the measurement protocol and freeze it as part of the benchmark manifest. |
| I-5 | §28 (infra) | Docker Compose infrastructure is under-specified relative to the services the contracts depend on (resource baselines, health/dependency startup order, version pinning policy). | Add an infrastructure baseline section pinning service versions, startup/health requirements, and minimum resource profile. |
| I-6 | §21, §12.4 | Late-event handling: no alert/decision rule for when forward correction is required vs. automatic; per-entity correction isn't offered as default for isolated late events. | Define a `REPLAY_REQUIRED` count/age alert and a decision rule; default to per-entity correction for bounded lateness, full rebuild for systematic divergence. |

### Product / AI agent / governance & spec quality (reviewer: `product-gov-reviewer`)

| ID | Refs | Finding | Recommendation |
|---|---|---|---|
| I-A | §18 vs §15 | Segregation-of-duties inconsistency between the RBAC role definitions (§18) and the lifecycle command matrix (§15) — the role/command mapping doesn't close. | Reconcile the §18 role list with the §15 command matrix so every command maps to exactly one authorized role. |
| I-B | §16 (AI investigator) | Two AI gates rely on undefined predicates, making them unenforceable as written (the grounding-validation predicate and the confidence-classification rule lack precise definitions). | Define the predicates numerically or structurally (input, check, threshold, output state) so they are testable. |
| I-C | §19 (disposition) | One disposition rule references an undefined term, making the rule unenforceable. | Add the missing definition or restate the rule in terms of defined entities. |
| I-D | §16.x (prompt-injection controls) | The injection control enumerates four retrieved-text channels as "all retrieved text and source fields", but analyst-entered text (notes/comments/reason codes) that later feeds agent context is not covered — an implementer could sanitize exactly the four channels and pass analyst text through raw. | Restate as a positive rule: *all* retrieved content of any kind (including analyst notes, comments, reason codes) is untrusted data; add a stored-narrative injection case to the §16.6 adversarial suite. |

*Note: I-B/I-C summarize reviewer output on AI-gate and disposition predicates; consult the reviewer notes for exact sub-section numbers during remediation.*

---

## 4. Minor Findings (consolidated)

1. **§6.1 heading overclaims** — "Verified AMLBench facts" before verification; rename to "Candidate AMLBench facts to verify" per the §2 truth boundary. *(aml)*
2. **No multiplicity accounting** across eight gated branches tested against shared validation data; require the CALIBRATION_FUSION report to state how many comparisons were made. *(aml)*
3. **Successor branches may execute after predecessor STOP**; require inheritance of data/label-driven STOPs as dependency skips unless a distinct input artifact is named. *(aml)*
4. **TGN/hybrid local-compute feasibility** — require a measured scaling curve (events/sec at ≥3 sample sizes) in the §9.2 profile gate so full-run cost is extrapolated, not assumed. *(aml)*
5. **"Where label support permits" (§8.5)** weakens MUST-report metrics; fold the C1 floors in — unsupported metrics must be reported as `NOT_SUPPORTED_EVIDENCE`, not omitted. *(aml)*
6. **Adversarial stress is parameter-sweep only** — no adaptive evasion axis and no explicit clean-graph FPR control; name both as post-V1/optional so §2's claim boundary stays explicit. *(aml)*
7. **Undefined terms** — `deployment_id` (§19.2, keys the audit chain), "compatible nonterminal evidence state" (§15.1 merge matrix), Champion "named local reference use" (§5), data-class documentation owner (§19.1). *(gov)*
8. **"All applicable Phase 12 gates MUST rerun" (Phase 13)** — "applicable" undefined; enumerate via the gate manifest or "all mandatory gates of Phases 11–12". *(gov)*
9. **Synchronous audit append before protected response (§19.2)** — couples audit write latency to every evidence read/tool call with no stated failure fallback; specify fail behavior. *(gov)*
10. **"Targets are requirements until measured" (§12.5)** — ambiguous phrasing; restate as "targets are acceptance criteria; reports MUST publish measured values and PASS/FAIL". *(gov)*
11. **Mega-clause readability (§8.1, §12.3–12.4, §15.1)** — 150–250-word single sentences chaining 10+ MUST clauses hide the document's few real ambiguities (C2, I-A); split into numbered sub-requirements. *(gov)*
12. **AI invocation not role-scoped (§16.2)** — per-call authorization uses the human user's identity, but no statement says *which* roles may invoke AI runs; map AI-run invocation to §18 roles. *(gov)*
13. **Systems minors** — define the "committed entity watermark" formula and commit location (§12.2); bound quarantine (count/size/retention + re-delivery path + §21 metric, §12.7); add PostgreSQL durability/RPO (it is the continuation source of truth, §12.3/§19.5); make Neo4j rebuildability an explicit MUST with a §22.5 drill; add RFC 8785 golden-vector conformance tests (non-NFC, exponent-notation adversarial inputs) and require a seeded/deterministic load generator with reported run variance (§14.3/§22.1/§13). *(systems)*

---

## 5. Strengths (keep — do not weaken during remediation)

- **Streaming correctness core** (§12.3–12.4): deterministic replay, idempotency-ID lineage, activation cutover with compare-and-set fencing, fail-closed semantics — rated above typical design-doc quality.
- **Leakage architecture** (§7.4, §8.1–8.3): scenario-grouped union-find leakage groups, anchor-time assignment, purge intervals, single-execution sealed final test, explicit leakage denylist.
- **Honest governance** (§2, §5, §8.6, §9.5, §20): truth boundary, null champion as a first-class outcome, human-gated promotion ("Automatic promotion is prohibited").
- **AI safety** (§16): read-only investigator, evidence-citation grounding validation, numeric adversarial gates in §16.6.
- **Audit integrity** (§19.2): gapless hash chain with non-exportable signing key and verification cadence.
- **Release truth** (§24, Phase 12/13): exact-SHA discipline, no tag-without-rerun.
- **PR-description honesty check passed:** every substantive claim in the PR description (Phases 0–13, preregistered gates, PROCEED/STOP/SKIPPED_BY_DEPENDENCY, null champion, sealed final test, purged split, state generations, activation cutover, forward correction, WCAG 2.2 AA, RBAC, audit integrity, exact-SHA release, Mobbin unavailability) was independently verified as present in the PR-head spec body. *(One caveat: the PR body reports an internal review with "no Critical… findings"; this review found two — see §2.)*

---

## 6. Required Changes Before Merge (checklist)

- [ ] **C1** — Add preregistered numeric label-support floors for every evaluation set; bind them to Phase 0 REVISE/STOP and the split manifest.
- [ ] **C2** — Resolve §15.1 vs §15.3 reopen-authority contradiction (define or delete "approved quality-control authorization").
- [ ] **C3** — Align the local working copy with the PR head (or rename the stale draft) so no divergent document shares the spec's path.
- [ ] **I-1 (systems)** — Cross-entity completeness rule + defined completeness watermark gating cross-entity scoring components.
- [ ] **I-2 (systems)** — Disambiguate cutover scope (global pointer vs per-partition) and multi-partition fence semantics.
- [ ] **I-3 (systems)** — Add the checkpoint contract (format, owner, cadence, integrity, restore validation).
- [ ] **I-4 (systems)** — Pin the latency/throughput measurement protocol in the benchmark manifest.
- [ ] **I-5 (systems)** — Add Docker Compose infrastructure baseline (versions, health/dependency order, resource profile).
- [ ] **I1–I8 (ML)** — Unknown-typology access/placement/freeze rules; ablation & heterogeneity-branch fallback definitions; candidate-path skip categories.
- [ ] **I-A…I-D (gov)** — Reconcile §18/§15 role-command mapping; define the two AI-gate predicates and the disposition-rule term; restate prompt-injection control as "all retrieved content is untrusted".
- [ ] Optionally sweep the Minor findings in the same pass (small textual amendments).

**Suggested merge gate:** a single remediation commit on `docs/spec-remediation` addressing C1, C2 and all Important findings, re-reviewed with a diff-only pass; then merge.

---

*Review produced by the `team-agent-orchestration` pass on 2026-08-28. Reviewer cards: `task_0001` (AML/ML), `task_0002` (systems/architecture), `task_0003` (product/governance & spec quality); consolidation by the orchestrator. All section references are to the PR-head spec on branch `docs/spec-remediation`.*
