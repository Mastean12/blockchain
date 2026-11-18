# Phase 8 — Failure Analysis

**Date:** 17 November 2026
**Status:** Analysis of the failed confirmatory gate. **G8 remains NOT PASSED.**
**Scope:** diagnosis of the 75 divergent confirmatory runs using existing logs and recorded per-round
metadata only. **No intervention was implemented, no configuration changed, no run executed, no
frozen artefact touched.**

---

## PART 1 — Preservation of the original experiment

### 1.1 What is preserved unchanged

| Artefact | Location | State |
|---|---|---|
| Frozen thresholds (0.05 / 0.10 / 0.90) | `PHASE_8_ADVERSARY_MODEL.md` §4 | **Unchanged** |
| Adversary model (7 spec-§20 parameters) | `PHASE_8_ADVERSARY_MODEL.md` | **Unchanged** |
| Baseline justification (K = 5) | `PHASE_8_BASELINE_JUSTIFICATION.md` | **Unchanged** |
| Development results (58 runs, seeds 47–48) | `experiments/logs/phase8/development/` | **Unchanged** |
| Confirmatory results (145 runs, seeds 49–53) | `experiments/logs/phase8/confirmatory/` | **Unchanged** |
| Attack configuration (λ = 5.0) | `configs/aggregation/*_fresh.yaml` | **Unchanged** |
| Aggregation mathematics | `src/aggregation/rules.py` | **Unchanged** |
| Original G8 decision: **NOT PASSED** | `PHASE_8_EXECUTION_STATUS.md` | **Preserved** |

Development and confirmatory results are **not pooled** anywhere in this document. Every number
below from confirmatory seeds is labelled as such.

### 1.2 The 15 unmeasurable cells — explicit classification

A cell is classified **UNMEASURABLE** when all five fresh seeds diverged before any aggregation rule
could be compared.

| # | Rule | Condition | f | Seeds diverged | First divergence |
|---|---|---|---:|---|---|
| 1 | fedavg | benign_outlier | 1 | 5/5 | rounds 5–11 |
| 2 | fedavg | benign_outlier | 2 | 5/5 | rounds 5–8 |
| 3 | fedavg | scaling | 1 | 5/5 | round 1 (all) |
| 4 | fedavg | scaling | 2 | 5/5 | round 1 (all) |
| 5 | fedavg | signflip | 1 | 5/5 | round 3 (4/5), round 3 |
| 6 | fedavg | signflip | 2 | 5/5 | rounds 3–4 |
| 7 | krum | benign_outlier | 1 | 5/5 | rounds 3–4 |
| 8 | krum | scaling | 1 | 5/5 | round 1 (all) |
| 9 | krum | signflip | 1 | 5/5 | rounds 1–3 |
| 10 | multi_krum | benign_outlier | 1 | 5/5 | round 5 (all) |
| 11 | multi_krum | scaling | 1 | 5/5 | round 1 (all) |
| 12 | multi_krum | signflip | 1 | 5/5 | rounds 1–3 |
| 13 | trimmed_mean | benign_outlier | 2 | 5/5 | rounds 7–30 |
| 14 | trimmed_mean | scaling | 2 | 5/5 | round 1 (all) |
| 15 | trimmed_mean | signflip | 2 | 5/5 | rounds 5–7 |

**Per-seed divergence evidence** (rounds logged, selected round, round-1 rejection, round-1 median
norm, round-0 validation loss) is recorded in
`experiments/logs/phase8/confirmatory/*/seed_*/phase8_summary.json` and extracted to
`divergence_evidence.json`. No run was deleted, reclassified or averaged.

### 1.3 Round-zero metrics are not aggregation performance

**This is the most important preservative statement in the document.**

In every diverged run, divergence occurred before any round was recorded as `best`, so the
untrained round-0 model was selected. Round-0 validation macro-F1 is a property of the
initialisation, not of any aggregation rule. Verified: for each seed, **exactly one distinct
round-0 validation macro-F1 value exists across all 15 cells**:

| Seed | Round-0 val macro-F1 (identical across every cell) |
|---:|---:|
| 49 | 0.007607296949 |
| 50 | 0.022520013923 |
| 51 | 0.000294637596 |
| 52 | 0.000000000000 |
| 53 | 0.001074608535 |

Because three different rules report identical values per seed, those cells carry **no information
about relative rule performance**. Any table presenting them as rule comparison is reporting the
properties of a randomly initialised network.

### 1.4 The 14 valid cells (for reference only)

| Rule | Condition | f |
|---|---|---|
| fedavg, krum, median, multi_krum, trimmed_mean | clean | 0 |
| median | benign_outlier | 1, 2 |
| median | scaling | 1, 2 |
| median | signflip | 1, 2 |
| trimmed_mean | benign_outlier | 1 |
| trimmed_mean | scaling | 1 |
| trimmed_mean | signflip | 1 |

---

## PART 2 — Root-cause analysis

Divergence is **not one phenomenon**. The evidence separates it into two mechanisms with different
causes, plus a shared structural amplifier.

### 2.1 The decisive measurement: round-1 update norms are identical across all conditions

The single most informative finding in this analysis:

| Condition (fedavg, seed 49) | Round-1 median update norm | Diverged at |
|---|---:|---|
| **clean** | **13.27** | never |
| benign_outlier | **13.27** | round 7 |
| signflip | **13.27** | round 3 |
| scaling | **13.27** | round 1 |

Across seeds 49, 50, 51 the clean round-1 medians are 13.27, 12.95, 12.73 — **bit-identical to the
attacked conditions**. The attack does not change the round-1 norm distribution.

**Interpretation.** Round-1 updates are intrinsically large (~13 in L2) regardless of attack, then
decay rapidly under clean training:

| Round | Clean median norm | Clean val macro-F1 |
|---:|---:|---:|
| 1 | 13.27 | 0.2476 |
| 2 | 5.33 | 0.2481 |
| 3 | 4.29 | 0.2672 |
| 4 | 3.78 | 0.2672 |
| 5 | 3.80 | 0.2701 |
| 8 | 3.44 | 0.2620 |

**Clean training recovers from the round-1 spike and stabilises at norm ≈3.4.** The attacks are
dangerous not because they inflate round 1, but because they **prevent that recovery**.

**Therefore: attack magnitude is not the primary cause.** A hypothesis that "λ = 5 is simply too
large" is not supported by the norm evidence.

### 2.2 Mechanism A — rejection collapses the client count (25 of 75 unmeasurable runs)

All 25 runs with this signature are scaling attacks at f = 1 or f = 2.

**Observed sequence:**

1. Round 1, scaling at f=1: median 13.27 → threshold 3.0 × 13.27 = **39.8**; the scaled malicious
   update exceeds it and **is rejected** (`rejected=['client_01']`).
2. Aggregation then runs on **4 clients** instead of 5.
3. The round still diverges.

At f = 2 with trimmed mean: both malicious clients are rejected, leaving **3 honest clients**.
Trimmed mean with `trim=1` on `n=3` keeps `n − 2·trim = 1` value — the single middle value. The
aggregate therefore **reduces to one client's update**, which is exactly the Krum collapse mode.

**Supported conclusion:** removing the attacker is insufficient when the same action shrinks the
client set below the minimum needed for a meaningful aggregate. At K = 5, rejecting one client leaves
four; rejecting two leaves three, which is at or below every rule's tolerance except raw FedAvg.

**This is a protocol-design defect, not an attack-strength problem.**

### 2.3 Mechanism B — no rejection, gradual destabilisation (50 of 75 unmeasurable runs)

These runs never reject a client. Divergence occurs at rounds 2–11, after several apparently
successful rounds.

**Observed trajectory (fedavg / benign_outlier / f1):**

| Seed | Diverged at | r1 | r2 | r3 | r4 |
|---:|---:|---:|---:|---:|---:|
| 49 | 7 | 0.2432 | 0.2432 | 0.2438 | 0.2691 |
| 50 | 5 | 0.2430 | 0.2432 | 0.2432 | 0.2432 |
| 51 | 10 | 0.2432 | 0.2432 | 0.2435 | 0.2322 |

Validation loss for seed 51 rises monotonically from round 6 onward: 0.544 → 0.917 → 1.303 → 1.399
→ 1.367 → divergence. The model is not converging and eventually produces a non-finite loss.

**Supported conclusion:** the aggregate drifts for several rounds until a BatchNorm running
statistic or a loss term overflows float32. The benign_outlier conditions show this most clearly
because **no client is malicious there** — the instability is produced by honest-but-random-direction
updates alone.

### 2.4 Mechanism C — the norm threshold is self-defeating

The rejection policy computes `threshold = 3.0 × median(norms)`. At round 1 the median is already
~13 because honest updates are large. Therefore:

| Condition | Median | Threshold | Malicious norm | Rejected? |
|---|---:|---:|---:|---|
| clean | 13.27 | 39.8 | — | n/a |
| scaling f=1 | 13.27 | 39.8 | >39.8 for the rejected client | **yes** |

The threshold works at round 1 only because the scaled update is **3× the round-1 median**. Once
honest updates decay to ~3.4 (round 8+), the threshold falls to ~10 — but by then divergence has
already occurred, or the attacker is below it.

**Supported conclusion:** the policy's reference statistic (a median) is contaminated by the same
scale that the attack exploits, and it is computed relative to a quantity that changes by 4× within
five rounds. **The threshold is not scale-invariant**, which is a design flaw independent of any
attack parameter.

### 2.5 What the evidence does NOT support

Stated explicitly, because these are the attractive-but-unsupported explanations:

| Hypothesis | Status | Why |
|---|---|---|
| "λ = 5 is too large" | **Not supported** | Round-1 norms are identical to clean; clean recovers, attacked does not |
| "Non-IID heterogeneity alone causes divergence" | **Not supported** | The clean F3 cell never diverges in 5/5 seeds |
| "Aggregation mathematics is wrong" | **Not supported** | Valid cells use identical code and complete 51 rounds |
| "Numerical instability is the root cause" | **Partially supported** | Non-finite loss is the *terminal symptom* of Mechanism B, not the initiating cause |
| "Krum is defective" | **Not supported as a code defect** | Its `n−f−2` selection is correct; at K=5 it degenerates by design |

### 2.6 Causal summary

| Mechanism | Runs | Trigger | Supported cause |
|---|---:|---|---|
| **A** rejection collapse | 25 | Scaling attack exceeds threshold; client removed | Client count falls to 3–4; trimmed mean degenerates to single-client selection |
| **B** gradual drift | 50 | No rejection; aggregate drifts for 2–11 rounds | Attack prevents post-round-1 recovery; BatchNorm/loss eventually overflow |
| **C** scale-dependent threshold | both | Threshold = 3 × median | Median contaminated by intrinsic round-1 norm; not scale-invariant |

**Primary cause: the interaction between an intrinsically large round-1 update distribution and an
attack that suppresses recovery — amplified by a rejection policy whose reference statistic moves
by 4× during training.** Attack magnitude is a contributing factor only through Mechanism A.

---

## PART 3 — Proposed interventions (separate experiments)

Each is proposed as an **independent** experiment. They are **not** to be combined.

### 3A — Bounded clipping as a stability intervention

**Hypothesis.** Capping the L2 norm of every client update before aggregation prevents the round-1
spike and the subsequent drift, so all rules complete 51 rounds and become comparable.

**Mechanism.** Before aggregation, `Δ_k ← Δ_k · min(1, C / ‖Δ_k‖₂)` for every client, including
honest ones and including the benign-outlier control. `C` is fixed in advance from the clean
development-seed norm distribution.

**Changed:** a clip constant `C` applied to all updates.
**Held constant:** model, batch size, learning rate, seeds, partition, attack λ = 5.0, aggregation
mathematics, selection rule, thresholds.

**Justified `C`.** From the clean development-seed medians (≈13 at round 1, ≈3.4 from round 8), a
fixed `C` must accommodate round 1 without being meaningless later. Recommend `C` = the 95th
percentile of **clean** development update norms across all rounds — computed before confirmatory
results are seen.

**Confounders.** (i) Clipping also bounds a *malicious* update, so a robust rule may appear to work
merely because the attack was truncated — stability and robustness must be reported separately.
(ii) A fixed `C` is poorly matched to a norm that varies 4× across rounds. (iii) Clipping changes
clean accuracy, so clean baselines must be re-measured under clipping.

**Effect on honest non-IID clients.** Directly adverse: honest round-1 updates (~13) would be
clipped hard if `C` is small. This is the §21 "rejects honest clients" risk in numeric form. Must be
quantified, not assumed.

**Required metrics.** Divergence rate per cell; clipped-update fraction (honest vs malicious); clean
macro-F1 under clipping vs unclipped; per-round norms; detection and false-positive rates.

**Privacy/security.** Clipping already exists in Phase 6 DP and bounds sensitivity; here it is used
for stability, not privacy, and **confers no DP guarantee**. Reusing the same operator does not
transfer the privacy claim.

**Acceptance criteria (proposed).** (a) ≥ 27 of 29 cells complete all 51 rounds on fresh seeds;
(b) honest-clip fraction ≤ 10 % from round 5 onward; (c) clean macro-F1 retention ≥ 0.90 of the
unclipped clean baseline; (d) honest FPR ≤ 0.10.

---

### 3B — Reduced attack strength λ as a sensitivity analysis

**Hypothesis.** Divergence frequency is a monotone function of λ; at smaller λ the attack still
degrades the model but does not annihilate it, making rules comparable.

**Mechanism.** Re-run the **same** 29-cell matrix with λ ∈ {1.5, 2.5} instead of 5.0. Nothing else
changes.

**Changed:** attack scale λ only.
**Held constant:** everything else.

**Confounders.** (i) A weaker attack may fall below the frozen 0.05 success threshold, producing a
null result that says more about λ than about robustness. (ii) λ and K interact: at small λ the
attacker may be indistinguishable from honest heterogeneity. (iii) This is explicitly a **sensitivity
analysis**, not a new primary condition — it cannot be used to claim the original λ = 5 result was
wrong.

**Effect on honest clients.** None — honest updates are untouched. This is the least invasive
proposal.

**Required metrics.** Divergence rate; attack success (drop ≥ 0.05); clean vs attacked macro-F1;
detection/FPR; per-rule comparison at each λ.

**Acceptance criteria.** The analysis is accepted if it produces a **monotone** relationship between
λ and (divergence rate, attack success). If no λ in {1.5, 2.5} yields a measurable attack that also
preserves comparability, the conclusion is that λ = 5 annihilates and smaller λ does not attack —
both reportable, neither a defence claim.

---

### 3C — Direction-aware detection as a separate detection intervention

**Hypothesis.** Divergence-inducing updates can be identified by their **direction relative to the
honest consensus**, not only their magnitude, so they can be flagged before they destabilise
aggregation.

**Mechanism.** For each client update compute cosine similarity to the coordinate-wise median of the
other clients. Flag updates below a pre-registered similarity threshold. This is a **detection**
mechanism, evaluated separately from aggregation.

**Changed:** adds a direction statistic and a flagging rule.
**Held constant:** aggregation mathematics unchanged — detection is measured, not used to filter,
in the first instance.

**Confounders.** At K = 5 the median-of-others is itself noisy. Honest non-IID updates legitimately
differ in direction, so a cosine test risks flagging heterogeneity. Sign-flip is **exactly** an
anti-parallel update, so it would be easy to detect — which makes an inflated detection rate likely
and must be interpreted carefully.

**Effect on honest clients.** The central risk. Honest non-IID updates can have low cosine
similarity to the consensus by construction. The benign_outlier control is the decisive test.

**Required metrics.** Detection rate by attack type (signflip vs scaling); FPR on honest clients;
FPR on benign_outlier; separation between honest-outlier and malicious similarity distributions.

**Privacy/security.** Direction statistics are computed on updates already visible to the server;
no new data is exposed. **Confers no DP guarantee.** Publishing per-client similarity values on-chain
would leak information about individual clients and must not be done (Phase 7 §1.4).

**Acceptance criteria.** Detection rate ≥ 0.80 on signflip **and** FPR ≤ 0.10 on benign_outlier. If
signflip is detected but benign_outlier is also flagged, the mechanism is rejected as unable to
separate attack from heterogeneity.

---

## PART 4 — Cross-cutting statement

**None of 3A, 3B, 3C may be combined.** Each changes a different quantity, and combining them would
make any observed improvement unattributable. The original experiment remains the historical
reference and its G8 decision stands.

---

## 5. What this analysis does not establish

1. **No new experiment was run**, so every causal statement is inference from existing logs.
2. **No checkpoint-level inspection was performed** (no saved per-round model states exist for the
   diverged runs; only summary records). The non-finite-loss attribution in Mechanism B is therefore
   inferred from the loss trajectory, not observed directly at the tensor level.
3. **The round-1 norm spike is a property of this architecture and initialisation**; whether it
   generalises to other models is unknown.
4. **K = 5 is binding throughout**; none of these findings transfers to larger client counts.
5. **S-class recall is 0.000 in every condition** including clean, so no intervention here can be
   evaluated on minority-class recovery.

---

## 6. Artefacts

| Artefact | Path |
|---|---|
| Confirmatory per-seed summaries (145) | `experiments/logs/phase8/confirmatory/*/seed_*/` |
| Divergence evidence extraction | `divergence_evidence.json` (session temp) |
| Original confirmatory report | `PHASE_8_CONFIRMATORY_REPORT.md` |
| Execution status | `PHASE_8_EXECUTION_STATUS.md` |

**G8 remains NOT PASSED.** No configuration, threshold, frozen artefact or result was modified.
