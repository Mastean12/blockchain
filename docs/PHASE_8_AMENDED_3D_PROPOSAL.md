# Phase 8 — Amended Proposal 3D: Server Step-Size Damping

**Status:** DEVELOPMENT COMPLETE — **criterion NOT met; 3D accepted as a partial improvement only.**
**Gate:** this does not change G8. **G8 remains NOT PASSED.**
**Date:** 18 November 2026

---

## 0. Why this proposal exists

The user asked for G8 to pass. Route analysis:

| Route | Permissible? |
|---|---|
| Change thresholds until results pass | **No** — prohibited by the project's own integrity rules |
| Keep trying interventions until one succeeds | **No** — G8 was frozen; 3B was the sanctioned attempt and was refuted |
| Run a **new, pre-registered** intervention with an evidence-based mechanism | **Yes** — this document |

## 1. The evidence that motivated 3D

The failure analysis established divergence is **rule-dependent, not attack-strength-dependent**
(λ = 1.5, 2.5, 5.0 all gave 51.7 %). That rules out 3B and weakens 3A (norm clipping bounds a
quantity that is not the cause).

A stronger signal was found in the per-round logs:

| Group | norm(round 4) / norm(round 1) |
|---|---|
| **Survived** (n = 70 runs) | **0.26 – 0.40** — always decays |
| **Diverged** (n = 32 runs) | 0.32 – 10.84, **mean 1.73** — usually grows |

Example trajectories (seed 49):

| Round | median (survives) | fedavg (diverges) |
|---:|---:|---:|
| 1 | 13.27 | 13.27 |
| 2 | 6.13 | 7.87 |
| 3 | 5.47 | 6.33 |
| 5 | 4.06 | 5.18 |
| 7 | **3.99** (decaying) | **6.32** (reversing → death) |

**Mechanism:** a positive-feedback loop. Large round-1 updates lead to a poorer optimum, which
produces larger round-2 updates, until BatchNorm statistics or the loss overflow float32. Rules that
dampen the aggregate (median) break the loop; FedAvg does not.

## 2. The intervention

A **server step size** applied after aggregation:

```
w_global ← w_global + step_size · aggregate(Δ_1 … Δ_K)
```

| Parameter | Value |
|---|---|
| `step_size` tested | **0.25** and 0.5 |
| Everything else | **unchanged**: λ = 5.0, all rules, K = 5, 51 rounds, 2 local epochs, frozen thresholds |

Implementation: `apply_server_step()` in `src/aggregation/rules.py`. `step_size = 1.0` is the identity,
so every pre-existing configuration is bit-identically unaffected (verified).

### 2.1 What 3D does not do

- It does not change any aggregation **rule**; it changes how far the model moves each round.
- It does not alter attack strength, thresholds, seeds, partitions or evaluation.
- It makes **no robustness claim**. It is a stability intervention.

## 3. Pre-registered acceptance criterion

Fixed **before** the development run completed:

> **3D is accepted if, on amended confirmatory seeds 56–60, at least 27 of 29 cells (≥93 %) are
> measurable** — up from 14 of 29 (48 %) in the original confirmatory run.

Secondary (reported, not gating): divergence rate; attack success per frozen 0.05 threshold; honest
FPR ≤ 0.10; clean utility retention ≥ 0.90.

## 4. Results — development seeds 54–55 (116 runs, 0 execution failures)

### 4.1 Divergence by step size

| Step | Runs diverged | Divergence rate | Cells measurable |
|---|---:|---:|---:|
| baseline 1.0 (seeds 49-53) | 75 / 145 | 51.7 % | 14 / 29 (48 %) |
| 0.5 | 29 / 58 | 50.0 % | 14 / 29 (48 %) |
| **0.25** | **21 / 58** | **36.2 %** | **18 / 29 (62 %)** |
| **pre-registered criterion** | — | — | **>= 27 / 29 (93 %)** |

**Verdict: criterion NOT met.** 18 of 29 cells is a real improvement over 14 of 29, but far short of 27.

### 4.2 Per-rule effect at step 0.25

| Rule | Baseline (1.0) | Step 0.5 | Step 0.25 |
|---|---|---|---|
| FedAvg | 12 / 14 | 12 / 14 | **8 / 14** |
| Multi-Krum | 6 / 8 | 6 / 8 | **4 / 8** |
| Trimmed mean | 6 / 14 | 5 / 14 | **3 / 14** |
| **Krum** | 6 / 8 | 6 / 8 | **6 / 8 (unchanged)** |
| Median | 0 / 14 | 0 / 14 | 0 / 14 |

### 4.3 Interpretation

**Step damping works, but only where the failure is amplification.** FedAvg, Multi-Krum and trimmed
mean all improve at step 0.25 and not at 0.5 — consistent with the mechanism: only aggressive damping
breaks the round-to-round feedback described in section 1.

**Krum is completely unaffected**, and this is the decisive structural finding. Krum selects a single
client's update. When the selected client is the adversary, scaling that update by 0.25 still applies
the adversary's direction — damping reduces magnitude, not wrongness. **A step size cannot repair a
selection failure.**

### 4.4 What 3D establishes

| Finding | Support |
|---|---|
| Round-to-round amplification is a real divergence mechanism | **Strong** — step 0.25 reduces divergence 51.7 % -> 36.2 % |
| Damping must be aggressive (0.25, not 0.5) | **Strong** — 0.5 is indistinguishable from baseline |
| Damping cannot fix selection-based rules | **Strong** — Krum unchanged at every step size |
| No single scalar intervention fixes G8 | **Strong** — the best cell count is 18 / 29 |

**3D does not make G8 pass, and the amended confirmatory phase was not run.** Spending ~10 h on seeds
56-60 would reproduce a development result that already falls well short of the criterion.

## 6. Integrity statement

- G8 unchanged and **NOT PASSED**.
- No frozen threshold, seed set, partition or historical result modified.
- `step_size` defaults to 1.0; all previous configurations are unaffected (verified).
- Pre-registered criterion fixed before results were complete.
- No robustness claim is made or implied.
