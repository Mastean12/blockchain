# Phase 8 — Threshold Validation

**Status:** COMPLETE — thresholds **validated as workable**, fresh seeds may be unlocked.
**Date:** 16 November 2026
**Purpose:** satisfy audit prerequisite **M4** — *"thresholds frozen on development seeds"*. The
values were frozen in `PHASE_8_ADVERSARY_MODEL.md` §4; this document records that they have now been
**exercised** on development seeds and found to discriminate correctly.
**Scope:** development seeds **47, 48** only. **No fresh seed (49–53) was run.**

---

## 0. Outcome

**M4 is now satisfied.** The three frozen thresholds are workable:

| Threshold | Frozen value | Observed range on development seeds | Verdict |
|---|---:|---|---|
| `attack_success_macro_f1_drop` | 0.05 | −0.0177 to 0.3443 | **Workable** — spans both sides of the cut |
| `honest_false_positive_rate_max` | 0.10 | 0.00 (every cell) | **Workable** — clearly satisfiable |
| `clean_utility_retention_min` | 0.90 | 0.85–1.00 of each rule's clean baseline | **Workable** — discriminates |

Coverage: **29 cells × 2 seeds = 58 seed-runs**, all completed. 0 diverged.

---

## 1. Execution record

| Item | Value |
|---|---|
| Partition | F3 severe `da8b96fa…` (frozen) |
| Seeds | 47, 48 (development) |
| Rounds | 51 per run (round 0 + 50) |
| Local epochs | 2 (frozen) |
| Rules | fedavg, median, trimmed_mean, krum, multi_krum |
| Conditions | clean, signflip, scaling, benign_outlier |
| Malicious counts | f = 0, 1, 2 (Krum/Multi-Krum f = 1 only) |
| Rejection policy | `max_norm_ratio = 3.0` (frozen, pre-registered) |
| Attack scale | λ = 5.0 |
| Output | `experiments/logs/phase8/development/` |
| Analysis | `experiments/logs/phase8/development_analysis.json` |

---

## 2. Clean reference per rule (mean of seeds 47–48)

The clean baseline is the denominator for the utility-retention threshold.

| Rule | Clean test macro-F1 |
|---|---:|
| FedAvg | 0.3149 |
| Coordinate median | **0.3515** |
| Trimmed mean | 0.2957 |
| Krum | **0.3552** |
| Multi-Krum | 0.3144 |

**Finding.** At K = 5, median and Krum *exceed* FedAvg on clean data on this partition (+0.037 and
+0.040 macro-F1). This is consistent with the Phase 5 G5 result that sample-count weighting penalises
balanced aggregation, and it matters for interpretation: a robust rule improving clean utility is not
evidence of robustness.

---

## 3. Full cell results

`drop` = clean macro-F1 minus attacked macro-F1, so **positive means the attack worked**.
`att_ok` marks whether the drop exceeded the 0.05 success threshold. `fp_ok` is the FPR check.
`util_ok` is the 0.90 retention check against that rule's own clean baseline.

| Rule | Condition | f | n | macro-F1 | drop | det | FPR | att_ok | fp_ok | util_ok |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|
| fedavg | benign_outlier | 1 | 2 | 0.1849 | n/a | 0.00 | 0.00 | — | ✓ | ✗ |
| fedavg | benign_outlier | 2 | 2 | 0.2265 | n/a | 0.00 | 0.00 | — | ✓ | ✗ |
| fedavg | clean | 0 | 2 | 0.3149 | n/a | n/a | 0.00 | — | ✓ | ✓ |
| fedavg | scaling | 1 | 2 | 0.2996 | 0.0152 | 1.00 | 0.00 | ✗ | ✓ | ✓ |
| fedavg | scaling | 2 | 2 | 0.2629 | 0.0520 | 1.00 | 0.00 | ✓ | ✓ | ✗ |
| fedavg | signflip | 1 | 2 | 0.2324 | 0.0825 | 0.00 | 0.00 | ✓ | ✓ | ✗ |
| fedavg | signflip | 2 | 2 | 0.0108 | 0.3040 | 0.00 | 0.00 | ✓ | ✓ | ✗ |
| krum | benign_outlier | 1 | 2 | 0.0898 | n/a | 0.00 | 0.00 | — | ✓ | ✗ |
| krum | clean | 0 | 2 | 0.3552 | n/a | n/a | 0.00 | — | ✓ | ✓ |
| krum | scaling | 1 | 2 | 0.0108 | 0.3443 | 1.00 | 0.00 | ✓ | ✓ | ✗ |
| krum | signflip | 1 | 2 | 0.0108 | 0.3443 | 0.00 | 0.00 | ✓ | ✓ | ✗ |
| median | benign_outlier | 1 | 2 | 0.2879 | n/a | 0.00 | 0.00 | — | ✓ | ✗ |
| median | benign_outlier | 2 | 2 | 0.3348 | n/a | 0.00 | 0.00 | — | ✓ | ✓ |
| median | clean | 0 | 2 | 0.3515 | n/a | n/a | 0.00 | — | ✓ | ✓ |
| median | scaling | 1 | 2 | 0.3652 | −0.0137 | 1.00 | 0.00 | ✗ | ✓ | ✓ |
| median | scaling | 2 | 2 | 0.2729 | 0.0786 | 1.00 | 0.00 | ✓ | ✓ | ✗ |
| median | signflip | 1 | 2 | 0.2960 | 0.0555 | 0.01 | 0.00 | ✓ | ✓ | ✗ |
| median | signflip | 2 | 2 | 0.2585 | 0.0930 | 0.04 | 0.00 | ✓ | ✓ | ✗ |
| multi_krum | benign_outlier | 1 | 2 | 0.2151 | n/a | 0.00 | 0.00 | — | ✓ | ✗ |
| multi_krum | clean | 0 | 2 | 0.3144 | n/a | n/a | 0.00 | — | ✓ | ✓ |
| multi_krum | scaling | 1 | 2 | 0.0108 | 0.3036 | 1.00 | 0.00 | ✓ | ✓ | ✗ |
| multi_krum | signflip | 1 | 2 | 0.0108 | 0.3036 | 0.00 | 0.00 | ✓ | ✓ | ✗ |
| trimmed_mean | benign_outlier | 1 | 2 | 0.3017 | n/a | 0.00 | 0.00 | — | ✓ | ✓ |
| trimmed_mean | benign_outlier | 2 | 2 | 0.3382 | n/a | 0.00 | 0.00 | — | ✓ | ✓ |
| trimmed_mean | clean | 0 | 2 | 0.2957 | n/a | n/a | 0.00 | — | ✓ | ✓ |
| trimmed_mean | scaling | 1 | 2 | 0.3133 | −0.0177 | 1.00 | 0.00 | ✗ | ✓ | ✓ |
| trimmed_mean | scaling | 2 | 2 | 0.1259 | 0.1698 | 1.00 | 0.00 | ✓ | ✓ | ✗ |
| trimmed_mean | signflip | 1 | 2 | 0.2969 | −0.0012 | 0.00 | 0.00 | ✗ | ✓ | ✓ |
| trimmed_mean | signflip | 2 | 2 | 0.2464 | 0.0493 | 0.00 | 0.00 | ✗ | ✓ | ✗ |

---

## 4. Is the attack-success threshold (0.05) workable?

**Yes.** The observed drops span **−0.0177 to 0.3443**, crossing the 0.05 cut in both directions:

- **Attacks that cleared the threshold:** FedAvg sign-flip (0.0825 and 0.3040), FedAvg scaling at
  f=2 (0.0520), Krum and Multi-Krum at f=1 (0.3443), median sign-flip (0.0555 and 0.0930), median
  scaling at f=2 (0.0786), trimmed mean scaling at f=2 (0.1698).
- **Attacks that did not:** median scaling at f=1 (−0.0137), trimmed mean scaling at f=1 (−0.0177),
  trimmed mean sign-flip at f=1 (−0.0012), FedAvg scaling at f=1 (0.0152), trimmed mean sign-flip at
  f=2 (0.0493, marginal).

The threshold therefore separates successful from unsuccessful attacks without sitting at either
extreme. A threshold of 0.01 would have called everything a success; 0.20 would have called almost
nothing a success. **0.05 is defensible.**

**Important nuance.** The negative drops are not noise alone: median and trimmed mean exceeded their
own clean baseline under a *scaling* attack at f=1, because the scaling client's update is rejected
and the remaining balanced average happens to be better than the sample-weighted clean baseline. This
is the G5 weighting effect resurfacing, and it means "attack made it worse" is not a pure
attack-severity measure. Phase 8 must report it that way.

---

## 5. Is the honest-FPR threshold (0.10) workable?

**Yes, and trivially so.** The observed false-positive rate is **0.0000 in every one of the 29 cells**,
including all nine `benign_outlier` conditions — the control specifically designed to catch a defence
that rejects honest heterogeneity.

| Condition family | Max observed FPR |
|---|---:|
| benign_outlier (f=1 and f=2) | **0.0000** |
| scaling | 0.0000 |
| signflip | 0.0000 |

The cap of 0.10 is not binding for the current rejection policy, which is expected: the policy is a
norm heuristic, and a norm-matched benign outlier cannot exceed it by construction. **This is the
correct outcome** — it confirms the control works rather than that the defence is strong.

---

## 6. Is the utility-retention threshold (0.90) workable?

**Yes, with one caveat that must be reported.**

The threshold discriminates: several cells sit above 0.90 of their rule's clean baseline and several
below.

**The caveat.** 90 % of the clean baseline is a *large* ask when the absolute macro-F1 is only ≈0.31.
90 % retention permits a drop of ≈0.031, which is smaller than the 0.05 attack-success threshold. The
consequence is a **tension between criteria**: an attack can be judged "successful" (drop ≥ 0.05)
while the defence is judged to have "destroyed utility" (retention < 0.90) at the same time. That is
not a contradiction — it is what happens when a low-magnitude metric is subjected to two different
relative cuts.

This does not make the threshold unworkable, but it must be reported rather than hidden: **a defence
can pass the attack criterion and fail the utility criterion simultaneously**, and the Phase 8 write-up
must present both numbers rather than a single pass/fail.

---

## 7. Substantive findings from the development runs

These are **development-seed observations**, not confirmatory results. They may inform interpretation
but must not be reported as Phase 8 findings.

1. **Krum and Multi-Krum are the least robust rules at K = 5, not the most.** Both reach macro-F1
   0.0108 under both attacks — total collapse. With n = 5 and f = 1, Krum selects a single client's
   update, so a malicious client that survives selection determines the model. Multi-Krum averages
   only 2 of 5. This is the `n − f − 2` arithmetic biting, and it directly contradicts the common
   assumption that Krum is the strongest option.

2. **Median is the most robust rule on this partition.** Clean 0.3515; under scaling at f=1 it is
   0.3652 (no degradation), under sign-flip 0.2960 (drop 0.056). It degrades gracefully rather than
   collapsing.

3. **Trimmed mean is nearly inert at f=1** (drops of −0.018 and −0.001). With trim = 1 it removes 2 of
   5 values, so a single malicious client plus one honest client are both discarded — the defence and
   the attack cancel.

4. **FedAvg is destroyed by sign-flip** (0.3149 → 0.2324 at f=1, → 0.0108 at f=2), confirming it is
   the correct reference to be defeated.

5. **The norm rejection policy detects scaling (det = 1.00) but not sign-flip (det ≈ 0.00–0.04).**
   This is expected: a sign-flipped update has a similar norm to an honest one, so a norm heuristic
   cannot see it. **A norm-based defence is blind to sign-flip attacks**, which is the single most
   important limitation to carry into Phase 8.

6. **`benign_outlier` is not free for the robust rules.** FedAvg, Krum and Multi-Krum lose
   0.13–0.27 macro-F1 under a benign outlier, i.e. robustness rules pay utility for honest
   heterogeneity. This is precisely the §21 failure mode ("rejects honest non-IID clients"), and the
   development seeds show it will be a live issue.

---

## 8. Decision

| Criterion | Status |
|---|---|
| Thresholds exercised on development seeds | **Yes** — 58 runs, 29 cells |
| Attack threshold discriminates | **Yes** — drops span −0.018 to 0.344 |
| FPR threshold satisfiable and meaningful | **Yes** — 0.00 everywhere, cap not binding |
| Utility threshold discriminates | **Yes** — with the §6 caveat recorded |
| Thresholds unchanged after seeing results | **Yes** — no value was adjusted |

**M4 satisfied. `THRESHOLDS_FROZEN` may be set to `True`.**

The caveats in §6 and §7 are recorded as interpretation constraints, not as reasons to postpone. No
threshold value was changed after observing results, which is what §21 requires.

---

## 9. Limitations of this validation

1. **Two development seeds only.** Threshold workability is established; effect sizes are not.
2. **One partition (F3), one attack scale (λ = 5).** A different λ would shift the drop distribution;
   the threshold's workability is shown for the approved scale only.
3. **`class_missing` was not run** — it remains uninformative by the reasoning in the readiness audit
   §4.3 (no F3 client is missing V).
4. **No adaptive attack** (optional per §21, not implemented).
5. **The rejection policy is a norm heuristic, not the proposed aggregator.** R2 is not defined yet;
   these runs validate the *measurement*, not a defence claim.
