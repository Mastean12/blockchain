# Phase 8 — Protocol Amendment Proposal

**Status:** **PROPOSAL — NOT APPROVED, NOT IMPLEMENTED.** Awaiting research-lead decision.
**Date:** 17 November 2026
**Relationship to the original protocol:** this proposal **does not replace** the original Phase 8
protocol. It defines a **separate, later** confirmatory protocol that runs alongside it. The original
experiment, its frozen thresholds and its **G8 NOT PASSED** decision remain on the record and are not
retroactively redefined.

---

## 1. Why an amendment is needed

The original protocol produced 145 confirmatory runs of which **40 (27.6 %) diverged** and **15 of
29 cells (51.7 %) became unmeasurable**. The failure analysis
(`PHASE_8_FAILURE_ANALYSIS.md`) established three mechanisms:

| Mechanism | Cause | Protocol implication |
|---|---|---|
| **A** rejection collapse | Rejecting a client at K = 5 leaves 3–4, and trimmed mean degenerates to single-client selection | The protocol must define behaviour when the client set shrinks |
| **B** gradual drift | Attack prevents post-round-1 recovery; BatchNorm/loss eventually overflow | The protocol must distinguish "diverged" from "performed" |
| **C** scale-dependent threshold | Threshold = 3 × median, where the median moves 4× during training | The protocol must not rely on a scale-relative statistic |

None of these is fixed by changing a threshold value. They are **protocol design** problems, which is
why an amendment is proposed rather than a re-run.

---

## 2. What is retained unchanged

| Item | Status |
|---|---|
| Frozen thresholds: attack success 0.05, FPR cap 0.10, utility retention 0.90 | **RETAINED, unchanged** |
| Adversary model (7 spec-§20 parameters) | **RETAINED** |
| K = 5 clients, F3 severe partition `da8b96fa…` | **RETAINED** |
| Model `compact_cnn_v1`, batch 256, lr 1e-3, AdamW, 2 local epochs | **RETAINED** |
| Original λ = 5.0 attack strength | **RETAINED as the historical reference** |
| Original 29-cell matrix | **RETAINED as the historical reference** |
| **G8 = NOT PASSED** | **RETAINED, not revisited** |
| Development results (seeds 47–48) | **RETAINED; never pooled with anything new** |
| Original confirmatory results (seeds 49–53) | **RETAINED; never re-used as confirmatory evidence** |

**The amendment adds; it does not overwrite.**

---

## 3. Measurable versus unmeasurable outcomes

The central addition. Every cell must be classified before its metrics are read.

### 3.1 Definition

> **A cell is MEASURABLE if and only if, for every one of its five fresh seeds, all 51 rounds
> completed without divergence and at least one round was selected above round 0.**

> **A cell is UNMEASURABLE if any seed diverged, or if any seed selected round 0.**

No partial credit. A cell with 4 measurable seeds and 1 diverged seed is **UNMEASURABLE**, and the
diverged seed is reported individually.

### 3.2 Required reporting per cell

| Field | Requirement |
|---|---|
| Classification | `MEASURABLE` / `UNMEASURABLE` |
| Seeds completed | integer 0–5 |
| Seeds diverged | integer 0–5 |
| First divergence round | list per seed, or `none` |
| Round-1 median update norm | per seed |
| Round-0 selection count | integer 0–5 |
| **Metrics** | reported **only if MEASURABLE** |

### 3.3 Absolute prohibition

> **Round-zero metrics must never appear in any aggregation-performance table.** Where a diverged run
> selected round 0, the only permissible record is "diverged at round N; no aggregation performance
> measurable".

This rule exists because the original analysis demonstrated that round-0 validation macro-F1 is
identical across rules for a given seed (0.007607296949 for seed 49 in every cell), so those values
carry no comparative information.

---

## 4. Preserving the honest-client false-positive constraint

The 0.10 FPR cap is **unchanged**, and the amendment strengthens how it is enforced.

| Requirement | Rule |
|---|---|
| Benign-outlier control is mandatory | A cell without it is incomplete |
| FPR computed on `benign_outlier` only | Not on clean, not pooled |
| Any intervention that lowers FPR by also lowering clean utility | Reported as a trade, never as an improvement |
| FPR threshold | **0.10, unchanged** |
| Honest clip/reject rate | **New, ≤ 0.10** — any mechanism that discards more than 10 % of honest updates is rejected regardless of attack metrics |

The last row is the direct lesson from Mechanism A: a defence that works by deleting honest clients
is not a defence.

---

## 5. Separating stability from attack detection

The original protocol conflated these, which is what made the failure hard to attribute.

### 5.1 Two independent questions

| Question | Metric family | Success means |
|---|---|---|
| **Q-stab**: does the pipeline complete 51 rounds under this condition? | Divergence rate, rounds completed, round-1 norm | The model trains to completion |
| **Q-detect**: can a mechanism identify malicious updates? | Detection rate, FPR on benign_outlier | Malicious separated from honest |

**A method may pass Q-stab and fail Q-detect, or vice versa.** Neither substitutes for the other, and
no single "robustness score" may be constructed that hides which one failed.

### 5.2 Reporting

Every cell reports both families. There is **no combined pass/fail** for robustness; there are two
independent verdicts.

---

## 6. Fresh confirmatory seeds

| Role | Seeds | Constraint |
|---|---|---|
| Original development | 47, 48 | **Consumed**; never used for amended confirmatory claims |
| Original confirmatory | 49, 50, 51, 52, 53 | **Consumed**; retained as the historical record only |
| **Amended development** | **54, 55** | For calibrating any intervention constant |
| **Amended confirmatory** | **56, 57, 58, 59, 60** | **Must not be run until all constants are frozen** |

**Verified requirement:** seeds 54–60 must be confirmed absent from every existing experiment log
before the amendment is approved for execution. This check must be performed and recorded
immediately before the first amended run, not assumed.

**Rule:** a run using a consumed seed can never contribute to an amended confirmatory claim, even if
it produces a favourable result.

---

## 7. Threshold determination before confirmatory observation

The original protocol froze thresholds before confirmatory runs; the amendment keeps that discipline
and adds specificity.

### 7.1 Sequence (mandatory, in order)

1. **Freeze intervention constants** using **amended development seeds 54–55 only**:
   clip constant `C` (3A), similarity threshold (3C), or λ set (3B) — whichever intervention is approved.
2. **Record the constants and the criterion for judging them** in this document as an approved
   addendum, with a timestamp, **before** any amended confirmatory run.
3. **Only then** run amended confirmatory seeds 56–60.
4. Report results against the constants frozen in step 2.

### 7.2 Prohibited

- Selecting `C`, λ or a similarity threshold after seeing amended confirmatory macro-F1.
- Re-running a cell with a different constant and reporting the better one.
- Adjusting the 0.05 / 0.10 / 0.90 thresholds under any circumstance.

### 7.3 Unchanged thresholds

| Threshold | Value | Status |
|---|---|---|
| Attack success (macro-F1 drop) | 0.05 | **Unchanged** |
| Honest FPR cap | 0.10 | **Unchanged** |
| Clean utility retention | 0.90 | **Unchanged** |
| Honest clip/reject cap (new) | 0.10 | **New, additive** |

---

## 8. No test data in selection or calibration

Restated because the amendment adds calibration steps, which create new opportunities for leakage.

| Use | Permitted data |
|---|---|
| Intervention constant selection (`C`, λ, similarity threshold) | **Amended development seeds 54–55, validation split only** |
| Attack scaling calibration | Development seeds only |
| Checkpoint selection | Validation split only |
| Final reported metrics | Test split, **read once per seed after selection** |
| **Any calibration, tuning or early stopping** | **Test split — never** |

A run in which the test split informed any constant, threshold or checkpoint is invalid and must be
discarded, not reported with a caveat.

---

## 9. Proposed amended experiment structure

The amendment proposes running **one** intervention per approval, not all three.

| Proposal | Cells | Seeds | Approx. runs | Purpose |
|---|---:|---|---:|---|
| **3A** bounded clipping | 29 | 56–60 | 145 | Stability |
| **3B** reduced λ sensitivity | 29 × 2 λ | 56–60 | 290 | Sensitivity, not primary |
| **3C** direction-aware detection | 29 | 56–60 | 145 | Detection only |

Only one may be approved at a time. Approving more than one would confound attribution, which is the
error the original protocol avoided by design and must continue to avoid.

---

## 10. Gate criteria for the amended protocol

The amended protocol defines its own gate, **G8-amended**, separate from G8.

| Requirement | Criterion |
|---|---|
| Measurable cells | ≥ 27 of 29 (≥ 93 %) |
| Honest-client protection | FPR ≤ 0.10 **and** honest reject/clip rate ≤ 0.10 |
| Stability vs detection separated | Both reported independently |
| Clean utility | Retention ≥ 0.90 of the matched clean baseline |
| Reproducibility | Bit-identical on re-run of one seed |
| Leakage | No test-split use in any calibration, verified |

**G8-amended passing does not retroactively pass G8.** They are distinct gates with distinct
evidence, and both must appear in the final report.

---

## 11. Risks of this amendment

| Risk | Assessment | Mitigation |
|---|---|---|
| Amendment appears to "move the goalposts" | **Real and serious** | G8 stays NOT PASSED; amendment is additive; original results retained verbatim |
| Clipping (3A) confounds stability with robustness | **High** — clipping bounds the attack too | Report clipped fraction for honest vs malicious separately |
| Smaller λ (3B) makes attacks ineffective | **Medium** — may produce a clean null | Report λ–success monotonicity; a null is a finding |
| Direction detection (3C) flags honest heterogeneity | **High** at K = 5 | benign_outlier FPR is the deciding test |
| Consumed seeds reused accidentally | Medium | Explicit pre-run verification of 54–60 |
| Amended results mistaken for the original | **High** — reporting integrity | Distinct gate names, distinct seed sets, distinct documents |

---

## 12. What this amendment does not do

1. It does **not** change G8 or any original threshold.
2. It does **not** reclassify any original cell.
3. It does **not** pool development and confirmatory data.
4. It does **not** implement any intervention — all three remain unimplemented proposals.
5. It does **not** authorise any run. Every proposed experiment requires separate approval.
6. It does **not** claim any of the interventions will work.

---

## 13. Approval request

| # | Decision required | Recommendation |
|---|---|---|
| **A8-1** | Accept this amendment as a separate protocol | Accept; keeps G8 and original results intact |
| **A8-2** | Choose at most one intervention to develop | **3B first** (least invasive; pure sensitivity analysis; no honest-client risk) |
| **A8-3** | Approve the seed allocation 54–55 / 56–60 | Approve after verifying 54–60 are unused |
| **A8-4** | Accept the measurable/unmeasurable classification rules | Approve as written |
| **A8-5** | Accept the honest clip/reject cap of 0.10 as an additive criterion | Approve |

Until A8-1 … A8-5 are resolved, **no amended experiment may be executed.**

**G8 remains NOT PASSED.**
