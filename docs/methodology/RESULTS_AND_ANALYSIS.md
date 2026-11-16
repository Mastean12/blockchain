# Results and Analysis

Canonical entry point to the study's results. Detailed analysis lives in the phase documents; this
file indexes the headline numbers and the claims they do and do not support.

---

## Phase 4 — Centralized and local-only baselines

| Condition | Test accuracy | Test macro-F1 | S recall |
|---|---|---|---|
| Centralized CNN (5 seeds) | 0.8510 ± 0.0348 | 0.2990 ± 0.0600 | **0.000 in 5/5** |
| D1 class-weighted | 0.8142 ± 0.0550 | 0.3403 ± 0.0752 | 0.000 in 5/5 |
| D2 balanced-accuracy selection | 0.8251 ± 0.0335 | 0.3207 ± 0.0189 | 0.000 in 5/5 |

**G4 PASSED 16 November 2026 with documented defect.** The model never predicts S despite 1,483 test S windows. Cause established in
`PHASE_4_S_CLASS_FAILURE_INVESTIGATION.md`: validation S comprises 61 windows across 4 records, and
global average pooling discards the intraband shape separating S from N. Neither loss weighting nor
selection-metric change recovered it.

## Phase 5 — Federated learning

| Condition | Test accuracy | Test macro-F1 |
|---|---|---|
| F1 FedAvg IID-like | 0.7861 ± 0.0223 | 0.3040 ± 0.0146 |
| F2 FedAvg moderate α=0.5 | 0.8061 ± 0.0363 | 0.3079 ± 0.0299 |
| F3 FedAvg severe α=0.1 | **0.8523 ± 0.0380** | **0.3752 ± 0.0448** |
| F4 FedProx severe | 0.8213 ± 0.0440 | 0.3390 ± 0.0445 |

Details: `PHASE_5_RESULTS_AND_ANALYSIS.md`.

1. S recall 0.000 in all 20 federated runs — the Phase 4 limitation carries forward unchanged.
2. F3 scoring highest is a **split-specific artefact**, not evidence that non-IID helps.
   **Mechanism identified 16 Nov 2026 (ablation A2):** 54 % of the F3-over-F1 macro-F1 advantage
   (0.0388 of 0.0712) is attributable to sample-count aggregation weight dispersion — one client
   held 37.1 % of the model (weight ratio 4.26× vs 1.26× on F1). Replacing weighted with uniform
   aggregation restored macro-F1 to 0.3364. The residual 46 % is partition composition.
   See `PHASE_5_G5_DIAGNOSIS.md`. **G5 PASSED.**
3. At matched rounds FedAvg and FedProx are indistinguishable (val macro-F1 0.2662 vs 0.2669);
   the apparent F4 test gap is checkpoint-selection noise.
4. Validation macro-F1 selection is fragile at ≈0.28 across all conditions.

## Phase 6 — Privacy mechanisms

| Condition | Test accuracy | Test macro-F1 | V recall | HE error | ε |
|---|---|---|---|---|---|
| P0 plaintext | 0.8523 ± 0.0380 | **0.3752 ± 0.0448** | 0.970 | — | n/a |
| P1-ctl clip-only | 0.8358 | 0.3420 | 0.954 | — | n/a (no noise) |
| **P2 HE-only** | 0.8471 ± 0.0370 | **0.3681 ± 0.0482** | 0.969 | 1.38e-07 | n/a (no DP) |
| P3-a HE+DP σ=1.0 | 0.5672 ± 0.2638 | 0.1847 ± 0.0562 | 0.200 | 1.58e-07 | 57.302 |
| P3-b HE+DP σ=2.0 | 0.4876 ± 0.2412 | 0.1648 ± 0.0453 | 0.200 | 1.59e-07 | 22.020 |

Details: `PHASE_6_RESULTS_AND_ANALYSIS.md`; DP frontier: `PHASE_6_DP_FRONTIER_DIAGNOSTIC.md`.

**HE is functionally lossless** (0.3681 vs 0.3752) at 20.5× communication cost and ≈4 % round time.
**DP destroys** this classifier at every tested whole-model client-level configuration. P3's ε equals
the DP-only values, confirming HE adds confidentiality but no differential privacy.

### Claims this does **not** support

- That a useful DP operating point exists (none found in the explored region).
- That DP is unsuitable in general — only whole-model client-level DP with five clients was tested.
- That any Phase 6 result improves or worsens class S (0.000 in the unnoised baseline).
- Any clinical, deployment or compliance claim.

## Phases 7–10

No results. Not started.
