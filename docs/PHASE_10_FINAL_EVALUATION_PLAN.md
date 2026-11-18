# Phase 10 — Final Evaluation and Defence Package: Plan

**Status:** Stage A — plan. **AWAITING RESEARCH-LEAD APPROVAL for E1 (SVDB).**
**Date:** 18 November 2026
**Authority:** `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` §28 Phase 10, §29 G10
**Gate on entry:** G0–G7 passed; **G8 NOT PASSED**; G9 passed.

---

## 1. The six Phase 10 obligations

| # | Obligation (§28) | Status entering Phase 10 |
|---|---|---|
| 1 | Freeze final model selection and evaluation code | Not done |
| 2 | Evaluate test data **once** for the selected configurations | Done incrementally per phase; requires a single frozen re-evaluation |
| 3 | Run external SVDB evaluation **separately if approved** | **Not approved, not run** |
| 4 | Generate final tables, figures, limitations and RQ answers | Partially: tables exist per phase; no consolidated set |
| 5 | Re-run reproducibility commands from a clean environment | Not done |
| 6 | Archive configurations, logs, hashes and reports | Not done |

---

## 2. Selected configurations for the final evaluation

Only configurations whose gates passed may be presented as results. The set is therefore:

| ID | Configuration | Gate | Role in thesis |
|---|---|---|---|
| **S1** | Centralized CNN (5 seeds) | G4 passed (documented S defect) | RQ1 baseline |
| **S2** | FedAvg IID-like (F1) | G5 | RQ2 |
| **S3** | FedAvg moderate (F2) | G5 | RQ2 |
| **S4** | FedAvg severe (F3) | G5 | RQ2 reference |
| **S5** | FedProx severe (F4) | G5 | RQ2 null result |
| **S6** | HE-only (P2) | G6 | RQ3 positive |
| **S7** | HE+DP σ=1.0 (P3-a) | G6 | RQ3 combined |
| **S8** | HE+DP σ=2.0 (P3-b) | G6 | RQ3 combined |
| **S9** | Audit B1 / B2 | G7 | RQ4 |

### 2.1 Explicitly excluded from the final evaluation

| Excluded | Reason |
|---|---|
| All Phase 8 robust-aggregation cells | **G8 NOT PASSED** — cannot be presented as a result |
| Amended 3B (λ = 1.5, 2.5) | Hypothesis refuted; development only |
| F5 | Conditional rule not met; never run |
| DP-only at approved σ | Approved grid not run |

**Note on Phase 8:** its findings remain reportable as a *failed gate with a diagnosed cause*
(RQ5), but no Phase 8 number may appear as an aggregation-performance result.

---

## 3. The SVDB decision (E1)

### 3.1 Facts established

| Fact | Evidence |
|---|---|
| SVDB is not present locally | `data/raw/` contains only MIT-BIH |
| PhysioNet is reachable (HTTP 200) | Verified this session |
| §8 requires **nine preconditions** before SVDB use | Spec §8, items 1–9 |
| E1 is described as *"only for a separately defined external evaluation unless a separate protocol is approved"* and *"if approved"* | §4, §8, §28 |

### 3.2 The nine preconditions and their current status

| # | Precondition | Status |
|---|---|---|
| 1 | Verify exact release and licence | Not done |
| 2 | Inspect annotation compatibility with the 5-class mapping | **Not done** — SVDB is a supraventricular database; its label distribution differs materially |
| 3 | Document missing/incompatible labels | Not done |
| 4 | Document sampling rates, channels, preprocessing | Not done |
| 5 | Establish defensible record/subject split | Not done |
| 6 | Freeze the evaluation protocol | Not done |
| 7 | Evaluate a checkpoint selected on MIT-BIH validation only | Available (S1–S5 checkpoints exist) |
| 8 | Do not tune on SVDB test labels | — |
| 9 | Report domain shift and label-coverage limitations | Not done |

**Eight of nine preconditions are unmet.**

### 3.3 Recommendation: **do not run E1**

| Consideration | Assessment |
|---|---|
| Time required for nine preconditions | Substantial — mapping audit, preprocessing alignment, protocol freeze |
| Scientific risk | **High**: SVDB is a supraventricular-focused database. Given the model's **S recall of 0.000**, an SVDB evaluation would likely report near-total failure on exactly the class that database emphasises |
| Value if run poorly | Negative — a rushed external evaluation with an unaudited mapping would be a weaker result than honestly declaring external validation out of scope |
| Spec permission | E1 is optional and gated on approval |

**Recommendation: declare external SVDB validation as future work (proposal F-5 in the submission
audit), and state clearly that no external generalisation evidence is claimed.** This is honest and
permitted.

**P10-1 requires your decision.** If you approve E1, it must be a separate protocol with its own
document, not folded into Phase 10.

---

## 4. Obligation 2 — "evaluate test data once"

This needs care. Test data has already been read once per seed in Phases 4, 5, 6, 7 and 9. The
Phase 10 obligation is to produce **one frozen, authoritative evaluation** rather than adding another
selective read.

### 4.1 Proposed approach

| Step | Action |
|---|---|
| 1 | Load each selected configuration's **already-selected** checkpoint (selection was made on validation) |
| 2 | Evaluate the test split **once**, in a single scripted pass |
| 3 | Record the resulting metrics as the **authoritative final table** |
| 4 | Verify they match the recorded per-phase values exactly; any mismatch is a defect |

**This is a re-evaluation for reporting integrity, not a new experiment.** It reuses the same
checkpoints and the same frozen evaluation code. If values differ from the recorded results, that is
a reproducibility finding and must be investigated, not overwritten.

### 4.2 What this does not do

- It does not re-select checkpoints using test data.
- It does not tune anything.
- It does not change any recorded per-phase result.

---

## 5. Obligations 1, 5, 6

### 5.1 Freeze code and configs (obligation 1)

| Artefact | Freeze method |
|---|---|
| `src/models/cnn1d.py` | SHA-256 recorded |
| `src/training/phase4.py`, `phase4_data.py` | SHA-256 recorded |
| `src/evaluation/phase4_metrics.py` | SHA-256 recorded |
| `src/federated/fedavg.py` | SHA-256 recorded |
| `src/privacy/*`, `src/blockchain/*`, `src/integration/*` | SHA-256 recorded |
| `configs/**/*.yaml` | SHA-256 manifest |
| Frozen split/client/F3 manifests | Already recorded; re-verified |

Recorded into `docs/PHASE_10_FREEZE_MANIFEST.md`.

### 5.2 Clean-environment reproducibility (obligation 5)

| Approach | Feasibility |
|---|---|
| Create a fresh venv from `requirements-lock.txt` and re-run a subset | **Feasible** — lockfile is pinned |
| Full re-run of every phase | Not feasible in scope |
| **Recommended: fresh venv + full test suite + one seed of one condition per phase** | Proves reproducibility without a multi-day re-run |

### 5.3 Archive (obligation 6)

Create `archive/` containing:
- freeze manifest with hashes;
- consolidated results JSON;
- final tables;
- reproduction commands;
- the test-output archive;
- a list of what is **deliberately excluded** (checkpoints are large; recorded by hash only).

---

## 6. What G10 will and will not certify

**Will certify:** all answerable RQs answered with evidence; limitations documented; reproducibility
package complete; configurations and hashes archived.

**Will not certify:**
- RQ5 success — **G8 failed**;
- external generalisation — **E1 not run**;
- any DP utility — negative finding;
- any clinical validity — S recall 0.000.

**G10 can be passed honestly with these gaps declared.** §29 requires "All RQs answered with evidence"
— and for RQ5 the evidence is that the gate failed.

---

## 7. Decisions required

| # | Decision | Recommendation |
|---|---|---|
| **P10-1** | Run SVDB external evaluation (E1) or declare it future work | **Declare future work** |
| **P10-2** | Approve the selected configuration set S1–S9 | Approve |
| **P10-3** | Approve the "evaluate once" approach as a reporting re-evaluation, not a new experiment | Approve |
| **P10-4** | Approve the clean-environment scope (fresh venv + tests + one seed per phase) | Approve |
| **P10-5** | Approve excluding all Phase 8 numbers from results tables | Approve (mandatory) |

**No final evaluation runs until P10-1 … P10-5 are resolved.**
