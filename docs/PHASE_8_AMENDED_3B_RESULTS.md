# Phase 8 — Amended Protocol 3B Results: Reduced-λ Sensitivity Analysis

**Date:** 17 November 2026
**Protocol:** `PHASE_8_PROTOCOL_AMENDMENT_PROPOSAL.md`, intervention **3B**
**Gate:** **G8-amended** — separate from G8. **G8 remains NOT PASSED.**
**Seeds run:** 54, 55 (amended development only)
**Runs:** 116 (58 cells × 2 seeds), **0 execution failures**
**Outcome:** **HYPOTHESIS REFUTED.** Reduced λ does not reduce divergence. Confirmatory phase not run.

---

## 0. Summary

Intervention 3B hypothesised that divergence is a monotone function of attack strength λ, so a
smaller λ would let rules complete and become comparable.

**Measured result: divergence is completely insensitive to λ.**

| λ | Runs | Diverged | Rate | Cells measurable |
|---:|---:|---:|---:|---:|
| **1.5** | 58 | **30** | **51.7 %** | 14 / 29 (48 %) |
| **2.5** | 58 | **30** | **51.7 %** | 14 / 29 (48 %) |
| 5.0 (original confirmatory, seeds 49–53) | 145 | 40 | 27.6 % | 14 / 29 (48 %) |

Not only is the relationship not monotone — divergence is **identical** at λ = 1.5 and λ = 2.5, and
measurability is **exactly the same 14/29** at all three λ values.

**Per the pre-registered acceptance criterion, 3B is rejected and the confirmatory phase is not
run.** Running it would spend ~15 h to reproduce a result already established.

---

## 1. Method and compliance

### 1.1 What was run

Only amended development seeds **54, 55** — never 47–48 (original development) or 49–53 (original
confirmatory). Verified beforehand that seeds 54–60 appeared in no existing experiment log.

### 1.2 What was held constant

Model, batch size 256, lr 1e-3, AdamW, 2 local epochs, 51 rounds, F3 partition `da8b96fa…`, all 29
matrix cells, aggregation mathematics, checkpoint selection, all four frozen thresholds
(0.05 / 0.10 / 0.90 / honest-clip 0.10).

### 1.3 What changed

**Only** `aggregation.scale`: λ = 5.0 → {1.5, 2.5}. 116 amended configs generated in
`configs/aggregation/amended/`, all validated through the seed-role gate.

### 1.4 Gate extension (required and recorded)

The Phase 8 runner hardcoded seeds 47–48 / 49–53, so amended seeds would have been rejected. The
gate was extended with `amended_development` (54–55) and `amended_confirmatory` (56–60) roles, plus a
guard that amended confirmatory seeds are **disjoint from every original seed set**. Original
configs were verified to still load unchanged.

---

## 2. Primary result: divergence is rule-dependent, not λ-dependent

The breakdown is the decisive evidence.

| λ | Rule | Runs | Diverged |
|---:|---|---:|---:|
| 1.5 | fedavg | 14 | **12** |
| 1.5 | krum | 8 | **6** |
| 1.5 | multi_krum | 8 | **6** |
| 1.5 | trimmed_mean | 14 | 6 |
| 1.5 | **median** | 14 | **0** |
| 2.5 | fedavg | 14 | **12** |
| 2.5 | krum | 8 | **6** |
| 2.5 | multi_krum | 8 | **6** |
| 2.5 | trimmed_mean | 14 | 6 |
| 2.5 | **median** | 14 | **0** |

**Every row is identical between λ = 1.5 and λ = 2.5.** The divergence count depends entirely on
the aggregation rule, not on attack magnitude.

### 2.1 Divergence by condition

| Condition | λ = 1.5 | λ = 2.5 |
|---|---|---|
| clean | 0 / 10 | 0 / 10 |
| benign_outlier | 10 / 16 | 10 / 16 |
| signflip | 10 / 16 | 10 / 16 |
| scaling | 10 / 16 | 10 / 16 |

**All three non-clean conditions diverge identically**, including `benign_outlier` where **no client
is malicious**. That is the strongest available confirmation of the failure analysis's Mechanism B:
the instability is produced by honest-but-non-IID updates and by the aggregation rule's response to
them, not by attack strength.

---

## 3. Attack effectiveness at reduced λ

Reduced λ also weakens the attack, so the sensitivity analysis needed both effects measured.

| Rule | λ | Clean macro-F1 | Attack | Attacked macro-F1 | Drop | Success (≥0.05)? |
|---|---:|---:|---|---:|---:|---|
| median | 1.5 | 0.3218 | scaling f1 | 0.3190 | 0.0028 | **no** |
| median | 2.5 | 0.3218 | scaling f1 | 0.3872 | −0.0654 | **no** |
| median | 1.5 | 0.3218 | scaling f2 | 0.3924 | −0.0707 | **no** |
| median | 2.5 | 0.3218 | scaling f2 | 0.3998 | −0.0781 | **no** |
| median | 1.5 | 0.3218 | signflip f1 | 0.3669 | −0.0451 | **no** |
| median | 2.5 | 0.3218 | signflip f1 | 0.3669 | −0.0451 | **no** |
| median | 1.5 | 0.3218 | signflip f2 | 0.3112 | 0.0105 | **no** |
| median | 2.5 | 0.3218 | signflip f2 | 0.3112 | 0.0105 | **no** |
| trimmed_mean | 1.5 | 0.3665 | scaling f1 | 0.3201 | 0.0464 | **no** |
| trimmed_mean | 2.5 | 0.3665 | scaling f1 | 0.3783 | −0.0118 | **no** |
| trimmed_mean | 1.5 | 0.3665 | signflip f1 | 0.2890 | **0.0775** | **YES** |
| trimmed_mean | 2.5 | 0.3665 | signflip f1 | 0.2890 | **0.0775** | **YES** |

**Two findings.**

1. **At λ ≤ 2.5 the scaling attack stops working on median.** Drops are negative (−0.065 to −0.078),
   meaning the "attacked" model scored *higher* than clean. The attack is no longer an attack.
2. **trimmed_mean is still defeated by sign-flip** (drop 0.0775, above threshold) at both λ values —
   and the value is *identical* at 1.5 and 2.5, again showing λ-independence.

Only genuinely measurable cells appear above. The rest diverged and are excluded.

---

## 4. Evaluation against the pre-registered acceptance criterion

The 3B proposal fixed its criterion **before** these runs:

> "The analysis is accepted if it produces a **monotone** relationship between λ and (divergence
> rate, attack success)."

| Criterion component | Result | Met? |
|---|---|---|
| Monotone λ → divergence rate | 51.7 % at λ=1.5, 51.7 % at λ=2.5, 27.6 % at λ=5.0 — flat, then **decreasing** | **NO** |
| Monotone λ → attack success | Success *decreases* with λ; at λ≤2.5 scaling attack has negative drop | **NO** |
| Improved measurability | 14/29 at every λ | **NO** |

**3B is rejected on all three components.**

---

## 5. Decision: confirmatory phase not run

The proposal stated: *"If no λ in {1.5, 2.5} yields a measurable attack that also preserves
comparability, the conclusion is that λ = 5 annihilates and smaller λ does not attack — both
reportable, neither a defence claim."*

That is precisely the observed situation:

- λ = 5.0 attacks effectively but annihilates several rules.
- λ = 1.5 and 2.5 leave the model intact but the attack mostly fails to degrade it.

**There is no λ at which the attack works and the comparison is measurable.** Running the
amended confirmatory phase would reproduce this at ~15 h of compute with no new information, so it
was **not run**. This is a decision to honour the pre-registered criterion, not to avoid work.

---

## 6. What this establishes

| Finding | Support |
|---|---|
| Divergence is independent of attack strength | **Strong** — identical counts at λ=1.5 and 2.5 |
| Divergence is a property of the aggregation rule | **Strong** — median 0, FedAvg 12/14, Krum 6/8, at both λ |
| Honest heterogeneity alone destabilises some rules | **Strong** — benign_outlier diverges 10/16 with no attacker |
| Reduced λ is not a viable stability intervention | **Strong** — 0 % measurability improvement |
| Mechanism A (rejection collapse) is not λ-driven | **Strong** — rejection pattern identical across λ |

These confirm the failure analysis's causal structure and **rule out 3B as a remedy**.

---

## 7. Implications for the remaining proposals

| Proposal | Status after this result |
|---|---|
| **3B** reduced λ | **REFUTED.** Not λ-dependent. Closed. |
| **3A** bounded clipping | **Not addressed by this evidence.** Clipping bounds *norms*, and divergence here is not magnitude-driven — so 3A may fail for the same reason. **Must be re-examined before implementation.** |
| **3C** direction-aware detection | Unaffected; it addresses a different question (detection, not stability). |

**Important consequence for 3A:** since divergence is rule-dependent and norm-insensitive (λ changed
norm by 3.3× with zero effect), bounding the norm is unlikely to fix it. This should temper 3A's
prospects and is recorded now rather than after a costly run.

---

## 8. Limitations

1. **Two development seeds only** (54, 55). This is sufficient to refute a monotone hypothesis
   (divergence counts are bit-identical between λ values), but effect sizes are not estimated.
2. **Two λ values tested.** The original λ = 5.0 is the third point, from a different seed set,
   so the three-point comparison crosses seed sets. The *within-seed-set* comparison (1.5 vs 2.5) is
   the clean one and shows exact equality.
3. **Median's 0 divergences is rule-specific**; it does not mean median is robust in any general
   sense, only that it completed at K = 5 on these conditions.
4. **S recall remains 0.000** in every condition including clean; none of this concerns class S.
5. **No test data informed any setting**; the test split was read once per seed after selection.

---

## 9. Status

| Item | Value |
|---|---|
| G8 | **NOT PASSED — unchanged** |
| G8-amended (3B) | **Not passed — hypothesis refuted** |
| Amended confirmatory seeds 56–60 | **NOT RUN** (decision recorded) |
| Original thresholds | **Unchanged** |
| Original results | **Unchanged** |
| Frozen artefacts | **Unchanged** — split `bbcfa25c…`, client `71dbcac3…`, F3 `da8b96fa…` |
| Test suite | 183 passed, 16 skipped |
| Committed / pushed | **No** |

**Recommendation:** close 3B. Re-examine 3A's viability in light of the norm-insensitivity finding
before implementing it. Consider whether 3C (detection) is worth pursuing independently, since the
stability problem it does not address remains unresolved.
