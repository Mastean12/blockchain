# Final Research Submission Audit

**Date:** 18 November 2026
**Purpose:** readiness audit before thesis writing. Maps every research question to its evidence,
reconciles Phase 1–8 findings, and separates mandatory corrections from optional improvements.
**Status:** **AWAITING RESEARCH-LEAD APPROVAL.** No chapter was written. No experiment was run.
No frozen artefact, threshold or historical result was modified.

---

## 0. Executive summary

| Item | State |
|---|---|
| Phases executed | 0–8 |
| Gates passed | G0–G7 (G4 and G6 with documented scope limits) |
| Gates failed | **G8 — NOT PASSED** |
| Research questions answerable in full | **RQ1, RQ3 (partly), RQ4** |
| Research questions answerable in part | **RQ2** |
| Research questions **not** answerable | **RQ5** |
| **Material error found in this audit** | **Divergence counts were understated by 47 % (§3.1)** |
| Mandatory corrections before submission | **6** (§6.1) |
| Optional improvements | 7 (§6.2) |

**The thesis can be submitted honestly.** It cannot claim a successful robust-aggregation
contribution, and one previously reported statistic must be corrected in the record.

---

## 1. Research-question evidence matrix

The full matrix is a separate deliverable (`RESEARCH_QUESTION_EVIDENCE_MATRIX.md`) intended for
direct use when writing chapters. Summary below.

### RQ1 — Centralized performance and known limitations

| Field | Content |
|---|---|
| **Experiments** | Phase 4 B0 majority baseline; B1 centralized CNN (5 seeds); D1 class-weighted; D2 balanced-accuracy selection |
| **Results** | Centralized test acc **0.8423 ± 0.0383**, macro-F1 **0.2947 ± 0.0495** (rerun, seeds 42–46); **S recall 0.000 in 5/5** |
| **Gate** | **G4 PASSED** 16 Nov 2026 with documented defect |
| **Supported conclusion** | The frozen compact CNN achieves ~0.84 accuracy but **never predicts class S**; the defect is reproducible and not caused by selection or pooling alone |
| **Unsupported claim** | Any claim of supraventricular (S) detection capability; any clinical claim |
| **Limitations** | Test F support = 0; test S 93.2 % record 232; validation S = 61 windows over 4 records |

### RQ2 — Federated learning under heterogeneity

| Field | Content |
|---|---|
| **Experiments** | F1 IID-like, F2 moderate α=0.5, F3 severe α=0.1, F4 FedProx μ=0.01; ablation A2 (uniform weighting) |
| **Results** | F1 0.7861/0.3040; F2 0.8061/0.3079; **F3 0.8523/0.3752**; F4 0.8213/0.3390 (acc/macro-F1, 5 seeds each) |
| **Gate** | **G5 PASSED** 16 Nov 2026 after ablation A2 |
| **Supported conclusion** | FedAvg and FedProx are indistinguishable at matched rounds (val macro-F1 0.2662 vs 0.2669); **54 % of the F3-over-F1 advantage is aggregation weight dispersion** (one client at 37.1 %), 46 % partition composition |
| **Unsupported claim** | "Non-IID data improves performance" — refuted; also any claim that FedProx helps |
| **Limitations** | K = 5; one partition draw; checkpoint selection fragile at ≈0.28 |

### RQ3 — Privacy mechanisms

| Field | Content |
|---|---|
| **Experiments** | P2 HE-only; P3-a/b HE+DP; P1-ctl clip-only; D-2 diagnostic σ ∈ {0.01, 0.05} |
| **Results** | P2 **0.8471/0.3681**, HE error **1.4e-07**; P3-a 0.5672/0.1847 at ε=57.30; P3-b 0.4876/0.1648 at ε=22.02; D-2 σ=0.01: 0.7714/0.2924 at ε=44,112; σ=0.05: 0.8707/0.2327 with **V recall 0.000** at ε=1,872 |
| **Gate** | **G6 PASSED** with scope limits (G6-a/b/c) |
| **Supported conclusion** | **HE is functionally lossless** at 20.5× communication cost; **whole-model client-level DP destroys this classifier** at every tested configuration; no defensible privacy–utility operating point exists |
| **Unsupported claim** | That a useful DP operating point was found; that ε < 10 was demonstrated; that DP is unsuitable in general |
| **Limitations** | Client-level DP only, not record/patient; no secure aggregation; BatchNorm buffers unprotected; approved σ grid not run |

### RQ4 — Auditability and cost

| Field | Content |
|---|---|
| **Experiments** | B1 hash chain; B2 Ganache contract; 30-trial cost measurements |
| **Results** | B0/B1/B2 all **0.8728 / 0.3993** (bit-identical); B1 +0.12 %, B2 +4.03 % round time; 88,819 gas per client submission; 30.6 M gas per run; ≈28 ms p50; 38.4 tx/s; ≈112 B on-chain per round |
| **Gate** | **G7 PASSED**, scoped to L1 hash chain + L2 single-node EVM |
| **Supported conclusion** | Training operations can be made tamper-evident at negligible cost; authorisation and replay rejection require the contract at 33× the hashing overhead |
| **Unsupported claim** | That this is a distributed blockchain; consensus; decentralisation; that hashing proves update honesty; production cost |
| **Limitations** | Single node; writer is the adversary; truncation undetectable without anchor; no confidentiality |

### RQ5 — Robust aggregation

| Field | Content |
|---|---|
| **Experiments** | Original confirmatory (seeds 49–53); amended 3B (seeds 54–55, λ ∈ {1.5, 2.5}) |
| **Results** | **75 of 145 runs diverged (51.7 %)** — corrected, see §3.1; **15 of 29 cells unmeasurable**; in the 14 valid cells, **median is the only rule resisting both attacks**; detection: scaling 1.00, sign-flip 0.00–0.12 |
| **Gate** | **G8 NOT PASSED** |
| **Supported conclusion** | At K = 5 on this partition, the candidate baselines are **not deployable**: most diverge; the norm-based rejection policy is **blind to sign-flip**; divergence is **rule-dependent, not attack-strength-dependent** |
| **Unsupported claim** | **R2 is not supported and is not claimed.** No Byzantine-robustness claim. No poisoning-detection claim beyond norm-inflating attacks |
| **Limitations** | 51.7 % of the matrix unmeasurable; K = 5 only; λ sensitivity shows no viable operating point |

---

## 2. Reconciliation of Phase 1–8 findings

### 2.1 The S-class defect threads through everything

S recall is **0.000 in every condition** across Phases 4–8, including clean baselines. This is a
single, coherent, documented limitation — not a series of separate failures. It must be stated once,
prominently, and referenced thereafter. **No result in this thesis may be read as evidence of
supraventricular arrhythmia detection.**

### 2.2 G5 — the one place where a positive, mechanistically explained result was obtained

Ablation A2 converted an initially implausible finding (deep skew beating IID-like) into a measured
mechanism: **54 % weight dispersion, 46 % partition composition**. This is the thesis's strongest
methodological contribution and should be presented as such.

### 2.3 G6 — a strong positive (HE) and a strong negative (DP)

These are equally reportable. HE being **lossless at 1.4e-07** is a clean result. Whole-model
client-level DP being **destructive at every tested ε** is a legitimate negative finding that the
specification explicitly permits (§21 negative-result commitment applies analogously).

**Do not** present the DP negative as a limitation to be apologised for; present it as evidence about
the mechanism at K = 5, with its scope stated.

### 2.4 G7 — positive, tightly scoped

The audit layer works and is neutral (bit-identical metrics). The finding that hashes cost 0.12 %
while the contract costs 4.03 % is genuinely useful and should be the headline, not the gas numbers.

### 2.5 G8 — failure, correctly retained

G8 is **NOT PASSED**. R2 is **not claimed**. The failure is attributable to three mechanisms
documented in `PHASE_8_FAILURE_ANALYSIS.md`. The amended 3B analysis **refuted** the reduced-λ
hypothesis. 3A and 3C were **never implemented or run**.

---

## 3. Inconsistencies found

### 3.1 MATERIAL ERROR — divergence counts were understated by 47 %

**This is the most important correction in this audit.**

| Document | Claimed | **Actual** |
|---|---|---|
| `PHASE_8_CONFIRMATORY_REPORT.md` §0 | "40 runs diverged (27.6 %)" | **75 runs diverged (51.7 %)** |
| `PHASE_8_FAILURE_ANALYSIS.md` §1 | "40 divergent runs" | **75** |
| `PHASE_8_EXECUTION_STATUS.md` §0.2 | "Runs that diverged: 40 (27.6 %)" | **75 (51.7 %)** |

**Root cause.** The original analysis counted runs where `selected_round == 0` (40) rather than runs
where `diverged_at_round` was set (75). **35 runs diverged *after* selecting a valid round** and were
therefore counted as clean completions. Example: `fedavg/benign_outlier/f1` seed 49 diverged at round
7 but had selected round 5, so it was excluded from the divergence count despite being a divergence.

**Impact — and its bound:**

| Quantity | Effect |
|---|---|
| Cell classification (14 valid / 15 unmeasurable) | **UNCHANGED** — verified, there are **zero mixed cells**; divergence is all-or-nothing per cell |
| Round-0 invalidity argument | **UNCHANGED** — still 40 runs with unusable round-0 selection |
| Headline divergence rate | **WRONG: 27.6 % → 51.7 %** |
| 3B comparison (51.7 % at λ=1.5/2.5) | **Unchanged** — 3B genuinely is 60/116 = 51.7 %; the coincidence that it equalled the *incorrect* original figure is now explained |
| 3B conclusion (λ-insensitive) | **UNCHANGED** — rule-by-rule divergence patterns remain identical across λ |

**Consequence for the thesis:** the divergence rate must be reported as **51.7 %**, and the
statements "40 runs diverged" and "27.6 %" must not appear. The 3B narrative should note that the
corrected original rate and the amended rate are both 51.7 %, which *strengthens* the λ-insensitivity
conclusion.

### 3.2 Secondary inconsistencies

| # | Issue | Location | Action |
|---|---|---|---|
| I-1 | Phase 7 test count quoted as "183 passed, 16 skipped" and "183 passed, 1 skipped" interchangeably | Phase 7/8 docs | State the Ganache-running condition explicitly |
| I-2 | `LIMITATIONS.md` item 36/37 were stale; corrected 16 Nov 2026 | `LIMITATIONS.md` | **Already corrected** — verify no other document repeats the stale text |
| I-3 | Two different Phase 4 accuracy figures circulate: 0.8510 (original Colab) and 0.8423 (rerun) | Phase 4 docs, `phase5_results.json` | Both valid; must always state which. Rerun is the one with retained artefacts |
| I-4 | The audit's §2.2 estimated the label-transfer defect at "~4 ms/epoch"; measured in-situ value is ~116 ms/round | `PHASE_8_GPU_PERFORMANCE_AUDIT.md` §9.3 | **Already corrected** in §9.3 |
| I-5 | Krum reported as "least robust" — accurate at K = 5 but stated loosely in places | Phase 8 docs | Must always carry the "at five clients" qualifier |

---

## 4. Claims that must be narrowed, withdrawn or qualified

### 4.1 Must be WITHDRAWN

| # | Claim | Reason |
|---|---|---|
| W-1 | "40 confirmatory runs diverged (27.6 %)" | **Factually wrong** — 75 (51.7 %) |
| W-2 | Any statement that a useful DP operating point exists | None was found |
| W-3 | Any claim that R2 (proposed robust aggregator) is supported | No R2 is defined or validated; G8 not passed |

### 4.2 Must be NARROWED

| # | Current form | Narrowed form |
|---|---|---|
| N-1 | "Blockchain audit" | "Hash-chained audit log (L1) and single-node EVM prototype (L2)" |
| N-2 | "The defence detects poisoning" | "A norm threshold detects **norm-inflating** attacks (1.00) and **not** sign-flip (0.00–0.12)" |
| N-3 | "Krum is not robust" | "At the tested five-client configuration, Krum's `n−f−2` selection degenerates to one client" |
| N-4 | "HE is lossless" | "HE approximation error (1.4e-07) did not measurably change metrics on this partition" |
| N-5 | "DP provides privacy protection" | "Client-level DP with ε = 22–57 at R = 50 provides no meaningful protection in this setting" |

### 4.3 Must be EXPLICITLY QUALIFIED

| # | Claim | Required qualifier |
|---|---|---|
| Q-1 | Any accuracy figure | Test F support = 0; S recall = 0.000; macro-F1 over N/S/V/Q only |
| Q-2 | Any "non-IID" result | 54 % is aggregation weighting; does not generalise beyond this partition draw |
| Q-3 | Any robustness statement | K = 5 only; 51.7 % of the matrix unmeasurable |
| Q-4 | Any gas/latency figure | Local single-node Ganache; not a production cost; no fee reported |
| Q-5 | Any DP ε | Client-level, not record/patient; no secure aggregation; BatchNorm unprotected |
| Q-6 | G4 "passed" | Passed **with documented defect**; the defect is not fixed |

---

## 5. Recommended thesis structure

### 5.1 Results chapter

Recommended order, by strength of evidence:

1. **RQ1 baseline and the S-class defect** — establish the limitation first, so everything after is read in context.
2. **RQ2 federated comparison and the A2 weighting ablation** — the strongest methodological result.
3. **RQ3 privacy** — HE positive, DP negative, presented as two separate findings.
4. **RQ4 audit** — tamper evidence at 0.12 % vs authorisation at 4.03 %.
5. **RQ5 robust aggregation** — present as a **failed gate with a diagnosed cause**, including the corrected 51.7 % divergence and the 3B refutation.

**Do not** order by phase number if it buries the S-class limitation. Lead with it.

### 5.2 Discussion chapter

Three subsections:

1. **What worked and why** — HE neutrality, audit neutrality, the A2 mechanism.
2. **What failed and why** — DP at K = 5; robust aggregation at K = 5; the S-class defect. Each with its measured mechanism, not speculation.
3. **The common thread** — three of the four negative results are **five-client / low-support artefacts**, not implementation errors. That is a coherent thesis-level insight.

### 5.3 Conclusion chapter

Must include the negative results as findings, not as caveats. A conclusion that reports only
positives would misrepresent the work.

### 5.4 Limitations chapter

Consolidate from `LIMITATIONS.md` (37 items) into 6 thematic groups: dataset, S-class, federated
scale, DP scope, ledger scope, robustness scope. Do not enumerate 37 items in the thesis body; use an
appendix.

### 5.5 Future work

Ordered by what the evidence actually supports:

| Priority | Direction | Justification from evidence |
|---|---|---|
| 1 | **Larger K** | Krum/Multi-Krum/trimmed-mean all fail by arithmetic at K = 5 |
| 2 | **Per-layer / central DP** | Whole-model DP fails on the `√d` term |
| 3 | **Direction-aware detection** | Norm detection is blind to sign-flip (proposal 3C, never run) |
| 4 | **Revisiting the S-class split** | The defect is structural, not architectural |
| 5 | **SVDB external validation** | E1 never executed |

---

## 6. Missing mandatory evidence and optional improvements

### 6.1 MANDATORY corrections before submission

| # | Item | Why mandatory |
|---|---|---|
| **M-1** | **Correct the divergence count to 75 / 51.7 %** in the confirmatory report, failure analysis and execution status | A published statistic is wrong by 47 % |
| **M-2** | Erratum noting the corrected figure in `PHASE_8_CONFIRMATORY_REPORT.md` §0 and `PHASE_8_EXECUTION_STATUS.md` §0.2 | Traceability of the correction |
| **M-3** | Every results table must state the S-class and test-F caveat | Prevent unsupported clinical reading |
| **M-4** | Every audit claim must carry the L1/L2 qualifier | Prevent blockchain over-claim |
| **M-5** | G8 must be reported NOT PASSED throughout; R2 not claimed | Integrity requirement |
| **M-6** | Confirm `LIMITATIONS.md` items 36/37 stay corrected and no document reverts them | Consistency |

**None of M-1 … M-6 requires running an experiment.** All are documentary.

### 6.2 Optional improvements (not blocking)

| # | Item |
|---|---|
| O-1 | Run proposal 3A (clipping) — note the failure analysis now suggests it will likely fail for the same norm-insensitivity reason |
| O-2 | Run proposal 3C (direction detection) — addresses an unaddressed question |
| O-3 | Execute E1 (SVDB external validation) |
| O-4 | Resolve G5 residual: 46 % of the F3 advantage remains unexplained |
| O-5 | Add per-record breakdowns for S to strengthen the RQ1 limitation |
| O-6 | Consolidate the 37 limitations into thematic groups |
| O-7 | Add a reproducibility appendix (hashes, seeds, environment) |

### 6.3 Is anything blocking submission outright?

**No.** Every research question has an honest answer at its current scope. RQ5's answer is "the
candidate baselines are not deployable at K = 5, and the gate is not passed" — which is a valid
finding. Submission is possible after the six documentary corrections.

---

## 7. Integrity confirmation

| Check | Result |
|---|---|
| Frozen split `bbcfa25c…` | **Unchanged** |
| Frozen client manifest `71dbcac3…` | **Unchanged** |
| Frozen F3 partition `da8b96fa…` | **Unchanged** |
| Frozen thresholds 0.05 / 0.10 / 0.90 | **Unchanged** |
| Phase 1–7 results | **Unchanged** |
| Phase 8 original confirmatory outputs | **Unchanged** |
| Phase 8 amended 3B outputs | **Unchanged** |
| 3A / 3C | **Never implemented, never run** |
| Amended confirmatory seeds 56–60 | **Never run** |
| Development/confirmatory pooling | **None** |
| New experiments run for this audit | **None** |
| Test suite | 183 passed, 16 skipped |
| Committed / pushed | **No** |

---

## 8. Decisions requested

| # | Decision | Recommendation |
|---|---|---|
| **F-1** | Approve the corrected divergence figure (75 / 51.7 %) and its propagation | **Approve** — mandatory |
| **F-2** | Approve the claim withdrawals W-1…W-3 | **Approve** |
| **F-3** | Approve the narrowed claim wording N-1…N-5 | **Approve** |
| **F-4** | Approve the recommended chapter structure (§5) | Approve, with the S-class limitation leading |
| **F-5** | Confirm no further Phase 8 work before submission | Confirm — 3A/3C are optional |
| **F-6** | Confirm G8 NOT PASSED and R2 not claimed appear in the abstract | **Mandatory** |

**Stopping here for research-lead approval. Nothing committed or pushed.**
