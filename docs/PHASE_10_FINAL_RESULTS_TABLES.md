# Phase 10 — Final Results Tables

**Date:** 18 November 2026
**Basis:** `archive/final_results.json`. Six configurations independently re-evaluated in Phase 10;
two are frozen recorded values only (evidence gap, §5).
**Gate context:** G0–G7 passed; **G8 NOT PASSED**; G9 passed.

---

## Table 1 — Authoritative final results (selected configurations)

Test split, frozen F3-independent evaluation, 5 seeds except where noted.

| ID | Configuration | n | Accuracy (mean ± SD) | Macro-F1 (mean ± SD) | S recall | V recall | Verified in P10 |
|---|---|---:|---|---|---|---|---|
| **S1** | Centralized CNN | 5 | 0.8423 ± 0.0383 | 0.2947 ± 0.0495 | 0.000 | 0.093 | **Yes** |
| **S2** | FedAvg IID-like (F1) | 5 | 0.7861 ± 0.0223 | 0.3040 ± 0.0146 | 0.000 | 0.970 | **No** — recorded only |
| **S3** | FedAvg moderate (F2) | 5 | 0.8061 ± 0.0363 | 0.3079 ± 0.0299 | 0.000 | 0.968 | **No** — recorded only |
| **S4** | FedAvg severe (F3) | 5 | **0.8523 ± 0.0380** | **0.3752 ± 0.0448** | 0.000 | 0.970 | **Yes** |
| **S5** | FedProx severe (F4) | 5 | 0.8213 ± 0.0440 | 0.3390 ± 0.0445 | 0.000 | 0.970 | **Yes** |
| **S6** | HE-only (P2) | 5 | 0.8471 ± 0.0370 | 0.3681 ± 0.0482 | 0.000 | 0.969 | **Yes** |
| **S7** | HE+DP σ=1.0 (P3-a) | 5 | 0.5672 ± 0.2638 | 0.1847 ± 0.0562 | 0.003 | 0.200 | **Yes** |
| **S8** | HE+DP σ=2.0 (P3-b) | 5 | 0.4876 ± 0.2412 | 0.1648 ± 0.0453 | 0.014 | 0.200 | **Yes** |

**S recall is 0.000 in every configuration.** This is not a rounding artefact; it is the documented
S-class defect established in Phase 4.

---

## Table 2 — Test-set class support (applies to every row above)

| Class | Support |
|---|---:|
| N | 13,099 |
| S | 1,483 |
| V | 461 |
| **F** | **0** |
| Q | 2 |

Test F is not estimable. Macro-F1 above covers **N/S/V/Q only** and is not five-class test macro-F1.
Test S support is 93.2 % record 232, so S recall is not generalisable.

---

## Table 3 — Reproducibility verification (Phase 10)

| Configuration | Recorded accuracy | Re-evaluated accuracy | Match |
|---|---:|---:|---|
| S1 | 0.8423 | 0.8423 | **Exact** |
| S4 | 0.8523 | 0.8523 | **Exact** |
| S5 | 0.8213 | 0.8213 | **Exact** |
| S6 | 0.8471 | 0.8471 | **Exact** |
| S7 | 0.5672 | 0.5672 | **Exact** |
| S8 | 0.4876 | 0.4876 | **Exact** |

**Six of six re-evaluated configurations reproduced their recorded values exactly** (to 1e-9).
This is the strongest reproducibility evidence in the project.

---

## Table 4 — G5 aggregation-weighting ablation (RQ2 mechanism)

| Configuration | Test macro-F1 | Δ from clean | Share of F1→F3 gap |
|---|---:|---:|---:|
| F1 IID-like (weighted) | 0.3040 | — | — |
| F3 weighted | 0.3752 | — | — |
| **F3 uniform weights** | **0.3364** | **−0.0388** | **54 %** |
| F1→F3 total gap | 0.0712 | | 100 % |
| Residual (partition composition) | 0.0324 | | 46 % |

Control reproduced frozen F3 **exactly on 5/5 seeds**. Dose–response confirmed on F2 (1.88× weight
ratio → +0.0079).

---

## Table 5 — Privacy parameters (RQ3)

| Configuration | ε at δ=1e-5, R=50 | HE approximation error | Communication |
|---|---:|---|---:|
| P2 HE-only | n/a (no DP) | **1.38e-07** | 20.5× (145 KB → 2.98 MB/client) |
| P3-a HE+DP σ=1.0 | **57.302** | 1.58e-07 | 20.5× |
| P3-b HE+DP σ=2.0 | **22.020** | 1.59e-07 | 20.5× |
| D-2 σ=0.01 (R=8) | **44,111.78** | n/a | n/a |
| D-2 σ=0.05 (R=8) | **1,871.78** | n/a | n/a |

**P3 reports exactly the DP-only ε**, confirming HE adds confidentiality and **not** differential
privacy.

**Warning on D-2 σ=0.05:** its accuracy (0.8707) is the majority-class rate. V recall is exactly
0.000 and macro-F1 (0.2327) is *below* σ=0.01. It must never be quoted as preserved utility.

---

## Table 6 — Audit cost (RQ4)

| Metric | B1 hash chain | B2 Ganache contract |
|---|---:|---:|
| Test accuracy / macro-F1 | 0.8728 / 0.3993 | 0.8728 / 0.3993 |
| Metrics vs baseline | **bit-identical** | **bit-identical** |
| Round-time overhead | **0.12 %** | **4.03 %** |
| Ledger entries (50 rounds) | 352 | 352 |
| Verification | valid | valid |
| Head hash | `ea4bc5ec…` | `ea4bc5ec…` (**identical**) |

Additional B2 measurements: 88,819 gas per client submission (n=150); 30.6 M gas per 50-round run;
≈28 ms p50 latency; 38.4 tx/s serial; ≈112 B on-chain per round.

**No fee is reported** — Ganache has no meaningful gas price and the specification forbids inventing
one.

---

## Table 7 — Phase 8 (RQ5): NOT a results table

**No Phase 8 number appears as an aggregation-performance result.** G8 did not pass.

| Quantity | Value |
|---|---|
| Confirmatory runs completed | 145 |
| Runs that diverged | **75 (51.7 %)** — corrected figure |
| Cells | 29 |
| Cells fully measurable | **14** |
| Cells unmeasurable | **15** |
| Medians only, valid cells | median resisted both attacks; **only rule to do so** |
| Detection: scaling | 1.00 |
| Detection: sign-flip | **0.00–0.12** (norm policy is blind) |
| Amended 3B (λ = 1.5, 2.5) | divergence 51.7 % at both — **λ-insensitive** |

Round-0 metrics are **not** reported: they are identical across rules by construction and carry no
information about aggregation performance.

---

## Table 8 — Gate summary

| Gate | Status | Scope |
|---|---|---|
| G0–G3 | Passed | Frozen split and manifests |
| G4 | **Passed** | **With documented S-class defect** |
| G5 | Passed | K = 5, one partition draw |
| G6 | **Passed** | Client-level DP; approved σ grid not run |
| G7 | Passed | **L1 + L2 only** |
| **G8** | **NOT PASSED** | 51.7 % of matrix unmeasurable |
| G8-amended (3B) | Not passed | Hypothesis refuted |
| G9 | Passed | Eligible component set |

---

## 5. Evidence gap (must be disclosed)

**S2 (F1) and S3 (F2) checkpoints do not exist locally.** They were produced on Colab and never
transferred; `experiments/logs/phase5/f1` and `/f2` are absent.

| Aspect | Detail |
|---|---|
| Consequence | Their numbers are **frozen recorded values**, not independently re-derived in Phase 10 |
| Validity | The recorded values remain valid as historical results |
| Remedy if required | Re-run F1 and F2 (5 seeds each, ≈2.5 h on the GTX 1650) and evaluate |

This does **not** invalidate any RQ2 conclusion, because the load-bearing RQ2 result is the **A2
ablation on F3**, whose checkpoints and control both verify exactly.
