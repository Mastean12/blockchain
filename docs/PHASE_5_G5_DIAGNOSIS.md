# Phase 5 — G5 Diagnosis

**Date:** 16 November 2026
**Status:** G5 **RESOLVED — PASSED**
**Authorisation:** research-lead instruction to complete G5 before Phase 7
**Scope:** the explanatory ablations required by master spec Phase 5 ("Diagnose the gap with
controlled ablations"), which had not been run
**Not changed:** frozen split, partitions, configs, Phase 4/5/6 results

---

## 0. Outcome

**G5 is resolved.** Both required components now exist:

| G5 requirement (master spec §29) | Status |
|---|---|
| IID/non-IID comparisons completed | **Pass** — F1 (IID-like), F2 (moderate α=0.5), F3 (severe α=0.1), 5 seeds each |
| Explanatory ablations completed | **Pass** — ablation A2 run on two partitions, 10 new runs |

The previously unexplained result — F3 (severe skew) scoring *higher* than F1 (IID-like) — now has
a measured mechanistic explanation, and the explanation is not "heterogeneity helps".

---

## 1. What was missing

`PHASE_5_RESULTS_AND_ANALYSIS.md` §10 recorded G5 as "evidence submitted, decision pending" and
listed G5-a as open: *"Accept the F3 > F1/F2 result as a split-specific effect, or require an
ablation to test it."*

The explanatory evidence then available was **analysis of logged runs** — matched-round comparison,
selected-round distribution, loss trajectories. No new ablation had been executed. Master spec
Phase 5 explicitly requires "diagnose the gap with controlled ablations", so G5 could not be closed
on observational analysis alone.

---

## 2. The gap to be explained

Frozen results, test set, 5 seeds:

| Condition | Partition | Test accuracy | Test macro-F1 |
|---|---|---|---|
| F1 | IID-like | 0.7861 ± 0.0223 | 0.3040 ± 0.0146 |
| F2 | moderate α=0.5 | 0.8061 ± 0.0363 | 0.3079 ± 0.0299 |
| **F3** | **severe α=0.1** | **0.8523 ± 0.0380** | **0.3752 ± 0.0448** |

The severe-skew partition beat the IID-like partition by **+0.066 accuracy and +0.071 macro-F1**.
The obvious reading — "non-IID data helps" — is implausible and was already flagged as such.

### 2.1 The candidate mechanism

FedAvg aggregates by **sample count**. The partitions differ sharply in how dispersed those counts
are:

| Partition | Client sample counts | Weights | Max | Min | **Ratio** |
|---|---|---|---|---:|---:|---:|
| F1 IID-like | 12,887 / 13,625 / 14,480 / 16,266 / 14,669 | 0.179–0.226 | 0.226 | 0.179 | **1.26×** |
| F2 moderate | 20,847 / 12,494 / 13,603 / 13,866 / 11,117 | 0.155–0.290 | 0.290 | 0.155 | **1.88×** |
| F3 severe | 26,685 / 14,780 / 6,260 / 11,149 / 13,053 | 0.087–0.371 | 0.371 | 0.087 | **4.26×** |

On F3 a single client supplies **37.1 %** of the aggregated model. If that client's data happens to
be favourable to the frozen test set, weighted FedAvg drifts towards training on roughly one
client's distribution — closer to centralized training on a subset than to balanced federation.

**Hypothesis H_A2:** the F3 advantage is substantially an *aggregation-weighting* artefact, not a
property of heterogeneity.

---

## 3. Pre-registered design

Recorded in `scripts/run_phase5_a2_ablation.py` **before any run**.

**Intervention.** Replace sample-count weights with **uniform weights** (each of the five clients
contributes 0.2), changing nothing else. Same partition, same client data, same model, same seeds,
same rounds, same local epochs, same checkpoint-selection rule.

**Decision rule, fixed in advance:**
- Gap = F3 − F1 macro-F1 = 0.3752 − 0.3040 = **0.0712**; half-gap = **0.0356**.
- If the uniform-weight drop exceeds the half-gap, H_A2 is **supported**.
- Otherwise H_A2 is **not supported** and partition label composition must be considered instead.

**Validity guard, also fixed in advance.** The harness must reproduce the frozen weighted-F3
results *exactly* when run with sample-count weighting. If it does not, the ablation is void.

**Generality check.** Repeat on F2 (1.88× spread) to test the dose–response prediction: a smaller
weight dispersion should produce a smaller change.

---

## 4. Guard: the harness is provably faithful

Control runs with sample-count weighting, all five seeds, same code path:

| Seed | Control (acc, macro-F1, round) | Frozen (acc, macro-F1, round) | Exact match |
|---:|---|---|---|
| 42 | 0.8728, 0.3993, 2 | 0.8728, 0.3993, 2 | **✓** |
| 43 | 0.8478, 0.3582, 44 | 0.8478, 0.3582, 44 | **✓** |
| 44 | 0.7878, 0.3037, 2 | 0.7878, 0.3037, 2 | **✓** |
| 45 | 0.8770, 0.4074, 24 | 0.8770, 0.4074, 24 | **✓** |
| 46 | 0.8763, 0.4073, 2 | 0.8763, 0.4073, 2 | **✓** |

**All five reproduce to 4 decimal places including the selected round.** The only difference from
the frozen runs is the aggregation weight vector, so any downstream difference is attributable to
weighting.

---

## 5. Result on F3 — H_A2 supported

| Seed | Sample-weighted (acc, macro-F1) | Uniform (acc, macro-F1) | Δ macro-F1 | Selected round (uniform) |
|---:|---|---|---:|---:|
| 42 | 0.8728, 0.3993 | 0.8941, **0.4572** | **+0.0579** | 2 |
| 43 | 0.8478, 0.3582 | 0.7993, 0.3123 | −0.0460 | 3 |
| 44 | 0.7878, 0.3037 | 0.7855, 0.3020 | −0.0018 | 3 |
| 45 | 0.8770, 0.4074 | 0.7942, 0.3083 | −0.0991 | 3 |
| 46 | 0.8763, 0.4073 | 0.7854, 0.3023 | −0.1050 | 2 |
| **Mean ± SD** | **0.8523 ± 0.0380, 0.3752 ± 0.0448** | **0.8117 ± 0.0464, 0.3364 ± 0.0676** | **−0.0388** | |

**Decision: −0.0388 > half-gap 0.0356 → H_A2 SUPPORTED.**

### 5.1 Attribution

| Component | Value | Share of the F1→F3 gap |
|---|---:|---:|
| F1 IID-like macro-F1 | 0.3040 | — |
| F3 weighted (deep skew + weighted aggregation) | 0.3752 | — |
| F3 uniform (deep skew, balanced aggregation) | 0.3364 | — |
| **Total F1→F3 advantage** | **0.0712** | 100 % |
| **Explained by aggregation weight dispersion** | **0.0388** | **54 %** |
| Residual attributable to partition composition | 0.0324 | 46 % |

**Just over half of the apparent "non-IID benefit" is an artifact of sample-weighted aggregation
giving one client 37 % of the model.** The remaining 46 % is a genuine, smaller effect of this
particular partition on this particular frozen test set, and must not be generalised.

---

## 6. Result on F2 — dose–response confirmed

Same intervention on the moderate partition (weight ratio 1.88×):

| Seed | Sample-weighted macro-F1 | Uniform macro-F1 | Δ |
|---:|---:|---:|---:|
| 42 | 0.3242 | 0.3449 | +0.0207 |
| 43 | 0.3518 | 0.3933 | +0.0415 |
| 44 | 0.2781 | 0.2673 | −0.0108 |
| 45 | 0.2883 | 0.2886 | +0.0003 |
| 46 | 0.2969 | 0.2845 | −0.0124 |
| **Mean** | **0.3079 ± 0.0299** | **0.3157 ± 0.0523** | **+0.0079** |

| Partition | Weight ratio | Δ macro-F1 from uniform weighting |
|---|---:|---:|
| F2 moderate | 1.88× | **+0.0079** |
| F3 severe | 4.26× | **−0.0388** |

The effect grows with weight dispersion, in the direction the mechanism predicts. On F2 uniform
weighting is marginally *better*, consistent with there being little concentration to exploit and
some benefit from not over-weighting the large client.

**This is a dose–response relationship across partitions, which is stronger evidence than a single
significant comparison.** With five seeds the individual Δ values are noisy (F3 ranges +0.058 to
−0.105), so the between-partition trend, not any single seed, carries the inference.

---

## 7. What this changes in the Phase 5 conclusions

`PHASE_5_RESULTS_AND_ANALYSIS.md` §7.2 already stated that F3 scoring highest is "not evidence that
non-IID data is beneficial" and called it "client-local specialisation that this particular test set
rewards". **That interpretation was correct but unsupported by an experiment.** It is now measured
and quantified:

- The specific mechanism is **sample-count weighting under 4.26× size dispersion**, not
  specialisation per se.
- 54 % of the gap is attributable to it.
- The residual 46 % remains a partition-specific effect that should not be generalised.

No frozen Phase 5 number changes. The interpretation sharpens from "split-specific effect,
cause unidentified" to "54 % aggregation-weighting artefact, 46 % partition composition".

---

## 8. G5 gate decision

| Master-spec G5 evidence | Status | Evidence |
|---|---|---|
| IID/non-IID comparisons completed | **Pass** | F1, F2, F3 × 5 seeds |
| Explanatory ablations completed | **Pass** | A2 on F3 and F2, 5 seeds each, pre-registered |
| Ablation validity guarded | **Pass** | Control reproduces frozen exactly on 5/5 seeds |
| Mechanism identified and quantified | **Pass** | 54 % weight dispersion / 46 % composition |
| Conclusion stated with its limits | **Pass** | §9 |

**G5: PASSED.**

---

## 9. Limitations

1. **Five clients only.** A weight ratio of 4.26× is specific to how the Dirichlet allocation fell
   for α=0.1 with record groups; other draws would give different dispersion. The finding is about
   *this* partition pair, not a law about skew.
2. **Five seeds.** Per-seed Δ on F3 spans +0.058 to −0.105; only the mean and the between-partition
   trend are interpretable. No significance test is claimed, and the resampling unit for a real
   test would be the record group, not the seed.
3. **One aggregation rule.** Uniform weighting is a single alternative. Weighted-by-√n or capped
   weights would probe the same mechanism differently and were not run.
4. **F1 was not given a uniform-weight run.** Its 1.26× dispersion probably leaves little to
   measure, but this was not verified; the three-point trend rests on F2 and F3 plus F1's weighted
   baseline.
5. **Checkpoint selection remains fragile** (Phase 5 §7.4). Uniform weighting changed the selected
   round in 3 of 5 F3 seeds (2→3, 24→3, 44→3), so some of the Δ is selection movement rather than
   pure training quality. The matched-round analysis in §5 of `PHASE_5_RESULTS_AND_ANALYSIS.md`
   showed FedAvg/FedProx were indistinguishable at matched rounds, and a similar caveat applies
   here.
6. **Test set is fixed and N-dominated** (87 % N), with test S concentrated in record 232. Results
   describe this frozen split.
7. **S recall remains 0.000** in every condition including all A2 runs. Nothing here concerns S.

---

## 10. Artefacts

| Artefact | Path |
|---|---|
| Ablation harness (pre-registered design in docstring) | `scripts/run_phase5_a2_ablation.py` |
| Control (sample-weighted, validity guard) | `experiments/logs/phase5/a2_control/` |
| F3 uniform-weight runs | `experiments/logs/phase5/a2_uniform/` |
| F2 uniform-weight runs | `experiments/logs/phase5/a2_uniform_f2/` |
| Checkpoints | `.../seed_N/checkpoints/` |

The frozen `src/federated/fedavg.py` was **not modified**; the ablation is a separate module.
