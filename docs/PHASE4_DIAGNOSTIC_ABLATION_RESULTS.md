# Phase 4 Diagnostic Ablation — Results

**Companion to:** [`PHASE_4_DIAGNOSTIC_ABLATION.md`](PHASE_4_DIAGNOSTIC_ABLATION.md) (protocol, frozen before execution)
**Executed:** 15 November 2026, Colab Tesla T4, torch 2.14.1+cu130, CUDA 13.0, Python 3.13.16
**Status:** Exploratory. Does not modify or validate the frozen baseline.

## 1. Headline answer

**Neither class weighting (D1) nor balanced-accuracy selection (D2) recovered class S.
S recall was 0.000 in all five seeds of both diagnostics, identical to the baseline.**

Both interventions changed class V behaviour instead, and moved the N/V trade-off. The
S collapse is not caused by the loss weighting or the selection metric.

| Condition | Test acc | Test macro-F1 | S recall (5 seeds) | V recall | N recall |
|---|---:|---:|---|---:|---:|
| Baseline `phase4_cnn_v1` | 0.8510 ± 0.0348 | 0.2990 ± 0.0600 | 0.000, 0.000, 0.000, 0.000, 0.000 | 0.251 | 0.969 |
| D1 `phase4_diag_d1_class_weighted` | 0.8142 ± 0.0550 | 0.3403 ± 0.0752 | 0.000, 0.000, 0.000, 0.000, 0.000 | 0.925 | 0.903 |
| D2 `phase4_diag_d2_selection_balanced_accuracy` | 0.8251 ± 0.0335 | 0.3207 ± 0.0189 | 0.000, 0.000, 0.000, 0.000, 0.000 | 0.797 | 0.920 |

Test macro-F1 covers **N/S/V/Q only**; test F support is 0, so test F is not estimable and no
row above is a five-class macro-F1. All numbers are means across seeds 42–46.

## 2. Per-class test results

Class order N/S/V/F/Q. `NA` means not estimable (no true support, or no predicted positives
so precision is undefined and excluded from precision averages).

### Baseline (centralized, frozen reference)

| Class | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| N | 13,099 | 0.874 | 0.969 | 0.919 |
| S | 1,483 | 0.000 | **0.000** | 0.000 |
| V | 461 | 0.355 | 0.251 | 0.277 |
| F | 0 | NA | NA | NA |
| Q | 2 | NA | 0.000 | 0.000 |

### D1 — class-weighted cross-entropy

| Class | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| N | 13,099 | 0.889 | 0.903 | 0.895 |
| S | 1,483 | 0.000 | **0.000** | 0.000 |
| V | 461 | 0.357 | 0.925 | 0.466 |
| F | 0 | NA | NA | NA |
| Q | 2 | 0.000 | 0.000 | 0.000 |

### D2 — validation balanced-accuracy selection

| Class | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| N | 13,099 | 0.886 | 0.920 | 0.902 |
| S | 1,483 | 0.000 | **0.000** | 0.000 |
| V | 461 | 0.331 | 0.797 | 0.381 |
| F | 0 | NA | NA | NA |
| Q | 2 | NA | 0.000 | 0.000 |

## 3. Seed-level variability

| Condition | Per-seed test macro-F1 | SD | Best epochs |
|---|---|---:|---|
| Baseline | 0.321, 0.233, 0.272, 0.390, 0.279 | 0.0600 | 15, 8, 11, 10, 7 |
| D1 | 0.287, 0.354, 0.300, 0.466, 0.294 | 0.0752 | 19, 1, 11, 1, 1 |
| D2 | 0.343, 0.298, 0.311, 0.313, 0.338 | 0.0189 | 12, 3, 3, 24, 27 |

D1 spread is wide and three of five seeds selected epoch 1, which suggests weighting makes the
validation macro-F1 criterion noisy rather than informative. D2 has the tightest spread of the
three, but with S still at zero.

Validation: baseline 0.9419 / 0.3667; D1 0.8532 / 0.3063; D2 0.7647 / 0.2888 (accuracy /
macro-F1 over N/S/V/F). Both diagnostics select checkpoints at **lower validation accuracy**
than the baseline, which is the expected cost of optimising a recall-balanced criterion over a
validation set where 61 S windows sit in 4 records.

## 4. Interpretation

### 4.1 What improved
- **V recall**: 0.251 → 0.925 (D1) and 0.797 (D2). The model now detects ventricular ectopy.
- **Test macro-F1**: 0.2990 → 0.3403 (D1), 0.3207 (D2). Driven entirely by V.
- **Stability** (D2): SD fell from 0.0600 to 0.0189.

### 4.2 What did not improve
- **S recall remained exactly 0.000 in every seed of both diagnostics.** The model never emits
  an S prediction.
- D1 lost N recall (0.969 → 0.903) and accuracy (0.8510 → 0.8142); V precision stayed poor
  (0.357), so V recall rose largely through false positives. D1 macro-F1 gain is therefore a
  shift in error direction, not a gain in minority discrimination.

### 4.3 Why, mechanistically

The two interventions could only ever act on classes the model already learns. Evidence:

- **The S decision boundary is never approached.** S support in training is 1,237 windows
  across many records, but the largest contributor is record 209 with 383. After a global
  z-score, validation S windows have mean |x| 0.262 and std 0.439, against N 0.404/0.712 —
  a small-amplitude, morphology-similar class. A 36k-parameter CNN optimising a softmax over
  1.7% prevalence does not allocate a region to it.
- **Weighting rescales the loss, it does not create features.** D1 raised S's weight 7.2× over
  N, yet the network still collapsed S. When a class is unreachable by the learned
  representation, re-weighting pushes the model towards other minority classes — which is
  exactly what happened to V.
- **Selection cannot select what never appears.** D2 could only choose among checkpoints whose
  S recall was already zero, so balancing the criterion harvested V instead.
- **Validation S is not estimable enough to steer training.** 61 windows in 4 records
  (record 100: 33, 210: 22, 108: 4, 103: 2) make validation S recall a near-binary signal with
  huge variance; a single record's behaviour dominates the score.

### 4.4 Test-set caveat, restated
93.2% of test S windows (1,382 of 1,483) come from record 232, which is absent from training.
Even a recovered S recall would mainly measure one record's morphology. Any future claim about
supraventricular detection must be qualified by this.

## 5. Limitations

- Two factors, one split, five seeds; this is a diagnostic, not a generalisation study.
- Test macro-F1 excludes F (support 0) and is dominated by Q's 2 windows being unlearnable.
- D1's weighted loss makes epoch-wise validation macro-F1 a noisy selection signal; the
  best-epoch distribution shows this, so D1's mean is less stable than its SD suggests.
- No D3 was run: both single-factor diagnostics failed to move S, so the precondition for a
  combined run (partial S recovery in each) was not met.
- These runs do not revise any Phase 4 conclusion; the frozen baseline remains the reported
  result.

## 6. Recommendation for G4

**Recommendation: G4 should not be passed on the present evidence, and the Phase 4 baseline
should be reported as executed-but-defective rather than replaced.**

Supporting reasoning:

1. The pipeline is sound: 30 baseline + 10 diagnostic fits, hashed checkpoints, verified
   frozen manifests, support-aware metrics, no train/test leakage.
2. The centralized reference model has 0.000 S recall on 1,483 test windows. Anchoring Phase 5
   FedAvg deltas or Phase 6 privacy–utility curves to it would propagate a class-blind model.
3. Both approved diagnostics are exhausted and both failed on S. The failure is structural
   (representation and validation support), not a tuning miss, so further loss/selection
   tweaks within the current protocol are unlikely to help.

Options for the research lead, in ascending scope:

- **A. Accept baseline as-is with documented limitation.** Proceed to Phase 5 treating S as a
  known non-learner; report S recall honestly in every later table.
- **B. Approve a targeted Phase 4 stage-7 ablation** addressing representational capacity and
  validation support — e.g. a class-conditioned sampler over training windows only, or a larger
  window/preprocessing review — as new pre-registered experiment IDs. This crosses the frozen
  preprocessing/split boundary only if preprocessing changes, which would require G3 review.
- **C. Revisit the G3 split** so validation S is not 4 records and test S is not 93% record 232.
  This invalidates Phase 3 approval and requires explicit re-approval.

I recommend **A or B, not C**, unless the defence requires defensible supraventricular
performance: C is the only option that makes S measurable, but it invalidates completed Phase 3
work and must be a deliberate research-lead decision rather than an implementation choice.

## 7. Reproduction

```
# D1
python -m scripts.run_phase4_diagnostics --experiment phase4_diag_d1_class_weighted \
  --output-dir <new dir> --device cuda
# D2
python -m scripts.run_phase4_diagnostics --experiment phase4_diag_d2_selection_balanced_accuracy \
  --output-dir <new dir> --device cuda
```

Artifacts on Drive:
- `.../diagnostics/phase4_diag_d1_class_weighted/20261115T125552Z/`
- `.../diagnostics/phase4_diag_d2_selection_balanced_accuracy/20261115T130019Z/`

Each contains `config.yaml`, `run_metadata.json` (environment, verified hashes, derived
weights, training counts), five `central_seed_*.json` reports with full epoch history and
confusion matrices, hashed checkpoints, and `summary.json`.
