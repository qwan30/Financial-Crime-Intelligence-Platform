# Financial Crime Intelligence Platform — Specification Review

**Review date:** 2026-08-28
**Pull request:** `qwan30/Financial-Crime-Intelligence-Platform#1`
**Reviewed head SHA:** `e25fb446899c0cb9478f9b605bfe470159fed29f`
**Reviewed file:** `.superpower/specs/2026-08-27-financial-crime-intelligence-platform-design.md`
**Review scope:** specification correctness, internal consistency, data/ML isolation, streaming/replay correctness, evidence/case semantics, security/authorization, governance, release truth, and implementation ordering.

## Overall verdict

**REQUEST CHANGES if this PR is intended to approve the document as the normative V1 design.**

There are **no P0/Critical findings** in this review. The specification is unusually strong in its truth boundary, final-test isolation, negative-result/null-champion handling, immutable evidence intent, forward-correction strategy, accessibility requirements, and refusal to claim cross-system exactly-once semantics.

However, several contracts are internally incomplete or inconsistent enough that different implementers could build mutually incompatible systems while still believing they satisfy the spec. The most important issues are around deterministic replay lineage, the evidence/case aggregate model, status-specific evidence semantics, Phase 7/8 dependency ordering, workload identity, poison-record behavior, and retention versus reconstructability/audit verification.

Recommended disposition:

- **Block normative approval/merge-as-final-design until P1 items are resolved.**
- If the document is merged only as an explicitly unfinished draft, retain the findings below as tracked design debt and remove any claim that the whole-branch review found no Important/Minor issues.

---

# Review method

The review was performed as independent review lenses and then reconciled:

1. **Architecture / dependency reviewer**
2. **Data / ML evaluation reviewer**
3. **Streaming / recovery reviewer**
4. **Security / authorization / governance reviewer**
5. **Evidence / case / AI-grounding reviewer**
6. **Release-truth / PR-evidence reviewer**

The current ChatGPT surface does not expose a literal subagent-dispatch runtime, so these were independent review passes rather than falsely claimed spawned agents.

---

# Strengths worth preserving

## 1. Truth boundary is excellent

The spec clearly distinguishes:

- research-grade vs. production-ready;
- local evidence vs. remote/release evidence;
- intended targets vs. measured results;
- candidate champion vs. null champion;
- mocks vs. live/integration evidence.

This is one of the strongest parts of the document and should not be weakened during remediation.

## 2. Final-test isolation is substantially better than a typical ML project spec

The separation among:

- development train;
- model-selection validation;
- calibration;
- final temporal test;
- unknown-typology evaluation;
- AMLSim stress evaluation

is explicit, and the sealed-null path correctly prevents a bad research outcome from creating pressure to inspect the final test.

## 3. Streaming semantics avoid the common “exactly once” overclaim

The spec correctly describes:

- at-least-once delivery;
- deterministic IDs;
- a PostgreSQL continuation ledger;
- idempotent sinks;
- replay/reconciliation;
- forward correction instead of pointer rollback after activation.

That conceptual direction is strong.

## 4. Case authority and AI authority are intentionally constrained

The human workflow, reviewer approval, immutable history, read-only AI tools, citation validation, prompt-injection controls, and provider-degraded manual path are well aligned.

## 5. External dataset planning facts are mostly grounded

The current AMLBench/AusAML dataset card confirms the major planning facts used by the spec, including roughly:

- 112,620 accounts;
- 35,554,888 transactions;
- seven months;
- 297 unique scenarios;
- 5% AML-customer prevalence;
- 45.1 GB total size;
- all 297 scenarios assigned to the provided training split, requiring users to define their own evaluation split.

The dataset card currently reports a `cc-by-4.0` license. Phase 0 should still pin and hash the exact revision and license text as the spec already requires.

---

# P1 — Important findings

## P1-1 — `ReplayManifestCore` does not include every output-affecting version

### Problem

Section 12.4 derives:

- `replay_core_hash`;
- `state_generation_id`;
- `replay_run_id`

from `ReplayManifestCore`.

The core explicitly includes schema/mapping/feature/rule/model/calibration/threshold versions, but the canonical `RiskDecision` and `EvidencePackage` contracts later depend on additional versioned inputs, including at least:

- fusion version;
- graph-state / graph-construction version;
- decision-contract version;
- evidence-contract / evidence-derivation version;
- potentially sensitivity/evidence-policy versions when those affect evidence-item canonical bytes.

The spec itself requires canonical hashes to include `fusion`, while the replay core does not explicitly freeze it.

### Why this matters

Two replay executions could have the **same replay lineage identifiers** but legitimately produce different canonical outputs because an output-affecting configuration was not part of the replay core.

That creates ambiguous lineage and can produce:

- same generation/run identity with different decisions;
- conflict quarantine for what was actually a configuration change;
- false replay-equivalence failures;
- inability to prove which configuration produced staged corrections.

### Required remediation

Define one normative rule:

> Every configuration, schema, policy, or artifact version capable of changing state, risk-decision canonical bytes, evidence canonical bytes, correction behavior, or ordering MUST be included in `ReplayManifestCore` before IDs are derived.

At minimum, explicitly add:

- graph construction/state contract version;
- fusion version;
- decision contract version;
- evidence contract / evidence extraction version;
- correction policy version where it affects generated artifacts;
- evidence sensitivity/authorization-classification policy version if it affects hashed evidence content.

Also require a test that mutates each output-affecting version and proves that the replay core hash/run lineage changes.

---

## P1-2 — Risk `EvidencePackage` and case evidence snapshots are conflated

### Problem

Section 14 defines an `EvidencePackage` around a scoring decision with fields such as:

- original event;
- model/rule/feature versions;
- component/final score;
- one decision status;
- one replay lineage.

Section 15 then allows one case to accumulate:

- multiple distinct risk occurrences;
- corrections and retractions;
- analyst-added evidence;
- notes;
- merge/split lineage;
- proposed dispositions;
- reopened investigations.

At the same time, the spec says every case snapshot references an immutable `EvidencePackage`, and case commands create successor “evidence versions,” but it never normatively defines the aggregate object that represents **case-level evidence across many packages and human additions**.

The AI grounding rules further require membership validation in “the exact package,” which becomes ambiguous when a case contains multiple risk packages.

### Why this matters

Without a distinct aggregate contract, different implementations may:

- mutate or clone a risk `EvidencePackage` to represent a case;
- silently flatten multiple risk packages;
- lose superseded/current semantics;
- give the AI an unclear grounding boundary;
- make merge/split and correction snapshots non-reconstructable.

### Required remediation

Introduce a separate immutable aggregate, for example:

`CaseEvidenceSnapshot`

Suggested minimum fields:

- `case_evidence_snapshot_id`;
- `case_id`;
- `case_version`;
- ordered/set-normalized references to all included `EvidencePackage` IDs/hashes;
- current/superseded/retracted occurrence mapping;
- analyst-authored evidence-item references;
- note references (notes should remain distinguishable from source facts);
- merge/split provenance;
- authorization/sensitivity summary;
- completeness/degradation state;
- creation command and prior snapshot ID;
- canonical content hash.

Then state:

- risk decisions reference `EvidencePackage`;
- case lifecycle commands reference `CaseEvidenceSnapshot`;
- AI runs are grounded against an exact authorized `CaseEvidenceSnapshot`, which may expose evidence items from multiple underlying packages.

---

## P1-3 — `ABSTAINED` / `FAILED_CLOSED` evidence semantics conflict with the continuation ledger contract

### Problem

Section 10.3 allows a scoring attempt to return:

- `SCORED`;
- `ABSTAINED`;
- `FAILED_CLOSED`.

Section 14.1 explicitly mandates an `EvidencePackage` for every `SCORED` risk decision, but does not clearly define status-specific requirements for the other outcomes.

Section 12.3, however, says every `EventTransitionResult` contains the complete canonical `RiskDecision` **and `EvidencePackage` payloads** before Redis advancement.

The canonical evidence schema also includes score-related fields that may not exist for `FAILED_CLOSED`.

### Why this matters

An implementation cannot tell whether:

1. `FAILED_CLOSED` must still create an evidence package;
2. that package must contain null score fields;
3. the package is optional in the ledger;
4. failure evidence uses a different schema.

This ambiguity affects idempotency, replay hashes, auditability, and downstream case behavior.

### Required remediation

Choose one normative model.

Preferred option:

> Every scoring attempt creates a canonical decision-evidence envelope. `SCORED`, `ABSTAINED`, and `FAILED_CLOSED` have status-specific required/forbidden fields, and no synthetic score is ever generated.

For example:

- `SCORED`: final score required.
- `ABSTAINED`: score may be absent; available components/evidence allowed.
- `FAILED_CLOSED`: final score forbidden; typed failure reason and available diagnostic evidence required.

Then update Sections 10, 12, and 14 so the ledger and hash contracts agree.

---

## P1-4 — Phase 7 requires a latency promotion gate before Phase 8 builds the streaming scoring integration

### Problem

The null/champion selection rules list latency among the frozen pre-final promotion gates.

But the roadmap says:

- **Phase 7** freezes/selects the eligible candidate and completes the final research protocol.
- **Phase 8** is where the frozen package is integrated into the ingestion/scoring worker and where the benchmark harness and end-to-end event-to-risk behavior appear.

If “latency” means end-to-end incremental scoring latency under the production-shaped streaming path, Phase 7 cannot measure the required system because Phase 8 has not been built yet.

If it means model-only inference latency, the spec does not distinguish that from the Section 13 end-to-end performance target.

### Why this matters

The phase DAG becomes non-executable or implementation-dependent.

One team may use model inference latency; another may use a research notebook; another may defer the gate, all while claiming compliance.

### Required remediation

Split the gate explicitly:

**Phase 7 pre-final model package gate**
- `model_inference_p95_ms`;
- memory footprint;
- deterministic package load/score time;
- bounded batch/single-event benchmark.

**Phase 8/12 operational gate**
- `event_to_decision_p95_ms`;
- throughput;
- Kafka lag;
- persistence/outbox overhead;
- failure rate;
- recovery behavior.

Do not make champion selection depend on an integration path that does not yet exist.

---

## P1-5 — Service-to-service identity is missing even though privileged system principals exist

### Problem

The case lifecycle gives a `case-ingestion system principal` authority to:

- `CREATE_CASE`;
- `ATTACH_RISK_OCCURRENCE`.

Section 18 strongly specifies human OIDC authentication and server-side authorization, but explicitly says OIDC protects the analyst web and every **non-service API**. It does not normatively define:

- workload identity;
- service authentication mechanism;
- token audience;
- credential rotation;
- mTLS/client credential expectations;
- least-privilege scopes;
- replay protection;
- how the ingestion/scoring worker authenticates to the case API.

This is especially important because correction attachment can affect current evidence, priority, proposals, and potentially reopen flow.

### Why this matters

A system principal with undefined authentication is a high-value authorization gap. An implementer could fall back to:

- static shared bearer tokens;
- network trust;
- unauthenticated internal routes;
- overly broad administrator credentials.

That would violate the production-shaped security goals even if the human UI is secure.

### Required remediation

Add a workload-identity contract.

For example:

- service principals MUST authenticate with OIDC/OAuth2 client credentials or workload identity, optionally bound by mTLS;
- credentials MUST be short-lived and rotatable;
- token audience MUST be the target service;
- scopes MUST be action-specific;
- ingestion principal may create/attach occurrences but MUST NOT gain analyst/reviewer/admin authority;
- service authorization MUST be evaluated server-side on every call;
- identity, token ID/key ID, authorization result, and trace lineage MUST be audited;
- fixture bypass MUST never satisfy integration/release gates.

---

## P1-6 — Poison-record quarantine is unsafe unless failure classes are separated

### Problem

Section 12.7 says poison records move to bounded quarantine after the declared retry count.

Section 12.3 simultaneously requires:

- PostgreSQL continuation record;
- Redis CAS;
- sink/outbox receipts;
- `COMPLETE`;
- only then Kafka offset commit.

The spec does not state whether “poison record” applies only to deterministic pre-transition validation failures or also to failures that occur **after durable state/effect work has begun**.

### Why this matters

If a record is quarantined-and-skipped after:

- the PostgreSQL result committed;
- Redis advanced;
- one sink succeeded;
- another sink failed,

then advancing the Kafka offset can create an incomplete logical effect.

If the offset is not advanced, the partition may remain permanently blocked despite the “move to quarantine” wording.

### Required remediation

Define a failure-class matrix.

At minimum:

**Pre-transition deterministic poison**
- invalid schema;
- impossible enum;
- malformed immutable source payload;
- deterministic unsupported input.

May:
- produce a terminal quarantine outcome;
- persist the quarantine receipt;
- commit the source offset according to a defined policy.

**Post-transition / post-ledger failure**
- Redis CAS mismatch;
- sink failure;
- outbox failure;
- receipt failure;
- corrupted stored canonical payload.

Must:
- never be converted into a skip-and-advance quarantine outcome;
- remain recoverable/blocking until reconciliation, forward correction, or controlled replay resolves it.

Add tests for each crash/failure boundary.

---

## P1-7 — Retention/deletion rules conflict with reconstructable evidence and full audit-chain verification

### Problem

The spec requires:

- immutable, reconstructable evidence for alerts and material case conclusions;
- every source fact to resolve to an immutable event/artifact;
- audit verification to stream records in sequence and recalculate every canonical hash.

The retention section also says:

- cases, evidence, audit, datasets, prompts/outputs, and logs MUST have finite explicit retention;
- eligible payloads may be deleted while legally/audit-required hashes and tombstones are preserved.

A hash/tombstone alone is insufficient to reconstruct deleted evidence content.

Likewise, if canonical audit event fields are deleted, a verifier cannot later recalculate every event hash from the original canonical record.

### Why this matters

The spec currently promises two things that cannot both remain universally true after payload deletion:

1. full reconstructability / full hash recalculation;
2. payload deletion with only hashes/tombstones retained.

### Required remediation

Define retention dependencies and sealed audit segments.

For evidence:

- source artifacts referenced by an active/retained `CaseEvidenceSnapshot` MUST be retained at least as long as that snapshot requires reconstructability;
- if lawful deletion requires source removal, the case/evidence state MUST explicitly transition to a typed `SOURCE_PAYLOAD_RETIRED` / non-reconstructable state rather than continuing to claim full reconstructability.

For audit:

- define immutable signed audit segments/checkpoints;
- state exactly which canonical fields remain retained;
- define what can be cryptographically verified after an old segment expires;
- do not claim full re-hashing of deleted records.

---

# P2 — Moderate / clarification findings

## P2-1 — “Signed manifest” semantics are not defined consistently

The document repeatedly requires manifests and decision records to be “signed” and content-hashed.

The audit root has stronger key-language, but research/evaluation manifest signatures do not define:

- whether signatures are cryptographic or application approvals;
- canonical signed envelope;
- algorithm;
- key ID;
- signer identity binding;
- trust root;
- verification procedure;
- rotation/revocation;
- behavior after key compromise.

### Recommendation

Create one `SignedArtifactEnvelope` contract used for:

- Phase decisions;
- pre-execution gate manifests;
- split manifests;
- evaluation manifests;
- release manifests where applicable.

If “signed” means human workflow approval rather than cryptographic signing, say that explicitly and use a different term.

---

## P2-2 — PR body claims independent approval, but the PR has no submitted GitHub reviews/comments

The PR description states that:

- independent task review approved after fixes;
- independent whole-branch review found no Critical, Important, or Minor findings.

At review time, the PR had:

- zero submitted GitHub reviews;
- zero PR comments.

This does not prove the review did not occur elsewhere, but the PR does not provide an immutable link/hash for that evidence.

### Recommendation

Either:

1. attach/link/hash the local agent-review artifacts; or
2. change the PR wording to something like:
   - “local agent review completed”;
   - “no findings in local review artifact `<hash>`”.

Avoid an unqualified “independent review approved” claim when the review evidence is not present.

---

## P2-3 — AMLSim stress testing uses mixed MUST/SHOULD language

The V1 goals and Phase 7 path make AMLSim stress evaluation part of the candidate research protocol, while Section 9.4 says AMLSim **SHOULD** generate controlled changes across stress axes.

### Recommendation

Make the normative intent explicit:

- candidate path: at least one approved AMLSim stress configuration **MUST** execute when Phase 0/branch prerequisites are satisfied;
- unsupported axes MAY be skipped only with the same dependency-evidence discipline;
- the choice of individual stress axes may remain SHOULD/MAY.

---

## P2-4 — Explicitly enforce the fiat-only claim boundary against crypto-labelled AMLBench scenarios

The current AMLBench/AusAML dataset card includes digital-asset typologies such as crypto/stablecoin-related scenarios.

The spec says V1 MUST NOT claim cryptocurrency/blockchain AML, and Phase 0 already provides a mechanism to exclude unsupported typologies.

### Recommendation

Make this scope boundary explicit in Phase 0:

- identify every scenario/feature/table associated with crypto/digital-asset typologies;
- exclude them from fiat-banking headline typology metrics and V1 claims;
- record whether their transactions remain only as unlabeled/background context;
- prevent a model from gaining a hidden advantage from crypto-specific generator markers if those scenarios are excluded from V1 scope.

This is primarily a claim-boundary clarification, not a dataset-selection blocker.

---

## P2-5 — Single global audit-chain serialization should have an explicit load/availability gate

The audit contract uses one ordered chain per deployment/project and requires protected read/access events to be appended before the response is returned.

That is simple and tamper-evident, but it also creates a serialized chain-head contention point for:

- evidence reads;
- AI tool calls;
- case mutations;
- authorization-relevant accesses.

### Recommendation

Either:

- explicitly accept the single-writer audit chain as a bounded local-reference constraint and include it in the benchmark manifest; or
- define approved partitioned chains with signed roots/aggregation.

Do not discover this bottleneck only during Phase 12.

---

# Suggested patch order

## Patch 1 — Determinism and evidence contracts

Fix first:

1. P1-1 ReplayManifestCore closure
2. P1-2 CaseEvidenceSnapshot
3. P1-3 status-specific evidence semantics

These affect IDs, hashes, schemas, replay, correction, AI grounding, and case state. They should stabilize before implementation planning.

## Patch 2 — Runtime/security correctness

Then fix:

4. P1-5 service/workload identity
5. P1-6 poison-record failure matrix
6. P1-7 retention / reconstructability / audit segments

## Patch 3 — Roadmap/governance cleanup

Then fix:

7. P1-4 Phase 7 vs Phase 8 latency gate
8. P2-1 signature semantics
9. P2-3 AMLSim normative wording
10. P2-4 fiat-only dataset scope
11. P2-5 audit-chain load gate

Finally update the PR validation section so review claims match the evidence actually attached to the PR.

---

# Proposed acceptance criteria for the remediated spec

Before calling the design review clean, verify all of the following:

- [ ] Every output-affecting version is frozen in replay lineage.
- [ ] Changing any output-affecting version changes the replay core hash/lineage in a contract test.
- [ ] Risk `EvidencePackage` and aggregate `CaseEvidenceSnapshot` are separate normative schemas.
- [ ] Multi-occurrence, correction, merge, split, note, disposition, and reopen flows identify the exact case evidence snapshot used.
- [ ] `SCORED`, `ABSTAINED`, and `FAILED_CLOSED` have unambiguous evidence/hash rules.
- [ ] Phase 7 uses model-package latency only; operational end-to-end latency is gated after integration.
- [ ] Service principals have explicit workload authentication and least-privilege authorization.
- [ ] Poison handling distinguishes pre-transition terminal quarantine from post-transition recoverable failures.
- [ ] Evidence retention cannot silently destroy reconstructability while the UI/API still claims evidence is reconstructable.
- [ ] Audit retention has a verifiable segment/checkpoint model.
- [ ] “Signed” approval artifacts have one defined signature/approval contract.
- [ ] AMLSim candidate-path obligations use consistent normative language.
- [ ] Fiat-only V1 scope explicitly handles crypto-labelled source scenarios.
- [ ] PR review claims link to or hash the actual review evidence.

---

# Final assessment

This is a **strong draft with sophisticated correctness thinking**, not a bad design.

The main issue is that the document has become precise enough that the remaining ambiguities are now **contract bugs**, not cosmetic gaps. Most of them come from interactions between otherwise good sections:

- replay lineage vs. canonical evidence hashing;
- per-risk evidence vs. case-level evidence aggregation;
- fail-closed outcomes vs. durable continuation;
- model governance vs. delivery-phase ordering;
- retention vs. reconstructability;
- human authorization vs. service-principal authority.

Fixing these now will materially reduce implementation churn later.

**Review result:** `REQUEST_CHANGES` for normative V1 approval; no P0/Critical findings.
