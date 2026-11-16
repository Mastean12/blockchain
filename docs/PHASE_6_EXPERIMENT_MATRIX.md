# Phase 6 — Experiment Matrix

**Status:** STAGE A — **NOT APPROVED**
**Date:** 16 November 2026
**Purpose:** The complete, pre-registered condition list for Phase 6, with seeds, partition, budget
and the control that separates clipping from noise. Nothing may be added or removed after any DP
utility is observed.
**Authority:** `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` §15.3, §16.2, §22; `RESEARCH_PROTOCOL.md` §4.1 (P1–P3)

---

## 1. Governing constraints from the master specification

| Requirement | Source | How this matrix satisfies it |
|---|---|---|
| Compare plaintext, HE-only, DP-only, HE+DP | §16.2 | P0, P2, P1, P3 |
| Same model, partition, client updates, seeds where technically possible | §16.2 | All conditions share `compact_cnn_v1`, F3 partition, seeds 42–46 |
| Predeclared set of DP noise levels; do **not** choose ε after seeing utility | §15.3 | σ grid fixed here (§4); ε computed after, not targeted |
| Validation-selected checkpoints; test evaluated once | §15.3 | Unchanged Phase 4/5 selection rule |
| Measure ε/δ, all assumptions, utility, convergence, selected round, clipping statistics, runtime, communication | §15.3 | §6 metrics |
| Record encryption time, encrypted size, homomorphic time, decryption time, total round time, approximation error, utility | §16.2 | §6 metrics |
| At least five seeds recommended; report every individual seed | §12 | 5 seeds, all reported |

## 2. Design basis

- **Model:** `compact_cnn_v1`, 36,357 trainable parameters (frozen).
- **Partition:** **F3 severe non-IID** (`da8b96fa…`), the hardest approved condition. Using F3
  means any mechanism-induced degradation is most visible, and P0 is already measured.
- **Seeds:** 42–46 (frozen, matching Phases 4/5).
- **Rounds:** 50, 2 local epochs, all five clients, BatchNorm buffers sample-weighted, optimizer
  state reset — all frozen Phase 5 values, unchanged.
- **Selection:** validation macro-F1 over N/S/V/F, round 0 evaluated, earliest on tie.
- **Test:** evaluated once per seed after the selected round is fixed.

### 2.1 Why F3 only (and not F1)

Cost control, and F3 is the condition where DP's interaction with label skew is most informative.
F1/F2 runs are **out of scope for Phase 6 Stage B** (decision D9). Adding them later requires an
approved amendment, not a silent extension.

## 3. Conditions

| ID | Condition | Clipping | Noise | Encryption | Purpose |
|---|---|---|---|---|---|
| **P0** | Plain FedAvg (no privacy) | none | none | none | Reference. **Already measured**: 0.8523 ± 0.0380 acc, 0.3752 ± 0.0448 macro-F1 |
| **P1-ctl** | Clip-only control | `C` | **none** | none | **Separates clipping loss from noise loss** |
| **P1-a** | DP, low noise | `C` | σ = 0.5 | none | Weak guarantee end of curve |
| **P1-b** | DP, moderate noise | `C` | σ = 1.0 | none | Mid curve |
| **P1-c** | DP, high noise | `C` | σ = 2.0 | none | Strong end of curve |
| **P2** | HE-only | none | none | CKKS N=8192 | Encryption cost + approximation error |
| **P3-a** | HE+DP | `C` | σ = 1.0 | CKKS N=8192 | Combined, mid |
| **P3-b** | HE+DP | `C` | σ = 2.0 | CKKS N=8192 | Combined, strong |

**Total: 8 conditions × 5 seeds = 40 runs × 51 rounds ≈ 2,040 federated rounds.**
*(P0 is not re-run; its 5 seeds are reused from Phase 5. Runs to execute: **35**.)*

### 3.1 Why P1-ctl is mandatory

Without it, a utility drop under P1 could be caused by clipping (information destroyed before
any noise) or by noise (variance added after clipping). The master specification requires
identifying which factor explains the gap (§11 Stage 7; §15.3). P1-ctl holds everything equal to
P1 except noise.

### 3.2 What is deliberately NOT in the matrix

| Excluded | Reason |
|---|---|
| Secure-aggregation DP (sensitivity `2C p_max`) | Not implemented; threat model OUT-2 |
| Central DP (server-side noise) | Different mechanism and trust model; not the research question |
| Local DP (per-coordinate LDP) | Different, much weaker utility regime; not proposed |
| Adaptive clipping | Needs an extra noisy signal; future work |
| F1/F2 partitions | Budget (D9) |
| Any per-record or per-patient DP | Not defensible (§5.2 threat model) |
| HE with N=16384 as a full condition | Optional one-seed precision sensitivity check only |

## 4. Pre-registered parameters

### 4.1 Clipping constant `C`

**Not yet known.** Set by the Stage B calibration pass under a rule fixed **now**:

> **Rule 4.1.** From a no-noise pass on F3, collect `‖Δ_k,r‖₂` for all k, r, all five seeds. Set
> `C` = the **median** of the per-round, per-client norms across the rounds that the no-privacy
> baselines actually selected (i.e. rounds ∈ {0,1,2,3,24,44} as observed in P0). Round to **three
> significant figures upward**. Freeze `C` for all conditions. Same `C` for P1, P1-ctl, P3.

The rule is fixed before seeing any norm. `C` is reported with its full distribution
(`docs/PHASE_6_CALIBRATION_REPORT.md`) and re-approved before Stage C.

### 4.2 Noise multipliers

| Condition | σ | Rationale |
|---|---:|---|
| P1-a / (P3 has no a) | 0.5 | noise SD = 0.5C: mild |
| P1-b / P3-a | 1.0 | noise SD = C: canonical |
| P1-c / P3-b | 2.0 | noise SD = 2C: strong |

**ε is not targeted.** Expected order of magnitude at `δ = 1e-5`, `R = 50`, per-client-release view
(sensitivity `2C`, relative noise `σ`):

| σ | RDP at α≈8 | Approx. ε (δ=1e-5) | Interpretation |
|---:|---|---:|---|
| 0.5 | — | order 10–100 | very weak guarantee |
| 1.0 | — | order 3–30 | weak |
| 2.0 | — | order 1–10 | moderate |

These are **orders of magnitude, deliberately not precise**, because the exact value comes from the
accountant in Stage C and **must not be pre-committed to a nice number**. The point to register now:
**with `R = 50`, full participation and no amplification, client-level ε will be large.** That is an
expected finding, not a defect.

### 4.3 Accounting view

Headline `ε` uses **view B (per-client transmission, sensitivity `2C`)** — see
`PHASE_6_PRIVACY_MATHEMATICS.md` §5.2. View A (`2C p_max`) is reported as the bound achievable only
with secure aggregation. View C (collusion) is discussed as a limitation.

### 4.4 δ

`δ = 1e-5`, justified as ≪ `1/N = 1.4e-5`. Decision D3′ offers a stricter alternative.

## 5. Controls protecting validity

| Control | Guarantee |
|---|---|
| Frozen hashes re-verified at load | split `bbcfa25c…`, client `71dbcac3…`, F3 `da8b96fa…` |
| Same seeds, same partition, same model across all conditions | Matched comparison |
| Test evaluated once per seed | No test-driven tuning |
| ε computed after the fact | No ε shopping |
| `C` fixed before DP utility seen | No clipping shopping |
| P1-ctl | Isolates clipping vs noise |
| Toy accountant test | Blocks invalid ε |
| CKKS round-trip + aggregate agreement | Blocks silently wrong HE |
| BatchNorm disclosure | Prevents over-claiming DP coverage |
| Every run writes config, environment, hashes, timings | Reproducibility |

## 6. Metrics per run

### 6.1 Predictive utility (identical code to Phases 4/5)
Accuracy; macro and weighted P/R/F1; per-class P/R/F1/support; confusion matrix (N,S,V,F,Q);
validation selection round; **S recall reported explicitly**. Per-seed values plus mean ± SD.

### 6.2 Privacy
Privacy unit; adjacency; `C`; sensitivity `S = 2C`; σ; ε at δ=1e-5; accountant name/version;
`R`; composition statement; accounting view; **unprotected components** (448 BN buffers); PRNG mode.

### 6.3 Computation
Client training; clip; noise generation; encryption; homomorphic aggregation; decryption; total
round; total run; peak host RAM; peak VRAM. Each as absolute and as a **multiple of P0**.

### 6.4 Communication
Plaintext update bytes (36,357 × 4 = 145,428 B); ciphertext bytes (9 × serialized size); expansion
factor; bytes per round and total; HE-induced delta vs P0/P1.

### 6.5 Convergence
Round-level train loss, validation loss, validation macro-F1, selected round; interrupted/failed
rounds; resume behaviour.

### 6.6 Calibration (Stage B only)
`‖Δ_k,r‖₂` distribution: per-client, per-round, median, mean, SD, p50/p90/p99/max; count of
clipped updates at candidate `C`; sensitivity recomputation.

## 7. Budget and environment

| Condition | Runs | Est. s/run (local GTX 1650) | Est. total |
|---|---:|---:|---:|
| P1-ctl | 5 | ≈460 | ≈0.6 h |
| P1-a/b/c | 15 | ≈470 | ≈2.0 h |
| P2 | 5 | ≈700–1,600 (HE-bound, CPU) | ≈1.0–2.2 h |
| P3-a/b | 10 | ≈1,200–2,100 | ≈3.3–5.8 h |
| Calibration | 1 pass | ≈500 | ≈0.2 h |
| **Total** | **36** | | **≈7–11 h** |

Estimates assume HE overhead of 50–300 % over the 453 s baseline and are **estimates pending
measurement of a single HE round**. GPU is used for training only; HE and accounting are CPU.

Environment record per run: OS, Python, torch, CUDA, GPU, Opacus, TenSEAL, SEAL version, plus
hashes of config and manifests.

## 8. Execution order (pre-registered)

1. Calibration pass (Stage B) → `C` → approval.
2. **P1-ctl** (5 seeds) — validates the DP code path without noise.
3. **P1-b** (σ=1.0, 5 seeds) — the central DP cell; review before proceeding.
4. **P1-a**, **P1-c** — complete the curve.
5. **P2** (5 seeds) — HE correctness and cost.
6. **P3-a**, **P3-b** — combined, only after P1 and P2 both validate.
7. Analysis.

Steps 4–6 must not begin until the previous step's artefacts are inspected. If P2 shows
unacceptable approximation error, P3 is postponed and the parameter set is revised **with a
recorded deviation**.

## 9. Stop conditions

Execution halts and reports rather than continues if:

- the toy accountant test fails;
- CKKS round-trip or aggregate agreement fails;
- `rel_err ≥ 1e-5` at the approved parameters;
- a DP run produces non-finite loss;
- any frozen hash mismatch;
- any run would overwrite existing output.

## 10. Decisions carried in from Stage A

| # | Decision | Status |
|---|---|---|
| D1′ | Fixed frozen weights `p_k`; per-client-vector clipping; sensitivity `2C` (view B) headline | Pending |
| D2 | `C` by Rule 4.1 (median of selected-round norms), fixed before DP utility | Pending |
| D3 | σ ∈ {0.5, 1.0, 2.0}; δ = 1e-5; R = 50 | Pending |
| D3′ | Alternative stricter `δ = 1.4e-6` | Pending |
| D4 | Opacus RDP accountant, sequential composition, **no amplification** | Pending |
| D4′ | Report ε under per-client view (B) as headline, not aggregate view (A) | Pending |
| D5 | BN buffers excluded from DP/HE; leak disclosed | Pending |
| D6 | CKKS N=8192, `[60,40,40,60]`, scale 2^40 | Pending |
| D7 | `rel_err < 1e-5` acceptance | Pending |
| D8 | Conditions P0, P1-ctl, P1-a/b/c, P2, P3-a/b | Pending |
| D9 | F3 only | Pending |
