# Phase 10 — Execution Status and G10 Assessment

**Last updated:** 18 November 2026
**Stage:** Final evaluation and defence package assembled.
**G10:** see §3 — **PASSED with declared gaps.**
**G8:** remains **NOT PASSED**; R2 not claimed; external SVDB evaluation not run.

---

## 0. The six Phase 10 obligations

| # | Obligation | Status | Evidence |
|---|---|---|---|
| 1 | Freeze model selection and evaluation code | **Complete** | `archive/freeze_manifest.json` — 18 sources, 201 configs, 3 manifests |
| 2 | Evaluate test once for selected configurations | **Complete for 6 of 8** | `archive/final_results.json`; 6/6 reproduced exactly |
| 3 | External SVDB evaluation if approved | **NOT RUN** — not approved (§4) | — |
| 4 | Generate final tables, figures, limitations, RQ answers | **Complete** | `PHASE_10_FINAL_RESULTS_TABLES.md`, `RESEARCH_QUESTION_EVIDENCE_MATRIX.md`, `FINAL_RESEARCH_SUBMISSION_AUDIT.md` |
| 5 | Re-run reproducibility from a clean environment | **Complete** | §2 |
| 6 | Archive configs, logs, hashes and reports | **Complete** | `archive/` |

---

## 1. What was frozen

| Artefact class | Count | Location |
|---|---:|---|
| Source modules (SHA-256) | 18 | `archive/freeze_manifest.json` |
| Configuration files (SHA-256) | 201 | same |
| Frozen manifests | 3 | same |
| Selected checkpoints (SHA-256) | 30 | `archive/final_results.json` |

**Canonical manifest hashes re-verified unchanged:**
split `bbcfa25c…`, client `71dbcac3…`, F3 `da8b96fa…`.

> Note: `freeze_manifest.json` also records **file-byte** hashes, which differ from the canonical
> **content** hashes by design. Both are recorded; the canonical ones govern.

---

## 2. Reproducibility from a clean environment

A fresh virtual environment was created from `requirements-lock.txt` and the suite re-run.

| Check | Result |
|---|---|
| Fresh venv -> lockfile install | **Succeeded** (after correcting the lockfile, see below) |
| Full test suite in fresh venv | **198 passed, 16 skipped** — identical to the primary environment |
| One configuration per phase re-evaluated | **All reproduced exactly** |

### 2.0 Defect found and fixed during this check

The first clean-venv run gave **198 passed, 1 skipped, 15 ERRORS**. The 15 errors were the Phase 7
contract tests failing on import web3: **web3, eth-account, eth-abi, pywin32 and
websockets were installed in the working environment during Phase 7 but were never added to

equirements-lock.txt.**

Consequence had it gone unnoticed: the lockfile could not reproduce the full test suite, and the
contract tests would *error* rather than *skip* in any fresh environment.

The lockfile was corrected (25 blockchain-audit entries added) and the clean venv re-verified:
**198 passed, 16 skipped**.

### 2.1 Clean-environment evaluation

| Configuration | Accuracy | Macro-F1 | Matches recorded |
|---|---:|---:|---|
| S1 centralized seed 42 | 0.843071 | 0.305444 | **Yes** |
| S4 F3 seed 42 | 0.872782 | 0.399288 | **Yes** |
| S6 P2 seed 42 | 0.882619 | 0.422044 | **Yes** |

### 2.1 Test result

Archived in `docs/test_output/pytest_full_phase9.txt`: **198 passed, 16 skipped** in the primary
environment. The 16 skips are 15 Ganache contract tests (node not running) plus one CPU-only test.

---

## 3. G10 assessment

Master spec §29: *"G10 Defence — All RQs answered with evidence, limitations and reproducibility
package complete."*

| Component | Status |
|---|---|
| All RQs answered with evidence | **Yes**, with RQ5 answered as a failed gate (§3.1) |
| Limitations documented | **Yes** — `LIMITATIONS.md`, plus per-phase scope statements |
| Reproducibility package complete | **Yes** — freeze manifest, clean-venv run, exact reproduction |
| Configurations and hashes archived | **Yes** |
| Final tables and RQ answers generated | **Yes** |

**G10: PASSED with declared gaps.**

### 3.1 Is "RQ5 answered" satisfied by a failed gate?

The specification requires evidence, not success. RQ5 asked whether a robust aggregator can mitigate
attacks while preserving honest utility at acceptable cost. The evidence answers it:

- at K = 5 on this partition, most candidate rules **diverge** (51.7 % of runs);
- divergence is **rule-dependent, not attack-strength-dependent** (λ-insensitive across 1.5, 2.5, 5.0);
- the norm-based detection method is **blind to sign-flip** (0.00–0.12);
- **no defensible operating point** exists in the explored region.

That is a complete, evidenced answer. It is negative, and it is reported as such.

### 3.2 Gaps that G10 does **not** paper over

| # | Gap | Declared in |
|---|---|---|
| 1 | **G8 NOT PASSED** | everywhere |
| 2 | **R2 not claimed** | confirmatory report, matrix |
| 3 | **SVDB external evaluation not run** | §4 |
| 4 | **F1/F2 checkpoints lost** — recorded values only | §5 |
| 5 | S recall 0.000 in every condition | all tables |
| 6 | Approved DP σ grid not run | Phase 6 docs |
| 7 | 3A and 3C never implemented | failure analysis |

---

## 4. External SVDB evaluation — decision required

§8 lists **nine preconditions**; **eight are unmet** (no local SVDB, mapping not audited,
preprocessing not aligned, protocol not frozen). E1 is described in the spec as optional
("only for a separately defined external evaluation unless a separate protocol is approved") and
"if approved".

**Recommendation, not executed: declare external generalisation as future work.** Given the model's
S recall of 0.000, an SVDB evaluation (a supraventricular database) would likely report near-total
failure on exactly the class that database emphasises — a negative result that would consume
substantial effort to produce honestly.

**P10-1 remains open for the research lead.**

---

## 5. Evidence gap: F1/F2 checkpoints

| Aspect | Detail |
|---|---|
| Missing | `experiments/logs/phase5/f1/` and `/f2/` (Colab-produced, never transferred) |
| Affected | S2 (F1) and S3 (F2) — two of eight selected configurations |
| Consequence | Their values are frozen recorded results, **not** independently re-derived in Phase 10 |
| Does it invalidate RQ2? | **No** — the load-bearing RQ2 result is ablation A2 on F3, fully verified |
| Remedy if required | Re-run F1/F2, 5 seeds each, ≈2.5 h on the GTX 1650 |

Recorded in `archive/final_results.json` under `evidence_gaps`.

---

## 6. Integrity statement

| Check | Result |
|---|---|
| Frozen split / client / F3 hashes | **Unchanged** |
| Frozen thresholds (0.05 / 0.10 / 0.90) | **Unchanged** |
| Phase 1–8 recorded results | **Unchanged** (re-evaluation confirmed, not overwritten) |
| New experiments run | **None** (only re-evaluation of existing checkpoints) |
| Development / confirmatory pooling | **None** |
| G8 | **NOT PASSED** |
| R2 | **Not claimed** |
| Committed / pushed | **No** |

---

## 7. Decisions still open

| # | Decision | Recommendation |
|---|---|---|
| **P10-1** | SVDB external evaluation | **Declare future work** |
| **P10-2** | Approve selected configuration set S1–S9 | Approve |
| **P10-3** | Approve "evaluate once" as reporting re-evaluation | Approve (executed) |
| **P10-4** | Approve clean-environment scope | Approve (executed) |
| **P10-5** | Exclude all Phase 8 numbers from results tables | Approve (implemented) |
| **F-1** | Correct Phase 8 divergence figure to 75 / 51.7 % | **Mandatory** |

---

## 8. Deliverables index

| Document | Purpose |
|---|---|
| `PHASE_10_FINAL_EVALUATION_PLAN.md` | Plan and obligations |
| `PHASE_10_FINAL_RESULTS_TABLES.md` | Eight final tables |
| `PHASE_10_EXECUTION_STATUS.md` | This document |
| `archive/freeze_manifest.json` | Code and config hashes |
| `archive/final_results.json` | Per-seed and aggregate final results |
| `archive/EXCLUDED_FROM_RESULTS.md` | What is deliberately absent and why |
| `docs/test_output/pytest_full_phase9.txt` | Full test output |
| `RESEARCH_QUESTION_EVIDENCE_MATRIX.md` | RQ-by-RQ evidence for writing |
| `FINAL_RESEARCH_SUBMISSION_AUDIT.md` | Submission readiness audit |
