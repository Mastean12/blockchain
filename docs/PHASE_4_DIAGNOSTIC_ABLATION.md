# Phase 4 Diagnostic Ablation

**Status:** Protocol frozen before execution; results recorded after the diagnostic runs
**Scope:** Controlled diagnosis of the centralized baseline's zero S-class recall
**Parent experiment:** `phase4_cnn_v1` (frozen, unchanged)
**Approval:** Research lead, 15 November 2026, Option 1 (controlled diagnostic ablation)

---

## 1. Why this document exists

The frozen Phase 4 baseline completed all 30 approved fits. Its centralized results show
a defect that must be diagnosed rather than hidden:

- test accuracy 0.8510 ± 0.0348, but test macro-F1 only 0.2990 ± 0.0600;
- **S-class recall is 0.000 in every one of the five centralized seeds**;
- accuracy is dominated by class N, which is 13,099 of 15,045 test windows.

The S collapse originates in the interaction between three frozen facts, not in a code fault:

| Fact | Value |
|---|---|
| Training S support (1.7% of 71,927 windows) | 1,237 |
| Validation S support (0.44% of 13,722 windows) | 61, of which 33 come from record 100 and 22 from record 210 |
| Test S support (9.9% of 15,045 windows) | 1,483, of which 1,382 (93.2%) come from record **232**, a record with no analogue in the training set |
| Loss | unweighted cross-entropy, no class weights, no oversampling (approved recipe) |
| Checkpoint selection | validation macro-F1 over N/S/V/F |

A model trained with unweighted cross-entropy on 1.7% S prevalence, selected on a 61-beat
validation macro-F1, converges to the majority decision boundary and never predicts S.
This is the expected behaviour of the approved recipe, and it is why the baseline cannot
anchor later federated, privacy or robustness comparisons on its own.

## 2. What this ablation may and may not conclude

May conclude: whether class weighting and/or a different validation selection metric
change S-class behaviour under the same frozen split and the same architecture.

Must not conclude:
- that a successful ablation retrospectively validates or repairs the frozen baseline;
- that any diagnostic configuration is the approved Phase 4 baseline;
- that the ablation answers RQ2, or that its test numbers are comparable to the
  frozen baseline as a paired comparison, since the test set is dominated by one record;
- anything about class F on test, which remains unsupported (0 windows) and not estimable.

The frozen baseline stays the reported Phase 4 result. Diagnostics are exploratory.

## 3. Invariants preserved by every diagnostic

- G3 split manifest, client manifest and processed arrays are unchanged; hashes are
  re-verified by the same loader used by the baseline and must equal
  `bbcfa25c7f0e0d903a6de44ccbaa6eb3fa0716253ff1ea730c912f99534d6f96` and
  `71dbcac37e2a605d5edcd0ce280acec60068a1f1defb4f403bc32a5e1cb8eba3`.
- Architecture `compact_cnn_v1` (36,357 parameters), optimizer, learning rate, weight decay,
  batch size, epoch budget, patience, seeds 42–46 and determinism settings are unchanged.
- No augmentation, no oversampling, no synthetic beats, no resampling of validation or test.
- Test data is never used for selection, tuning or early stopping. Test is evaluated once
  per fit, after the checkpoint is chosen from validation only.
- Original 30 baseline runs, checkpoints and reports are untouched; diagnostics write to
  new directories with new experiment IDs.
- Absent classes stay `null` / not estimable; class support is reported with every metric.

## 4. Experiments

### D1 — `phase4_diag_d1_class_weighted`

**ID:** `phase4_diag_d1_class_weighted`
**Question:** Does class-weighted cross-entropy alone recover S-class learning?

**Class weights.** Derived exclusively from the training split label counts
(N 63,989 / S 1,237 / V 5,900 / F 788 / Q 13; total 71,927), never from validation or test:

```
balanced_c   = n_total / (n_classes * n_c)          # sklearn "balanced"
weight_c     = sqrt(balanced_c) / mean_c(sqrt(balanced_c))   # documented tempering
```

Resulting weights, rounded to six decimals and stored in the config:

| Class | Training support | Balanced weight | **D1 weight (sqrt-tempered)** |
|---|---:|---:|---:|
| N | 63,989 | 0.224811 | 0.055154 |
| S | 1,237 | 11.629264 | 0.396683 |
| V | 5,900 | 2.438203 | 0.181636 |
| F | 788 | 18.255584 | 0.497010 |
| Q | 13 | 1,106.569231 | 3.869517 |

**Rationale for tempering (fixed before execution).** Full balanced weights give Q a weight
of 1,106.57 derived from 13 training windows. With batch size 256 and a softmax loss, a single
Q window would dominate the gradient of its batch by roughly three orders of magnitude,
which is an unstable optimisation regime and would confound the diagnostic. The square-root
tempering is a monotone function of the inverse frequency, keeps every class ordered by
rarity, and limits the maximum weight to 3.87. This choice is made from training-label
counts only and before any result was observed; it is not tuned on validation or test.

**Everything else is identical to the baseline recipe**, including selection
(validation macro-F1 over N/S/V/F), patience 8, evaluate epoch 0, keep-earliest tie policy.

### D2 — `phase4_diag_d2_selection_balanced_accuracy`

**ID:** `phase4_diag_d2_selection_balanced_accuracy`
**Question:** Does the checkpoint-selection metric itself suppress S learning?

**Selection metric (fixed before execution):** validation **balanced accuracy** over the
classes supported in validation (N/S/V/F), computed from the validation confusion matrix as
the unweighted mean of per-class recall:

```
score = mean_{c in supported} recall_c = mean_c( TP_c / support_c )
```

**Rationale.** Macro-F1 is dominated by precision for rare classes. On a 61-beat validation
S support, a model that predicts S for a handful of rarely-correct windows loses precision
faster than it gains recall, so macro-F1 is flat or decreasing along the path that fixes S.
Balanced accuracy depends only on recall per class, and is exactly the quantity that the
baseline failed to move (S recall 0.000). It is support-independent up to the class set and
is computable without touching test data. Ties keep the earliest epoch, as in the baseline.

D2 uses **unweighted cross-entropy**, so it isolates the selection rule. Its loss remains
identical to the frozen baseline; only the checkpoint-selection score differs.

### D3 — combined diagnostic: deliberately not run

A combined D3 (class weights **and** balanced-accuracy selection) would confound the two
effects in a single condition. The master protocol's Stage 7 guidance is to change one
factor at a time and require evidence. Because D1 and D2 each isolate one factor, a
combined run only becomes justified if both individually show an S improvement but neither
reaches acceptable minority recall on its own. **Decision: not run now.** If that condition
arises after seeing the results, it must be proposed to the research lead as a new
pre-registered experiment rather than added post hoc to this document's conclusions.

## 5. Execution protocol

- Device: Colab Tesla T4 (`cuda`), required; no silent CPU fallback.
- Seeds: 42, 43, 44, 45, 46 (unchanged), one centralized fit per seed per experiment.
- Output directories, separate from the baseline:
  - `experiments/logs/phase4/diagnostics/phase4_diag_d1_class_weighted/<timestamp>/`
  - `experiments/logs/phase4/diagnostics/phase4_diag_d2_selection_balanced_accuracy/<timestamp>/`
- Each run writes: the exact config and its SHA-256, verified split/client/preprocessing
  hashes, environment metadata, per-epoch history, per-seed metrics, checkpoint and
  checkpoint SHA-256, and a `diagnostic_summary.json` with mean ± SD across seeds.
- No resume: a diagnostic directory is single-use; a rerun creates a new timestamped
  directory so no earlier result is overwritten.

## 6. Reporting requirements

For each diagnostic and for the frozen baseline reference, report at validation and test:

- accuracy;
- macro precision, recall and F1, with the exact included class set;
- weighted precision, recall and F1;
- per-class precision, recall, F1 and support for N/S/V/F/Q;
- the fixed-order confusion matrix;
- mean, standard deviation and each individual seed value.

Explicitly state that test F support is 0 and therefore test F metrics are not estimable.
Do not present a five-class test macro-F1; label the macro column with the classes included.

## 7. Results

**Executed 15 November 2026.** Outcome: neither diagnostic recovered class S; S recall was
0.000 in all 15 fits. Full tables, seed-level values and interpretation are in
[`PHASE4_DIAGNOSTIC_ABLATION_RESULTS.md`](PHASE4_DIAGNOSTIC_ABLATION_RESULTS.md).

The D3 precondition (partial S recovery in both D1 and D2) was not met, so the combined
diagnostic remains not run, as declared above.
