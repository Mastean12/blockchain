# ECG Federated Learning Research Project

This project follows the research execution plan in `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md`.

Phases 0–3 are complete. Phase 4 is authorized and its baseline code is implemented. A one-batch CPU smoke test passed; the full five-seed centralized and local-only runs still need to be executed on the approved Colab GPU. G4 has not passed.

## Project objective

A Blockchain-Enabled Privacy-Preserving Federated Learning Framework for ECG Arrhythmia Classification under an AAMI-derived five-class taxonomy.

## Governance

- The authoritative specification is `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md`.
- All project changes must align with the stop/go gates and execution order in that document.
- The approved Phase 2 mapping and Phase 3 data manifests are frozen. Model training and evaluation remain governed by the Phase 4 gate and subsequent experiment approvals.

## Repository layout

```text
project-root/
├── MASTER_RESEARCH_EXECUTION_SPECIFICATION.md
├── README.md
├── pyproject.toml
├── requirements-lock.txt
├── .gitignore
├── configs/
├── data/
├── src/
├── tests/
├── experiments/
├── results/
├── docs/
├── scripts/
└── .venv/                  # Local virtual environment, not tracked
```

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
```

## Google Colab workflow

This project is designed to run in a Google Colab runtime with a dedicated GPU. Use the repository as a mounted working directory. Check the existing CUDA-enabled PyTorch runtime before installing packages; do not blindly replace Colab's GPU build of PyTorch.

```python
# Example Colab setup from the project root
!python --version
!nvidia-smi
!python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

For a drive-mounted repo:

```python
from google.colab import drive
drive.mount('/content/drive')
# then work from /content/drive/MyDrive/.../blockchain
```

Run the approved Phase 4 CNN smoke test first, then the full five-seed baseline sweep:

```python
!python -m scripts.run_phase4_baselines --smoke-test --device cuda
!python -m scripts.run_phase4_baselines --device cuda
```

The full command runs five centralized and 25 local-only fits. It refuses to overwrite an existing output directory and does not fall back to CPU if CUDA is unavailable. See [Phase 4 baseline protocol](docs/PHASE4_BASELINE_PROTOCOL.md) and [the approved config](configs/models/phase4_cnn_v1.yaml).

## Data setup (required before running anything)

Raw MIT-BIH files and processed arrays are **not** in this repository. `.gitignore` excludes
`data/raw/`, `data/processed/` and all `.npy` files. A fresh clone therefore has code, configs,
documentation and frozen *manifests* only.

To make a clone runnable:

1. Download the MIT-BIH Arrhythmia Database v1.0.0 into `data/raw/mit-bih-arrhythmia-database-1.0.0/`.
   Verify it against `docs/data_and_labels/MITBIH_v1.0.0_SHA256SUMS.csv`.
2. Rebuild the frozen split and processed arrays (deterministic, seed 42):

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.preprocess_mitdb_phase3
   ```

   This must reproduce the frozen hashes
   `bbcfa25c7f0e0d903a6de44ccbaa6eb3fa0716253ff1ea730c912f99534d6f96` (split) and
   `71dbcac37e2a605d5edcd0ce280acec60068a1f1defb4f403bc32a5e1cb8eba3` (clients).
   The loader refuses to train if they differ.
3. Rebuild the Phase 5 partitions (deterministic; refuses to overwrite differing content):

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.build_phase5_partitions
   ```

Alternatively, copy `data/processed/phase3/` and `data/raw/` from an existing machine.

## Running the experiments locally on a GPU

Both experiment families are plain CLI entry points and do not require Colab.

```powershell
# Phase 4 baselines (30 fits: 5 centralized + 25 local-only)
.\.venv\Scripts\python.exe -m scripts.run_phase4_baselines --device cuda

# Phase 4 diagnostics
.\.venv\Scripts\python.exe -m scripts.run_phase4_diagnostics `
    --experiment phase4_diag_d1_class_weighted --device cuda

# Phase 5 federated conditions
.\.venv\Scripts\python.exe -m scripts.run_phase5_federated `
    --experiment phase5_f3_fedavg_severe `
    --output-dir experiments/logs/phase5/phase5_f3_fedavg_severe/manual --device cuda
```

Both refuse to run on a device they cannot use (no silent CPU fallback), refuse to overwrite an
existing output directory, and support resume. `--seed N` runs a single seed.

Approved Phase 5 hyperparameters, already recorded in every config: 50 rounds, 2 local epochs,
all five clients each round, FedProx `proximal_mu` 0.01, BatchNorm buffers aggregated weighted
by sample count, optimizer state reset each round.

Run cost: measured 98 s/round on CPU for five clients. On a consumer GPU expect roughly
20â€“50x faster. One condition (5 seeds x 51 rounds) is the unit of work.

## Validation

Run focused validation with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\python.exe -m scripts.create_phase3_splits
.\.venv\Scripts\python.exe -m scripts.preprocess_mitdb_phase3
```

These commands validate the mapping, regenerate the deterministic split, and rebuild the processed arrays. They do not train a model.

## Current status

Status: Phases 0–3 are complete and G3 passed. Phase 4 baseline implementation is in progress; the full GPU experiments have not run, and G4 has not passed. The approved split and preprocessing manifests remain frozen.

Important Phase 3 limitation: Q is absent from validation and F is absent from test. Those class-specific metrics are not estimable for the affected partitions; the split was not redrawn to improve metrics.

Project documents:
- [Literature review](docs/literature/LITERATURE_REVIEW.md)
- [Reference register](docs/literature/REFERENCES.md)
- [Approved research protocol](docs/protocol/RESEARCH_PROTOCOL.md)
- [MIT-BIH provenance](docs/data_and_labels/DATA_PROVENANCE.md)
- [AAMI mapping and approval report](docs/data_and_labels/AAMI_MAPPING_AND_EXCLUSIONS.md)
- [Approved mapping configuration](configs/data/aami5_mapping_v1.yaml)
- [Phase 3 split policy and preprocessing audit](docs/data_and_labels/SPLIT_POLICY.md)
- [Frozen split manifest](data/splits/phase3_split_manifest.json)
- [Training-client manifest](data/splits/client_manifests.json)
- [Preprocessing audit report](docs/data_and_labels/PHASE3_PREPROCESSING_AUDIT.json)
- [Phase 3 final split evaluation](docs/PHASE_3_FINAL_EVALUATION.md)
- [Phase 4 baseline protocol](docs/PHASE4_BASELINE_PROTOCOL.md)
- [Approved Phase 4 CNN config](configs/models/phase4_cnn_v1.yaml)
- [Phase 4 execution status](docs/PHASE4_EXECUTION_STATUS.md)
- [Phase 4 diagnostic ablation protocol](docs/PHASE_4_DIAGNOSTIC_ABLATION.md)
- [Phase 4 diagnostic ablation results](docs/PHASE4_DIAGNOSTIC_ABLATION_RESULTS.md)
- [Phase 4 S-class failure investigation](docs/PHASE_4_S_CLASS_FAILURE_INVESTIGATION.md)
- [Phase 5 implementation plan](docs/PHASE_5_IMPLEMENTATION_PLAN.md)
- [Phase 5 execution status](docs/PHASE_5_EXECUTION_STATUS.md)
- [Phase 5 manifest audit](docs/PHASE_5_MANIFEST_AUDIT.md)
- [Phase 5 results snapshot](docs/phase5_results/phase5_results_partial.json)
- [New machine runbook](docs/NEW_MACHINE_RUNBOOK.md)
- [Federated configs](configs/federated/)
- [Phase 5 frozen partitions](data/splits/phase5/)
