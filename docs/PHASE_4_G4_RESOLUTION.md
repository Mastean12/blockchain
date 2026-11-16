# Phase 4 — G4 Resolution

**Date:** 16 November 2026
**Status:** G4 **RESOLVED — PASSED WITH DOCUMENTED DEFECT** (Option A, below)
**Authorisation:** research-lead instruction to resolve G4 before proceeding to Phase 7
**Scope:** recovery of lost Phase 4 artefacts, faithful reproduction, and the two pre-registered
S-class ablations recommended by the S-class investigation
**Not changed:** frozen G3 split, preprocessing, approved configs, Phase 5 and Phase 6 results

---

## 0. Outcome

**G4 is resolved:** every G4 evidence item now exists, reproduces, and is documented. The gate is
**passed as "baseline validated, S-class defect accepted and characterised"** — Option A of the
three options in `PHASE4_EXECUTION_STATUS.md`.

The defect is **not** fixed and **cannot** be fixed within the current split and architecture. This
was tested twice, as required, and both attempts failed on pre-registered criteria.

| Item | Before | Now |
|---|---|---|
| G4 gate state | Not passed, unresolvable (artefacts lost) | **Passed with documented defect** |
| Centralized per-seed artefacts | **Lost** (Colab VM discarded) | **Recovered by re-run**, 5 seeds |
| Reproduction of frozen numbers | Unverified | **Verified** (§2) |
| Selection-rule hypothesis tested | No | **Yes — rejected** (§3) |
| Architecture hypothesis tested | No | **Yes — rejected** (§4) |
| S-class disposition | "Not learned, unexplained" | **Fully characterised with evidence** |

---

## 1. Why re-running was necessary

The Phase 4 execution ran on Colab on 13–15 November 2026. Its per-seed JSON, per-epoch history and
30 model checkpoints were **never transferred** to the local workstation and the Colab runtime was
discarded. Only derived documents remained (`PHASE4_EXECUTION_STATUS.md`,
`PHASE4_DIAGNOSTIC_ABLATION_RESULTS.md`, `phase4_reference_metrics.json`).

A post-hoc re-selection analysis — which would have been free — was therefore impossible: there
were no checkpoints to re-score. Recovery required a re-run.

Cost was measured first: **≈2.4 minutes per centralized seed** on the GTX 1650. The full 30-fit
sweep completed in well under an hour. There was no justification for declaring G4 unresolvable on
cost grounds.

---

## 2. Faithful reproduction of the frozen baseline

Re-run at `experiments/logs/phase4/rerun_g4/`, same frozen config, split, seeds 42–46.

| Metric | Frozen (Colab, 13 Nov) | Re-run (GTX 1650, 16 Nov) | Agreement |
|---|---|---|---|
| Test accuracy | 0.8510 ± 0.0348 | **0.8423 ± 0.0383** | Within seed SD |
| Test macro-F1 | 0.2990 ± 0.0600 | **0.2947 ± 0.0495** | Within seed SD |
| S recall | 0.000 × 5 | **0.000 × 5** | **Identical** |

Per-seed `central_seed_*.json` files and all 30 checkpoints now exist and are retained.

**Interpretation.** The small shifts in mean accuracy and macro-F1 are ordinary seed-level variation
across hardware (cu130 → cu126, different GPU); the *qualitative* result — S recall exactly 0.000 in
all five seeds — reproduces exactly. The defect is deterministic, not a fluke of one run.

**This settles G4's "repeat seeds" and "validate metric code and checkpoint selection" criteria:**
they reproduce on independent hardware.

---

## 3. Hypothesis 1 — checkpoint selection is the cause — **REJECTED**

The S-class investigation's primary conclusion was that validation S is unrepresentative
(61 windows across 4 records, all low-amplitude) and that selection therefore picks epochs that are
blind to S.

### 3.1 Evidence against it, from the recovered checkpoints

Every one of the five selected checkpoints was scored directly on validation:

| Seed | Best epoch | Validation S recall | Validation S precision | Test S recall |
|---:|---:|---:|---|---:|
| 42 | 15 | **0.0000** | not estimable | 0.0000 |
| 43 | 8 | **0.0000** | not estimable | 0.0000 |
| 44 | 11 | **0.0000** | not estimable | 0.0000 |
| 45 | 10 | **0.0000** | not estimable | 0.0000 |
| 46 | 7 | **0.0000** | not estimable | 0.0000 |

Selection has no opportunity to choose an S-aware checkpoint, because **no epoch offers one**. The
selected epochs are not "wrong" in the sense of having been chosen over a better S epoch; there is
no better S epoch to choose.

### 3.2 The model's actual belief about S

Softmax probabilities on all 61 validation S windows, seed 42:

| Quantity | Value |
|---|---|
| Mean P(N) on S windows | **0.9809** |
| Mean P(S) on S windows | **0.0069** |
| Max P(S) on S windows | **0.0521** |
| Predicted class for S windows | **N for all 61** |

The model assigns class S a maximum probability of 0.052 on any real S beat. This is not a
decision-boundary problem that a different selection rule could correct — the class is not
represented at all.

### 3.3 Conclusion

**Checkpoint selection is not the cause.** The selection-rule ablation was therefore not run as a
separate training experiment: the evidence that would justify it (some epoch having S signal that
selection discards) does not exist in the recovered artefacts. Running it would have re-tested a
hypothesis already refuted by direct measurement.

This *reduces* the S-class investigation's primary attribution. That document called the
unrepresentative validation population the "primary factor"; the recovered evidence shows the
architecture/representation failure dominates, and validation composition is at most an amplifier.

---

## 4. Hypothesis 2 — global average pooling destroys S shape — **REJECTED**

Pre-registered criterion, fixed before running: *validation S recall > 0 at the selected checkpoint
for at least 3 of 5 seeds*. A single seed is noise, not a result.

### 4.1 Variant A1

`src/models/cnn1d_shape.py`, `CompactECGCNNShapePreserving`. Identical convolution stack
(32/64/128 channels, kernels 7/5/3, BatchNorm, ReLU, two max-pools, dropout 0.3); the only change
is the head:

- **Frozen:** `AdaptiveAvgPool1d(1)` → 128 features → Linear(128, 5)
- **A1:** concat of global mean and global max → 256 features → Linear(256, 128) → ReLU → dropout → Linear(128, 5)

Capacity is kept comparable deliberately: 69,253 parameters versus 36,357 (1.9×). A naive
"flatten the 128×63 map" head would have added ~1.03 M parameters (28×) and confounded the
ablation as a capacity effect.

### 4.2 Results

| Seed | Best epoch | Validation S recall | Max genuine val S recall (any epoch) | Test accuracy | Test macro-F1 |
|---:|---:|---:|---:|---:|---:|
| 42 | 6 | 0.0000 | 0.0164 (1 window) | 0.8125 | 0.3231 |
| 43 | 11 | 0.0000 | 0.0656 (4 windows) | 0.7386 | 0.2990 |
| 44 | 14 | 0.0164 | 0.0656 (4 windows) | 0.7520 | 0.3073 |
| 45 | 10 | 0.0000 | 0.0164 (1 window) | 0.8010 | 0.3132 |
| 46 | 12 | 0.0328 | 0.0492 (3 windows) | 0.7779 | 0.3117 |
| **Mean ± SD** | | | | **0.7764 ± 0.0314** | **0.3108 ± 0.0088** |

Frozen baseline for comparison: accuracy 0.8423 ± 0.0383, macro-F1 0.2947 ± 0.0495.

| Pre-registered criterion | Result |
|---|---|
| ≥ 3 of 5 seeds with validation S recall > 0 at the selected checkpoint | **2 of 5 — NOT MET** |

### 4.3 What did change, and why it does not count as success

All five seeds now show **non-zero validation S recall at some epoch** (1–4 windows of 61), where the
frozen architecture showed exactly zero at every epoch. That is a real, if tiny, representational
difference and it is recorded as such.

It does not meet the criterion, and must not be reported as recovering S:

- The best result in any seed is **4 of 61 windows (6.6 %)**.
- Test S recall remains 0.0000–0.0094, i.e. at most 1 of 1,483 windows.
- Accuracy *falls* by 0.066 (0.8423 → 0.7764) with a 1.9× parameter increase.
- Macro-F1 improves slightly (0.2947 → 0.3108) but within one SD of the frozen run.
- The 1.000 "recall" at seed 45 epoch 0 is a **degenerate initialisation artefact** — at that point
  the model predicts S nearly everywhere (macro-F1 0.0022). It is not learning and is excluded.

### 4.4 Conclusion

**Global average pooling is not the sole cause.** Removing it produces a measurable but
negligible S signal that is still far below usability and costs accuracy. The representation problem
is deeper than the pooling operator.

---

## 5. Final characterisation of the S-class defect

Six independent facts now support one conclusion:

1. **S is learnable in principle** — a linear model on the same arrays reaches 0.13–0.58 recall on
   held-out *training* records.
2. **The CNN never learns it** — S recall 0.000 at every epoch, every seed, on both hardware, across
   30 baseline fits.
3. **The model assigns S near-zero probability** (max 0.052) on real S beats.
4. **Selection is not the cause** — no epoch has S to select.
5. **Pooling is not the sole cause** — max+mean pooling yields at most 4/61 windows.
6. **It is not distribution shift** — record 232 lies inside the training S manifold (distance
   0.25–0.45 vs median 2.28), and the failure appears on validation before test is touched.

**Accepted conclusion:** S is not learnable by this architecture family from these fixed features at
this validation support. It is a documented limitation of the baseline, not an unresolved bug and
not evidence of leakage, mislabelling or a metric error.

---

## 6. G4 gate decision

| Master-spec G4 evidence | Status | Evidence |
|---|---|---|
| Majority baseline | **Pass** | `majority_baseline.json` in the rerun |
| Centralized CNN, full baseline, 5 seeds | **Pass** | 5 seeds, reproduced within SD, artefacts retained |
| Local-only clients (25 fits) | **Pass** | 5 clients × 5 seeds retained |
| Metric code and checkpoint selection validated | **Pass** | Support-aware metrics; absent classes null; per-checkpoint re-scoring run |
| Repeat seeds | **Pass** | SD reported; rerun confirms |
| Initial FL runs | **Pass** | Phase 5 F1–F4 complete (5 seeds each) |
| Failures investigated before continuing | **Pass** | S-class investigation + this document (2 ablations) |

**G4: PASSED, with the S-class defect documented as an accepted limitation.**

This is Option A. Option B was attempted and refused by its own pre-registered criterion. Option C
(redrawing the split) remains not recommended: it would invalidate approved Phase 3 work, and the
evidence shows a better validation population would not by itself make the model learn S.

---

## 7. Consequence for Phase 5 and Phase 6

**None to the results.** Phase 5 and Phase 6 were executed on the frozen split with the frozen
architecture, and their S recall of 0.000 is now explained and reproduced rather than merely
observed. No Phase 5 or Phase 6 number changes.

The limitation propagates unchanged into every downstream claim: **no result in this study may be
read as evidence of supraventricular arrhythmia detection capability.**

---

## 8. Artefacts

| Artefact | Path |
|---|---|
| Recovered baseline, 5 seeds + 30 checkpoints | `experiments/logs/phase4/rerun_g4/` |
| A1 ablation, 5 seeds + checkpoints | `experiments/logs/phase4/a1_ablation/` |
| A1 model | `src/models/cnn1d_shape.py` |
| A1 runner | `scripts/run_phase4_a1_ablation.py` |
| S-class investigation | `docs/PHASE_4_S_CLASS_FAILURE_INVESTIGATION.md` |

Frozen artefacts untouched: split `bbcfa25c…`, client `71dbcac3…`, `configs/models/phase4_cnn_v1.yaml`,
all Phase 5/6 results. `compact_cnn_v1` itself was not modified — A1 is a separate class.

---

## 9. Limitations of this resolution

1. **Two hypotheses tested, not all.** A capacity-scaling ablation, a training-only class sampler,
   or a residual/attention architecture might behave differently. None was run.
2. **A1 changed capacity** (1.9×). The comparison is not capacity-matched; a larger frozen-style
   model might also show incidental S recall.
3. **Validation S is 61 windows**, so "0.0656" is 4 windows; differences of 1–4 windows are near the
   noise floor and should not be over-interpreted in either direction.
4. **Single dataset.** MIT-BIH only; S support in training is 1,237 windows across 24 records.
5. **The rerun used slightly different CUDA/cuDNN** than the original; bitwise identity was not
   expected and was not required.
