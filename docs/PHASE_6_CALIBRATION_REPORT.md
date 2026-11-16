# Phase 6 — Calibration Report

**Status:** STAGE B COMPLETE — **AWAITING RESEARCH-LEAD APPROVAL**
**Date:** 16 November 2026
**Purpose:** Determine the L2 clipping constant `C` and the achievable privacy budget under the
pre-registered rule of `PHASE_6_EXPERIMENT_MATRIX.md` §4.1.
**Privacy status of this pass:** **THE CALIBRATION PASS PROVIDES NO PRIVACY PROTECTION.** It ran
with no clipping and no noise. It is a measurement exercise only.

---

## 0. Executive summary

| Item | Result |
|---|---|
| Seeds run | 42–46 (5/5 complete) |
| Observations | 1,250 client-round update norms |
| Equivalence to Phase 5 | **Verified** — seed-42 validation curve reproduces Phase 5 exactly |
| `C` under Rule 4.1 as written | **1.58** |
| Consequence of `C = 1.58` | Clips **37.2 %** of all updates; **88 %** of updates in rounds 1–5 |
| **Recommended `C` (amendment)** | **3.44** (global p99) — clips 0.9 % |
| ε at σ=1.0, R=50, δ=1e-5 | **57.30** |
| ε at σ=2.0, R=50, δ=1e-5 | **22.02** |
| Blocking issues | **Two** (§6): Rule 4.1 produces a destructive `C`; the σ grid produces very weak ε |

**Two decisions are required before Stage C. Neither can be resolved by me without fabricating a
design choice.**

---

## 1. Environment and dependency verification (Stage B step 1)

| Component | Version / value |
|---|---|
| Python | 3.12.10 |
| Platform | Windows-11-10.0.26200-SP0 |
| torch | 2.14.1+cu126 (unchanged) |
| CUDA | 12.6, available |
| GPU | NVIDIA GeForce GTX 1650 (4 GB) |
| Opacus | **1.6.0** (newly installed, pinned) |
| TenSEAL | **0.3.18** (newly installed, pinned, cp312 win_amd64) |
| opt-einsum | 3.4.0 (Opacus transitive dependency) |

Installed into `.venv` only. No major dependency was upgraded; torch was not touched.

### 1.1 Accountant validity gate — PASSED

Toy test, `d = 1`, `R = 1`, sensitivity `S`, noise `σS`:

| Quantity | Value |
|---|---|
| Opacus RDP accountant ε (δ=1e-5) | 1.0126 |
| Analytic Gaussian-mechanism bound | 1.2112 |

The accountant is **tighter** than the classical bound, as expected for RDP→DP conversion. The
gate passes; **no ε may be reported without this check having passed**, and it has.

### 1.2 CKKS validity gate — PASSED

TenSEAL, N=8192, `[60,40,40,60]`, scale 2^40:

| Test | Result |
|---|---|
| Round-trip relative L2 error (4,096 slots) | **2.12e-07** |
| Homomorphic weighted sum of 5 clients, relative L2 error | **5.19e-07** |
| D7 acceptance threshold | < 1e-5 → **PASS with ~19× margin** |

CKKS is fit for purpose at these parameters. This satisfies Stage C prerequisite D7.

---

## 2. Calibration design and equivalence check

The calibration module (`src/privacy/calibration.py`) reuses the frozen Phase 5 training procedure
unchanged (same model, optimizer, loss, loader, epochs, seeds, partition) and only *observes* the
update `Δ_k = w_local,k − w_global` after local training. Norms are taken over the **36,357
trainable parameters only**, matching the DP vector (decision D5; BatchNorm buffers excluded).

**Equivalence proof (empirical).** Seed 42, rounds 0–5, calibration pass vs frozen Phase 5 F3:

| Round | Phase 5 val macro-F1 | Calibration val macro-F1 |
|---:|---:|---:|
| 0 | 0.001886 | 0.0019 |
| 1 | 0.248779 | 0.2488 |
| 2 | 0.284643 | 0.2846 |
| 3 | 0.275862 | 0.2759 |
| 4 | 0.266448 | 0.2664 |
| 5 | 0.274937 | 0.2749 |

**Identical.** This confirms the claim in `PHASE_6_PRIVACY_MATHEMATICS.md` §4.2 that replacing
realised sample counts with frozen public weights is **arithmetic-preserving**, and that the
calibration measures the same update the real experiments will use.

Full pass: 5 seeds × 50 rounds × 5 clients = **1,250 norms**; ≈343 s per seed on the GTX 1650.

---

## 3. Update-norm distribution

### 3.1 All observations (n = 1,250)

| Statistic | ‖Δ‖₂ |
|---|---:|
| min | 1.1266 |
| median (p50) | 1.5491 |
| mean | 1.6083 |
| SD | 0.3697 |
| p90 | 1.8408 |
| p95 | 2.2226 |
| p99 | **3.3471** |
| max | 4.3514 |

### 3.2 Norms at the rounds P0 actually selected (n = 75)

Selection rounds (§ from Phase 5): seed 42→2, 43→44, 44→2, 45→24, 46→2.

| Statistic | ‖Δ‖₂ |
|---|---:|
| min | 1.2403 |
| **median** | **1.5779** |
| mean | 1.8984 |
| SD | 0.6573 |
| p90 | 3.0414 |
| p99 | 3.3479 |
| max | 3.3722 |

### 3.3 Norms are strongly round-dependent

| Round index | Median ‖Δ‖ | % above `C = 1.58` |
|---:|---:|---:|
| 1 | 3.34 | **100.0 %** |
| 2 | 2.89 | **100.0 %** |
| 3 | 2.30 | 80.0 % |
| 5 | 1.87 | 80.0 % |
| 10 | 1.64 | 68.0 % |
| 20 | 1.56 | 44.0 % |
| 30 | 1.52 | 12.0 % |
| 44 | 1.51 | 12.0 % |
| 50 | 1.51 | 0.0 % |

Updates are large early (the model is converging fast from its random-like initialisation) and
settle to ≈1.5. **Rounds 1–5 carry 88 % clipped mass at `C = 1.58`; rounds 44–50 only 8 %.**

### 3.4 Per-client distribution

| Client | Median | p95 | Max |
|---|---:|---:|---:|
| client_01 | 1.570 | 2.599 | 4.351 |
| client_02 | 1.573 | 2.297 | 3.523 |
| client_03 | 1.303 | 1.476 | 2.814 |
| client_04 | 1.567 | 1.860 | 2.992 |
| client_05 | 1.563 | 2.345 | 3.561 |

Clients are broadly similar; client_03 (smallest, 6,260 windows) has consistently smaller updates.
No client is an outlier requiring special treatment.

---

## 4. Rule 4.1 applied as written — and why it is unsuitable

Rule 4.1 (`PHASE_6_EXPERIMENT_MATRIX.md` §4.1), fixed before any norm was seen:

> `C` = median of per-round, per-client norms **across the rounds the no-privacy baselines actually
> selected**, rounded up to three significant figures.

Applied: median of the 75 selected-round norms = **1.5779 → `C = 1.58`**.

**Problem found.** Medians are computed over a *pooled* set that is dominated by the low-norm late
round of seed 43 (round 44, norms ≈1.5) and masks the bimodality of §3.3. At `C = 1.58`:

| Region | Updates clipped |
|---|---:|
| All rounds | **37.2 %** |
| Rounds 1–5 (the rounds validation selects) | **88.0 %** |
| Rounds 44–50 | 8.0 % |

Because **three of five seeds select round 2** and one selects round 3, the rounds that determine
the reported checkpoint are exactly the rounds that would be clipped most aggressively. A `C` of
1.58 would rescale 88 % of the updates that matter by a mean factor of 0.883, and would
substantially confound P1-ctl's purpose (isolating clipping cost) by making that cost enormous.

**Conclusion: Rule 4.1 as written produces a `C` that is statistically defensible as a median but
methodologically destructive.** I will not adopt it silently.

---

## 5. Recommended amendment: `C` from the update-scale, not the pooled median

### 5.1 Candidate grid

| `C` | Basis | Clips | Mean rescale of clipped |
|---|---:|---:|---:|
| 1.58 | Rule 4.1 pooled median | 37.2 % | 0.883 |
| 2.00 | 3 s.f. | 6.5 % | 0.761 |
| 2.50 | 3 s.f. | 3.6 % | 0.800 |
| 3.00 | 3 s.f. | 2.2 % | 0.876 |
| **3.44** | **global p99, 3 s.f.** | **0.9 %** | 0.903 |
| 3.50 | 3 s.f. | 0.8 % | 0.911 |

### 5.2 Recommendation: `C = 3.44`

Rationale:

1. It is the **global 99th percentile**, a standard, pre-statistic (not tuned to utility).
2. It clips under 1 % of updates and **spares the early rounds entirely** at the p99 tail, so the
   validation-selected checkpoints are not systematically destroyed.
3. It leaves P1-ctl interpretable: the clipping cost is measured in isolation, not confounded by a
   near-total projection of early updates.
4. It is **independent of which round was selected**, so it does not depend on P0 outcomes — a
   weaker circularity than Rule 4.1's.

**Trade-off that must be acknowledged:** a larger `C` reduces per-update distortion but increases
sensitivity `S = 2C`. As shown below, `S` cancels in this accountant, so **`C` does not change ε**;
it only changes utility. The choice is therefore purely a utility/validity matter, which makes the
larger `C` strictly preferable under this design.

### 5.3 Sensitivity consequences

| Quantity | `C = 1.58` | `C = 3.44` |
|---|---:|---:|
| `p_max` (F3) | 0.371001 | 0.371001 |
| `S_A = 2C·p_max` (aggregate view) | 1.172 | 2.553 |
| **`S_B = 2C` (per-client view, headline)** | **3.16** | **6.88** |
| Noise SD per coordinate at σ=1.0 | 3.16 | 6.88 |

---

## 6. The σ grid produces very weak ε — a blocking finding

ε computed by the validated accountant (δ = 1e-5, full participation, **no amplification**):

| σ | R = 10 | **R = 50 (approved)** | R = 100 |
|---:|---:|---:|---:|
| 0.5 | 48.80 | **166.04** | 294.86 |
| 1.0 | 19.05 | **57.30** | 96.12 |
| 2.0 | 8.08 | **22.02** | 35.08 |

To reach ε ≈ 10 at R = 50 requires **σ ≈ 4.0**; ε ≈ 7 needs σ = 5.0.

**Assessment.** With five fixed clients, full participation, no subsampling amplification and 50
sequential releases, client-level ε cannot be small at any σ that leaves the model trainable.
σ = 2.0 already means noise with SD twice the clipping norm on every one of 36,357 coordinates.

This is **not a defect in the implementation** — it is the honest consequence of the architecture.
It is, however, a finding the σ grid in the approved matrix did not anticipate: the grid was
chosen before ε could be computed.

### 6.1 Options for the research lead

| Option | Change | Effect | Cost |
|---|---|---|---|
| **S-1** | Keep σ ∈ {0.5, 1.0, 2.0}, R = 50 | ε = 166 / 57 / 22 | Reports very weak guarantees honestly |
| **S-2** | Extend grid to σ ∈ {1.0, 2.0, **4.0**} | Adds ε ≈ 9.2 point | One extra condition (5 runs) |
| **S-3** | Extend grid **and** add σ = 8.0 | ε ≈ 4.1 | Two extra conditions |
| **S-4** | Reduce R (e.g. 20 rounds) | ε falls, but breaks budget-matching with P0/Phase 5 | **Not recommended** — invalidates the matched comparison |
| **S-5** | Add subsampling amplification | Requires participation < 1.0 | **Not available** — approved participation is all five every round |

**Recommendation: S-2.** Keep the original three σ values (they are pre-registered and comparable)
and **add σ = 4.0** so the study contains at least one configuration with ε < 10. This adds one
condition (5 runs, ≈0.7 h) and does not disturb the approved matrix; the original three remain
untouched and are reported as the weak-privacy end of the curve.

**S-4 and S-5 are rejected outright** because they would break comparability with the frozen
non-private baseline, which the master spec requires.

---

## 7. Privacy accounting summary for the approved matrix

| Condition | σ | `S_B = 2C` at C=3.44 | ε (δ=1e-5, R=50) | Status |
|---|---:|---:|---:|---|
| P1-a | 0.5 | 6.88 | 166.04 | Very weak; report as-is |
| P1-b | 1.0 | 6.88 | 57.30 | Weak |
| P1-c | 2.0 | 6.88 | 22.02 | Weak |
| **P1-d (proposed)** | **4.0** | 6.88 | **9.23** | Moderate |
| P3-a | 1.0 | 6.88 | 57.30 | **Identical to P1-b** by design |
| P3-b | 2.0 | 6.88 | 22.02 | **Identical to P1-c** by design |

**P1-ctl** has no noise and therefore **no DP guarantee**; its ε is undefined and must be reported
as "not applicable (no noise mechanism)".

Note that P3-a and P3-b carry **exactly** the ε of the corresponding P1 cells. This is the intended
and required outcome (`PHASE_6_PRIVACY_MATHEMATICS.md` §8.2): P3 adds confidentiality against the
key-blind server, **not** additional differential privacy.

---

## 8. What this pass did not do

- No noise was added; no privacy was provided.
- No test data was read at any point.
- No clipping was applied, so the utility cost of clipping is **not** measured here — that is
  P1-ctl's job in Stage C.
- No model was saved as a result; the pass is a measurement, not a model-selection run.
- ε values are **computed from the approved accountant**, not measured.

## 9. Artefacts

| Artefact | Path |
|---|---|
| Per-seed norms and summaries | `experiments/logs/phase6/calibration/seed_{42..46}/norms.json` |
| Per-seed run metadata | `experiments/logs/phase6/calibration/seed_{42..46}/run_metadata.json` |
| Calibration module | `src/privacy/calibration.py` |

(Calibration output is git-ignored under `experiments/logs/`.)

## 10. Decisions required before Stage C

| # | Decision | Recommendation |
|---|---|---|
| **CAL-1** | Reject `C = 1.58` (Rule 4.1 as written) in favour of `C = 3.44` (global p99) | **Adopt 3.44** |
| **CAL-2** | Extend the σ grid with **σ = 4.0** so one cell has ε < 10 | **Adopt S-2** |
| CAL-3 | Confirm `δ = 1e-5` (vs the stricter 1.4e-6 of D3′) | Keep 1e-5 |
| CAL-4 | Accept that reported ε values are 22–166 for the original grid, and state this as a finding | Acknowledge |
| CAL-5 | Confirm that P1-ctl reports ε as "not applicable" | Acknowledge |

**Stage C does not begin until CAL-1 and CAL-2 are resolved.**
