# Continuing this project on a new machine

A short, ordered runbook for cloning to a machine with its own GPU and resuming Phase 5.

## 1. What the clone contains, and what it does not

Contains: all source, configs, tests, frozen *manifests* (JSON), documentation, and the Phase 5
results snapshot under `docs/phase5_results/`.

Does **not** contain: `data/raw/`, `data/processed/`, any `.npy` array, any checkpoint, or
`experiments/logs/`. `.gitignore` excludes all of these. This is deliberate: the raw database is
177 MB and the processed arrays are ~101 MB.

## 2. Set up

```powershell
git clone https://github.com/Mastean12/blockchain.git
cd blockchain
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
```

For an NVIDIA GPU, replace the CPU-only torch wheel if the lock installed one:

```powershell
python -m pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu124
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

## 3. Restore the data

Either copy from the old machine:

```
data/raw/mit-bih-arrhythmia-database-1.0.0/     (706 files)
data/processed/phase3/                          (15 .npy files)
```

Or rebuild from raw:

```powershell
.\.venv\Scripts\python.exe -m scripts.preprocess_mitdb_phase3
.\.venv\Scripts\python.exe -m scripts.build_phase5_partitions
```

Then prove the data is the frozen data:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

`tests/test_phase5_federated.py` and the Phase 4 loader both re-verify the frozen hashes; 54
tests must pass. If they fail with a hash mismatch, the processed arrays are not the approved
ones - stop and restore them properly.

## 4. Confirm where you are

| Phase | State |
|---|---|
| 0-3 | Complete, G3 passed |
| 4 | Executed in full. G4 NOT passed (S recall 0.000) |
| 5 | F1 and F2 complete (5 seeds each). **F3, F4 not run.** F5 conditional |
| 6-10 | Not started |

Read, in this order, before changing anything:

1. `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` - authoritative rules and gates
2. `docs/PHASE_5_EXECUTION_STATUS.md` - exact state and results so far
3. `docs/PHASE_5_IMPLEMENTATION_PLAN.md` - approved design and the approved hyperparameters
4. `docs/PHASE4_EXECUTION_STATUS.md` - why G4 failed
5. `docs/PHASE_4_S_CLASS_FAILURE_INVESTIGATION.md` - why S fails, with evidence

## 5. Resume Phase 5

`--seed N` runs one seed at a time, which is the safest way to work through a long queue.
`--resume` continues an interrupted seed from its last completed round.

```powershell
# F3 severe skew, one seed at a time
.\.venv\Scripts\python.exe -m scripts.run_phase5_federated `
    --experiment phase5_f3_fedavg_severe `
    --output-dir experiments/logs/phase5/f3 --seed 42 --device cuda

# then 43, 44, 45, 46 with the same --output-dir
```

If a seed is interrupted:

```powershell
.\.venv\Scripts\python.exe -m scripts.run_phase5_federated `
    --experiment phase5_f3_fedavg_severe `
    --output-dir experiments/logs/phase5/f3 --seed 42 --device cuda --resume
```

Then F4 (FedProx, severe), then decide on F5 from the F4 result:

```powershell
.\.venv\Scripts\python.exe -m scripts.run_phase5_federated `
    --experiment phase5_f4_fedprox_severe `
    --output-dir experiments/logs/phase5/f4 --seed 42 --device cuda
```

Rules that the CLI enforces and you should not work around:

- No silent CPU fallback. `--device cuda` fails loudly if CUDA is unavailable.
- A condition with 5 completed seeds cannot be re-run; a new timestamped directory is created
  instead, which would duplicate results. Use `--seed` rather than re-running a finished seed.
- Output directories are never overwritten.
- Validation selects the round; test is evaluated once per seed. The config gate also rejects
  any change to the approved hyperparameters.

## 6. Budget

Measured on CPU: 98 s per round for five clients. On a consumer GPU expect roughly 20-50x
faster.

| Work | Rounds | Estimate (GPU) |
|---|---|---|
| One seed | 51 | ~3-5 min |
| One condition (5 seeds) | 255 | ~20-30 min |
| F3 + F4 + F5 | 765 | ~1-1.5 h |

Colab exhausted its free compute units partway through F3; a local GPU has no such limit.

## 7. After the runs

Send back or commit the per-seed `run_summary.json` files. The remaining deliverables are
`docs/PHASE_5_RESULTS_AND_ANALYSIS.md` (with the FedAvg/FedProx comparison against centralized
and local-only baselines) and a G5 assessment. G5 must not be declared passed on partial
evidence, and G4 remains not passed regardless of Phase 5 results.
