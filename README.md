# A Blockchain-Enabled Privacy-Preserving Federated Learning Framework for ECG Arrhythmia Classification

Research implementation of a federated learning framework for ECG arrhythmia classification under an
AAMI-derived five-class taxonomy (N/S/V/F/Q), with differential privacy, homomorphic encryption, a
hash-chained audit layer, and robust-aggregation evaluation.

**All ten phases have been executed. Six of seven stop/go gates passed; G8 (robustness) did not.**

---

## Headline results

| RQ | Question | Outcome |
|---|---|---|
| **RQ1** | Centralized baseline performance and limits | Centralized test accuracy **0.8423 ± 0.0383**, macro-F1 **0.2947 ± 0.0495** — but **class S recall is 0.000 in every condition** |
| **RQ2** | Federated learning under heterogeneity | FedAvg severe **0.8523 / 0.3752**; FedProx indistinguishable at matched rounds. **54 % of the F3-over-F1 advantage is aggregation weight dispersion**, 46 % partition composition |
| **RQ3** | Privacy mechanisms | **HE is functionally lossless** (macro-F1 0.3681 vs 0.3752, error 1.4e-07) at 20.5× communication. **Whole-model client-level DP destroys the classifier** — no defensible operating point found |
| **RQ4** | Auditability and cost | Tamper-evident audit at **0.12 %** overhead (hash chain) or **4.03 %** (contract) with **bit-identical metrics** |
| **RQ5** | Robust aggregation | **GATE FAILED.** 51.7 % of runs diverged; 15 of 29 cells unmeasurable; divergence is rule-dependent, not attack-strength-dependent |

---

## Gate status

| Gate | Status | Scope limit |
|---|---|---|
| G0–G3 | **Passed** | Frozen split and manifests |
| G4 | **Passed** | With documented S-class defect |
| G5 | **Passed** | K = 5; one partition draw |
| G6 | **Passed** | Client-level DP; approved σ grid not run |
| G7 | **Passed** | L1 hash chain + L2 single-node EVM only |
| **G8** | **NOT PASSED** | 51.7 % of matrix unmeasurable |
| G9 | **Passed** | Eligible component set |
| G10 | **Passed** | With declared gaps |

---

## What was actually built

### Data and baselines (Phases 0–4)

- MIT-BIH Arrhythmia Database v1.0.0, 705 files verified against SHA-256 manifest.
- AAMI-derived five-class mapping; **record-independent** split (no record appears in more than one
  split), frozen as `bbcfa25c…`.
- 100,694 windows of 253 samples; training-only z-score normalisation.
- Compact 1-D CNN, **36,357 trainable parameters**.
- 30 baseline fits (centralized + local-only + two diagnostics), 5 seeds each.

**Key finding:** the model never predicts class S. Investigated in
`docs/PHASE_4_S_CLASS_FAILURE_INVESTIGATION.md`; two pre-registered ablations (selection rule, pooling
architecture) both failed their criteria. Accepted as a documented limitation, not fixed.

### Federated learning (Phase 5)

- FedAvg and FedProx across three non-IID partitions (IID-like, α = 0.5, α = 0.1).
- **G5 ablation A2** provided the project's strongest methodological result: replacing sample-count
  weights with uniform weights restored macro-F1 from 0.3752 to 0.3364, attributing **54 %** of the
  apparent non-IID benefit to aggregation weighting (one client held 37.1 % of the model).
- Control reproduced frozen F3 **exactly on 5/5 seeds**.

### Privacy (Phase 6)

- **CKKS homomorphic encryption** (N = 8192, 9 ciphertexts): functionally lossless, 1.4e-07 error,
  20.5× communication expansion.
- **Differential privacy**: full pipeline with a validated RDP accountant, per-client clipping, and
  frozen sensitivity. The result is **negative** — noise scales as `σ√d` with d = 36,357, giving
  47–377× noise-to-signal at the approved σ. No σ exists where both utility and privacy hold.
- DP+HE reports **exactly** the DP-only ε, confirming HE adds confidentiality and not differential
  privacy.

### Audit layer (Phase 7)

- **L1**: SHA-256 hash-chained append-only log. Detects interior alteration, deletion and reordering
  **at the exact index**. Truncation requires an external anchor — documented and tested.
- **L2**: single-node Ganache smart contract. Rejects unauthorised writers and replayed submissions.
- **44 personal-information tests** enforce a closed-whitelist schema: no waveform data, identifiers,
  tensors, keys, seeds, or per-client privacy diagnostics can reach a ledger.
- Metrics **bit-identical** across audited and unaudited runs.

> This is a Level 1 hash chain and a Level 2 local prototype. **It is not a distributed blockchain**
> and no consensus, decentralisation or Byzantine-resistance claim is made.

### Robust aggregation (Phase 8) — gate failed

- Pre-registered adversary model, baseline justification against K = 5, and frozen thresholds.
- 145 confirmatory runs: **75 (51.7 %) diverged**, leaving **15 of 29 cells unmeasurable**.
- Root cause established: divergence is **rule-dependent, not attack-strength-dependent** —
  identical counts at λ = 1.5, 2.5 and 5.0, and identical rule-by-rule (median 0 divergences,
  FedAvg 12/14, Krum/Multi-Krum 6/8).
- Norm-based detection is **blind to sign-flip** (0.00–0.12) while perfect on scaling (1.00).
- **R2 is not claimed.** The amended reduced-λ hypothesis (3B) was refuted; proposals 3A and 3C were
  never implemented.

### Integration and finalisation (Phases 9–10)

- Integration composes only components whose gates passed. **Robust aggregation is excluded by code
  guard**, not merely by documentation.
- Six of eight selected configurations **reproduced recorded results exactly** on re-evaluation.
- Clean-environment reproduction from a pinned lockfile verified.

---

## Honest scope statement

**This project reports four negative findings alongside its positives**, and they are findings, not
failures of execution:

1. **The model never learns class S** — an architectural and validation-support limitation.
2. **Whole-model client-level DP is not viable** at five clients with a 36k-parameter model.
3. **Robust aggregation is not deployable** at K = 5 — most rules diverge by arithmetic.
4. **Norm-based poisoning detection cannot see sign-flip attacks.**

No clinical, deployment, or production-security claim is made anywhere in this work.
See `docs/FINAL_RESEARCH_SUBMISSION_AUDIT.md` for the full claim-by-claim review.

---

## Repository layout

```text
project-root/
├── MASTER_RESEARCH_EXECUTION_SPECIFICATION.md   # authoritative specification
├── README.md
├── pyproject.toml
├── requirements-lock.txt                        # pinned, clean-venv verified
├── configs/
│   ├── models/                                  # frozen Phase 4 recipe + diagnostics
│   ├── federated/                               # F1–F5
│   ├── privacy/                                 # P1-ctl, P1-a..d, P2, P3-a/b
│   └── aggregation/                             # Phase 8 matrix (+ amended 3B)
├── contracts/AuditLog.sol                       # Level 2 audit contract
├── src/
│   ├── data/            # Phase 3 pipeline, canonical hashing
│   ├── models/          # CompactECGCNN (+ A1 pooling ablation)
│   ├── training/        # Phase 4 training/evaluation/metrics
│   ├── federated/       # FedAvg/FedProx round loop
│   ├── privacy/         # clipping, DP mechanism, CKKS, calibration
│   ├── blockchain/      # schema, commitments, ledger, EVM adapter
│   ├── aggregation/     # robust rules, attacks, defence accounting
│   └── integration/     # Phase 9 composition layer
├── scripts/             # one CLI per phase
├── tests/               # 198 tests
├── experiments/logs/    # per-run artefacts (git-ignored)
├── archive/             # Phase 10 defence package
└── docs/                # phase reports, audits, threat models
```

---

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt `
    --extra-index-url https://download.pytorch.org/whl/cu126
.\.venv\Scripts\python.exe -m pytest tests -q
```

Expected: **198 passed, 16 skipped**. The 16 skips are 15 Ganache contract tests (node not running)
plus one CPU-only test.

Data is not tracked. See `docs/reproducibility/REPRODUCIBILITY.md` for download, checksum
verification and regeneration commands.

---

## Documentation map

**Using this work:**
- [Research question evidence matrix](docs/RESEARCH_QUESTION_EVIDENCE_MATRIX.md) — start here
- [Final results tables](docs/PHASE_10_FINAL_RESULTS_TABLES.md)
- [Submission audit](docs/FINAL_RESEARCH_SUBMISSION_AUDIT.md)
- [Limitations](docs/limitations/LIMITATIONS.md)
- [Reproducibility](docs/reproducibility/REPRODUCIBILITY.md)

**By phase:**
- [G4 resolution](docs/PHASE_4_G4_RESOLUTION.md) · [S-class investigation](docs/PHASE_4_S_CLASS_FAILURE_INVESTIGATION.md)
- [Phase 5 results](docs/PHASE_5_RESULTS_AND_ANALYSIS.md) · [G5 diagnosis](docs/PHASE_5_G5_DIAGNOSIS.md)
- [Phase 6 results](docs/PHASE_6_RESULTS_AND_ANALYSIS.md) · [DP frontier](docs/PHASE_6_DP_FRONTIER_DIAGNOSTIC.md) · [Threat model](docs/PHASE_6_PRIVACY_THREAT_MODEL.md)
- [Phase 7 results](docs/PHASE_7_RESULTS_AND_ANALYSIS.md) · [Readiness](docs/PHASE_7_READINESS_REPORT.md) · [Security model](docs/threat_model/SECURITY_THREAT_MODEL.md)
- [Phase 8 confirmatory](docs/PHASE_8_CONFIRMATORY_REPORT.md) · [Failure analysis](docs/PHASE_8_FAILURE_ANALYSIS.md) · [Amendment proposal](docs/PHASE_8_PROTOCOL_AMENDMENT_PROPOSAL.md) · [3B results](docs/PHASE_8_AMENDED_3B_RESULTS.md)
- [Phase 9 integration](docs/PHASE_9_INTEGRATION_RESULTS.md) · [Combined threat model](docs/PHASE_9_COMBINED_THREAT_MODEL.md)
- [Phase 10 plan](docs/PHASE_10_FINAL_EVALUATION_PLAN.md) · [Execution status](docs/PHASE_10_EXECUTION_STATUS.md)
- [Experiment registry](docs/methodology/EXPERIMENT_REGISTRY.md)

**Governance:** the authoritative document is `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md`. Every
number in this repository traces to a frozen artefact and a recorded gate decision.
