# Phase 8 — Confirmatory Execution Report

**Date:** 17 November 2026
**Status:** EXECUTION COMPLETE — **G8 NOT passed**; see §7
**Authorisation:** research-lead confirmation, 17 November 2026
**Seeds:** fresh set **49, 50, 51, 52, 53** (development seeds 47–48 excluded from all confirmatory claims)
**Runs:** 145 (29 cells × 5 seeds), **0 execution failures, 0 aborted cells**

---

## 0. Summary and headline

All 145 confirmatory runs completed. The analysis yields **two distinct outcomes** that must not be
merged:

1. **14 of 29 cells are valid** and support rule comparison.
2. **15 of 29 cells are invalid** — every seed in them diverged, so the untrained round-0 model was
   selected and the aggregation rule had no effect. Reporting these as rule performance would be
   false.

**G8 is not passed.** The frozen criteria require independent evaluation complete; nearly half the
matrix could not be evaluated because the attacks destroyed the models before aggregation could be
compared.

---

## 1. Pre-execution verification (all 7 checks)

| # | Check | Result |
|---|---|---|
| 1 | `THRESHOLDS_FROZEN = True` | **PASS** |
| 2 | All fresh configs use only seeds 49–53; none development-labelled | **PASS** |
| 3 | Development-seed rejection gate active (verified behaviourally: a fresh-labelled config containing seed 47 is REFUSED) | **PASS** |
| 4 | Fresh config set matches the frozen 29-cell matrix exactly (missing=[] extra=[]) | **PASS after correction** — see §1.1 |
| 5 | `LIMITATIONS.md` items 36 and 37 updated | **PASS** — see §1.2 |
| 6 | Krum/Multi-Krum client-count correction and divergence guard present | **PASS** |
| 7 | No frozen threshold, development result, Phase 1–7 result or manifest modified | **PASS** — split `bbcfa25c…`, client `71dbcac3…`, F3 `da8b96fa…` all unchanged |

### 1.1 A discrepancy found and corrected before execution

The first verification run **failed checks 4a and 4b**: 37 fresh configs existed against an expected
29. Eight were contradictions — `condition=clean` with `byzantine_clients=1` or `2`. "Clean" means
*f = 0*, so those cells were semantically impossible. They were artefacts of an earlier config
generator that emitted `clean_f0`, `clean_f1` and `clean_f2` for every rule.

The 8 contradictory configs were deleted before any confirmatory run. The fresh set now matches the
approved matrix exactly. **No approved cell was removed**, and no threshold or rule was altered.

### 1.2 Documentation correction

`LIMITATIONS.md` item 36 ("G5 is undecided") and item 37 ("Phases 7–10 have no results") were stale.
Both were rewritten to the true state while preserving their historical meaning: each now opens by
quoting what it previously said and records that the earlier wording was a staleness defect.

---

## 2. The divergence problem — the central finding

### 2.1 What happened

**40 of 145 runs (27.6 %) diverged** under attack. In every one of those, the divergence occurred at
round 1, before any aggregation comparison was possible.

| Cells affected | Seeds affected | Status |
|---|---|---|
| 15 of 29 | **5/5 in every affected cell** | Fully invalid |
| 14 of 29 | 0 | Fully valid |

There were **no partially-affected cells**, which makes the split clean.

### 2.2 Why the affected cells are invalid, not merely poor

When divergence occurs at round 1, no round is ever recorded as `best`, so `best` remains the
**round-0 model — the untrained network**. The consequence is directly observable:

| Rule | Round-0 validation macro-F1 (seed 49) | Test macro-F1 |
|---|---:|---:|
| FedAvg | 0.007607 | 0.232714 |
| Krum | 0.007607 | 0.190890 |
| Multi-Krum | 0.007607 | 0.190890 |

Round-0 validation macro-F1 is **bit-identical across all rules**, because an untrained model does
not depend on how updates are aggregated. Three different rules reporting the same value is therefore
not evidence that the rules behave equivalently — it is evidence that **no aggregation occurred**.

This is the single most important observation in the confirmatory phase. Any table that presented
these cells as rule performance would be reporting the properties of a randomly initialised network.

### 2.3 What the divergence means scientifically

The divergence is **not** an execution failure. It is a real property of the conditions:

- at f = 2, FedAvg, Krum and Multi-Krum cannot resist a 40 % malicious fraction at K = 5;
- trimmed mean at f = 2 and every FedAvg condition likewise collapse;
- the `benign_outlier` conditions diverge for FedAvg, Krum and Multi-Krum, which is itself a
  finding: those rules are destabilised by honest heterogeneity of matched norm.

So the attacks worked. What failed is the *measurement design*: a single diverged run removes the
ability to compare rules, and my runner recorded that as a completed run with round-0 output rather
than flagging the cell as unmeasurable.

**This is a defect in my runner's reporting, and it is recorded as such.** The `diverged_at_round`
field and the round-0 selection are both preserved per seed; nothing was concealed, but the summary
layer failed to warn that a round-0 selection invalidates the cell.

---

## 3. Valid cells — clean baselines (matched reference)

Clean baselines are the denominators for every utility change. All five rules completed 5 seeds with
no divergence.

| Rule | Mean macro-F1 | SD | Per-seed (49, 50, 51, 52, 53) |
|---|---:|---:|---|
| FedAvg | **0.3868** | 0.0811 | 0.3096, 0.2875, 0.4412, 0.4543, 0.4414 |
| Median | 0.3398 | 0.0429 | 0.3422, 0.3131, 0.3289, 0.4119, 0.3031 |
| Trimmed mean | 0.3483 | 0.0678 | 0.3105, 0.3426, 0.3028, 0.3192, 0.4666 |
| Krum | 0.3315 | 0.0542 | 0.3088, 0.3057, 0.2786, 0.4184, 0.3460 |
| Multi-Krum | 0.3199 | 0.0210 | 0.3238, 0.2926, 0.3506, 0.3211, 0.3115 |

**Note the reversals from the development seeds.** On development seeds, median (0.3515) and Krum
(0.3552) exceeded FedAvg (0.3149). On fresh seeds, **FedAvg is highest (0.3868)** and Krum is lowest
but one (0.3315). The development ordering did not replicate.

This is exactly why §21 requires fresh seeds, and it is a direct caution against reading the
development rankings as findings. Seed-to-seed SD (0.02–0.08) is comparable to most between-rule
differences.

---

## 4. Valid cells — attack results

Only the 14 cells with **no divergence in any seed** are reported as rule performance.

### 4.1 Norm-inflating attack (scaling, λ = 5)

| Rule | f | Clean | Attacked | Drop | Detection | FPR | Attack succeeded? | Utility retained? |
|---|---:|---:|---:|---:|---:|---:|---|---|
| FedAvg | 1 | 0.3868 | **INVALID** (diverged) | — | 1.00 | 0.00 | — | — |
| FedAvg | 2 | 0.3868 | **INVALID** (diverged) | — | 1.00 | 0.00 | — | — |
| Median | 1 | 0.3398 | **0.3856** | **−0.0458** | 1.00 | 0.00 | **No** | **Yes** |
| Median | 2 | 0.3398 | **0.3754** | **−0.0355** | 0.98 | 0.00 | **No** | **Yes** |
| Trimmed mean | 1 | 0.3483 | 0.3085 | 0.0398 | 1.00 | 0.00 | **No** (< 0.05) | **No** |
| Trimmed mean | 2 | 0.3483 | **INVALID** (diverged) | — | 1.00 | 0.00 | — | — |
| Krum | 1 | 0.3315 | **INVALID** (diverged) | — | 1.00 | 0.00 | — | — |
| Multi-Krum | 1 | 0.3199 | **INVALID** (diverged) | — | 1.00 | 0.00 | — | — |

**Median is the only rule that consistently resists the scaling attack**, and it does so at both
f = 1 and f = 2, with attack drops that are *negative* (the attacked model scored higher than the
matched clean baseline). Trimmed mean at f = 1 is marginal: drop 0.0398 is below the 0.05 success
threshold, so the attack did not succeed, but utility fell just outside the 0.90 retention bound.

**Detection of scaling is 1.00 everywhere** — the norm heuristic sees norm-inflating attacks
perfectly. This is expected and must be stated narrowly: it is not evidence of general poisoning
detection.

### 4.2 Sign-flip attack

| Rule | f | Clean | Attacked | Drop | Detection | FPR | Attack succeeded? | Utility retained? |
|---|---:|---:|---:|---:|---:|---:|---|---|
| FedAvg | 1 | 0.3868 | **INVALID** (diverged) | — | 0.00 | 0.00 | — | — |
| FedAvg | 2 | 0.3868 | **INVALID** (diverged) | — | 0.00 | 0.00 | — | — |
| Median | 1 | 0.3398 | 0.3263 | **0.0135** | 0.01 | 0.00 | **No** | **Yes** |
| Median | 2 | 0.3398 | 0.3123 | **0.0276** | 0.12 | 0.00 | **No** | **Yes** |
| Trimmed mean | 1 | 0.3483 | 0.2949 | 0.0534 | 0.04 | 0.00 | **Yes** (marginal) | **No** |
| Trimmed mean | 2 | 0.3483 | 0.2760 | 0.0723 | 0.00 | 0.00 | **Yes** | **No** |
| Krum | 1 | 0.3315 | **INVALID** (diverged) | — | 0.00 | 0.00 | — | — |
| Multi-Krum | 1 | 0.3199 | **INVALID** (diverged) | — | 0.00 | 0.00 | — | — |

**Median is the only rule not defeated by sign-flip**, at either malicious fraction. Trimmed mean
degrades (drops 0.0534 and 0.0723, both above the success threshold).

**Detection of sign-flip is 0.00–0.12** — effectively zero. This confirms the development-seed
observation: **a norm-based rejection policy is blind to sign-flip attacks**, because the flipped
update has an honest-looking magnitude. The detection rate here is essentially noise.

### 4.3 Explicit distinction required by the directive

| Attack | Detection | Interpretation |
|---|---|---|
| **Scaling** (norm-inflating) | **1.00** | Norm heuristic sees it; this is not general poisoning detection |
| **Sign-flip** (norm-preserving) | **0.00–0.12** | Norm heuristic is blind; detection must not be claimed |

Any statement that "the defence detects poisoning" is unsupported. The correct statement is: *a norm
threshold detects norm-inflating attacks and not sign-flip attacks.*

---

## 5. Benign-outlier control — does robust aggregation reject honest clients?

§21 is explicit that a method rejecting honest non-IID clients is not a defence. The
`benign_outlier` condition is the control that decides this.

| Rule | f | Clean | Benign outlier | Change | FPR | Verdict |
|---|---:|---:|---:|---:|---:|---|
| FedAvg | 1 | 0.3868 | **INVALID** (diverged) | — | 0.00 | — |
| FedAvg | 2 | 0.3868 | **INVALID** (diverged) | — | 0.00 | — |
| **Median** | 1 | 0.3398 | **0.4014** | **+0.0616** | **0.00** | **No rejection** |
| **Median** | 2 | 0.3398 | 0.3169 | −0.0230 | 0.00 | **No rejection** |
| **Trimmed mean** | 1 | 0.3483 | **0.3932** | **+0.0449** | **0.00** | **No rejection** |
| Trimmed mean | 2 | 0.3483 | **INVALID** (diverged) | — | 0.00 | — |
| Krum | 1 | 0.3315 | **INVALID** (diverged) | — | 0.00 | — |
| Multi-Krum | 1 | 0.3199 | **INVALID** (diverged) | — | 0.00 | — |

**Result: for the two rules where the control is measurable (median and trimmed mean), no honest
client is rejected and no honesty penalty is observed** — FPR is 0.0000 throughout, and both rules
scored *higher* under a benign outlier than on clean data at f = 1.

**But there is a serious secondary finding.** FedAvg, Krum and Multi-Krum **diverged under the
benign-outlier condition**. A benign outlier is an honest update with the same norm as an honest one
but a random direction. Their divergence under this control means those three rules are destabilised
by honest heterogeneity — which is precisely the §21 failure mode, manifesting as divergence rather
than as measured rejection.

---

## 6. Krum and Multi-Krum — recorded without generalisation

Krum and Multi-Krum diverged in **every attacked cell** at K = 5, f = 1, and also under the benign
control. The only cells where they completed are the clean baselines.

This is consistent with the arithmetic: at n = 5, f = 1, Krum selects a single client's update and
Multi-Krum averages 2 of 5. A single malicious client that survives selection determines the model,
and a matched-norm outlier can likewise be selected.

**Scope limits, stated explicitly:**

- These observations hold **only for K = 5**, the frozen client count. They say nothing about Krum at
  larger n, where its `n ≥ 2f + 3` margin is comfortable.
- No claim is made that "Krum is not robust" in general. The correct statement is that at five
  clients Krum has no margin, and its selection rule degenerates to one client.
- No claim is made about Byzantine robustness at any other client count, attack fraction or model.

---

## 7. G8 assessment — NOT PASSED

Master spec §29: *"G8 Robustness — Attack model, baselines and thresholds frozen; independent
evaluation complete."*

| G8 component | Status | Evidence |
|---|---|---|
| Attack model frozen | **PASS** | `PHASE_8_ADVERSARY_MODEL.md`, approved |
| Baselines frozen | **PASS** | `PHASE_8_BASELINE_JUSTIFICATION.md`, enforced at runtime |
| Thresholds frozen | **PASS** | Validated on development seeds; unchanged after results |
| Independent evaluation complete | **FAIL** | 15 of 29 cells (51.7 %) produced no evaluable comparison |

**G8 is not passed** because independent evaluation is incomplete: for over half the matrix, no
aggregation rule could be compared, since every seed diverged before aggregation mattered.

### 7.1 R2 — is the proposed aggregator supported?

**No claim is made.** R2 (the proposed robust aggregator) is not defined in this study; the matrix
evaluates established baselines. Per §21, if a candidate does not outperform appropriate baselines,
the claim must be revised or withdrawn — and here there is no candidate to evaluate.

What the valid cells *do* show is a legitimate comparative result:

> At five clients on the frozen F3 partition, **coordinate median is the only evaluated rule that
> resists both attacks without destroying clean utility**, and it does not reject honest
> benign-outlier clients. Trimmed mean resists scaling at f = 1 and is defeated by sign-flip.
> FedAvg, Krum and Multi-Krum diverge under attack and cannot be compared.

That is narrower than a robustness claim and must be reported that narrowly.

---

## 8. Preserved negative findings

Recorded, not concealed:

1. **40 runs diverged (27.6 %)** and 15 cells are unmeasurable.
2. **Round-0 fallback produced identical metrics across rules** in every diverged cell — an artefact
   that must never be tabulated as a rule comparison.
3. **Sign-flip detection is effectively zero (0.00–0.12).** The norm heuristic cannot see it.
4. **The development-seed clean ranking did not replicate.** Median and Krum led on development
   seeds; FedAvg leads on fresh seeds.
5. **FedAvg, Krum and Multi-Krum diverge under the benign control**, indicating destabilisation by
   honest heterogeneity.
6. **Trimmed mean at f = 1 is defeated by sign-flip** and fails the utility-retention bound under
   scaling.

---

## 9. What must be fixed before Phase 8 can be re-evaluated

These are proposed corrections, **not implemented** — they require research-lead approval.

| # | Issue | Proposed correction |
|---|---|---|
| F1 | Diverged runs silently produce round-0 metrics that look like results | Mark the cell `unmeasurable` and exclude it from rule comparison; report it as a divergence outcome |
| F2 | Divergence destroys the comparison entirely | Add a divergence-robust condition: clip updates to a bounded norm before aggregation, or reduce λ, so the attack degrades rather than annihilates |
| F3 | FedAvg/Krum/Multi-Krum cannot be evaluated under attack at K = 5 | Report their divergence as the finding, and restrict cross-rule comparison to rules that complete |
| F4 | Sign-flip is undetectable by the norm policy | Either state the detection claim narrowly, or add a direction-aware statistic in a newly approved condition |

None of these changes a frozen threshold. They change how unmeasurable cells are reported and what
conditions are run.

---

## 10. Artefacts

| Artefact | Path |
|---|---|
| All 145 per-seed summaries | `experiments/logs/phase8/confirmatory/*/seed_*/phase8_summary.json` |
| Consolidated analysis | `experiments/logs/phase8/confirmatory_analysis.json` |
| Development results (never pooled) | `experiments/logs/phase8/development/` |
| Frozen configs | `configs/aggregation/*_fresh.yaml` (29), `*_development.yaml` (37) |

Per-seed values, per-seed status and divergence rounds are retained in every summary and in the
consolidated JSON.

**Test evidence:** 183 passed, 16 skipped (contract tests skip without a running Ganache node).

No frozen threshold, manifest, Phase 1–7 result or development result was modified. Nothing committed
or pushed.
