# Phase 5 — Results and Analysis

**Date:** 16 November 2026
**Execution host:** local workstation, NVIDIA GeForce GTX 1650 (compute 7.5), CUDA 12.6, torch 2.14.1+cu126, Python 3.12.10
**Conditions executed:** F1, F2 (previously on Colab Tesla T4), F3 and F4 (this host)
**Conditions not executed:** F5 — conditional rule not met (see §6)
**G5:** **PASSED 16 November 2026** after ablation A2 — see `PHASE_5_G5_DIAGNOSIS.md`
**G4:** **PASSED 16 November 2026** with documented defect — see `PHASE_4_G4_RESOLUTION.md`

This document supersedes the "Stage B partially executed" state of
`PHASE_5_EXECUTION_STATUS.md`. All Phase 4 material below is the previously frozen record and is
quoted, not recomputed.

---

## 1. What was run

| ID | Method | Partition | Seeds | Status |
|---|---|---|---|---|
| `phase5_f1_fedavg_iid_like` | FedAvg | frozen IID-like client manifest `7d635f51…` | 42–46 | Complete |
| `phase5_f2_fedavg_moderate` | FedAvg | record-group Dirichlet α=0.5, seed 42, `c447d732…` | 42–46 | Complete |
| `phase5_f3_fedavg_severe` | FedAvg | record-group Dirichlet α=0.1, seed 42, `da8b96fa…` | 42–46 | Complete (this host) |
| `phase5_f4_fedprox_severe` | FedProx μ=0.01 | same manifest as F3 | 42–46 | Complete (this host) |
| `phase5_f5_fedprox_moderate` | FedProx μ=0.01 | same manifest as F2 | — | **Not run** |

Frozen recipe, unchanged and enforced by the config gate on every run: `compact_cnn_v1`
(36,357 trainable parameters), 50 rounds, 2 local epochs, all five clients every round,
sample-count-weighted aggregation, BatchNorm buffers weighted by sample count,
`num_batches_tracked` summed, optimizer state reset each round, unweighted cross-entropy,
AdamW lr 1e-3 wd 1e-4, batch 256, checkpoint selection on validation macro-F1 over N/S/V/F with
epoch/round 0 evaluated and earliest kept on tie.

Every run re-verified the frozen hashes at load time: split `bbcfa25c…`, client `71dbcac3…`,
and the partition manifest named in the config.

## 2. Test-set class support (all conditions)

| Class | Support |
|---|---:|
| N | 13,099 |
| S | 1,483 |
| V | 461 |
| F | **0** |
| Q | 2 |

Test F is not estimable. Test macro metrics cover **N/S/V/Q only** and are not five-class test
macro-F1. Test S support is concentrated in record 232 (93.2%), so test S recall is not evidence
of generalisable supraventricular performance.

## 3. Per-seed results, F3 (FedAvg, severe skew)

| Seed | Selected round | Test acc | Test macro-F1 | Weighted F1 | S recall | V recall | V precision | Seconds |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 42 | 2 | 0.8728 | 0.3993 | 0.8306 | 0.000 | 0.9718 | 0.5074 | 444 |
| 43 | 44 | 0.8478 | 0.3582 | 0.8133 | 0.000 | 0.9675 | 0.3528 | 445 |
| 44 | 2 | 0.7878 | 0.3037 | 0.7758 | 0.000 | 0.9696 | 0.2030 | 471 |
| 45 | 24 | 0.8770 | 0.4074 | 0.8337 | 0.000 | 0.9675 | 0.5439 | 453 |
| 46 | 2 | 0.8763 | 0.4073 | 0.8331 | 0.000 | 0.9718 | 0.5430 | 451 |
| **Mean ± SD** | | **0.8523 ± 0.0380** | **0.3752 ± 0.0448** | | 0.000 | | | 453 |

## 4. Per-seed results, F4 (FedProx, severe skew)

| Seed | Selected round | Test acc | Test macro-F1 | Weighted F1 | S recall | V recall | V precision | Seconds |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 42 | 3 | 0.7599 | 0.2876 | 0.7592 | 0.000 | 0.9761 | 0.1694 | 512 |
| 43 | 3 | 0.8538 | 0.3673 | 0.8172 | 0.000 | 0.9740 | 0.3831 | 507 |
| 44 | 3 | 0.8053 | 0.3160 | 0.7864 | 0.000 | 0.9653 | 0.2318 | 510 |
| 45 | 3 | 0.8726 | 0.4001 | 0.8303 | 0.000 | 0.9696 | 0.5120 | 512 |
| 46 | 2 | 0.8150 | 0.3240 | 0.7924 | 0.000 | 0.9696 | 0.2521 | 506 |
| **Mean ± SD** | | **0.8213 ± 0.0440** | **0.3390 ± 0.0445** | | 0.000 | | | 509 |

## 5. Comparison across conditions

| Condition | Test acc (mean ± SD) | Test macro-F1 (mean ± SD) | S recall |
|---|---|---|---|
| Phase 4 centralized (frozen reference) | 0.8510 ± 0.0348 | 0.2990 ± 0.0600 | 0.000 in 5/5 |
| F1 FedAvg IID-like | 0.7861 ± 0.0223 | 0.3040 ± 0.0146 | 0.000 in 4/5 |
| F2 FedAvg moderate (α=0.5) | 0.8061 ± 0.0363 | 0.3079 ± 0.0299 | 0.000 in 5/5 |
| F3 FedAvg severe (α=0.1) | **0.8523 ± 0.0380** | **0.3752 ± 0.0448** | 0.000 in 5/5 |
| F4 FedProx severe (α=0.1) | 0.8213 ± 0.0440 | 0.3390 ± 0.0445 | 0.000 in 5/5 |

### 5.1 Paired FedProx − FedAvg differences on F3/F4 (same seeds, same partition)

| Metric | Mean Δ (FedProx − FedAvg) | SD | Naive 95% CI (t, df=4) | FedProx better in |
|---|---:|---:|---|---:|
| Test accuracy | −0.0310 | 0.0549 | −0.0992 … +0.0372 | 2 / 5 |
| Test macro-F1 | −0.0362 | 0.0573 | −0.1073 … +0.0350 | 2 / 5 |
| Weighted F1 | −0.0202 | 0.0348 | −0.0634 … +0.0230 | 2 / 5 |

Every interval includes zero. FedProx is *directionally* worse but the difference is not
separable from seed-to-seed variation at five seeds. The CI is descriptive only: the resampling
unit should be the record group, not the seed, so it must not be read as a confirmatory interval.

### 5.2 Matched-round comparison (removes checkpoint-selection noise)

Validation macro-F1 (N/S/V/F), mean over the five seeds:

| Rounds averaged | F3 FedAvg | F4 FedProx |
|---|---:|---:|
| 1–5 | 0.2662 | 0.2669 |
| 6, 10, 15, 20 | 0.2658 | 0.2652 |
| 40, 45, 50 | 0.2697 | 0.2669 |

At matched rounds the two methods are indistinguishable. The whole apparent test-set gap in
§5.1 comes from **which round validation happened to select**: F3 seeds mostly selected round 2
(three seeds) while F4 seeds mostly selected round 3 (four seeds). Best validation macro-F1 is
~0.28 in both conditions and the differences between adjacent rounds (typically 0.002–0.02) are
smaller than seed-to-seed variation.

## 6. Why F5 was not run

The pre-declared rule (`PHASE_5_IMPLEMENTATION_PLAN.md` §6, `PHASE_5_EXECUTION_STATUS.md` §7
item 4) is that F5 runs **only if F4 shows a meaningful FedAvg–FedProx difference worth
isolating**; otherwise it is not run and the omission is documented.

The rule is not met:

1. At matched rounds FedProx and FedAvg have effectively identical validation macro-F1 (§5.2).
2. The test-set difference is not distinguishable from zero and favours FedAvg in neither a
   majority of seeds nor an interpretable direction (§5.1).
3. The mechanism FedProx targets — client drift on the severe partition — is not visible:
   validation loss rises after the selected round in both conditions, and the selected rounds
   are early in both.

Running F5 would spend 255 rounds (five seeds) re-testing a hypothesis already not supported on
the *more* heterogeneous partition, where FedProx should have the largest effect. F5 is therefore
recorded as `not_run` with this justification. This is a documented omission, not a result.

## 7. Findings (stated as findings, with their limits)

1. **S is not recovered by federated training.** S recall is exactly 0.000 in all 20 federated
   runs. This is consistent with the Phase 4 S-class investigation: the failure is a validation
   population and representational-capacity problem, not a training-topology problem. FL does not
   change it, and it should not be claimed to.
2. **Severe skew (F3) scored higher than IID-like (F1) and moderate (F2) on this frozen test
   set.** Test accuracy rose from 0.786 (F1) to 0.852 (F3) and macro-F1 from 0.304 to 0.375.
   This is *not* evidence that non-IID data is beneficial. The frozen test set is dominated by N
   (87%), F3 concentrated large V-heavy records into single clients, and the higher macro-F1 is
   driven by V recall (~0.97 in every run) together with better V precision on three of five
   seeds. The correct reading is that this particular α=0.1 record grouping produced
   client-local specialisation that this particular test set rewards. It must not be generalised
   beyond this split.
3. **Client drift is the visible dynamical feature, but FedProx at μ=0.01 does not fix it.**
   Validation loss rises after the selected round in both F3 and F4; FedProx neither stabilises
   later rounds nor improves the selected checkpoint at matched rounds. μ=0.01 is the approved
   value and was not retuned.
4. **Checkpoint selection on validation macro-F1 is fragile at ~0.28.** Round-to-round
   differences are smaller than seed variation, so the selected round — and therefore the
   headline test number — is partly arbitrary within rounds 1–5. This is a reporting caveat that
   applies to every condition, including F1 and F2.
5. **Communication cost is identical across methods** (≈73.6 MB per run, aggregate model size ×
   participants × 2 directions). FedProx adds no communication; its extra cost is local compute
   (≈509 s vs ≈453 s per 51 rounds on this hardware).

## 8. What this does and does not answer

**RQ2 is partially evidenced, not answered.** There are local-only, centralized, IID-like,
moderate and severe conditions on one frozen split with five seeds each. There is no defensible
performance gap attributable to heterogeneity in the claimed direction; the F3 result is a
split-specific effect. A G5 decision requires the research lead to accept or reject that
interpretation.

**Not established:** any privacy result (Phase 6 not started), any blockchain result (Phase 7),
any robust-aggregation result (Phase 8), any external generalisation (SVDB, E1). Nothing here
supports a clinical or novelty claim.

## 9. Reproduction

```powershell
# F3, one seed at a time (output dir must be new or hold only completed seeds)
.\.venv\Scripts\python.exe -m scripts.run_phase5_federated `
    --experiment phase5_f3_fedavg_severe `
    --output-dir experiments/logs/phase5/f3 --seed 42 --device cuda

# F4
.\.venv\Scripts\python.exe -m scripts.run_phase5_federated `
    --experiment phase5_f4_fedprox_severe `
    --output-dir experiments/logs/phase5/f4 --seed 42 --device cuda
```

Per-seed artefacts: `experiments/logs/phase5/{f3,f4}/seed_N/` containing `run_summary.json`,
`rounds.json`, `rounds_state.json`, `run_metadata.json`, `checkpoints/selected_seed_N.pt` (SHA-256
recorded in the summary) and `checkpoints/latest_global_state.pt`.

Machine-readable summary: `docs/phase5_results/phase5_results.json`.

## 10. G5 assessment

> **RESOLVED 16 November 2026 — G5 PASSED.** This section records the position at the time of
> writing (analysis only, no ablations). The required explanatory ablation has since been executed;
> the full record is in [`PHASE_5_G5_DIAGNOSIS.md`](PHASE_5_G5_DIAGNOSIS.md). Summary: ablation A2
> (uniform vs sample-count-weighted aggregation) on F3 and F2, five seeds each, with a control that
> reproduces the frozen F3 results exactly, showed that **54 % of the F3-over-F1 advantage is
> attributable to aggregation weight dispersion** (one client holding 37.1 % of the aggregated
> model), leaving 46 % partition composition. G5-a, G5-b and G5-c below are all closed.

G5 requires IID/non-IID comparisons **and explanatory ablations** completed. Conditions F1–F4 are
complete with five seeds each. The explanatory evidence here is analysis of the logged runs
(matched-round comparison, selected-round distribution, loss trajectories), not new ablation runs.

Recommendation to the research lead as submitted: treat G5 as **evidence-submitted, decision
pending**. The decisions requested were:

| # | Decision | Evidence | Resolution |
|---|---|---|---|
| G5-a | Accept the F3 > F1/F2 result as a split-specific effect, or require an ablation to test it | §7.2 | **Ablation required and run** — 54 % weighting / 46 % composition |
| G5-b | Accept the FedProx null result and the documented F5 omission | §5, §6 | **Accepted** — documented in §6 |
| G5-c | Record the fragile checkpoint-selection behaviour as a limitation across all conditions | §7.4 | **Recorded** — §9 of the G5 diagnosis and `LIMITATIONS.md` |
