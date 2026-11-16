# Phase 6 — DP Privacy–Utility Frontier Diagnostic (D-2)

**Status:** DIAGNOSTIC COMPLETE — **AWAITING RESEARCH-LEAD REVIEW**
**Date:** 16 November 2026
**Authorisation:** research-lead D-2 decision, 16 November 2026, with conditions
**Scope:** diagnostic investigation only. One seed (42), maximum eight communication rounds,
σ ∈ {0.01, 0.05}, matched P0 and clip-only references.
**Mechanism evaluated:** whole-model client-level DP with per-client L2 clipping and Gaussian
noise, as implemented in `src/privacy/`.
**Effect on approved artefacts:** none. The approved σ grid {0.5, 1.0, 2.0, 4.0}, the Phase 6
implementation, the configurations, the frozen G3 manifests and all Phase 1–5 results are
unchanged.
**Not done, per instruction:** approved full σ grid not executed, no per-layer DP, no central DP,
no Opacus switch, no Phase 7 work, nothing committed or pushed.

---

## 0. Summary

| Condition | σ | Clipped updates | Val macro-F1 (rounds 1–8) | Test acc | Test macro-F1 | V recall | ε (δ=1e-5, R=8) |
|---|---:|---:|---|---:|---:|---:|---:|
| P0 reference (unclipped, unnoised) | — | 0.0 % | 0.249–0.285 | 0.8728 | 0.3993 | 0.972 | n/a (no mechanism) |
| Clip-only control (C = 3.44, no noise) | — | 1.2 % | 0.252–0.276 | 0.8358 | 0.3420 | 0.954 | **n/a (no noise mechanism)** |
| **Diagnostic A** | **0.01** | 10.0 % | 0.117–0.276 | **0.7714** | **0.2924** | 0.946 | **44,111.78** |
| **Diagnostic B** | **0.05** | 60.0 % | 0.022–0.243 | **0.8707** | **0.2327** | **0.000** | **1,871.78** |

**No defensible privacy–utility operating point was identified in the explored diagnostic region.**
At σ = 0.01, utility is broadly comparable to the unnoised baseline while ε = 44,111.78 provides no
meaningful privacy. At σ = 0.05, ε remains 1,871.78 while the model has collapsed to predicting only
class N (V recall 0.000). Both utility and privacy fail their respective requirements at every point
tested.

These findings apply to the **implemented whole-model client-level DP mechanism** at the tested
configurations. They are not a statement about all possible differential-privacy mechanisms (§8).

---

## 1. Pre-execution verifications (all six required checks)

### 1.1 Sensitivity from the approved adjacency — VERIFIED

Replace-one adjacency, **equal cardinality**, five fixed clients. Because equal-cardinality
replacement leaves `n_k` invariant, the frozen weights are identical on neighbouring datasets, so
the release is a fixed linear functional and the proof in
`PHASE_6_PRIVACY_MATHEMATICS.md` §4.3 applies:

```
‖G(D) − G(D')‖₂ = p_j‖x − y‖₂ ≤ p_j(‖x‖₂ + ‖y‖₂) ≤ 2C·p_max ≤ 2C
```

with `S_B = 2C = 6.88` at C = 3.44. The bound is tight (take `x = C·u`, `y = −C·u` for the
maximum-weight client).

### 1.2 Sample-weighted aggregation sensitivity — VERIFIED

| Quantity | Value |
|---|---|
| Frozen per-client sample counts | 26,685 / 14,780 / 6,260 / 11,149 / 13,053 |
| Total | 71,927 |
| Weights `p_k` | 0.371001 / 0.205486 / 0.087033 / 0.155004 / 0.181476 |
| Sum of weights | 1.000000000000 |
| **`p_max`** | **0.371001** |
| `S_A = 2C·p_max` (aggregate-only view) | 2.552488 |
| `S_B = 2C` (per-client view) | 6.880000 |
| Headline view used | **B**, because `S_B > S_A` |

Correct under the threat model: with no secure aggregation (OUT-2), the server observes each
client's update individually, so the per-client sensitivity governs.

### 1.3 Clipping location and noise calibration — VERIFIED

| Check | Result |
|---|---|
| DP vector = trainable parameters only | 14 tensors, 36,357 elements |
| BatchNorm `running_mean`/`running_var` excluded | Yes — 448 floats remain unprotected (D5, disclosed) |
| `num_batches_tracked` excluded | Yes — 3 ints |
| Clip applied to the whole update vector, per client, **before** noise | Yes |
| Position in the flow | clip → noise → (encrypt) → aggregate → (decrypt) |
| Noise std at σ = 0.01 | measured 0.034509 vs requested 0.034400 |
| Noise std at σ = 0.05 | measured 0.172546 vs requested 0.172000 |
| Total noise L2 at σ = 0.01 / 0.05 | 6.580 / 32.900 vs predicted 6.559 / 32.796 |

### 1.4 Accountant and composition — VERIFIED

- Toy gate passed: accountant ε = 1.0126 vs analytic Gaussian bound 1.2112 (ratio 0.836). The
  accountant is tighter than the classical bound, as expected for RDP→DP conversion.
- **Sequential composition**, `sample_rate = 1.0`, **no subsampling amplification**. This is
  enforced in code: any `sample_rate ≠ 1.0` raises, because participation is all five clients
  every round.
- `R = 8` releases, matching the 8 executed rounds.

| σ | ε at R = 8 (this diagnostic) | ε at R = 50 (for reference only) |
|---:|---:|---:|
| 0.01 | **44,111.78** | 275,111.78 |
| 0.05 | **1,871.78** | 11,111.78 |
| 0.50 | 41.65 | 166.04 |
| 1.00 | 16.51 | 57.30 |
| 4.00 | 3.19 | 9.23 |

**Only the R = 8 column was executed.** The R = 50 column is an arithmetic projection used earlier
for planning and is included here solely to show the composition trend; **no R = 50 DP run exists**
(§7).

### 1.5 Expected noise-to-signal ratio — COMPUTED

`Σ p_k² = 0.244401`, `√(Σ p_k²) = 0.494369`.

| σ | Per-client ratio `σ√d` | Aggregate ratio `σ√(d·Σp²)` | Aggregate noise L2 |
|---:|---:|---:|---:|
| **0.01** | 1.91× | **0.94×** | 3.24 |
| **0.05** | 9.53× | **4.71×** | 16.21 |
| 0.50 | 95.34× | 47.13× | 162.13 |
| 1.00 | 190.68× | 94.26× | 324.27 |
| 4.00 | 762.70× | 377.06× | 1,297.07 |

This is why σ = 0.01 and 0.05 were the correct diagnostic cells: aggregate noise is comparable to,
or a few times, the signal, versus 47–377× for the approved grid.

### 1.6 No test data in model selection — VERIFIED

`src/privacy/dp_federated.py` evaluates **validation** at round 0 and after each round (lines 222,
339) and **test exactly once** (line 389), after `selected_round` is fixed at line 384. Test data
never enters the training loop, checkpoint selection, clipping statistics or noise calibration.

---

## 2. Execution record

| Item | Value |
|---|---|
| Hardware | NVIDIA GeForce GTX 1650, 4 GB; CUDA 12.6; torch 2.14.1+cu126; Python 3.12.10 |
| DP/HE libraries | opacus 1.6.0 (accounting only); tenseal 0.3.18 (not used in this diagnostic) |
| Partition | F3 severe non-IID `da8b96fa…` (unchanged) |
| Seeds | 42 only |
| Rounds | 8, plus round-0 evaluation |
| Local epochs | 2 (frozen) |
| Clip norm | C = 3.44 |
| δ | 1e-5 |
| Stopping criterion | stop if validation loss > 1e6 or non-finite |
| Stopping triggered | **No** — neither condition reached the guard |
| Round wall-time | ≈ 6.3–6.5 s (5 clients × 2 epochs) |
| Total wall-time | 51.1 s (σ=0.01), 51.3 s (σ=0.05) |
| Output | `experiments/logs/phase6/diagnostic/{sigma0.01,sigma0.05}/seed_42/` |

Round-level training loss, validation loss, validation macro-F1, clipping statistics, noise
magnitude, ε/δ and timings are recorded in each `rounds.json`; aggregates in `run_summary.json`;
the selected checkpoint and its SHA-256 in `checkpoints/`. Recovery information: `rounds.json` is
rewritten after every round, so an interrupted condition can be re-run from its last persisted
round.

---

## 3. Findings

### 3.1 Separating clipping loss from noise loss

This separation is the reason the clip-only control exists, and the measurements are distinct.

| Step | Test acc | Test macro-F1 | V recall | Δ macro-F1 from P0 |
|---|---:|---:|---:|---:|
| P0 (no clip, no noise) | 0.8728 | 0.3993 | 0.972 | — |
| **+ clipping at C = 3.44 (clip-only)** | 0.8358 | 0.3420 | 0.954 | **−0.0573 (clipping)** |
| + noise at σ = 0.01 | 0.7714 | 0.2924 | 0.946 | **−0.1069 total → −0.0496 additional (noise)** |
| + noise at σ = 0.05 | 0.8707 | 0.2327 | 0.000 | **−0.1666 total → −0.1093 additional (noise)** |

**Clipping cost (isolated):** macro-F1 0.3993 → 0.3420, a loss of 0.0573, at a clipped-update rate
of only **1.2 %** (median update norm 1.546 against C = 3.44). Clipping is therefore not free even
when it touches few updates: the handful of large early-round updates carry disproportionate
information.

**Additional noise cost:** at σ = 0.01 a further 0.0496 of macro-F1, and at σ = 0.05 a further
0.1093 including total loss of V recall. Clipping and noise therefore contribute comparably at
σ = 0.01; at σ = 0.05 noise dominates and destroys a class entirely.

### 3.2 Why the σ = 0.05 accuracy of 0.8707 is misleading

σ = 0.05 records the **highest test accuracy of any DP condition (0.8707)**, close to P0's 0.8728.
That figure must not be read as preserved utility. The per-class breakdown shows why:

| Class | Support | σ = 0.01 recall | σ = 0.05 recall |
|---|---:|---:|---:|
| N | 13,099 | 0.853 | **1.000** |
| S | 1,483 | 0.000 | 0.000 |
| V | 461 | **0.946** | **0.000** |
| F | 0 | not estimable | not estimable |
| Q | 2 | 0.000 | 0.000 |

At σ = 0.05 the model predicts **N for every single window**: N recall is exactly 1.000, and no V,
S or Q window is ever identified. The 0.8707 accuracy is simply the majority-class rate of the test
set (13,099 of 15,045 windows are N, i.e. 87.1 %). Accuracy is maximised rather than degraded by
collapse when the dominant class is this frequent.

**Macro-F1 exposes the collapse:** it falls to **0.2327**, the lowest value in the diagnostic and
*below* σ = 0.01's 0.2924, despite σ = 0.05 having the higher accuracy. Weighted-F1 is also
uninformative here (0.8105) because it is dominated by N.

The collapse is consistent with the round trajectory: validation macro-F1 sits flat at ≈0.243 for
rounds 1–7 and then drops to 0.0225 at round 8 as validation loss jumps to 10.18. Validation
selected round 1, so the reported checkpoint is an early one, before that final disruption — the
lowest-macro-F1 selection in the diagnostic.

**Conclusion:** σ = 0.05 does not preserve utility. It preserves *accuracy* while eliminating
minority-class detection. Any report quoting its accuracy without macro-F1 and V recall would
misrepresent the result.

### 3.3 Convergence and instability

| Round | σ = 0.01 val macro-F1 | σ = 0.01 val loss | σ = 0.05 val macro-F1 | σ = 0.05 val loss |
|---:|---:|---:|---:|---:|
| 0 | 0.0019 | 1.6278 | 0.0019 | 1.6278 |
| 1 | 0.2465 | 0.3034 | 0.2432 | 0.7794 |
| 2 | 0.2756 | 0.5667 | 0.2432 | 0.2193 |
| 3 | 0.2432 | 0.3068 | 0.2384 | 0.4470 |
| 4 | 0.2642 | 1.0440 | 0.2429 | 0.2753 |
| 5 | 0.2764 | 0.4747 | 0.2360 | 0.7344 |
| 6 | 0.1168 | 3.8594 | 0.2432 | 0.3943 |
| 7 | 0.2327 | 0.4177 | 0.2431 | 0.5509 |
| 8 | 0.1678 | 3.6788 | 0.0225 | 10.1761 |

The pre-declared stop criterion (validation loss > 1e6, or non-finite) **did not trigger** in either
condition; the maximum observed loss was 10.18. No condition was halted, and no result was
discarded. The recorded instability is milder than divergence but real: loss spikes of 3.7–10.2
with macro-F1 oscillation at σ = 0.01, and a terminal collapse at σ = 0.05. The criterion threshold
was calibrated for catastrophic divergence, not for this intermediate regime; that is recorded as a
limitation of the guard, not as a pass.

### 3.4 Predictive utility — overall assessment

Neither diagnostic condition preserves predictive utility in a defensible sense. σ = 0.01 is closer
to baseline on macro-F1 (0.2924) but remains 0.107 below P0 and shows unstable late rounds.
σ = 0.05 loses an entire supported class. The carried-forward Phase 4/5 limitation also persists:
**S recall is 0.000 in every condition, including the unnoised P0 reference**, so nothing here is
attributable to DP and no Phase 6 result may be described as improving or worsening S.

### 3.5 Formal privacy guarantee — assessment

Under the approved threat model the executed guarantees are **ε = 44,111.78 at σ = 0.01** and
**ε = 1,871.78 at σ = 0.05**, at δ = 1e-5 over 8 releases.

Both values are so large that the mechanism provides **no meaningful protection** against the
honest-but-curious server of ADV-1. A valid accountant produces a nominal ε; that does not make the
protection useful. Per the directive, a condition that preserves utility but has an extremely large
ε must not be presented as successful privacy protection — and here even the utility is not
preserved.

The clip-only control adds no noise and therefore has **no DP guarantee**; its ε is reported as
**not applicable**, not as zero or infinity.

### 3.6 Computational and communication overhead

| Component (8 rounds) | σ = 0.01 | σ = 0.05 | Baseline per round |
|---|---:|---:|---:|
| Clipping time | 0.019 s | 0.026 s | — |
| Noise generation | 0.027 s | 0.029 s | — |
| Total, 8 rounds | 51.1 s | 51.3 s | ≈ 6.3 s/round |
| Added communication | **0 bytes** | 0 bytes | — |

DP overhead is computationally negligible and adds no communication payload. It is not the
bottleneck; utility loss is.

---

## 4. Interpretation: why the frontier is where it is

Noise is added independently to all 36,357 coordinates of a whole-client model update. Total noise
L2 grows as `σ·C·√d` while the update itself is bounded by `C`, so the noise-to-signal ratio is
`σ·√d` (per client) and `σ·√(d·Σp²)` (after weighted aggregation), **independent of the dataset and
of the partition**. With five clients and full-model updates there is no large batch over which to
average the noise down.

This is an architectural property of whole-model client-level DP at `d = 36,357`, not a defect in
the implementation. All six pre-execution checks confirm the implementation matches the specified
mathematics exactly; the negative outcome is a property of the mechanism, not of the code.

---

## 5. Limitations

1. **One seed, eight rounds.** Diagnostic observations, not estimates. No standard deviations; no
   convergence claims past round 8.
2. **Selected rounds differ across conditions** (P0: 2; control: 23; σ=0.01: 5; σ=0.05: 1), and
   Phase 5 already showed checkpoint selection on validation macro-F1 is fragile at ≈0.28.
   Cross-condition test comparisons are indicative only.
3. **σ = 0.01 and 0.05 are outside the approved matrix** and must never be reported as approved
   conditions or merged into the approved grid.
4. **Only F3** (severe non-IID) was explored. The `σ√d` term does not depend on the partition, but
   utility effects might.
5. **ε is computed, not measured**, and is valid only under the stated adjacency, full
   participation and no-amplification assumptions.
6. **The clip-only control ran to round 23** (its config is an approved-grid config), so its test
   number is not matched to 8 rounds; its rounds 1–8 statistics are used for the clipping comparison
   where round-matched, and this is noted.
7. **BatchNorm buffers remain unprotected** (D5) in every condition, a disclosed leak of
   activation-distribution statistics.
8. **V recall 0.000 at σ = 0.05** is observed at a single selected round with one seed; it should be
   confirmed across seeds before being treated as a stable property, though the round-8 validation
   collapse corroborates it.
9. **The instability guard did not fire**, so its threshold was not validated against a genuine
   divergence event.

---

## 6. What is not claimed

- No claim that a useful privacy–utility operating point exists anywhere in DP for this
  architecture was tested beyond the region explored. **No defensible operating point was identified
  in the explored diagnostic region.**
- No claim about untested ε values. **Only ε = 44,111.78 (σ=0.01, R=8) and ε = 1,871.78
  (σ=0.05, R=8) were evaluated.** The R = 50 projections in §1.4 were not run and do not describe
  evaluated configurations.
- No claim that DP generally is unsuitable. The findings apply to the **implemented whole-model
  client-level DP mechanism** under this threat model, aggregate level, clipping rule, client count
  and tested configurations (§8).
- No claim of improved or worsened S-class behaviour, which is 0.000 in every condition including
  the unnoised reference.

---

## 7. Status of the approved full σ grid

**The approved full σ grid {0.5, 1.0, 2.0, 4.0} × 5 seeds × 50 rounds was NOT executed.**

Reason: the verified noise-to-signal mathematics (§1.5) and an earlier eight-round probe showed
whole-model client-level DP at these σ values produces noise 47–377× the signal after weighted
aggregation, driving validation loss to as much as 6.9 × 10⁹. Executing 20 runs × 51 rounds of
known-collapsed models would consume ≈ 6 h of GPU time to reproduce a result already determined by
arithmetic that the six checks confirm is implemented correctly. The research lead authorised this
limited diagnostic (D-2) in place of that sweep.

The approved configurations remain on disk, unmodified and ready to run if a future decision
reverses this. Their execution status is **not run**, not "failed" and not "passed".

---

## 8. Recommendation for the next experiment

**Do not run the approved σ grid as-is.** The outcome is predetermined by the verified mechanism
arithmetic, and the diagnostic confirms the direction.

**If a usable DP operating point is required, the noise target must change — not σ.** The obstacle
is `√d`. Three options, each requiring a **separate research-lead approval and a revised threat
model and sensitivity derivation**; none is implemented here:

| Option | Change | Effect on `√d` | Re-approval needed |
|---|---|---|---|
| R2-a | Per-layer (per-tensor) DP with per-tensor clipping | Removes the single global `√d`; retains `√d_t` per tensor | New per-tensor sensitivity derivation |
| R2-b | Server-side central DP (noise on the aggregate only) | `√d` applies once, against the full aggregate signal | Different trust model (trusted server) |
| R2-c | Opacus per-sample DP-SGD | Averaging over ~256 samples per batch suppresses noise | Mechanism change and sensitivity re-derivation |

**If no mechanism change is authorised,** the defensible path is to report the DP arm as a
**negative result** restricted to what was measured: "with this compact CNN, five clients, and
whole-model client-level DP, the mechanism yields no defensible privacy–utility trade-off at any
tested configuration." That is a legitimate contribution and requires no new approval.

**Next required decision:** whether Phase 6's DP arm proceeds as a documented negative result
limited to the tested mechanism and configurations, or whether a mechanism change (R2-a/b/c) is
authorised. No further Phase 6 execution will occur without that decision.

---

## 9. Final state verification

| Check | Result |
|---|---|
| Test suite | **90 passed, 1 skipped** (the skip is a CPU-only test, correctly skipped while CUDA is available) |
| Tracked-file diffs | **0** — `git diff --stat` is empty |
| Approved σ grid configs | Unchanged on disk (`configs/privacy/phase6_p1*.yaml`, `p2`, `p3*`) |
| Frozen manifests | Unchanged — split `bbcfa25c…`, client `71dbcac3…`, F3 `da8b96fa…` |
| Phase 1–5 results | Unchanged |
| Phase 6 implementation | Unchanged by this report (implementation code was finalised in Stage C) |
| Historical results | Unchanged |
| Committed / pushed | **No** |

New untracked artefacts from Phase 6 (not committed): `configs/privacy/`, `scripts/run_phase6_privacy.py`,
`src/privacy/*.py`, `tests/test_phase6_*.py`, and the Phase 6 documentation set.

**Phase 6 is not complete.** Explicit-privacy evaluation of **HE-only (P2)** and **combined HE+DP
(P3)** has not been executed, so the RQ3 comparison required by master spec §16.2 is not yet
answerable. **G6 is not passed.**
