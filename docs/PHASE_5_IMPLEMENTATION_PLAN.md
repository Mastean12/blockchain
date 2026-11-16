# Phase 5 — Federated Learning Implementation Plan (Stage A)

**Status:** Stage A — preparation, protocol definition, infrastructure, tests. **Awaiting research-lead approval for Stage B execution.**  
**Date:** 15 November 2026  
**Authorised by:** Research lead, 15 November 2026 (Phase 5 authorisation; Phase 4 limitation formally accepted)  
**G4:** remains NOT PASSED. Not retrospectively revised.  
**Phase 6:** not started.

---

## 1. Mandatory preparation — completed reading

| Document | What it requires of Phase 5 |
|---|---|
| `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` | Stages 4–7: FedAvg first with 12 explicitly defined controls; three partition types; one justified FL alternative; controlled diagnostics; test used once; round-0 selection must be reported |
| `docs/protocol/RESEARCH_PROTOCOL.md` | Five client slots; FedProx as the single planned alternative; macro-F1 selection; whole-record grouping; IID-like terminology only |
| `docs/data_and_labels/SPLIT_POLICY.md` + `data/splits/` | Frozen split `bbcfa25c…` and client manifest `71dbcac3…` |
| `docs/PHASE4_EXECUTION_STATUS.md` | 30 baseline fits complete; S recall 0.000; G4 not passed |
| `docs/PHASE4_DIAGNOSTIC_ABLATION_RESULTS.md` | D1/D2 both left S at 0.000 |
| `docs/PHASE_4_S_CLASS_FAILURE_INVESTIGATION.md` | S failure is primarily a validation-population problem plus an architecture/pooling problem, **not** distribution shift |
| `configs/models/phase4_cnn_v1.yaml` | Frozen `compact_cnn_v1` recipe reused unchanged |

## 2. Current implementation state (inspected)

| Component | State |
|---|---|
| `src/federated/` | **Placeholder only** (`__init__.py`, docstring). No FL code exists. |
| `src/aggregation/` | **Placeholder only.** No aggregation code exists. |
| Client assignment | Frozen, 5 clients, greedy class-count balancing, training records only |
| Phase 4 reusable code | `phase4_data.py` (verified loader), `phase4.py` (model, training loop, metrics), `phase4_metrics.py` |
| Tests | 34 passing (baseline + diagnostics) |

**Conclusion:** Phase 5 requires new implementation. Nothing is being retrofitted into approved modules; `src/training/phase4*.py` are imported, not modified.

## 3. Approved client partition (frozen, unchanged)

| Client | Records | N | S | V | F | Q | Absent | S share |
|---|---|---:|---:|---:|---:|---:|---|---:|
| client_01 | 117, 124, 208, 220, 222, 230 | 11,139 | 337 | 1,040 | 378 | 2 | — | 2.61% |
| client_02 | 113, 116, 123, 200, 213, 228 | 11,678 | 68 | 1,520 | 364 | 0 | Q | 0.50% |
| client_03 | 105, 205, 207, 212, 231, 233 | 13,186 | 118 | 1,155 | 22 | 5 | — | 0.81% |
| client_04 | 114, 115, 201, 202, 203, 223, 234 | 14,743 | 320 | 1,180 | 22 | 4 | — | 1.97% |
| client_05 | 106, 121, 209, 214, 215, 219 | 13,269 | 394 | 1,006 | 3 | 2 | — | 2.69% |
| **Total** | 31 records | 64,015 | 1,237 | 5,901 | 789 | 13 | | |

Observed heterogeneity is already substantial at the S class (0.50% on client_02 vs 2.69% on
client_05, a 5.4× range) and extreme at F (3 to 378, a 126× range). This is the manifest that
Phase 4 local-only runs already used.

## 4. Design of the federated implementation

### 4.1 Module layout (new files only)

| File | Purpose |
|---|---|
| `src/federated/partitions.py` | Build / verify IID-like, moderate-skew and severe-skew partitions as **whole training records only**, with manifests and hashes |
| `src/federated/fedavg.py` | Round loop, local training, weighted aggregation, BN handling, round metrics |
| `src/federated/fedprox.py` | Proximal term (Li et al., 2020, *Federated Optimization in Heterogeneous Networks*, MLSys) as the single approved alternative |
| `scripts/build_phase5_partitions.py` | Generate and freeze non-IID partition manifests |
| `scripts/run_phase5_federated.py` | CLI, per-experiment output directories, resume |
| `configs/federated/*.yaml` | One config per condition |
| `tests/test_phase5_partitions.py`, `tests/test_phase5_fedavg.py` | Aggregation correctness, client isolation, data integrity |

### 4.2 Aggregation

Standard FedAvg: `w_global = Σ (n_k / N) · w_k` over participating clients, weighted by local
training-sample count. Aggregation operates on `state_dict` tensors in float64 accumulation,
then casts back. Integer buffers are excluded; BatchNorm running statistics are aggregated
**weighted by client sample count**, and `num_batches_tracked` is summed.

### 4.3 Reproducibility

- Global seeds 42–46, matching Phase 4, so comparisons are budget-matched.
- Per-round client sampling derived from `(seed, round)` so a resumed run reproduces the same
  participation sequence.
- `torch.use_deterministic_algorithms(True)`, cudnn deterministic.

## 5. What the approved documents determine vs what is missing

### 5.1 Already determined (no decision needed)

- Model: `compact_cnn_v1`, unchanged.
- Optimizer: AdamW, lr 1e-3, wd 1e-4.
- Loss: unweighted cross-entropy.
- Batch size 256.
- Selection: validation macro-F1 over N/S/V/F, epoch 0 evaluated, keep earliest on tie.
- Seeds 42–46.
- Five clients, whole-record grouping, training records only.
- FedProx as the single alternative.
- Test evaluated once after all choices are frozen.

### 5.2 Decisions required — NOT invented, requested below

The master spec lists twelve controls Phase 5 must define. Eight are covered by existing
approval. **Four are genuinely undecided**, and I will not invent them.

| # | Decision | Why it must be approved | Options |
|---|---|---|---|
| D1 | **Number of communication rounds** | Not specified anywhere in the protocol or master spec | 20 / 50 / 100 |
| D2 | **Local epochs per round** | FedAvg needs a local-epoch budget; spec lists it as a definition, not a value | 1 / 2 / 5 |
| D3 | **Participation fraction** | Spec requires it; nothing is frozen | All 5 always / 3-of-5 / 4-of-5 |
| D4 | **Partition construction for F2 and F3** | Only one frozen manifest exists; F2/F3 require new whole-record allocations, and the method (Dirichlet vs greedy-by-class) is an experimental design choice | Dirichlet over records with stated α, or deterministic class-concentrated assignment |

**Recommended defaults (for approval, not adopted):** D1 = 50 rounds, D2 = 2 local epochs,
D3 = all 5 clients participating each round (no dropout in the baseline), D4 = Dirichlet α = 0.5
for moderate skew and α = 0.1 for severe skew, applied to **record groups** rather than to
individual beats, with assignment solved so every group stays whole; the resulting manifests
are frozen and hashed before any training, and the achieved per-client class distribution is
reported rather than the nominal α.

Additional sub-decisions implied by D4 that also need approval:

- **D4a** Does F2/F3 keep the same five client identities, or is the count re-derived? (Recommendation: keep five.)
- **D4b** For severe skew, is an *absent class per client* required, or only strong skew? The spec says "severe label-skew **or** class-missing-client"; client_02 already lacks Q in the frozen manifest. (Recommendation: accept natural absence; do not force it.)

### 5.3 Additional uncertainties worth flagging

| # | Uncertainty | Impact |
|---|---|---|
| U1 | BatchNorm in federated settings: aggregating running statistics is standard FedAvg but known to be fragile under skew. The spec requires an explicit "normalization-layer handling" statement. | Must be stated in the config; diagnostic ablation candidate (Stage 7) |
| U2 | Optimizer state: reset each round vs persist locally. Standard FedAvg resets. | Spec requires an explicit choice; default = reset, and listed as a diagnostic |
| U3 | Whether "local-only" Phase 4 results are comparable to FL rounds at all given different epoch budgets (50 epochs local vs rounds × local epochs) | Reporting caveat, not a blocker |
| U4 | S-class: given Phase 4 findings, FL cannot be expected to fix S; the plan must pre-commit to reporting S honestly even if it stays 0.000 | Reporting rule, no decision needed |

## 6. Experiment matrix (Stage B)

| ID | Condition | Partition | Method | Purpose |
|---|---|---|---|---|
| `phase5_f1_fedavg_iidlike` | F1 | Frozen manifest `71dbcac3…` | FedAvg | Federated baseline |
| `phase5_f2_fedavg_moderate` | F2 | New frozen manifest (D4) | FedAvg | Moderate label skew |
| `phase5_f3_fedavg_severe` | F3 | New frozen manifest (D4) | FedAvg | Severe skew / class-missing |
| `phase5_f4_fedprox_severe` | F4 | Same manifest as F3 | FedProx | Justified alternative, matched partition and budget |
| `phase5_f5_fedprox_moderate` | F5 | Same manifest as F2 | FedProx | Only if F4 shows a gap worth isolating |

F5 is included conditionally, mirroring the Phase 4 D3 rule: it runs only if F4 shows a
meaningful FedAvg–FedProx difference on F3; otherwise it is not run and the omission is
documented.

Every condition is run with seeds 42–46, producing 5 independent runs per condition.

## 7. Metrics

Per round, per run:
- validation loss and validation macro-F1 over N/S/V/F, plus validation balanced accuracy
  (descriptive, so a future selection discussion has evidence without rerunning);
- test metrics are **not** computed per round.

Per run, once, at the selected round:
- accuracy, macro and weighted precision/recall/F1 with the included class set stated;
- per-class precision, recall, F1 and support for N/S/V/F/Q;
- confusion matrix in fixed order;
- checkpoint and its SHA-256.

Systems cost:
- wall-clock per round and total;
- bytes communicated per round and cumulative (aggregate model size × participants × 2 directions);
- local epochs and samples processed.

## 8. Convergence and comparison plan

- Convergence curve of validation macro-F1 per round, mean ± SD across seeds.
- Round-0 reporting: if validation selection picks round 0, it is reported as such and
  investigated, not silently replaced.
- Comparison to Phase 4: centralized (0.8510 test acc, 0.2990 macro-F1, S recall 0.000) and
  local-only per client, both already measured on the same frozen test set.

## 9. Data integrity controls

- Loader re-verifies split `bbcfa25c…` and client `71dbcac3…` on every run.
- New F2/F3 manifests carry `parent_split_manifest_sha256` and are written with their own
  SHA-256, and assert: union of clients == frozen training records; no record in two clients;
  no validation or test record appears in any client.
- Test is read exactly once per run, after the selected round is fixed.

## 10. Automated tests (required before Stage B)

| Test | Asserts |
|---|---|
| Aggregation correctness | Equal-weight and count-weighted means match closed-form on synthetic tensors; BN buffers aggregate by count; `num_batches_tracked` sums |
| Single-client FedAvg | FedAvg over one client equals that client's local model exactly |
| Client isolation | No record, and no window, appears in two client partitions |
| Data integrity | Every partition's union == frozen training records; validation/test disjoint from all clients |
| Manifest hashing | Partition manifests hash deterministically and reject tampering |
| Resume | An interrupted run resumes to an identical result from the same seed |
| Round-0 policy | Selection at round 0 is reported, not replaced |

## 11. Execution environment

Colab Tesla T4 via the existing notebook workflow, `/usr/bin/python3` (has torch), Drive for
artefacts. Expected cost estimate: one F1 run ≈ 50 rounds × 2 local epochs × 5 clients; on a
T4 with 256-sample batches across ~64k training windows this is roughly 640 epoch-equivalents
of training per run, i.e. orders of magnitude larger than a Phase 4 local fit. **This is why
D1/D2 matter financially as well as scientifically** — I will not start Stage B without them.

## 12. Deliverables produced in Stage A

- This plan.
- `docs/PHASE_5_EXECUTION_STATUS.md` (status stub, marked Stage A).
- Frozen-partition builder + verifier, FedAvg with resume, FedProx.
- Configs for F1 (fully specified) and F2–F4 (marked `pending approval` for D1–D4).
- Tests.

## 13. Stop point

Stage A ends here pending research-lead answers to **D1–D4** (and acknowledgement of D4a/D4b,
U1, U2). On approval, Stage B executes F1 first, reviews it, then F2/F3, then F4/F5 by the
pre-declared rule. No Phase 6 work begins, G4 is not restated as passed, and nothing is
committed without explicit authorisation.
