# Scripts

This directory contains operational, validation, and baseline-experiment scripts.

## Phase 4 baselines

Run these commands from the project root in a Colab runtime configured with a GPU. In VS Code, open the [Phase 4 launcher notebook](../experiments/phase4_colab_runner.ipynb), select **Colab** as the kernel provider, choose **Auto Connect**, and verify the connected server has a GPU before continuing. Make the project code, approved config, frozen manifests, and processed Phase 3 arrays available in the Colab server filesystem. Mount Google Drive and point output paths there so results survive runtime disconnection.

The smoke test performs one CNN update using training data; it does not select a checkpoint or evaluate the CNN on validation/test data. The fixed majority baseline is also evaluated on validation and test.

```powershell
python -m scripts.run_phase4_baselines --smoke-test --device cuda
python -m scripts.run_phase4_baselines --device cuda --output-dir /content/drive/MyDrive/blockchain/phase4_full_run
```

The full run uses the frozen Phase 3 split, the approved config, seeds 42–46, one centralized model per seed, and one local-only model per client per seed. Results include per-run JSON, checkpoints, execution progress, and a summary with per-class metrics, confusion-matrix mean/standard deviation, seed summaries, and measured fit times. The command refuses to overwrite an existing output directory and does not fall back to CPU when CUDA is requested.

If Colab disconnects, rerun with the same project/config, device environment, and output directory, adding `--resume`:

```powershell
python -m scripts.run_phase4_baselines --device cuda --output-dir /content/drive/MyDrive/blockchain/phase4_full_run --resume
```

Resume verifies the approved config and frozen manifest hashes, runtime environment, and hashes of saved checkpoints. It reuses complete verified fits and reruns an incomplete fit from its approved seed; it does not restore an optimizer mid-epoch. Do not change the config or input manifests to make a run resumable.

If a checkpoint exists without a completed per-fit report (for example, interruption between checkpoint and report persistence), resume preserves it under `checkpoints/unverified/` and reruns that fit. A completed report whose checkpoint hash does not match is an explicit error and is not silently replaced.

## Phase 4 diagnostics

Two controlled diagnostics diagnose the zero S-class recall in the centralized baseline. They do not modify the approved baseline.

```powershell
python -m scripts.run_phase4_diagnostics --experiment phase4_diag_d1_class_weighted --device cuda
python -m scripts.run_phase4_diagnostics --experiment phase4_diag_d2_selection_balanced_accuracy --device cuda
```

## Phase 5 federated learning

```powershell
python -m scripts.build_phase5_partitions
python -m scripts.run_phase5_federated --experiment phase5_f3_fedavg_severe --output-dir <dir> --device cuda
python -m scripts.run_phase5_federated --experiment phase5_f3_fedavg_severe --output-dir <dir> --seed 42 --device cuda
python -m scripts.run_phase5_federated --experiment phase5_f3_fedavg_severe --output-dir <dir> --seed 42 --device cuda --resume
```

Approved hyperparameters are recorded in every config and enforced by the config gate: 50 rounds, 2 local epochs, all five clients every round, FedProx proximal_mu 0.01. The runner writes per-round global and client metrics, aggregation weights, per-class metrics, communication volume, round duration and resume state. See [the Phase 5 implementation plan](../docs/PHASE_5_IMPLEMENTATION_PLAN.md).
