# Phase 9 — Integration Plan

**Status:** Stage A — **AWAITING RESEARCH-LEAD APPROVAL** before the full integrated experiment.
**Date:** 18 November 2026
**Authority:** `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` §22 (X1), §24, §28 Phase 9, §29 G9
**Gate on entry:** G0–G7 passed (G4 and G6 scoped). **G8 NOT PASSED.**

---

## 1. The blocking determination

Master spec §37 states:

> **"Integrate only components that passed individual tests."**

and §22 defines the integrated condition as:

> "**X1** — Integrated selected configuration — **Only after independent component validation**"

Applying this strictly:

| Component | Independent gate | Eligible for integration? |
|---|---|---|
| Dataset, split, preprocessing | G3 **passed** | **YES** |
| Centralized baseline | G4 **passed** (documented S defect) | **YES** — reference only |
| FedAvg / FedProx | G5 **passed** | **YES** |
| DP mechanism | G6 **passed** | **YES**, but see §1.2 |
| HE mechanism | G6 **passed** | **YES** |
| Ledger (L1/L2) | G7 **passed** | **YES** |
| **Robust aggregator (R1 baselines / R2)** | **G8 NOT PASSED** | **NO — ineligible** |

### 1.1 Consequence

**X1 cannot include robust aggregation.** The component failed its gate, so under §37 it must be
excluded. Phase 9 therefore integrates **G4 + G5 + G6 + G7 only**.

This is not a scope reduction chosen for convenience; it is the specification's own rule. Recording
it explicitly prevents an integrated run from quietly implementing a robustness claim the project
does not have.

### 1.2 DP eligibility caveat

G6 passed, but its **result was negative**: whole-model client-level DP destroys this classifier at
every tested configuration. The mechanism is *technically validated* (accountant gated, toy tests
pass, ε computed correctly) but *scientifically unproductive*.

Two options, and the choice belongs to the research lead:

| Option | Integrated DP configuration | Consequence |
|---|---|---|
| **9-DP-a** | Do **not** integrate DP | Integrated result stays usable; DP remains a separate negative finding |
| **9-DP-b** | Integrate DP at the diagnostic σ = 0.01 | Demonstrates composition end-to-end, but the integrated model will be degraded; must be labelled a **composition demonstration, not a utility result** |

**Recommendation: 9-DP-a.** Integrating a mechanism already shown to destroy the model adds cost and
invites the reader to read the degraded accuracy as an integration failure. The DP finding is
stronger standing alone.

---

## 2. What the integrated configuration is

### 2.1 Components and configuration

| Element | Setting | Source |
|---|---|---|
| Partition | F3 severe `da8b96fa…` | frozen G3 |
| Client count | 5 | frozen |
| Model | `compact_cnn_v1`, 36,357 params | frozen |
| Rounds | 50, 2 local epochs | frozen |
| Seeds | **fresh set, one seed for smoke; 5 seeds only if approved** | see §4 |
| Aggregation | **FedAvg only** (no robust rule) | G5 |
| Privacy | **none** (recommendation 9-DP-a) | G6 not integrated |
| Encryption | **HE optional** — see 9-HE below | G6 |
| Audit | **L1 hash chain**, optionally L2 contract | G7 |
| Selection | validation macro-F1, frozen rule | frozen |

### 2.2 Two integration variants

| ID | Configuration | Purpose |
|---|---|---|
| **X1-a** | FedAvg + L1 hash-chain audit | Minimum defensible integration |
| **X1-b** | FedAvg + HE + L1 audit | Adds encryption; measures end-to-end HE cost in a full round |

Both are **compositions of already-validated components**. Neither adds a new mechanism.

### 2.3 What is explicitly excluded and why

| Excluded | Reason |
|---|---|
| Robust aggregators (R1) | G8 not passed (§37) |
| R2 proposed aggregator | Not defined, not validated |
| DP (per recommendation 9-DP-a) | Gate passed but result negative |
| Attack conditions | They belong to the failed Phase 8 protocol |
| L2 contract | Available, but L1 suffices for X1; L2 can be an option |

---

## 3. Required integration smoke tests (§24)

The specification names seven. All must exist and pass before G9 can be assessed.

| # | Test | What it proves | Implementation |
|---|---|---|---|
| **IT-1** | One short centralized training run | Model + data + metrics compose | `run_integrated(..., mode="centralized", rounds=2)` |
| **IT-2** | One short local-only run | Per-client training isolation | `mode="local_only"` |
| **IT-3** | One short federated round | FedAvg aggregation correctness | `mode="federated", rounds=2` |
| **IT-4** | DP mechanism smoke test | Clip → noise → aggregate path | Reuse `apply_rejection_policy`-free DP path; assert finite + ε reported |
| **IT-5** | HE aggregation smoke test | CKKS encrypt → weighted sum → decrypt | Assert rel. error < 1e-5 |
| **IT-6** | Ledger lifecycle smoke test | Register → round → commit → close → seal → verify | Assert `verify_ledger().valid` |
| **IT-7** | Attack/defence smoke test | Attack construction + detection accounting runs | Assert detection/FPR computed, **not** that a defence succeeds |

**IT-7 is deliberately narrow.** It tests that the attack/defence *plumbing* works. It does not and
must not imply robustness, because G8 failed.

### 3.1 Additional integration tests required by this project

| # | Test | Why |
|---|---|---|
| **IT-8** | Integrated run is audit-neutral | B0 vs X1-a metrics bit-identical (as Phases 5/7 established) |
| **IT-9** | No sensitive data in the integrated ledger | Re-run the Phase 7 schema assertions over integrated entries |
| **IT-10** | Determinism on re-run | Same seed twice → identical metrics and head hash |

---

## 4. Seeds and approval

### 4.1 Seed allocation

| Purpose | Seeds | Rule |
|---|---|---|
| Integration smoke | **61** | One short run per variant |
| Full integrated experiment (if approved) | **62–66** | Only after written approval |

Seeds 61–66 must be verified absent from all existing logs before use, as with previous allocations.

### 4.2 Two-stage approval

§28 Phase 9 says: *"Run full experiment only after written approval."*

1. **Stage A (this document + smoke tests).** No full run.
2. **Stage B (full integrated experiment).** Requires separate written approval after smoke results
   are reviewed.

---

## 5. Privacy boundary review (§28: "Review logs, artifacts and privacy boundaries")

Required before G9. The review must confirm:

| # | Boundary | Check |
|---|---|---|
| PB-1 | No ECG/patient data on-chain | Schema assertions over integrated ledger |
| PB-2 | No model parameters on-chain | Hash-only entries |
| PB-3 | No keys/seeds in released artefacts | Artifact scan |
| PB-4 | BatchNorm buffers remain unprotected (D5) and this is disclosed | Documentation |
| PB-5 | If HE used, the decryptor sees the plaintext aggregate | Documentation |
| PB-6 | If DP integrated, client-level scope stated | Documentation |
| PB-7 | No cross-phase leakage: no test data in selection | Code inspection |

---

## 6. What G9 will and will not certify

**Will certify:** the validated components compose correctly; the integration tests pass; the
privacy boundaries were reviewed; the integrated run is audit-neutral and reproducible.

**Will not certify:** any robustness result (G8 failed); any DP utility result (negative, not
integrated); any blockchain claim beyond L1/L2; any clinical claim.

---

## 7. Decisions required

| # | Decision | Recommendation |
|---|---|---|
| **P9-1** | Confirm robust aggregation is **excluded** from integration per §37 | **Confirm** |
| **P9-2** | Choose 9-DP-a (exclude DP) or 9-DP-b (include at σ=0.01) | **9-DP-a** |
| **P9-3** | Approve X1-a and X1-b variants | Approve |
| **P9-4** | Approve seed 61 for smoke, 62–66 reserved | Approve |
| **P9-5** | Approve two-stage process (smoke first, full run only after review) | Approve |

**No full integrated experiment runs until P9-1…P9-5 are resolved.**
