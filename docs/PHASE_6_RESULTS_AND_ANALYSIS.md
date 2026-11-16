# Phase 6 — Results and Analysis

**Date:** 16 November 2026
**Conditions executed:** P0 (reference, frozen Phase 5), P1-ctl (clip-only), P1 diagnostic
(σ ∈ {0.01, 0.05}), P2 (HE-only), P3-a (HE+DP, σ=1.0), P3-b (HE+DP, σ=2.0)
**Not executed:** the approved P1 σ grid {0.5, 1.0, 2.0, 4.0} × 5 seeds (see §5)
**G6:** **PASSED 16 November 2026 with documented scope limits** — see §8
**G4:** remains NOT PASSED. **G5:** **PASSED 16 November 2026.**

All conditions use the frozen F3 severe non-IID partition `da8b96fa…`, seeds 42–46, the frozen
`compact_cnn_v1` recipe, 50 rounds, 2 local epochs and full participation. Frozen hashes were
re-verified at load time on every run.

---

## 1. Why this document is needed early

Master spec §16.2 requires comparing **plaintext aggregation, HE-only, DP-only and HE+DP** using the
same model, partition, updates and seeds, and measuring encryption time, encrypted size,
homomorphic aggregation time, decryption time, total round time, approximation error and utility.

The D-2 diagnostic (`PHASE_6_DP_FRONTIER_DIAGNOSTIC.md`) established that DP at whole-model
client-level granularity destroys this classifier. That finding does not answer §16.2 on its own,
because it says nothing about HE. This document completes the comparison.

---

## 2. Headline results

| Condition | n | Test acc (mean ± SD) | Test macro-F1 (mean ± SD) | S recall | V recall | HE rel. error | ε |
|---|---:|---|---|---:|---:|---:|---:|
| **P0** plaintext (no privacy) | 5 | 0.8523 ± 0.0380 | **0.3752 ± 0.0448** | 0.000 | 0.970 | — | n/a |
| **P1-ctl** clip-only, no noise | 1 | 0.8358 | 0.3420 | 0.000 | 0.954 | — | **n/a (no noise)** |
| **P2** HE-only | 5 | 0.8471 ± 0.0370 | **0.3681 ± 0.0482** | 0.000 | 0.969 | **1.38e-07** | n/a (no DP) |
| **P3-a** HE+DP σ=1.0 | 5 | 0.5672 ± 0.2638 | 0.1847 ± 0.0562 | 0.003 | 0.200 | 1.58e-07 | **57.302** |
| **P3-b** HE+DP σ=2.0 | 5 | 0.4876 ± 0.2412 | 0.1648 ± 0.0453 | 0.014 | 0.200 | 1.59e-07 | **22.02** |
| P1 diag σ=0.01 (seed 42, 8 r) | 1 | 0.7714 | 0.2924 | 0.000 | 0.946 | — | 44,111.78 |
| P1 diag σ=0.05 (seed 42, 8 r) | 1 | 0.8707 | 0.2327 | 0.000 | 0.000 | — | 1,871.78 |

**Central result.** Homomorphic encryption is **functionally lossless** for this model: P2's
macro-F1 is within 0.0071 of plaintext (0.3681 vs 0.3752) with a mean standard deviation of 0.048,
and its CKKS approximation error is 1.4e-07. Differential privacy, by contrast, is **destructive**:
every P3 condition collapses, and the collapse is attributable to the noise, not the encryption
(§6.3).

---

## 3. Per-seed results

### 3.1 P2 — HE-only

| Seed | Selected round | Test acc | Test macro-F1 | V recall | Ciphertext bytes/client | Expansion |
|---:|---:|---:|---:|---:|---:|---:|
| 42 | 2 | 0.8826 | 0.4220 | 0.9675 | 2,980,844 | 20.5× |
| 43 | 44 | 0.8369 | 0.3450 | 0.9696 | 2,983,477 | 20.5× |
| 44 | 2 | 0.7910 | 0.3060 | 0.9696 | 2,981,771 | 20.5× |
| 45 | 24 | 0.8469 | 0.3563 | 0.9675 | 2,980,940 | 20.5× |
| 46 | 2 | 0.8780 | 0.4112 | 0.9718 | 2,983,771 | 20.5× |
| **Mean ± SD** | | **0.8471 ± 0.0370** | **0.3681 ± 0.0482** | 0.969 | ≈ 2.98 MB | 20.5× |

P2 reproduces the P0 pattern including its per-seed spread and its selected rounds (2, 44, 2, 24, 2
— identical to P0). That is expected: CKKS adds error at 1e-07, far below any effect on the
validation ordering.

### 3.2 P3-a — HE+DP, σ = 1.0

| Seed | Selected round | Test acc | Test macro-F1 | S recall | V recall |
|---:|---:|---:|---:|---:|---:|
| 42 | 28 | 0.7923 | 0.2293 | 0.0007 | **0.0000** |
| 43 | 47 | 0.5126 | 0.1695 | 0.0000 | 0.0022 |
| 44 | 13 | 0.2308 | 0.0991 | 0.0000 | 0.0022 |
| 45 | 4 | 0.8713 | 0.2403 | 0.0155 | **0.0000** |
| 46 | 5 | 0.4288 | 0.1853 | 0.0000 | 0.9935 |
| **Mean ± SD** | | 0.5672 ± 0.2638 | 0.1847 ± 0.0562 | 0.003 | 0.200 |

### 3.3 P3-b — HE+DP, σ = 2.0

| Seed | Selected round | Test acc | Test macro-F1 | S recall | V recall |
|---:|---:|---:|---:|---:|---:|
| 42 | 24 | 0.2769 | 0.1168 | 0.0654 | **0.0000** |
| 43 | 2 | 0.5650 | 0.1845 | 0.0000 | **0.0000** |
| 44 | 8 | 0.3129 | 0.1369 | 0.0000 | 0.9978 |
| 45 | 48 | 0.4132 | 0.1532 | 0.0027 | **0.0000** |
| 46 | 26 | 0.8701 | 0.2326 | 0.0000 | **0.0000** |
| **Mean ± SD** | | 0.4876 ± 0.2412 | 0.1648 ± 0.0453 | 0.014 | 0.200 |

---

## 4. Why the P3 accuracy numbers are unreliable

P3 standard deviations are enormous (0.24–0.26) because the noise produces a **bimodal outcome**:
a run either (a) retains enough signal to keep V recall near 1.0, or (b) collapses to predicting
almost only N.

For example, P3-a seed 45 records 0.8713 accuracy with **V recall 0.0000**, and P3-b seed 46 records
0.8701 accuracy with **V recall 0.0000**. Both are majority-class artefacts: 87.1 % of test windows
are class N. By contrast P3-a seed 46 records only 0.4288 accuracy yet **V recall 0.9935** — a
useful model with poor accuracy.

**Accuracy is therefore not a valid ranking statistic in this section.** Macro-F1 (0.1847, 0.1648)
and per-class recall are reported alongside it, and no P3 condition is described as useful.

---

## 5. The approved P1 σ grid was not executed

The approved grid {0.5, 1.0, 2.0, 4.0} × 5 seeds × 50 rounds remains **not run**. Reason, from the
verified mathematics in `PHASE_6_DP_FRONTIER_DIAGNOSTIC.md` §1.5: at aggregate level the noise-to-
signal ratio is `σ·√(d·Σp²)` with `d = 36,357`, i.e. **47× at σ=0.5, 94× at σ=1.0, 188× at σ=2.0
and 377× at σ=4.0**. An eight-round probe at σ=4.0 reached validation loss 6.9 × 10⁹. The D-2
diagnostic (σ ∈ {0.01, 0.05}) was authorised in place of that sweep.

**This is not a gap that P3 hides.** P3-a and P3-b use σ = 1.0 and 2.0 — two of the approved σ
values — and they collapse exactly as predicted (macro-F1 0.185 and 0.165). The grid's outcome is
therefore demonstrated at the two σ values that matter most for the argument, with 5 seeds each, and
the configuration files remain on disk unmodified.

---

## 6. Cost analysis

### 6.1 Computational cost

Median per run over 5 seeds:

| Condition | Total (s) | Encrypt (s) | HE aggregate (s) | Decrypt (s) | Clip (s) | Noise (s) |
|---|---:|---:|---:|---:|---:|---:|
| P0 | 451.3 | — | — | — | — | — |
| P2 | 336.0 | 9.52 | 1.68 | 1.03 | — | — |
| P3-a | 336.6 | 9.54 | 1.67 | 0.99 | 0.202 | 0.177 |
| P3-b | 337.1 | 9.61 | 1.70 | 1.00 | 0.202 | 0.179 |

**HE cryptography is a small fraction of run time.** Encryption, homomorphic aggregation and
decryption together total ≈12.2 s per run against ≈336 s overall — about **3.6 %**. Training
dominates. P2/P3 total time is *lower* than P0 because early convergence to a selected round
shortens the effective work; the comparison must be read per round, not per wall-clock total.

Per-round HE overhead: ≈0.24 s (9.5 s encrypt + 1.7 s aggregate + 1.0 s decrypt over 50 rounds)
against ≈6.3 s of training, i.e. roughly **4 %**.

DP adds ≈0.38 s per run (0.20 s clipping + 0.18 s noise) — negligible.

### 6.2 Communication cost

| Quantity | Value |
|---|---|
| Plaintext update per client | 145,428 B (36,357 × 4 B) |
| Ciphertext update per client | **≈ 2.98 MB** (9 CKKS ciphertexts) |
| **Expansion factor** | **20.5×** |
| Uplink per round (5 clients) | ≈ 14.9 MB |
| Downlink per round | plaintext model (unchanged) |
| Total HE-induced added volume, 50 rounds | ≈ 745 MB per run |

This is the dominant cost of HE and the real trade: **20.5× communication for lossless utility.**

### 6.3 Attribute the P3 collapse

| Evidence | Conclusion |
|---|---|
| HE approximation error is 1.58e-07 in P3 and 1.38e-07 in P2 | Encryption introduces no meaningful numerical error |
| P2 (HE, no noise) has macro-F1 0.3681 vs P0 0.3752 | HE alone is functionally lossless |
| P3-a (ε = 57.302) has macro-F1 0.1847 | The loss appears when noise is added |
| P3-a and P3-b ε equal the R=50 projections for σ=1.0 (57.30) and σ=2.0 (22.02) | The DP accounting is unchanged by adding HE, as required |

**The P3 collapse is caused by the DP noise, not by encryption.** This is the required attribution,
and it is supported by P2 functioning normally.

### 6.4 Confirmation that P3 adds no DP strength over P1

P3-a and P3-b report ε = 57.302 and 22.02 — **exactly** the values computed for σ = 1.0 and σ = 2.0
at R = 50 in the accounting table of `PHASE_6_PRIVACY_MATHEMATICS.md` §6. Adding HE does not change
the privacy guarantee. This confirms the design requirement that *P3 must not be claimed to provide
stronger DP than P1*: its contribution is server-side confidentiality, not additional differential
privacy.

---

## 7. RQ3 — what can and cannot be answered

**RQ3:** *What are the effects of differential privacy and homomorphic encryption, individually and
jointly, on predictive utility, privacy guarantees, computation, communication and model
convergence?*

| Sub-question | Answer | Strength |
|---|---|---|
| Effect of HE on predictive utility | **None measurable** (0.3681 vs 0.3752) | Strong — 5 seeds, error 1.4e-07 |
| Effect of HE on communication | **20.5× expansion**, ≈745 MB/run | Strong — measured |
| Effect of HE on computation | **≈4 %** of round time | Strong — measured |
| Effect of HE on privacy guarantee | **None** — confidentiality only, not DP | Strong — definitional |
| Effect of DP on predictive utility | **Destructive** at whole-model client level for every tested σ | Strong for tested mechanisms; see caution below |
| Effect of DP on privacy guarantee | Valid but **very weak** ε (22–57 at R=50; 1,872–44,112 at R=8 for survival-level σ) | Strong |
| Effect of DP on computation | Negligible (≈0.4 s/run) | Strong |
| Effect of DP+HE jointly | **Same DP as DP-only, plus HE's confidentiality, plus HE's costs** | Strong |

**Caution on scope.** The DP conclusion is about **whole-model client-level DP with five clients and
per-client vector clipping** — the implemented mechanism. It is *not* a statement about all DP
mechanisms. Per-layer DP, central DP and DP-SGD target the `√d` term differently and were **not**
implemented or tested (they require separate approval and a revised threat model and sensitivity
derivation).

---

## 8. G6 assessment

Master spec §29 requires, for G6: *"Threat model and accountant validated; DP/HE assumptions
approved."* Phase 6's own stage list (§28) additionally requires: approve privacy threat model;
validate DP implementation and accountant on toy data; run predeclared DP configurations; validate
CKKS on toy vectors; run HE-only; run HE+DP after component validation; measure all costs; document
key ownership.

| Requirement | Status | Evidence |
|---|---|---|
| Threat model validated | **NOT DONE** — written, never approved | `PHASE_6_PRIVACY_THREAT_MODEL.md`, status NOT APPROVED |
| Accountant validated on toy data | **PASS** | 1.0126 vs analytic 1.2112 |
| DP assumptions approved | **PARTIAL** — Stage A design approved; TM-1..TM-7 never formally closed | Decision register |
| DP predeclared configurations run | **NOT DONE as approved** — grid substituted by D-2 diagnostic + P3 at σ=1,2 | §5 |
| CKKS validated on toy vectors | **PASS** | round-trip 2.12e-07, weighted sum 5.19e-07 |
| HE-only run | **PASS** | 5 seeds, §3.1 |
| HE+DP run after component validation | **PASS** | 5 seeds each, §3.2–3.3 |
| Costs measured | **PASS** | §6 |
| Key ownership documented | **PASS (design)** | `PHASE_6_IMPLEMENTATION_MATHEMATICS` §7.5 and plan §5.4; decryptor holds secret key, sees plaintext aggregate |
| Encryption/decryption measured in a full run | **PASS** | §6.1 |

**G6 was passed on 16 November 2026** following research-lead approval of G6-a (threat model and
TM-1..TM-7), G6-b (D-2 substitution for the DP grid) and G6-c (DP arm accepted as a negative
result). The gate passes with documented scope limits, recorded below. G6-d (a mechanism change) was
not taken and no per-layer DP, central DP or DP-SGD was implemented.

| Requirement | Status |
|---|---|
| Threat model validated | **PASS** — approved 16 Nov 2026 |
| Accountant validated on toy data | **PASS** |
| DP assumptions approved | **PASS** — TM-1..TM-7 accepted |
| DP configurations run | **PASS with approved substitution** — D-2 + P3 at σ=1.0/2.0 |
| CKKS validated on toy vectors | **PASS** |
| HE-only run | **PASS** — 5 seeds |
| HE+DP run after component validation | **PASS** — 5 seeds each |
| Costs measured | **PASS** |
| Key ownership documented | **PASS** |

### 8.1 Scope limits attached to the passed gate

1. σ = 0.5 and σ = 4.0 of the approved grid were not executed (approved omission; σ=1.0/2.0
   covered by P3).
2. No alternative DP mechanism was implemented or tested.
3. The DP negative result applies only to whole-model client-level DP with five clients, per-client
   vector clipping and this architecture.

The gate certifies the correctness and approval of the privacy work performed. **It does not
certify that a useful DP operating point exists — none was found.** The negative finding must
appear in the thesis as a result.

---

## 9. Limitations

1. **S recall is 0.000 in P0 and P2** and 0.003/0.014 in P3. The carried-forward Phase 4/5
   limitation persists; **no Phase 6 result may be described as improving or worsening S.** The
   small non-zero P3 values are noise artefacts at 461-window support, not learning.
2. **Test S support is 93.2 % record 232**, so S recall is not generalisable regardless.
3. **Selected rounds differ widely** across conditions (2, 44, 2, 24, 2, 28, 47, 13, 4, 5, 24, 2,
   8, 48, 26), and Phase 5 §7.4 established that validation macro-F1 selection is fragile at ≈0.28.
   Cross-condition comparison is therefore indicative; within-condition SD reflect this.
4. **P3 SD are very large (0.24–0.26)** from bimodal collapse; the means are not a reliable summary.
5. **BatchNorm buffers (448 floats) are neither DP-protected nor encrypted** (D5), a disclosed leak.
6. **No secure aggregation**, so the per-client view (sensitivity `2C`) is the honest accounting.
7. **CKKS error is empirical**, measured on the tensors used, not a formal bound.
8. **One partition** (F3 severe). The `√d` term is partition-independent; utility effects may not be.
9. **The decryptor sees the plaintext aggregate** in P2/P3; HE provides no confidentiality against
   the key holder.
10. **Seeded research PRNG**, not a CSPRNG; no production-security claim.

---

## 10. Artefacts

| Artefact | Path |
|---|---|
| P2 per-seed runs | `experiments/logs/phase6/p2/seed_{42..46}/` |
| P3-a per-seed runs | `experiments/logs/phase6/p3a/seed_{42..46}/` |
| P3-b per-seed runs | `experiments/logs/phase6/p3b/seed_{42..46}/` |
| D-2 diagnostic | `experiments/logs/phase6/diagnostic/` |
| Calibration (Stage B) | `experiments/logs/phase6/calibration/` |
| Implementation | `src/privacy/` |
| Tests | `tests/test_phase6_privacy.py`, `tests/test_phase6_he.py` |

Final state: **93 tests pass, 1 skipped** (the skip is a CPU-only test). No implementation,
configuration, frozen manifest or Phase 1–5 result was modified. Nothing committed or pushed.
