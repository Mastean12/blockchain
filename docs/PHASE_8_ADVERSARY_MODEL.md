# Phase 8 — Adversary Model

**Status:** **APPROVED** by the research lead on 16 November 2026, as part of the instruction to
make Phase 8 ready for execution.
**Authority:** `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` §20, §21, §28-8.1
**Companion:** `docs/threat_model/SECURITY_THREAT_MODEL.md` (Phase 7, blockchain) — this document
supplies the adversary model that §4.2 of that file deferred to Phase 8.

---

## 1. Purpose

§20 requires that the adversary's capabilities be defined **before writing attack code**. This
document supplies all seven required parameters, fixes the admissible attack conditions, and records
what Phase 8 will *not* claim.

## 2. The seven §20 parameters

### 2.1 Number and fraction of malicious clients

| Condition | Malicious clients | Fraction | Role |
|---|---:|---:|---|
| `f0` | 0 | 0 % | Clean control |
| `f1` | 1 | 20 % | **Primary condition** |
| `f2` | 2 | 40 % | Secondary condition, admissible only for methods that support it |

**Rationale for f = 1 as primary.** The frozen client count is K = 5. The widely used Byzantine
bounds require:
- Krum: `n ≥ 2f + 3` → at K = 5 this holds only for **f = 1** (2·1+3 = 5). At f = 2 it requires
  n ≥ 7 and is **inadmissible**.
- Multi-Krum selects `n − f − 2` clients → 2 of 5 at f = 1, **1 of 5 at f = 2**, which is degenerate.
- Coordinate-wise median and trimmed mean: breakdown `f < n/2` → admissible at both f = 1 and f = 2.

A single malicious client out of five is also the realistic scale of the threat this study can
honestly model.

### 2.2 Does the attacker know the aggregation rule?

**Yes — full knowledge (white-box).** The attacker knows the aggregation rule, including any
threshold, and knows it is being applied. This is the strongest assumption and therefore the
conservative choice for evaluating a defence.

**Explicit consequence:** a defence that only works because its rule is secret is not evaluated here
and must not be claimed.

### 2.3 Can the attacker coordinate?

**Yes** for the `f2` condition; not applicable at `f1`. Coordinated attackers share the aggregation
rule and may jointly craft updates. No communication-latency or partial-coordination model is
assumed.

### 2.4 What can the attacker alter?

| Capability | In scope |
|---|---|
| Model updates (the transmitted update vector) | **Yes — primary** |
| Local data and labels | **No** (out of scope; would change the task definition) |
| The aggregation rule itself | **No** (server-side, trusted) |
| The audit ledger (Phase 7) | **No** — Phase 7 addresses evidence, not training |

Attacks operate on `Δ_k = w_local,k − w_global` after local training, before aggregation.

### 2.5 Can the attacker control client identity?

**No.** Client identities are the frozen slots `client_01`…`client_05`. An attacker occupies one or
two existing slots and cannot create, duplicate or impersonate another. Sybil attacks are out of
scope.

### 2.6 Can the attacker adapt to detection?

**Not in the primary conditions (static, non-adaptive).** An *adaptive* attacker who observes
detection and adjusts is listed in §21 as conditional ("if the scope and implementation allow"). It
is recorded as an **optional** condition, and any adaptive result must be reported separately from
the static results — never pooled with them.

### 2.7 Attack objective and success criterion

**Objective:** degrade the global model's classification performance on the frozen test partition
without being rejected by the defence.

**Primary success criterion (fixed before any run):**

> An attack is **successful** if test **macro-F1** falls by at least **0.05 absolute** relative to the
> matched clean condition on the same seed, *and* the attack is not rejected in a majority of rounds.

**Secondary criteria (reported, not used to define success):** accuracy degradation; V-class recall
degradation; attack persistence across rounds.

**Defence success criterion (from §21, verbatim intent):** a defence is effective only if it
(a) blocks the attack, **and** (b) does not reject honest non-IID clients, **and** (c) does not
destroy clean utility. Failure of any one of the three means the defence is not effective, and the
result must be reported as negative.

Thresholds for (b) and (c) are frozen in §4 and must not be adjusted after seeing results.

---

## 3. Attack conditions required by §21

| ID | Condition | Applicability | Implementation |
|---|---|---|---|
| `clean` | Clean non-IID clients | Required | Frozen F3 partition, no modification |
| `signflip` | Sign-flip update attack | Required | Malicious update multiplied by −λ |
| `scaling` | Update scaling attack | Required | Malicious update multiplied by λ ≫ 1 |
| `benign_outlier` | Norm-matched noise / benign outlier | Required | Same norm as an honest update, random direction |
| `class_missing` | Class-missing honest clients | **Conditionally applicable** | See §3.1 |
| `multi` | Multiple malicious clients | `f2` only | Two coordinated attackers |
| `adaptive` | Adaptive attack | **Optional** | Not implemented in the primary plan |

### 3.1 Class-missing clients: applicability finding

Inspection of the frozen F3 partition shows no client is missing class V — the only minority class
with meaningful support (461 test windows). Clients are missing only:

| Client | Missing |
|---|---|
| client_01 | Q |
| client_03 | F, Q |

F has **0** test windows and Q has **2**. Therefore this condition is **technically applicable but
uninformative**, and must be reported as such. It must not be used as evidence that a defence
"preserves honest non-IID clients" — that claim must rest on the `clean` and `benign_outlier`
conditions.

### 3.2 Why `benign_outlier` is the most important control

§21 is explicit that a method which "rejects honest non-IID clients" is not a defence. A norm-matched
noise update is statistically indistinguishable from an honest non-IID update by design, so a
detector that rejects it is rejecting legitimate heterogeneity. **This condition, not the attacks,
decides whether a defence is honest.**

---

## 4. Frozen decision thresholds

These are fixed **now**, before any run, and scored on **development seeds only** (§5).

| Threshold | Value | Meaning |
|---|---|---|
| `attack_success_macro_f1_drop` | **0.05** absolute | Attack counts as successful at or above this |
| `honest_false_positive_rate_max` | **0.10** | Defence fails if it rejects >10 % of honest updates |
| `clean_utility_retention_min` | **0.90** | Defence fails if clean macro-F1 falls below 90 % of FedAvg |
| `detection_rate_reported` | not thresholded | Reported descriptively; no pass/fail |

**These values were chosen before any Phase 8 run and must not be changed after seeing results.**
If they prove unworkable, execution stops and the change is recorded as a protocol deviation with
the reason — it is not silently adjusted.

---

## 5. Seed allocation

§21 requires thresholds frozen on development data and final evaluation on **fresh seeds not used
for threshold selection**. Seeds 42–46 were consumed by Phases 4–7 and are therefore unavailable as
fresh seeds.

| Role | Seeds | Rule |
|---|---|---|
| **Development** | **47, 48** | May be used for threshold selection and debugging |
| **Fresh (confirmatory)** | **49, 50, 51, 52, 53** | **Must not be run until thresholds are frozen**; no result from them may inform any setting |
| Historical | 42–46 | Continuity with Phases 4–7; not used for Phase 8 confirmatory claims |

The development/fresh boundary is recorded here, in advance. A confirmatory run that used a
development seed is invalid and must be re-run.

---

## 6. What Phase 8 can and cannot conclude

**Can conclude (if results support):** that a specific aggregation rule, under white-box static
attack by one malicious client out of five on the frozen F3 partition, degrades test macro-F1 by at
most X relative to FedAvg, while rejecting at most Y % of honest updates, at a measured computational
cost.

**Cannot conclude:**
- that the defence is Byzantine-robust in general (K = 5 supports only one Byzantine client);
- that it resists adaptive attacks (not evaluated);
- that it generalises to other K, other partitions or other model families;
- that it preserves minority-class utility in the sense of learning S, which is 0.000 in every
  condition including clean;
- any claim resting on the `class_missing` condition (§3.1);
- any novelty claim beyond what the literature already establishes.

**Mandatory negative-result commitment (§21).** If the proposed aggregator does not outperform the
appropriate baselines on the frozen criteria, the proposed-method claim must be revised or withdrawn.
Recording a null or negative result is a successful Phase 8 outcome; concealing one is not.

---

## 7. Approval

| Item | Status |
|---|---|
| All seven §20 parameters specified | **Yes** (§2) |
| Attack conditions fixed | **Yes** (§3) |
| Thresholds frozen before runs | **Yes** (§4) |
| Seed allocation fixed | **Yes** (§5) |
| Claim limits stated | **Yes** (§6) |
| Research-lead approval | **APPROVED** 16 November 2026 |
