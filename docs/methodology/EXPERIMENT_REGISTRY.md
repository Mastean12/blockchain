# Experiment Registry

Every executed condition for Phases 0–6, with configuration, partition, seeds, status and output
location. Hyperparameters and architecture are frozen in `configs/`; per-run metadata is written to
each output directory's `run_metadata.json`.

**Frozen identifiers (unchanged since G3):** split `bbcfa25c7f0e0d903a6de44ccbaa6eb3fa0716253ff1ea730c912f99534d6f96`,
client `71dbcac37e2a605d5edcd0ce280acec60068a1f1defb4f403bc32a5e1cb8eba3`,
Phase 4 config `phase4_cnn_v1.yaml`, preprocessing audit `5e363d0eb41747649d46442412dc2009fe93c5c220bb7e8a5d18003775d10025`.

---

## Phase 4 — Baselines (executed 15 Nov 2026, Colab Tesla T4)

| ID | Condition | Config | Seeds | Status | Output |
|---|---|---|---|---|---|
| B0 | Majority baseline | `configs/models/phase4_cnn_v1.yaml` | — | Complete | Phase 4 full run |
| B1 | Centralized CNN | same | 42–46 | Complete (S recall 0.000) | `experiments/logs/phase4/colab_full_20261113/full_run/` |
| B2 | Local-only × 5 clients | same | 42–46 | Complete | same |
| D1 | Class-weighted loss | `phase4_diag_d1_class_weighted.yaml` | 42–46 | Complete (S 0.000) | `.../diagnostics/phase4_diag_d1_class_weighted/` |
| D2 | Balanced-accuracy selection | `phase4_diag_d2_selection_balanced_accuracy.yaml` | 42–46 | Complete (S 0.000) | `.../diagnostics/...d2.../` |

**G4: PASSED 16 November 2026 with documented defect** (S recall 0.000 across all conditions).

### Phase 4 recovery and ablations (16 Nov 2026, local GTX 1650)

| ID | Condition | Config | Seeds | Status | Output |
|---|---|---|---|---|---|
| B1r | Centralized re-run (artefact recovery) | phase4_cnn_v1.yaml | 42–46 | Complete; reproduces frozen metrics within SD | experiments/logs/phase4/rerun_g4/ |
| A1 | Max+mean pooling architecture ablation | cnn1d_shape.py | 42–46 | Complete — **criterion not met** (2/5 seeds) | experiments/logs/phase4/a1_ablation/ |
| SEL | Selection-rule ablation | — | — | **Not run** — refuted by checkpoint evidence | PHASE_4_G4_RESOLUTION.md §3 |

## Phase 5 — Federated learning (F1/F2 Colab; F3/F4 local GTX 1650, 16 Nov 2026)

| ID | Condition | Partition | Seeds | Status | Output |
|---|---|---|---|---|---|
| F1 | FedAvg IID-like | `phase5_f1_iid_like` `7d635f51…` | 42–46 | Complete | `experiments/logs/phase5/f1` |
| F2 | FedAvg moderate α=0.5 | `phase5_f2_moderate` `c447d732…` | 42–46 | Complete | `experiments/logs/phase5/f2` |
| F3 | FedAvg severe α=0.1 | `phase5_f3_severe` `da8b96fa…` | 42–46 | Complete | `experiments/logs/phase5/f3` |
| F4 | FedProx μ=0.01 severe | `phase5_f3_severe` | 42–46 | Complete | `experiments/logs/phase5/f4` |
| F5 | FedProx moderate | `phase5_f2_moderate` | — | **Not run** (conditional rule not met) | — |

**G5: PASSED 16 November 2026.**

### Phase 5 G5 diagnosis — ablation A2 (16 Nov 2026, local GTX 1650)

| ID | Condition | Partition | Weighting | Seeds | Status | Output |
|---|---|---|---|---|---|---|
| A2-ctl | Validity control (reproduces frozen F3) | F3 severe | sample_count | 42–46 | Complete — **exact match on 5/5** | experiments/logs/phase5/a2_control/ |
| A2 | Aggregation-weighting ablation | F3 severe | **uniform** | 42–46 | Complete — mF1 0.3752 → 0.3364 | experiments/logs/phase5/a2_uniform/ |
| A2 | Aggregation-weighting ablation | F2 moderate | **uniform** | 42–46 | Complete — mF1 0.3079 → 0.3157 | experiments/logs/phase5/a2_uniform_f2/ |

Result: 54 % of the F3-over-F1 advantage is aggregation weight dispersion. See PHASE_5_G5_DIAGNOSIS.md.

## Phase 6 — Privacy (16 Nov 2026, local GTX 1650)

| ID | Condition | σ | ε (δ=1e-5) | Seeds | Rounds | Status | Output |
|---|---|---|---:|---:|---|---|---|
| Cal | Clip calibration, no noise | — | — | 42–46 | 50 | Complete | `experiments/logs/phase6/calibration/` |
| P1-ctl | Clip-only, no noise | — | n/a | 42 | 50 | Complete | `.../diagnostic/p0_ctl_unclipped/` |
| Diag | DP-only | 0.01 | 44,111.78 (R=8) | 42 | 8 | Complete | `.../diagnostic/sigma0.01/` |
| Diag | DP-only | 0.05 | 1,871.78 (R=8) | 42 | 8 | Complete | `.../diagnostic/sigma0.05/` |
| **P2** | HE-only (CKKS N=8192) | — | n/a (no DP) | 42–46 | 50 | Complete | `experiments/logs/phase6/p2/` |
| **P3-a** | HE+DP | 1.0 | 57.302 | 42–46 | 50 | Complete | `experiments/logs/phase6/p3a/` |
| **P3-b** | HE+DP | 2.0 | 22.020 | 42–46 | 50 | Complete | `experiments/logs/phase6/p3b/` |
| P1-a | DP-only | 0.5 | 166.04 (proj.) | — | 50 | **Not run** | — |
| P1-c | DP-only | 2.0 | 22.02 (proj.) | — | 50 | **Not run** (covered by P3-b) |
| P1-d | DP-only | 4.0 | 9.23 (proj.) | — | 50 | **Not run** | — |

Frozen hashes verified at load on every run. **G6: passed 16 Nov 2026 with documented scope limits.**

## Phases 7–10

Not started.
