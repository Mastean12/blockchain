# Research Question Evidence Matrix

**Purpose:** working reference for thesis writing. Every RQ and hypothesis mapped to its
experiments, numbers, gate, permitted conclusions and required qualifications.
**Status:** for research-lead approval. Companion to `FINAL_RESEARCH_SUBMISSION_AUDIT.md`.
**Rule:** a claim may appear in the thesis **only** if it is listed as supported here. Everything in
the "Unsupported / must not claim" column is prohibited regardless of how it is phrased.

---

## 0. Reading guide

| Column | Meaning |
|---|---|
| **Evidence** | Experiment IDs and their document locations |
| **Result** | Verified numbers, 5 seeds unless stated |
| **Gate** | Gate status; G4/G6 are scoped |
| **Supported** | Claims permitted in the thesis |
| **Prohibited** | Claims that must not appear |
| **Required qualifier** | Text that must accompany any use of the result |

---

## RQ1 — Centralized baseline and known limitations

| Field | Content |
|---|---|
| **Evidence** | B0 majority baseline; B1 centralized CNN (seeds 42–46); D1 class-weighted; D2 balanced-accuracy selection. Docs: `PHASE4_EXECUTION_STATUS.md`, `PHASE_4_G4_RESOLUTION.md`, `PHASE_4_S_CLASS_FAILURE_INVESTIGATION.md` |
| **Result** | Test acc **0.8423 ± 0.0383**; macro-F1 **0.2947 ± 0.0495**; **S recall 0.000 in 5/5**; D1 0.8142/0.3403; D2 0.8251/0.3207; S recall 0.000 in D1 and D2 also |
| **Gate** | **G4 PASSED** 16 Nov 2026 — *with documented defect* |
| **Supported** | (a) The frozen compact CNN reaches ~0.84 accuracy on the frozen split. (b) It **never predicts class S** across 30 fits. (c) The defect is reproducible on independent hardware. (d) Two interventions were tested and **both failed** their pre-registered criteria: selection is not the cause (max P(S) = 0.052 on real S beats) and max+mean pooling reached at most 4 of 61 validation S windows. (e) A linear model reaches 0.13–0.58 S recall on held-out *training* records, so S is learnable in principle |
| **Prohibited** | Any S detection capability claim. "The model classifies five arrhythmia classes" without qualification. Any clinical or diagnostic framing |
| **Required qualifier** | "Test F support is 0; test S support is concentrated in record 232 (93.2 %); macro-F1 excludes F and covers N/S/V/Q" |

---

## RQ2 — Federated learning under non-IID heterogeneity

| Field | Content |
|---|---|
| **Evidence** | F1 IID-like (`7d635f51…`), F2 moderate α=0.5 (`c447d732…`), F3 severe α=0.1 (`da8b96fa…`), F4 FedProx μ=0.01; **ablation A2** uniform weighting. Docs: `PHASE_5_RESULTS_AND_ANALYSIS.md`, `PHASE_5_G5_DIAGNOSIS.md` |
| **Result** | F1 **0.7861/0.3040**; F2 **0.8061/0.3079**; F3 **0.8523/0.3752**; F4 **0.8213/0.3390**. A2: F3 uniform **0.3364** (drop 0.0388 = 54 % of the 0.0712 gap); F2 uniform 0.3157 (dose–response). Control reproduced frozen F3 **exactly on 5/5 seeds** |
| **Gate** | **G5 PASSED** 16 Nov 2026 |
| **Supported** | (a) Federated training tracks centralized within ~0.07 acc. (b) **FedAvg and FedProx are indistinguishable at matched rounds** (val macro-F1 0.2662 vs 0.2669) — the apparent F4 gap is checkpoint-selection noise. (c) **54 % of the F3-over-F1 macro-F1 advantage is sample-count aggregation weight dispersion**, with one client holding 37.1 % of the aggregate (weight ratio 4.26× vs 1.26× on F1). (d) The residual 46 % is partition composition. (e) The effect **scales with weight dispersion** across F2 and F3 |
| **Prohibited** | "Non-IID data improves federated performance." "FedProx improves over FedAvg here." Any generalisation beyond this partition draw |
| **Required qualifier** | "Five clients; one Dirichlet draw per partition; 54 % attribution measured on this split, not a general law about skew" |

---

## RQ3 — Differential privacy and homomorphic encryption

| Field | Content |
|---|---|
| **Evidence** | P2 HE-only (CKKS N=8192); P3-a/b HE+DP; P1-ctl clip-only; D-2 diagnostic σ∈{0.01,0.05}. Docs: `PHASE_6_RESULTS_AND_ANALYSIS.md`, `PHASE_6_DP_FRONTIER_DIAGNOSTIC.md`, `PHASE_6_CALIBRATION_REPORT.md` |
| **Result** | **P2: 0.8471/0.3681, HE rel. error 1.4e-07**, +20.5× communication, ≈4 % round time. P3-a **0.5672/0.1847** at **ε = 57.30**; P3-b **0.4876/0.1648** at **ε = 22.02**. D-2 σ=0.01 **0.7714/0.2924** at **ε = 44,112**; σ=0.05 **0.8707/0.2327** with **V recall 0.000** at **ε = 1,872** |
| **Gate** | **G6 PASSED** with scope limits (G6-a threat model, G6-b D-2 substitution, G6-c DP negative accepted) |
| **Supported** | (a) **HE is functionally lossless**: P2 macro-F1 0.3681 vs plaintext 0.3752, approximation error 1.4e-07, at 20.5× communication cost. (b) **Whole-model client-level DP destroys this classifier** at every tested configuration. (c) **No defensible privacy–utility operating point exists** in the explored region. (d) P3 reports ε **identical** to the corresponding DP-only values, so HE adds confidentiality and **not** differential privacy. (e) The arithmetic cause: noise L2 scales as `σ·√d` with d = 36,357, giving 47–377× noise-to-signal at the approved σ |
| **Prohibited** | Any claim of a useful DP operating point. Any ε below 9.23 being demonstrated. "DP is unsuitable in general" — only the whole-model client-level mechanism at K = 5 was tested. Any record/patient-level privacy claim. Any confidentiality claim against the CKKS key holder |
| **Required qualifier** | "Client-level DP, replace-one equal-cardinality adjacency, five clients, no secure aggregation; the 448 BatchNorm buffers are unprotected" |

**Note on σ=0.05:** its higher accuracy (0.8707) is the **majority-class rate**, not preserved
utility — V recall is exactly 0.000 and macro-F1 (0.2327) is *below* σ=0.01. This must be stated
whenever the figure appears.

---

## RQ4 — Auditability and blockchain cost

| Field | Content |
|---|---|
| **Evidence** | B1 hash chain; B2 Ganache contract; 30-trial cost measurement. Docs: `PHASE_7_RESULTS_AND_ANALYSIS.md`, `PHASE_7_READINESS_REPORT.md`, `docs/threat_model/SECURITY_THREAT_MODEL.md` |
| **Result** | B0/B1/B2 all **0.8728 / 0.3993** — **bit-identical**; B1 **0.12 %**, B2 **4.03 %** of round time; B1 and B2 produced the **same ledger head hash**; 88,819 gas per `UpdateCommitted` (n=150); 30.6 M gas per 50-round run; ≈28 ms p50; **38.4 tx/s** serial; ≈112 B on-chain per round; 352 ledger entries verify |
| **Gate** | **G7 PASSED** — scoped to L1 + L2 only |
| **Supported** | (a) The audit layer is **neutral**: bit-identical metrics across B0/B1/B2. (b) Training operations can be recorded **tamper-evidently** at 0.12 % overhead. (c) The contract adds **authorisation and replay rejection** at 4.03 % — 33× the hashing cost. (d) Interior alteration, deletion and reordering are detected **at the exact index**. (e) **Truncation and consistent rewrite are undetectable without an out-of-band anchor** — a documented limitation with a test asserting it. (f) Personal-information controls are enforced by 44 tests over a closed whitelist |
| **Prohibited** | "Blockchain" unqualified. "Consensus", "decentralised", "Byzantine-resistant", "immutable" (use *tamper-evident*). "Verifies that updates are correct/honest". "Encrypted on-chain". Any production cost, fee or energy claim |
| **Required qualifier** | "Level 1 hash-chained audit log and Level 2 single-node Ganache prototype; local-environment measurements only; the ledger writer is the party the audit is meant to constrain" |

---

## RQ5 — Robust aggregation under malicious clients

| Field | Content |
|---|---|
| **Evidence** | Original confirmatory (seeds 49–53, 145 runs); amended 3B (seeds 54–55, 116 runs, λ ∈ {1.5, 2.5}). Docs: `PHASE_8_CONFIRMATORY_REPORT.md`, `PHASE_8_FAILURE_ANALYSIS.md`, `PHASE_8_AMENDED_3B_RESULTS.md`, `PHASE_8_PROTOCOL_AMENDMENT_PROPOSAL.md` |
| **Result** | **75 of 145 runs diverged (51.7 %)** — *corrected figure*; **15 of 29 cells unmeasurable**; 14 valid cells: **median resists both attacks** (scaling drop −0.046/−0.036; sign-flip 0.014/0.028) with **honest FPR 0.0000**; trimmed mean resists scaling at f=1 (0.040) but is **defeated by sign-flip** (0.053/0.072); **FedAvg, Krum, Multi-Krum diverge in every attacked cell**; detection **scaling 1.00, sign-flip 0.00–0.12**. **3B: divergence 51.7 % at λ=1.5 and 2.5 — identical, and identical rule-by-rule** (median 0, FedAvg 12/14, Krum 6/8) |
| **Gate** | **G8 NOT PASSED** |
| **Supported** | (a) The candidate robust baselines are **not deployable at K = 5** on this partition. (b) **Divergence is a property of the aggregation rule, not attack strength** — identical divergence counts at λ = 1.5 and 2.5, and identical to which rules fail. (c) **Honest heterogeneity alone destabilises some rules**: `benign_outlier` diverges 10/16 with no malicious client. (d) A **norm-based rejection policy is blind to sign-flip** (0.00–0.12) while detecting scaling perfectly (1.00). (e) Median is the only evaluated rule that completes under both attacks without rejecting honest clients. (f) Reduced λ is **not** a viable stability intervention — 0 % measurability improvement |
| **Prohibited** | **R2 is NOT supported and must not be claimed.** "G8 passed". "The defence detects poisoning" (narrow to norm-inflating). "Krum is not robust" (qualify to K = 5). Any round-0 metric presented as aggregation performance. Pooling development with confirmatory results |
| **Required qualifier** | "Five clients only; 51.7 % of the matrix unmeasurable; Krum and Multi-Krum degenerate by arithmetic at this client count (`n ≥ 2f+3` fails at f = 2); no Byzantine-robustness claim is made" |

### RQ5 unmmeasurable cells — must be disclosed

All 15 below had **5/5 seeds diverge**. They must appear in the thesis as unmeasurable, not omitted.

fedavg/benign_outlier f1, f2 · fedavg/scaling f1, f2 · fedavg/signflip f1, f2 ·
krum/benign_outlier f1 · krum/scaling f1 · krum/signflip f1 ·
multi_krum/benign_outlier f1 · multi_krum/scaling f1 · multi_krum/signflip f1 ·
trimmed_mean/benign_outlier f2 · trimmed_mean/scaling f2 · trimmed_mean/signflip f2

---

## Hypotheses

| ID | Hypothesis | Status | Evidence |
|---|---|---|---|
| H1 | Deep skew degrades federated performance relative to IID-like | **REFUTED** | F3 (0.8523) > F1 (0.7861); A2 explains 54 % as weighting |
| H2 | FedProx mitigates non-IID degradation | **NOT SUPPORTED** | F4 0.3390 vs F3 0.3752; indistinguishable at matched rounds; F5 not run |
| H3 | DP can be applied with acceptable utility loss | **REFUTED** at this scale | P3-a/b collapse; D-2 finds no operating point |
| H4 | HE protects updates at acceptable cost | **SUPPORTED** (with scope) | P2 lossless at 1.4e-07; 20.5× communication cost |
| H5 | Combined DP+HE gives the expected trade-off | **PARTIALLY** | P3 has exactly P1's ε; HE adds confidentiality, not privacy; but utility collapses |
| H6 | Training can be audited at low cost | **SUPPORTED** | B1 0.12 %, bit-identical metrics |
| H7 | A robust aggregator can resist attacks while preserving honest utility | **NOT SUPPORTED / GATE FAILED** | G8 not passed; 51.7 % unmeasurable |
| H8 | Reducing attack strength restores measurability | **REFUTED** | 3B: identical divergence at λ=1.5, 2.5 |

---

## Cross-cutting required statements

These must appear wherever the corresponding result is used:

1. **S recall = 0.000 in every condition** including clean baselines (Phases 4–8). No result is evidence of S detection.
2. **Test F support = 0**; macro-F1 covers N/S/V/Q only.
3. **K = 5 clients** throughout; several negative results are arithmetic consequences of this.
4. **G8 is NOT PASSED**; R2 is not claimed.
5. **Phase 8 divergence = 51.7 % (75/145)** — the corrected figure.
6. Development (47–48) and confirmatory (49–53) and amended (54–55) results are **never pooled**.
7. The audit layer is **L1/L2**, not a distributed blockchain.
8. DP is **client-level**, not record- or patient-level.

---

## Gate summary table

| Gate | Status | Scope limit |
|---|---|---|
| G0–G3 | Passed | Split and manifests frozen |
| G4 | **Passed** | **With documented S-class defect** |
| G5 | Passed | K = 5; one partition draw |
| G6 | **Passed** | Client-level DP; approved σ grid not run; DP negative accepted |
| G7 | Passed | **L1 + L2 only; no consensus claim** |
| **G8** | **NOT PASSED** | 51.7 % of matrix unmeasurable |
| G8-amended (3B) | **Not passed** | Hypothesis refuted |
| G9, G10 | Not reached | — |
