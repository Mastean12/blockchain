# Reproducibility

Environment, commands and artifacts required to reproduce Phases 0–6.

---

## 1. Recorded environment

| Item | Value |
|---|---|
| OS | Windows 11 (10.0.26200) |
| CPU | AMD Ryzen 7 5700X, 8C/16T |
| RAM | 16 GB |
| GPU | NVIDIA GeForce GTX 1650, 4 GB, compute 7.5 |
| Driver / CUDA | 591.86 / CUDA 12.6 runtime (cu126 wheel) |
| Python | 3.12.10 |
| torch | 2.14.1+cu126 |
| numpy / scipy / scikit-learn | 2.5.5 / 1.18.1 / 1.9.1 |
| pandas / PyYAML / wfdb | 3.1.1 / 6.0.3 / 4.3.1 |
| opacus | 1.6.0 |
| tenseal | 0.3.18 (cp312 win_amd64) |
| pytest | 9.2.0 |

Phases 4 and 5 (F1, F2) were executed on Colab Tesla T4, CUDA 13.0, torch 2.14.1+cu130,
Python 3.13.16. Phase 5 (F3, F4) and all of Phase 6 ran on the local GTX 1650 above.

## 2. Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

If the default index installs a CPU-only torch wheel, replace it with the CUDA build:

```powershell
.\.venv\Scripts\python.exe -m pip install --force-reinstall "torch==2.14.1+cu126" `
    --index-url https://download.pytorch.org/whl/cu126
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

## 3. Data

Raw MIT-BIH and processed arrays are **not** in the repository (`.gitignore` excludes
`data/raw/`, `data/processed/`, `*.npy`).

1. Download MIT-BIH v1.0.0 into `data/raw/mit-bih-arrhythmia-database-1.0.0/`
   (archive SHA-256 `47b26926927c11bd9174154d367c811afc1b186f650f8a205931ca8c520f0a87`).
2. Verify all 705 files against `docs/data_and_labels/MITBIH_v1.0.0_SHA256SUMS.csv`.
3. Rebuild the frozen split and arrays:

```powershell
.\.venv\Scripts\python.exe -m scripts.create_phase3_splits
.\.venv\Scripts\python.exe -m scripts.preprocess_mitdb_phase3
.\.venv\Scripts\python.exe -m scripts.build_phase5_partitions
```

## 4. Frozen hashes that must reproduce

| Artifact | SHA-256 |
|---|---|
| Split manifest | `bbcfa25c7f0e0d903a6de44ccbaa6eb3fa0716253ff1ea730c912f99534d6f96` |
| Client manifest | `71dbcac37e2a605d5edcd0ce280acec60068a1f1defb4f403bc32a5e1cb8eba3` |
| Preprocessing audit | `5e363d0eb41747649d46442412dc2009fe93c5c220bb7e8a5d18003775d10025` |
| Phase 5 F1 partition | `7d635f51c966fd47dbfa8db960aa27f23d66dc514dc28113842bf2271e54c0a2` |
| Phase 5 F2 partition | `c447d732cb9e886b87db10b50bec8ec3df9944458198162f920b8966413a02d3` |
| Phase 5 F3 partition | `da8b96fa118e53bf53bee50b4f56bb6c281c65093b3c690058664f7b0cf8bbd4` |

The loaders re-verify these on every run and refuse to train on a mismatch.

## 5. Validation

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Expected: **93 passed, 1 skipped**. The skip is a CPU-only test, skipped when CUDA is present.

Committing note: the splits and processed arrays are regenerated deterministically from raw data;
the report's own manifest hash differs only in recorded `numpy_version` when the patch version
changes, while all 15 array hashes remain identical.

## 6. Running experiments

```powershell
# Phase 4 baselines (30 fits)
.\.venv\Scripts\python.exe -m scripts.run_phase4_baselines --device cuda

# Phase 4 diagnostics
.\.venv\Scripts\python.exe -m scripts.run_phase4_diagnostics `
    --experiment phase4_diag_d1_class_weighted --device cuda

# Phase 5 federated (one seed at a time; --resume continues)
.\.venv\Scripts\python.exe -m scripts.run_phase5_federated `
    --experiment phase5_f3_fedavg_severe `
    --output-dir experiments/logs/phase5/f3 --seed 42 --device cuda

# Phase 6 privacy
.\.venv\Scripts\python.exe -m scripts.run_phase6_privacy --experiment phase6_p2_he_only `
    --output-dir experiments/logs/phase6/p2 --device cuda
.\.venv\Scripts\python.exe -m scripts.run_phase6_privacy --experiment phase6_p3a_he_dp_sigma1.0 `
    --output-dir experiments/logs/phase6/p3a --device cuda
```

Rules enforced by the CLIs: no silent CPU fallback; no overwriting an existing output directory;
config gates reject changes to frozen hyperparameters; test data is read once per seed after the
selected round is fixed.

## 7. Determinism and randomness

- Seeds 42–46 throughout; `torch.use_deterministic_algorithms(True)`, cuDNN deterministic,
  `CUBLAS_WORKSPACE_CONFIG=:4096:8`.
- Phase 6 DP noise uses a seeded `torch.Generator` derived from `(seed, round, client)` — reproducible
  research mode, **not** a CSPRNG.
- CKKS key material is generated per run and never written to released artifacts.

## 8. Expected timings (GTX 1650)

| Work | Measured |
|---|---|
| Phase 5 one seed (51 rounds) | ≈450 s |
| Phase 6 calibration, one seed | ≈343 s |
| Phase 6 P2 HE-only, one seed | ≈336 s total (HE ≈12 s of it) |
| Phase 6 P3, one seed | ≈337 s |
| D-2 diagnostic, 8 rounds | ≈51 s |
