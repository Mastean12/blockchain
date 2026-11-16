# Phase 4 Baseline Protocol

**Status:** Phase 4 authorized; implementation validated locally; baseline execution complete on Colab GPU, G4 not passed  
**Training status:** Majority baseline, CPU and GPU smoke tests passed; all 30 centralized and local-only fits completed (5 seeds each)  
**Split:** Frozen G3 split retained; no candidate split adopted  
**Approval date:** 13 November 2026  
**Execution date:** 15 November 2026 (Colab Tesla T4)

## Approved experiment

The research lead approved the configuration in [phase4_cnn_v1.yaml](../configs/models/phase4_cnn_v1.yaml):

- Mandatory training-majority baseline.
- `compact_cnn_v1`: input `(batch, 1, 253)`; Conv1d channels 32/64/128 and kernel sizes 7/5/3; BatchNorm1d and ReLU; max-pooling after the first two blocks; adaptive average pooling; dropout 0.3; linear five-class head; 36,357 trainable parameters.
- AdamW, learning rate 0.001, weight decay 0.0001, unweighted cross-entropy, batch size 256, maximum 50 epochs. No class weights or augmentation.
- The same architecture and training recipe for centralized and local-only runs. Local models use only the assigned client's training records; the frozen validation split is used for checkpoint selection.
- Full-run seeds: 42, 43, 44, 45, 46. Run and inspect the one-batch CNN smoke test before the full sweep.
- Evaluate epoch 0. Select the earliest checkpoint attaining the highest validation macro-F1 over N/S/V/F; early stop after eight epochs without an improvement in that score.

## Metric policy for the retained split

- Validation Q support is zero. Q per-class validation metrics are not estimable and are excluded from the validation checkpoint-selection average.
- Test F support is zero. F test metrics are not estimable. Test averages use only classes with true test support and must state that class set; do not call this five-class test macro-F1.
- Report the fixed-order N/S/V/F/Q confusion matrix and support counts. Do not replace undefined metrics with zero.
- For any supported class with no predicted positives, precision is not estimable and is excluded from precision averages; recall and F1 follow the documented confusion-count formulas. The JSON result records the classes included in each average.

## Execution and artifacts

The intended execution environment is the user's Colab GPU runtime. From the project root, first verify `nvidia-smi`, then run:

```powershell
python -m scripts.run_phase4_baselines --smoke-test --device cuda
python -m scripts.run_phase4_baselines --device cuda
```

The smoke test checks one forward/backward/update batch and does not use CNN validation or test results for selection. It also writes the deterministic majority-baseline validation/test metrics. The full command runs five centralized fits and 25 local-only fits, selecting checkpoints only from validation and evaluating test after selection. CUDA is required unless CPU is explicitly requested; there is no silent fallback.
The [Colab launcher notebook](../experiments/phase4_colab_runner.ipynb) only verifies the selected runtime, checks required files, mounts Drive, and invokes this existing CLI. It does not duplicate training logic. The notebook normalizes Windows ZIP path separators and extracts the approved repository and processed arrays to `/content/blockchain-phase4`, leaving any previous `/content/blockchain` contents untouched.

Each unique run directory under `experiments/logs/phase4/` contains the exact config and its hash, verified split/client/preprocessing hashes, environment metadata, epoch histories, per-seed metrics, and selected state-dict checkpoints with SHA-256 hashes. The runner refuses to overwrite an existing output directory.

For persistent Colab results, mount Google Drive and set `--output-dir` to a new directory on that mounted drive. On the first full-run invocation, omit `--resume`; if interrupted, use the same path and add `--resume`. Resume requires an unchanged config, G3 artifacts, and execution environment. It verifies saved checkpoints and reuses completed fits; an incomplete fit restarts from its seed at epoch 0. A checkpoint without its completed fit report is preserved under `checkpoints/unverified/` before that fit is rerun. A completed report with a mismatched checkpoint hash is an explicit error. No optimizer state is checkpointed mid-fit.

The complete-run `summary.json` retains each seed/client result, summarizes validation and test scalar/per-class metrics with mean and standard deviation, summarizes confusion-matrix cells across runs, and records per-fit and aggregate execution times. Undefined class metrics remain `null`; support and class averaging sets are retained.

## Preliminary evidence

The fixed majority baseline predicts N, the training majority class. On the frozen arrays it achieved:

| Evaluation split | Support (N/S/V/F/Q) | Accuracy | Macro-F1 and classes included | Weighted F1 |
|---|---|---:|---|---:|
| Validation | 13,000 / 61 / 647 / 14 / 0 | 0.9474 | 0.2432 over N/S/V/F | 0.9218 |
| Test | 13,099 / 1,483 / 461 / 0 / 2 | 0.8707 | 0.2327 over N/S/V/Q | 0.8105 |

These are baseline results, not CNN results. Q validation and F test remain not estimable. The complete confusion matrices and per-class metrics are in the [smoke-run majority report](../experiments/logs/phase4/local_cpu_smoke_20261113c/majority_baseline.json). The [smoke metadata](../experiments/logs/phase4/local_cpu_smoke_20261113d/smoke_test.json) and [run metadata](../experiments/logs/phase4/local_cpu_smoke_20261113d/run_metadata.json) record the environment and frozen manifest/config hashes.

The CNN one-batch smoke test passed on local CPU on 13 November 2026: 256 training windows, logits shape `(256, 5)`, finite loss `1.6235155`, finite gradients, and one optimizer update. CNN validation/test data were not used by that smoke test.

On 15 November 2026 the approved GPU smoke test and the full 30-fit sweep ran to completion
on a Colab Tesla T4 (torch 2.14.1+cu130, CUDA 13.0). Centralized results: validation accuracy
0.9419, validation macro-F1 0.3667 (N/S/V/F), test accuracy 0.8510 ± 0.0348, test macro-F1
0.2990 ± 0.0600 (N/S/V/Q), weighted-F1 0.8085. **S-class recall was 0.000 in all five seeds**,
so the baseline is completed but not trustworthy as a reference model. The cause and the
approved controlled diagnostic ablation are documented in
[the Phase 4 diagnostic protocol](PHASE_4_DIAGNOSTIC_ABLATION.md) and
[the execution status](PHASE4_EXECUTION_STATUS.md).

Results are not claimed reproducible across different PyTorch releases or device types; see the [PyTorch reproducibility note](https://docs.pytorch.org/docs/2.15/notes/randomness.html).

## Gate status

Passing code tests and the smoke test are not sufficient to claim G4. Record the full-run metrics, seed variability, checkpoint hashes, class support, and limitations before judging the centralized and local-only baselines. The master gate table also requires initial FL evidence for G4, while the specification assigns FedAvg experiments to Phase 5 and this request prohibits starting Phase 5. Unless the research lead resolves that gate/phase dependency, G4 cannot be fully passed solely by completing the 30 Phase 4 fits. No privacy, encryption, blockchain, or robust-aggregation work is authorized by this protocol.
