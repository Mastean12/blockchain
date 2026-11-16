# Phase 4 Execution Status

**Last updated:** 15 November 2026  
**Baseline execution:** Complete — all 30 approved fits finished on a Colab Tesla T4  
**Diagnostic ablation:** Complete — D1 and D2 executed; neither recovered class S  
**G4 gate:** NOT passed — recommendation submitted for research-lead review  
**G3 split:** Frozen and unchanged; no manifest, config or recipe modifications  
**Phase 5:** Not started and not authorized

This document separates two distinct facts:

1. **Phase 4 baseline execution completed.** The approved 30-fit sweep ran to completion and
   produced valid artifacts.
2. **G4 is not approved.** The completed baseline does not meet the master specification's
   requirement that the non-private baseline be trustworthy.

## Baseline execution record

- 30/30 fits complete: `central_seed_{42..46}` and `client_01..05_seed_{42..46}`.
- Output: Colab Drive
  `experiments/logs/phase4/colab_full_20261113/full_run/`.
- Environment: Tesla T4, CUDA 13.0, torch 2.14.1+cu130, Python 3.13.16.
- Frozen hashes verified at runtime: split `bbcfa25c7f0e0d903a6de44ccbaa6eb3fa0716253ff1ea730c912f99534d6f96`,
  client `71dbcac37e2a605d5edcd0ce280acec60068a1f1defb4f403bc32a5e1cb8eba3`,
  config `3d03ff3993b7c9c3fb8bab57f90a65b94fb2690c7e63ce0962ac1706f648593b`.
- GPU smoke test passed before the sweep: finite loss 1.6337, logits `(256, 5)`,
  `cnn_validation_used_for_selection: false`, `cnn_test_used_for_evaluation: false`.
- Test class support N/S/V/F/Q = 13099 / 1483 / 461 / **0** / 2. Test F is not estimable.

### Centralized baseline results, 5 seeds

| Metric | Value |
|---|---|
| Validation accuracy | 0.9419 |
| Validation macro-F1 (N/S/V/F) | 0.3667 |
| Test accuracy | 0.8510 ± 0.0348 |
| Test macro-F1 (N/S/V/Q) | 0.2990 ± 0.0600 |
| Test weighted-F1 | 0.8085 |
| S-class test recall | **0.000 in all five seeds** |

### Per-client local-only results, 5 seeds each

| Client | Val acc | Val macro-F1 | Test acc ± SD | Test macro-F1 ± SD |
|---|---:|---:|---:|---:|
| client_01 | 0.9434 | 0.3687 | 0.8958 ± 0.0051 | 0.4598 ± 0.0285 |
| client_02 | 0.7657 | 0.2884 | 0.7075 ± 0.1460 | 0.2721 ± 0.0522 |
| client_03 | 0.9434 | 0.3224 | 0.8493 ± 0.0339 | 0.2297 ± 0.0049 |
| client_04 | 0.9433 | 0.3043 | 0.8668 ± 0.0058 | 0.2462 ± 0.0177 |
| client_05 | 0.7846 | 0.2832 | 0.8143 ± 0.0297 | 0.3279 ± 0.0270 |

## Why G4 is not passed

The centralized model never predicts S despite 1,483 test S windows. Accuracy near 0.85 is
carried by class N (87% of test windows).

Established cause, from the frozen artifacts:

- training S support is 1,237 of 71,927 windows (1.7%);
- validation S support is 61 windows, of which 33 come from record 100 and 22 from record 210;
- test S support is 1,483 windows, of which **1,382 (93.2%) come from record 232**, absent
  from training;
- the approved loss is unweighted cross-entropy with no class weights or oversampling, and
  checkpoint selection is validation macro-F1.

Under those conditions a minority class at 1.7% prevalence has no pathway to be learned or
to be selected for. This is a property of the approved recipe interacting with the frozen
split, not a software fault. The loader verified `train ∩ test = ∅`, so it is not leakage.

## Diagnostic ablation (approved Option 1)

Protocol frozen before execution in
[`docs/PHASE_4_DIAGNOSTIC_ABLATION.md`](PHASE_4_DIAGNOSTIC_ABLATION.md).

| ID | Change | Status |
|---|---|---|
| `phase4_diag_d1_class_weighted` | sqrt-tempered balanced class weights from training counts only | Executed 15 Nov 2026 on T4; S recall 0.000 in all 5 seeds |
| `phase4_diag_d2_selection_balanced_accuracy` | unweighted loss, validation balanced-accuracy selection | Executed 15 Nov 2026 on T4; S recall 0.000 in all 5 seeds |
| D3 combined | deliberately not run | Precondition (partial S recovery in both) not met |

Results, per-class tables and interpretation:
[`docs/PHASE4_DIAGNOSTIC_ABLATION_RESULTS.md`](PHASE4_DIAGNOSTIC_ABLATION_RESULTS.md).

Summary: both diagnostics improved **V** recall (0.251 → 0.925 for D1, 0.797 for D2) and test
macro-F1 over N/S/V/Q (0.2990 → 0.3403 / 0.3207), but left **S recall at exactly 0.000 in every
fit**. D1 also lost N recall (0.969 → 0.903) and accuracy (0.8510 → 0.8142). D2 produced the
tightest seed spread (SD 0.0189 vs 0.0600 baseline).

Interpretation: the S failure is structural — a small-amplitude class at 1.7% training
prevalence, with validation S confined to 61 windows across 4 records — not a loss-weighting or
selection-metric defect. Re-weighting redirected capacity to V rather than to S.

### S-class representation and distribution-shift investigation

Completed 15 November 2026, no model training:
[`docs/PHASE_4_S_CLASS_FAILURE_INVESTIGATION.md`](PHASE_4_S_CLASS_FAILURE_INVESTIGATION.md).

Findings:

- **Distribution shift is not the primary cause.** Record 232 (93.2% of test S) sits inside the
  training S manifold: scaled centroid distance 0.25–0.45 against a median within-training
  S-record separation of 2.28.
- **The failure precedes test.** A simple N/S/V linear model fit on training data also scores
  S recall 0.000 on validation, which is where checkpoints are selected. Validation S is 61
  windows in 4 records and the lowest-amplitude S population in the dataset.
- **S is partly learnable.** The same linear model reaches S recall 0.13–0.58 on held-out
  training S records, and 1.00 in-sample, so the class is not unrepresentable.
- **Architecture compounds it.** S→N centroid separation ratio is 0.20, and global average
  pooling discards exactly the intraband shape that separates S from N.
- **Window boundaries and normalisation are ruled out as primary causes** (S energy is
  well-contained; <1% of test S windows have their peak near a window edge).

Recommended decision for review: treat this as two components — an unrepresentative
validation population for S and an architecture that cannot separate S from N — and consider a
pre-registered selection/architecture ablation (option A), or accept the limitation (option B).
Revisiting the split (option C) is not supported by the evidence.

## G4 criteria assessment

| Master-spec G4 evidence | Status | Evidence / blocker |
|---|---|---|
| Majority baseline | Passed | Frozen validation/test arrays |
| Centralized CNN, 5 seeds | Executed, result not trustworthy | 30-fit sweep complete; S recall 0.000 |
| Local-only models, 25 fits | Executed | Per-client table above |
| Metrics and checkpoint selection validated | Passed | Support-aware metrics, null for absent classes, hashed checkpoints |
| Repeated seeds | Passed | 5 seeds per condition, SD reported |
| Initial FL runs | Not run; out of authorized scope | Phase 5 not started |

**Gate decision:** G4 is **not passed**. Baseline execution is complete and documented; the
centralized model fails to learn a supported minority class; and both approved diagnostics
failed to recover it. The master gate additionally expects initial FL evidence that belongs to
Phase 5.

### G4 recommendation submitted for research-lead review

Report the Phase 4 baseline as **executed but defective**, not as replaced. The pipeline is
sound and the defect is structural, so neither further loss tuning nor further selection tuning
within the current protocol is expected to help.

| Option | Scope | Assessment |
|---|---|---|
| A. Accept with documented limitation | None; carry S as a known non-learner into Phase 5 | Lowest cost; honest reporting only |
| B. Targeted stage-7 ablation (representational capacity or training-only sampler) | New pre-registered experiment IDs; changes preprocessing only if a window/preprocessing review is chosen | Recommended if some S performance is required |
| C. Revisit the G3 split (validation S in 4 records; test S 93% record 232) | Invalidates Phase 3 approval | Only option that makes S measurable; requires explicit re-approval |

## Metric limitations

The frozen split has no validation Q examples and no test F examples. Q validation and F test
metrics are not estimable and remain `null`. Validation selection uses N/S/V/F only. Test
macro metrics cover only classes with true test support and must state that class set; they
must not be described as five-class test macro-F1. Test S support is concentrated in one
record, so test S recall is not evidence of generalizable supraventricular performance.

## Next steps (not started)

1. Research lead reviews the G4 recommendation above (options A/B/C).
2. Record the decision and any approved follow-up experiment IDs.
3. Do not begin Phase 5 until G4 disposition is recorded.

No Phase 5, privacy, encryption, blockchain or robust-aggregation work is authorized.
