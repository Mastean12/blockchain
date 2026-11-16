# Phase 5 - Execution Status

**Last updated:** 16 November 2026  
**Stage:** Stage B **partially executed** - 2 of 5 conditions complete  
**G4:** NOT PASSED (unchanged, not retrospectively revised)  
**G5:** **not assessable yet** - severe-skew and FedProx conditions not run  
**Phase 6:** not started

---

## 0. Where execution stands

| Condition | Method | Partition | Seeds | Status |
|---|---|---|---|---|
| `phase5_f1_fedavg_iid_like` | FedAvg | frozen IID-like manifest | 5/5 | **Complete** |
| `phase5_f2_fedavg_moderate` | FedAvg | Dirichlet alpha=0.5 | 5/5 | **Complete** |
| `phase5_f3_fedavg_severe` | FedAvg | Dirichlet alpha=0.1 | 0/5 | **Not run** - Colab compute units exhausted |
| `phase5_f4_fedprox_severe` | FedProx mu=0.01 | Dirichlet alpha=0.1 | 0/5 | **Not run** |
| `phase5_f5_fedprox_moderate` | FedProx mu=0.01 | Dirichlet alpha=0.5 | 0/5 | Conditional on F4 |

Approved hyperparameters, applied and recorded in every config: 50 rounds, 2 local epochs, all
five clients every round, FedProx `proximal_mu` 0.01, BatchNorm buffers weighted by sample
count, optimizer state reset each round.

## 0.1 Results obtained so far

| Condition | Test acc (mean +/- SD) | Test macro-F1 (mean +/- SD) | S recall | Seeds selecting round 3 |
|---|---|---|---|---|
| Phase 4 centralized (reference) | 0.8510 +/- 0.0348 | 0.2990 +/- 0.0600 | 0.000 in all 5 | n/a |
| F1 FedAvg IID-like | 0.7861 +/- 0.0223 | 0.3040 +/- 0.0146 | 0.000 in 4 of 5 (1 seed: 0.0007) | 1 of 5 |
| F2 FedAvg moderate | 0.8061 +/- 0.0363 | 0.3079 +/- 0.0299 | 0.000 in all 5 | **4 of 5** |

Per-seed detail is in `docs/phase5_results/phase5_results_partial.json`; the machine-readable
comparison is `docs/phase5_results/phase5_comparison.csv`.

### Observations recorded so far (not yet conclusions)

1. **Federated accuracy trails centralized** (0.786 / 0.806 vs 0.851) while macro-F1 is
   comparable (0.304 / 0.308 vs 0.299). The macro-F1 metric covers N/S/V/Q only.
2. **S recall remains 0.000** in all ten federated runs. Federated learning has not changed the
   Phase 4 S-class limitation. This is consistent with the S-class investigation finding that
   the failure is a validation-population and representation problem, not a training-topology
   problem.
3. **Client drift is visible.** In F2, four of five seeds selected round 3 and validation loss
   then rose steadily (for example seed 46: 0.57 at round 3 to 1.05 at round 50) while
   validation macro-F1 stayed flat. This is the condition FedProx is designed to address, which
   makes F4 the most informative remaining run.
4. Moderate label skew did not reduce aggregate accuracy relative to IID-like, but it reduced
   the number of seeds reaching a late selected round (1 of 5 to 4 of 5 selecting round 3).

---

## 1. Stage A summary

| Requirement | Status |
|---|---|
| Mandatory reading completed | Done — master spec Stages 4–7, research protocol, split policy, Phase 4 execution/diagnostic/investigation reports |
| Existing FL implementation inspected | Done — `src/federated/` and `src/aggregation/` were **empty placeholders**; no FL code existed |
| Client training and aggregation logic verified | Implemented and tested (20 new tests) |
| Reproducible configurations and seeds | Configs created; seeds 42–46 fixed; **four hyperparameters pending approval** |
| Rounds / local epochs / participation defined | **NOT defined — requires approval (D1–D3)** |
| Convergence and communication metrics defined | Defined in the plan, implemented in code |
| Automated tests: aggregation, isolation, integrity | 20 tests, all passing |
| Implementation plan | `docs/PHASE_5_IMPLEMENTATION_PLAN.md` |
| Client partition manifests | Built and frozen (3 partitions, hashed) |

## 2. Frozen artefacts preserved

| Artefact | Hash | Changed? |
|---|---|---|
| Split manifest | `bbcfa25c7f0e0d903a6de44ccbaa6eb3fa0716253ff1ea730c912f99534d6f96` | No |
| Client manifest | `71dbcac37e2a605d5edcd0ce280acec60068a1f1defb4f403bc32a5e1cb8eba3` | No |
| Phase 4 config | `3d03ff3993b7c9c3fb8bab57f90a65b94fb2690c7e63ce0962ac1706f648593b` | No |
| Phase 4 results (30 fits + 10 diagnostics) | unchanged | No |
| Preprocessing audit | `5e363d0eb41747649d46442412dc2009fe93c5c220bb7e8a5d18003775d10025` | No |

Phase 5 adds new files only. `src/training/phase4*.py` are imported, never modified.

## 3. New Phase 5 partitions (frozen, hashed)

| ID | Family | Manifest SHA-256 | Purpose |
|---|---|---|---|
| `phase5_f1_iid_like` | frozen client manifest | `7d635f51c966fd47dbfa8db960aa27f23d66dc514dc28113842bf2271e54c0a2` | F1 baseline |
| `phase5_f2_moderate` | record-group Dirichlet α=0.5, seed 42 | `c447d732cb9e886b87db10b50bec8ec3df9944458198162f920b8966413a02d3` | F2 moderate skew |
| `phase5_f3_severe` | record-group Dirichlet α=0.1, seed 42 | `da8b96fa118e53bf53bee50b4f56bb6c281c65093b3c690058664f7b0cf8bbd4` | F3 severe skew |

Class support derived from the frozen arrays (not from the Phase 3 manifest's stored counts):

| Partition | Client | Records | Samples | N | S | V | F | Q | Absent |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| F1 | client_01 | 6 | 12,887 | 11,131 | 337 | 1,040 | 377 | 2 | — |
| F1 | client_02 | 6 | 13,625 | 11,673 | 68 | 1,520 | 364 | 0 | Q |
| F1 | client_03 | 6 | 14,480 | 13,181 | 118 | 1,154 | 22 | 5 | — |
| F1 | client_04 | 7 | 16,266 | 14,740 | 320 | 1,180 | 22 | 4 | — |
| F1 | client_05 | 6 | 14,669 | 13,264 | 394 | 1,006 | 3 | 2 | — |
| F2 | client_01 | 9 | 20,847 | 18,465 | 528 | 1,480 | 374 | 0 | Q |
| F2 | client_02 | 5 | 12,494 | 10,437 | 106 | 1,553 | 391 | 7 | — |
| F2 | client_03 | 6 | 13,603 | 12,321 | 293 | 981 | 4 | 4 | — |
| F2 | client_04 | 6 | 13,866 | 12,108 | 244 | 1,511 | 3 | 0 | Q |
| F2 | client_05 | 5 | 11,117 | 10,658 | 66 | 375 | 16 | 2 | — |
| F3 | client_01 | 11 | 26,685 | 23,225 | 951 | 2,464 | 45 | 0 | Q |
| F3 | client_02 | 7 | 14,780 | 13,162 | 42 | 1,192 | 377 | 7 | — |
| F3 | client_03 | 3 | 6,260 | 5,894 | **3** | 363 | **0** | 0 | **F, Q** |
| F3 | client_04 | 5 | 11,149 | 10,284 | 203 | 657 | 1 | 4 | — |
| F3 | client_05 | 5 | 13,053 | 11,424 | 38 | 1,224 | 365 | 2 | — |

F3 delivers the required severe condition: one client has 3 S windows, another has no F or Q.

## 4. Verification performed

- **54 tests pass** (34 Phase 4 + 20 Phase 5).
- Aggregation: closed-form weighted mean, equal-weight identity, single-client identity,
  `num_batches_tracked` summed not averaged, empty-set and key-mismatch rejection.
- Isolation: no record in two clients, no validation/test record ever assigned, union covers
  the frozen training records exactly, record groups never split.
- Manifests: deterministic hashing, tamper rejection, parent-split linkage.
- **End-to-end CPU smoke of the real FedAvg loop:** 2 rounds, 5 clients, validation macro-F1
  0.0019 (round 0) → 0.2453 → 0.2550, test accuracy 0.8504, macro-F1 0.3626, **S recall 0.000,
  F not estimable** — the Phase 4 limitation carries forward exactly as expected.
- **Resume reproduced an identical result** from the same seed.
- Config gate confirmed: running with `pending_approval` hyperparameters is rejected.

## 5. Decisions still required (blocking Stage B)

| # | Decision | Current state |
|---|---|---|
| D1 | Communication rounds | `pending_approval` in every config |
| D2 | Local epochs per round | `pending_approval` |
| D3 | Participation fraction | `pending_approval` |
| D4 | Partition construction method (α values already used to build F2/F3 manifests) | Proposed and built with Dirichlet α=0.5 / 0.1, seed 42 — **needs confirmation that this is the approved method**, because the manifests are now hashed and would need rebuilding if not |
| D4a | Keep 5 client identities for F2/F3 | Assumed yes |
| D4b | Accept natural class absence in severe skew rather than forcing it | Assumed yes |
| U1 | BatchNorm handling: running statistics weighted by sample count | Implemented; needs acknowledgement |
| U2 | Optimizer state reset each round | Implemented (standard FedAvg); needs acknowledgement |
| D5 | FedProx `proximal_mu` | `pending_approval` |

## 6. Defect found and handled (needs to be on record)

**The frozen Phase 3 client manifest's stored `class_counts` are inaccurate.** They do not
reconcile with the frozen label arrays, for every client:

| Client | Stored (N,S,V,F,Q) | Actual from arrays |
|---|---|---|
| client_01 | 11139, 337, 1040, 378, 2 | 11131, 337, 1040, 377, 2 |
| client_02 | 11678, 68, 1520, 364, 0 | 11673, 68, 1520, 364, 0 |
| client_03 | 13186, 118, 1155, 22, 5 | 13181, 118, 1154, 22, 5 |
| client_04 | 14743, 320, 1180, 22, 4 | 14740, 320, 1180, 22, 4 |
| client_05 | 13269, 394, 1006, 3, 2 | 13264, 394, 1006, 3, 2 |

Root cause is not yet established; the record-to-client assignment itself is correct and
complete (31 records, union exact). Phase 5 therefore **derives all class support from the
frozen arrays** and records it in its own partition manifests. The Phase 3 manifest is
**not modified**.

Impact on earlier phases: Phase 4 used the arrays for training, so its results are unaffected.
The Phase 3 documentation table in `SPLIT_POLICY.md` carries the inaccurate counts. A research
decision is needed on whether to correct that documentation (it is an approved artefact).

## 7. Stage B plan on approval

1. Fill D1–D3, D5 into the configs and re-freeze.
2. Run F1 (5 seeds) on Colab GPU, review before proceeding.
3. Run F2 and F3 (5 seeds each).
4. Run F4 (FedProx, severe) and F5 (FedProx, moderate) **only** if the F4 result justifies it.
5. Produce `docs/PHASE_5_RESULTS_AND_ANALYSIS.md`, then assess G5.

No Phase 6 work, no commits, and G4 remains not passed.
