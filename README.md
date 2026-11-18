# A Blockchain-Enabled Privacy-Preserving Federated Learning Framework for ECG Arrhythmia Classification

A ten-phase research study on federated learning for ECG arrhythmia classification under an
AAMI-derived five-class taxonomy (N/S/V/F/Q), evaluating differential privacy, homomorphic
encryption, a tamper-evident audit layer, and robust aggregation against malicious clients.

---

## What this study found

Six substantive findings. Four are negative, and they are reported as findings because they are
reproducible, mechanistically explained, and more informative than the positives.

### 1. Homomorphic encryption is free

CKKS (N = 8192, 9 ciphertexts) preserved classification exactly: **macro-F1 0.3681 vs 0.3752
plaintext**, approximation error **1.4 × 10⁻⁷**, at 20.5× communication cost and ≈4 % round time.

*Encryption did not cost accuracy. It cost bandwidth.*

### 2. Whole-model client-level DP destroys this classifier — and the arithmetic says why

At every tested configuration, differential privacy eliminated performance. The cause is not
implementation: noise scales as `σ·√d` across 36,357 coordinates, giving **47–377× noise-to-signal**
at the approved σ. Across σ ∈ {0.01, 0.05, 0.5, 1.0, 2.0, 4.0}, **no operating point preserves both
utility and privacy simultaneously**.

| σ | ε (δ=1e-5) | Macro-F1 | V recall |
|---:|---:|---:|---:|
| 0.01 | 44,112 | 0.2924 | 0.946 |
| 0.05 | 1,872 | 0.2327 | **0.000** |
| 1.0 | 57.3 | 0.1847 | 0.200 |

The σ = 0.05 row is instructive: its high accuracy (0.8707) is the **majority-class rate** — the
model predicts N for every window. Macro-F1 correctly falls below the σ = 0.01 result.

### 3. "Non-IID improves performance" is an aggregation-weighting artefact

FedAvg on severely skewed data (α = 0.1) scored **higher** than on IID-like data (0.3752 vs 0.3040
macro-F1). A controlled ablation replacing sample-count weights with uniform weights restored
macro-F1 to 0.3364.

**54 % of that advantage was one client holding 37.1 % of the model.** The remaining 46 % is
partition composition. The control reproduced the frozen baseline **exactly on 5/5 seeds**.

### 4. Robust aggregation fails at five clients — for two separable reasons

145 confirmatory runs on fresh seeds. **75 diverged (51.7 %)**, leaving 15 of 29 cells with no
comparable result.

| Failure mode | Rules affected | Repairable? |
|---|---|---|
| **Amplification** — updates grow round-over-round until BatchNorm or loss overflows | FedAvg, Multi-Krum, trimmed mean | **Partially** — a server step size reduced divergence to 36.2 % |
| **Selection collapse** — `n − f − 2` selects one client, who may be the adversary | Krum | **No** — needs `n ≥ 2f+3`, i.e. 7 clients |

The evidence for the split is strong: divergence was **identical at attack strengths λ = 1.5, 2.5 and
5.0** (a 3.3× change with zero effect), and **identical rule-by-rule** at every λ. Divergence depends
on the aggregation rule, not the attack.

A server step size of 0.25 reduced divergence from 51.7 % to 36.2 % — a real improvement — but left
Krum **completely unchanged**, confirming the two mechanisms are distinct and only one is
parameter-tunable.

### 5. Norm-based poisoning detection is blind to sign-flip

Detection rate **1.00 on scaling** attacks (norm-inflating) and **0.00–0.12 on sign-flip**
(norm-preserving). A norm threshold cannot see an attack that preserves magnitude. Any detection
claim must be restricted to norm-inflating attacks.

### 6. Training records can be made tamper-evident almost for free

A SHA-256 hash chain recorded all 50 rounds and 250 client submissions with **bit-identical model
metrics** at **0.12 %** overhead. Detects interior alteration, deletion and reordering at the exact
index. A single-node smart contract added submitter authorisation and replay rejection at 4.03 %.

> **Scope:** this is a Level 1 hash chain and a Level 2 local prototype — **not a distributed
> blockchain**. No consensus, decentralisation or Byzantine-resistance claim is made. Truncation and
> consistent rewrite require an external anchor to detect.

---

## The unifying finding

Three of the four negative results share one cause: **the study is limited to five clients and a
36,357-parameter model.**

- DP fails because noise scales with model size while there are too few clients to average it out.
- Robust aggregation fails because Byzantine bounds require `n ≥ 2f+3`, which five clients cannot
  satisfy.
- The S-class defect (below) stems from validation support of 61 windows across 4 records.

This is a coherent thesis-level conclusion, not a collection of separate misfortunes.

---

## The known limitation that runs through everything

**Class S recall is 0.000 in every condition** — centralized, federated, private, audited and
attacked. The model never predicts supraventricular beats.

This was investigated thoroughly (`docs/PHASE_4_S_CLASS_FAILURE_INVESTIGATION.md`,
`docs/PHASE_4_G4_RESOLUTION.md`). Two pre-registered interventions failed:

- **Selection is not the cause** — no epoch has S signal to select; max P(S) = 0.052 on real S beats.
- **Pooling is not the sole cause** — max+mean pooling reached at most 4 of 61 validation S windows.

**No result in this study may be read as evidence of S detection capability.**

---

## Baseline results

| Configuration | Accuracy | Macro-F1 | Verified |
|---|---:|---:|---|
| Centralized CNN | 0.8423 ± 0.0383 | 0.2947 ± 0.0495 | exact |
| FedAvg severe (α=0.1) | **0.8523 ± 0.0380** | **0.3752 ± 0.0448** | exact |
| FedProx severe | 0.8213 ± 0.0440 | 0.3390 ± 0.0445 | exact |
| HE-only | 0.8471 ± 0.0370 | 0.3681 ± 0.0482 | exact |
| HE+DP σ=1.0 | 0.5672 ± 0.2638 | 0.1847 ± 0.0562 | exact |
| HE+DP σ=2.0 | 0.4876 ± 0.2412 | 0.1648 ± 0.0453 | exact |

Test-set caveat: F support is **0**; S support is concentrated in record 232 (93.2 %). Macro-F1
covers N/S/V/Q only.

---

## Reproducibility

Every configuration re-evaluated in the final phase **reproduced its recorded value exactly** (to
1e-9). Frozen identifiers:

| Artefact | SHA-256 |
|---|---|
| Split manifest | `bbcfa25c7f0e0d903a6de44ccbaa6eb3fa0716253ff1ea730c912f99534d6f96` |
| Client manifest | `71dbcac37e2a605d5edcd0ce280acec60068a1f1defb4f403bc32a5e1cb8eba3` |
| F3 partition | `da8b96fa118e53bf53bee50b4f56bb6c281c65093b3c690058664f7b0cf8bbd4` |

A clean virtual environment rebuilt from `requirements-lock.txt` reproduced the full test suite
(**198 passed, 16 skipped**).

---

## Running this work

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt `
    --extra-index-url https://download.pytorch.org/whl/cu126
.\.venv\Scripts\python.exe -m pytest tests -q
```

Data is not tracked. Download, checksum verification and regeneration commands are in
[Reproducibility](docs/reproducibility/REPRODUCIBILITY.md).

---

## Phase record

| Phase | Subject | Outcome |
|---|---|---|
| 0–3 | Data, AAMI mapping, frozen split | Complete |
| 4 | Centralized baselines; S-class investigation | Complete — S defect documented and characterised |
| 5 | Federated learning; aggregation-weighting ablation | Complete — mechanism identified |
| 6 | DP and HE | Complete — HE positive, DP negative |
| 7 | Hash-chain and contract audit | Complete — L1/L2 scope |
| 8 | Robust aggregation | Complete — findings 4 and 5 above |
| 9 | Integration of validated components | Complete |
| 10 | Final evaluation and reproducibility package | Complete |

Gate-by-gate status, including the scope limits attached to each, is recorded in the per-phase
`*_EXECUTION_STATUS.md` documents. Those files are the authoritative record of what each gate
certified; this README summarises findings.

---

## Repository layout

```text
project-root/
├── MASTER_RESEARCH_EXECUTION_SPECIFICATION.md   # authoritative specification
├── requirements-lock.txt                        # pinned, clean-venv verified
├── configs/            # models, federated, privacy, aggregation
├── contracts/          # AuditLog.sol (Level 2 audit)
├── src/
│   ├── data/           # Phase 3 pipeline, canonical hashing
│   ├── models/         # CompactECGCNN (+ pooling ablation)
│   ├── training/       # training, evaluation, metrics
│   ├── federated/      # FedAvg / FedProx round loop
│   ├── privacy/        # clipping, DP mechanism, CKKS, calibration
│   ├── blockchain/     # schema, commitments, ledger, EVM adapter
│   ├── aggregation/    # robust rules, attacks, defence accounting
│   └── integration/    # Phase 9 composition layer
├── scripts/            # one CLI per phase
├── tests/              # 198 tests
├── archive/            # frozen hashes and final results
└── docs/               # phase reports, threat models, audits
```

---

## Documentation

**Start here:**
- [Research question evidence matrix](docs/RESEARCH_QUESTION_EVIDENCE_MATRIX.md) — every claim mapped to its evidence
- [Final results tables](docs/PHASE_10_FINAL_RESULTS_TABLES.md)
- [Submission audit](docs/FINAL_RESEARCH_SUBMISSION_AUDIT.md)
- [Limitations](docs/limitations/LIMITATIONS.md)

**The four negative findings:**
- [S-class investigation](docs/PHASE_4_S_CLASS_FAILURE_INVESTIGATION.md)
- [G5 aggregation-weighting ablation](docs/PHASE_5_G5_DIAGNOSIS.md)
- [DP frontier](docs/PHASE_6_DP_FRONTIER_DIAGNOSTIC.md)
- [Robust aggregation failure analysis](docs/PHASE_8_FAILURE_ANALYSIS.md) · [step-size follow-up](docs/PHASE_8_AMENDED_3D_PROPOSAL.md)

**By phase:**
- [Phase 5 results](docs/PHASE_5_RESULTS_AND_ANALYSIS.md) · [Phase 6 results](docs/PHASE_6_RESULTS_AND_ANALYSIS.md) · [Phase 6 threat model](docs/PHASE_6_PRIVACY_THREAT_MODEL.md)
- [Phase 7 results](docs/PHASE_7_RESULTS_AND_ANALYSIS.md) · [security model](docs/threat_model/SECURITY_THREAT_MODEL.md)
- [Phase 8 confirmatory](docs/PHASE_8_CONFIRMATORY_REPORT.md) · [amendment proposal](docs/PHASE_8_PROTOCOL_AMENDMENT_PROPOSAL.md)
- [Phase 9 integration](docs/PHASE_9_INTEGRATION_RESULTS.md) · [Phase 10 status](docs/PHASE_10_EXECUTION_STATUS.md)
- [Experiment registry](docs/methodology/EXPERIMENT_REGISTRY.md)

**Governance:** `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` is authoritative. Every number in this
repository traces to a frozen artefact and a recorded gate decision.
