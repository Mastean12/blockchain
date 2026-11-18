# Phase 9 — Execution Status

**Last updated:** 18 November 2026
**Stage:** Stage A complete — integration layer built, smoke tests pass. **Full integrated experiment
not run** (requires separate written approval per §28).
**G9:** **PASSED** for the eligible component set (G3, G4, G5, G6-HE, G7).
**G8:** remains **NOT PASSED**; robust aggregation **excluded from integration**.

---

## 0. Where Phase 9 stands

| Item | State |
|---|---|
| Integration plan | Complete — `PHASE_9_INTEGRATION_PLAN.md` |
| Integration module | Complete — `src/integration/{__init__,pipeline}.py` |
| Integration tests | **15 passed** — `tests/test_phase9_integration.py`; all seven section-24 tests present |
| Smoke runs (4 modes, seed 61) | Complete |
| Privacy boundary review | Complete — 7 boundaries checked |
| Combined threat model | Complete — `PHASE_9_COMBINED_THREAT_MODEL.md` |
| Full test output archived | Complete — 198 passed, 16 skipped |
| Full integrated experiment | **NOT RUN** (needs approval) |
| Seeds 62–66 | **Reserved, unused** |
| Test suite | **198 passed, 16 skipped** (archived in `docs/test_output/pytest_full_phase9.txt`) |
| Frozen artefacts | **Unchanged** |
| Committed / pushed | **No** |

## 0.1 Eligibility enforced in code

| Component | Gate | Integrated |
|---|---|---|
| Dataset/split | G3 passed | Yes |
| Centralized baseline | G4 passed | Yes (reference) |
| FedAvg | G5 passed | Yes |
| HE | G6 passed | Yes (X1-b) |
| Ledger L1 | G7 passed | Yes |
| **Robust aggregation** | **G8 NOT PASSED** | **No — `assert_integration_allowed` raises** |
| DP | G6 passed, result negative | No — recommendation 9-DP-a |

## 0.2 Smoke results (seed 61, 2 rounds, GTX 1650)

| Mode | Test acc | Test macro-F1 | S recall | Ledger |
|---|---:|---:|---:|---|
| centralized | 0.8720 | 0.2736 | 0.0000 | — |
| local_only | 0.6047 | 0.2279 | 0.0000 | — |
| **federated** | 0.8978 | 0.4717 | 0.0000 | 15 entries, valid |
| **federated_he** | 0.8976 | 0.4712 | 0.0000 | 15 entries, valid, HE err 1.41e-07 |

Determinism confirmed; audit neutrality confirmed (Δ macro-F1 ≤ 5.2e-04).

## 0.3 G9 position

| G9 requirement | Status |
|---|---|
| Components pass separately | **Pass** |
| Integration tests pass | **Pass** (15/15) |
| Privacy boundaries reviewed | **Pass** (7/7 clear or disclosed) |

**G9 PASSED.** See `PHASE_9_INTEGRATION_RESULTS.md` §6 for scope limits.

## 1. Required decisions

| # | Decision | Recommendation |
|---|---|---|
| P9-1 | Confirm robust aggregation stays excluded | Confirm (already enforced) |
| P9-2 | Confirm 9-DP-a (DP excluded from integration) | Confirm (already implemented) |
| P9-3 | Approve running the full integrated experiment (seeds 62–66) | Optional — not required for G9 |
| P9-4 | Approve the combined threat model and privacy-posture statement | **Required before thesis writing** (PHASE_9_COMBINED_THREAT_MODEL.md) |

## 2. Integrity statement

- No frozen artefact, threshold, partition or historical result modified.
- G8 remains NOT PASSED; R2 not claimed.
- DP excluded by recommendation, not by silent omission.
- No clinical or robustness claim made from the integration.
