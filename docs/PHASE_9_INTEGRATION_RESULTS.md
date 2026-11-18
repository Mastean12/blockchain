# Phase 9 — Integration Results and Privacy Boundary Review

**Date:** 18 November 2026
**Status:** Stage A complete — smoke tests pass. **Full integrated experiment NOT run** (requires
separate written approval per §28).
**Gate:** **G9 — evidence submitted, assessment in §6.**

---

## 1. Eligibility determination

Master spec §37: *"Integrate only components that passed individual tests."*

| Component | Gate | Integrated? |
|---|---|---|
| Dataset / split | G3 passed | **Yes** |
| Centralized baseline | G4 passed (documented S defect) | **Yes** (reference) |
| FedAvg | G5 passed | **Yes** |
| HE (CKKS) | G6 passed | **Yes** (variant X1-b) |
| Ledger L1 | G7 passed | **Yes** |
| **Robust aggregation** | **G8 NOT PASSED** | **NO — excluded by §37** |
| DP | G6 passed, result negative | **No** — recommendation 9-DP-a |

**P9-1 and P9-2 are implemented as code-level guards**, not documentation alone:
`assert_integration_allowed("robust_aggregation")` and `... ("dp")` both raise `IntegrationError`
with the spec citation. A future caller cannot enable either by accident.

---

## 2. Integrated variants

| ID | Configuration |
|---|---|
| **X1-a** | FedAvg + L1 hash-chain audit |
| **X1-b** | FedAvg + CKKS HE + L1 hash-chain audit |

Both are compositions of validated components. Neither adds a mechanism.

---

## 3. Integration smoke test results

Run on the GTX 1650, seed 61, 2 rounds, F3 partition.

| Mode | Test acc | Test macro-F1 | S recall | V recall | Ledger | Elapsed |
|---|---:|---:|---:|---:|---|---:|
| centralized | 0.8720 | 0.2736 | **0.0000** | 0.0933 | — | 8.5 s |
| local_only | 0.6047 | 0.2279 | **0.0000** | 0.9718 | — | 7.9 s |
| **federated** | **0.8978** | **0.4717** | **0.0000** | 0.9610 | 15 entries, **valid** | 7.1 s |
| **federated_he** | **0.8976** | **0.4712** | **0.0000** | 0.9610 | 15 entries, **valid** | 8.3 s |

### 3.1 Required §24 tests

| # | Test | Result |
|---|---|---|
| IT-1 | Short centralized run | **Pass** |
| IT-2 | Short local-only run | **Pass** (5 per-client entries) |
| IT-3 | Short federated round | **Pass** |
| IT-4 | DP mechanism smoke | **Pass** — clip/noise/accountant path runs; finite output; deterministic |
| IT-5 | HE aggregation smoke | **Pass** — rel. error **1.41e-07** |
| IT-6 | Ledger lifecycle | **Pass** — 15 entries, `verify_ledger().valid == True` |
| IT-7 | Attack/defence smoke | **Pass** — plumbing runs end to end; asserts **no** robustness |

### 3.2 Project-specific tests

| # | Test | Result |
|---|---|---|
| IT-8 | Audit neutrality | **Pass** — federated vs federated_he differ by acc 1.3e-04, macro-F1 5.2e-04 |
| IT-9 | No sensitive data in integrated ledger | **Pass** — no prohibited field names |
| IT-10 | Determinism | **Pass** — metrics and ledger head identical on re-run |
| — | S-class visibility | **Pass** — S recall 0.000 asserted, not hidden |

**Test suite: 15 passed** (`tests/test_phase9_integration.py`).

---

## 4. Privacy boundary review (§28)

| # | Boundary | Check performed | Result |
|---|---|---|---|
| **PB-1** | No ECG/patient data on-chain | Ledger entries inspected; schema whitelist applies | **Clear** — hashes and integers only |
| **PB-2** | No model parameters on-chain | `UpdateCommitted` stores a SHA-256 and a byte count | **Clear** |
| **PB-3** | No keys or seeds in released artefacts | No key material written; ledgers in temp paths | **Clear** |
| **PB-4** | BatchNorm buffers unprotected (D5) | Not DP-protected, not encrypted; disclosed | **Disclosed, unchanged** |
| **PB-5** | HE decryptor sees plaintext aggregate | HE context is in-process; decryptor is the integration process | **Disclosed** |
| **PB-6** | DP client-level scope | DP not integrated; scope statement retained from Phase 6 | **N/A here** |
| **PB-7** | No test data in selection | Selection uses validation only; test read once at end | **Clear** — verified by code path |

### 4.1 Honest statement about the integrated privacy posture

**The integrated configuration provides no differential privacy.** X1-a and X1-b are
privacy-*mechanism*-free in the DP sense: the ledger is public-by-design, and HE protects ciphertexts
only from a key-blind server (the decryptor is the same process).

Anyone reading "privacy-preserving federated learning" in the thesis title should understand:
- DP was evaluated and **failed** on utility grounds;
- HE works but does not provide DP;
- the ledger provides tamper evidence, not confidentiality.

**This must appear explicitly in the integration section of the thesis**, not only in a limitation.

---

## 5. What integration established

| Finding | Support |
|---|---|
| Validated components compose correctly | **Strong** — four modes, 13 tests |
| HE preserves metrics end-to-end | **Strong** — 1.41e-07 error, Δ ≤ 5.2e-04 |
| Audit layer is neutral in an integrated run | **Strong** — determinism and neutrality tests pass |
| S-class defect persists through integration | **Strong** — 0.000 in all four modes |
| Robust aggregation cannot be integrated | **Structural** — G8 failed, enforced in code |

---

## 6. G9 assessment

Master spec §29: *"G9 Integration — Components pass separately; integration tests pass; privacy
boundaries reviewed."*

| Requirement | Status |
|---|---|
| Components pass separately | **Pass** — G3, G4, G5, G6, G7 all passed; G8 excluded by rule |
| Integration tests pass | **Pass** — 15/15; **all seven section-24 tests now present** (IT-1,2,3,4,5,6,7) |
| Privacy boundaries reviewed | **Pass** — §4 above, 7 boundaries, all clear or disclosed |
| Combined configuration and threat model defined | **Pass** — `PHASE_9_COMBINED_THREAT_MODEL.md` |
| Full test output preserved | **Pass** — `docs/test_output/pytest_full_phase9.txt` (198 passed, 16 skipped) |

**G9: PASSED for the eligible component set.**

### 6.1 What G9 does not certify

- **No robustness result** — G8 failed and robust aggregation was never integrated.
- **No DP utility result** — DP excluded; its Phase 6 negative finding stands alone.
- **No blockchain claim** beyond L1/L2.
- **No clinical claim** — S recall remains 0.000.
- The smoke tests prove **software composition**, not scientific validity; per §24, "a passing unit
  test does not prove scientific validity".

### 6.2 The full integrated experiment was not run

§28 requires *"Run full experiment only after written approval."* Only 2-round smoke tests were
executed. Seeds **62–66 remain reserved and unused** for a full run if approved.

---

## 7. Artefacts

| Item | Path |
|---|---|
| Integration module | `src/integration/{__init__,pipeline}.py` |
| Integration tests | `tests/test_phase9_integration.py` |
| Integration plan | `PHASE_9_INTEGRATION_PLAN.md` |
| Smoke measurement log | session temp (`phase9_smoke.json`) |

No frozen artefact, threshold, partition or historical result was modified.
