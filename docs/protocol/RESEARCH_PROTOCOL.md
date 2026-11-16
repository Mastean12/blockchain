# Research Protocol

**Protocol version:** 1.0  
**Status:** Approved by the research lead on 13 November 2026, with the documented source-access limitations below  
**Authority:** `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md`  
**Phase:** 1 — Literature and protocol freeze

## 1. Purpose and scope

This protocol proposes a reproducible research evaluation of ECG heartbeat classification under an AAMI-derived five-class grouping, comparing centralized and federated learning and evaluating the predictive-utility and systems-cost effects of DP, HE, blockchain-backed auditing, and robust aggregation.

The study is an offline research prototype. It is not a clinically validated diagnostic device and will make no claim of clinical safety, deployment readiness, formal EC57 compliance, distributed consensus, or formal differential privacy unless the relevant evidence and assumptions support that claim.

## 2. Research questions

These are adopted verbatim from the master specification and are fixed for the study unless the research lead approves a protocol amendment.

1. **RQ1 — Classification performance:** How accurately can deep learning detect and classify ECG heartbeats under the AAMI five-class grouping, using centralized and federated training?
2. **RQ2 — Federated learning under heterogeneity:** How does federated learning compare with centralized and local-only training under heterogeneous (non-IID) client data, and which factors explain any performance gap?
3. **RQ3 — Privacy–utility–cost trade-off:** What are the effects of differential privacy and homomorphic encryption, individually and jointly, on predictive utility, privacy guarantees, computation, communication and model convergence?
4. **RQ4 — Auditability and blockchain cost:** Can a blockchain-backed audit mechanism make federated training operations verifiable and auditable, and what are its gas, latency, throughput, storage and operational costs?
5. **RQ5 — Robust aggregation:** Can the proposed aggregation mechanism mitigate specified malicious-client attacks while preserving benign-client utility under non-IID ECG data, and at what computational and communication cost?

## 3. Data and label scope

- **Primary dataset:** MIT-BIH Arrhythmia Database, exact release and file checksums to be recorded before use.
- **External evaluation:** SVDB is out of the primary training protocol. If separately approved, evaluate a checkpoint selected using MIT-BIH validation only; describe it as external evaluation, not multi-dataset federated training.
- **Task:** AAMI-derived N/S/V/F/Q heartbeat classification using the approved mapping and the 44 non-pacemaker-record protocol described by [de Chazal et al. (2004)](https://doi.org/10.1109/TBME.2004.827359). Exclude records 102, 104, 107 and 217 before any split or training. The audited mapping assigns `/` and `f` to Q, but those symbols have no observations in the included records; Q support is 15 annotations across 5 records.
- **Data handling:** Raw data remain immutable and separate from processed data. Phase 2 acquisition/audit and Phase 3 splitting/preprocessing are complete; no model training has begun.
- **Records 201/202:** Keep grouped because they originate from the same subject. Other patient identity assumptions must be documented; do not claim verified patient independence without evidence.
- **Annotation mapping, symbol exclusions, paced-record handling and Q policy:** approved at G2 on 13 November 2026. Beat-window and preprocessing choices remain open for Phase 3. No unknown symbol may be silently mapped or discarded.
- **EC57 access:** The full licensed standard was not provided or accessed in this workspace. The research lead approved this protocol with that limitation recorded. Do not make clause-level or compliance claims; any later decision relying on EC57 clauses requires source review.

## 4. Evaluation design

### 4.1 Planned comparison sequence

| Block | Planned condition | Purpose |
|---|---|---|
| B0 | Majority-class predictor | Validate labels and metric pipeline |
| B1 | One documented 1D CNN trained centrally | Reference utility |
| B2 | Same model trained independently per client | Local-only reference |
| F1 | FedAvg on an IID-like whole-record client partition | Federated baseline |
| F2 | FedAvg on a moderate label-skew partition | Heterogeneity comparison |
| F3 | FedAvg on a severe label-skew or class-missing-client partition | Stress condition |
| F4 | FedProx | Research-lead selection; compare against FedAvg under matched partitions and budget |
| P1 | DP-only, predeclared configurations | Privacy–utility and cost |
| P2 | HE-only aggregation | Encryption overhead and utility |
| P3 | HE+DP | Combined mechanism after each component is independently validated |
| L1 | Hash-chain audit | Tamper-evident logging baseline |
| L2 | Local Ganache smart-contract prototype | Research-lead selection; contract verification and local-chain costs, without production-consensus claims |
| R1/R2 | Selected robust baselines and candidate aggregator | Clean and attack-condition comparison |
| E1 | Frozen MIT-BIH-selected model on SVDB, only if approved | Separate external evaluation |

This table defines the planned sequence, not authorization to execute it. Component experiments are gated by the data, baseline, privacy, blockchain and robustness approvals in the master specification.

### 4.2 Partitions and client distribution

- Use record/group-level partitions; never split beats from one record across train, validation and test.
- Assign whole records/groups to clients. Report each client’s record IDs, beat count, N/S/V/F/Q support and absent classes.
- Compare IID-like, moderate non-IID, and severe non-IID distributions. Call a partition “IID-like,” not “IID,” if whole-record allocation cannot establish exact IID.
- The research lead approved a 70/15/15 group split with seed 42, grouping 201/202. The exact record lists and counts are frozen in [SPLIT_POLICY.md](../data_and_labels/SPLIT_POLICY.md) and its hashed manifest. No metric-based retries are permitted.
- Use five client slots, selected by the research lead. Client manifests assign training groups only, using deterministic greedy class-count and record-load balancing. The manifests and per-client class distributions are frozen with the split. No beat-level distribution across clients is permitted.
- The test set is excluded from fitting, tuning, threshold selection, checkpoint selection and client training.

### 4.3 Model and training controls

- The research lead approved the `compact_cnn_v1` architecture in `configs/models/phase4_cnn_v1.yaml`: input `(B,1,253)`, three Conv1d blocks (32/64/128 channels; kernels 7/5/3), BatchNorm1d/ReLU, max-pooling after the first two blocks, adaptive-average pooling, dropout 0.3 and a five-class linear head (36,357 trainable parameters).
- Use AdamW (learning rate 0.001, weight decay 0.0001), unweighted cross-entropy, batch size 256, maximum 50 epochs, and no augmentation or class weighting for this baseline.
- Start with the mandatory majority baseline, then the configured CNN centrally and independently on each of the five frozen training clients. Do not tune repeatedly against test results.
- Keep architecture and training budgets matched across methods where possible; record any unavoidable differences.
- Validation data alone determine hyperparameters, early stopping and checkpoint selection. Because Q is absent from validation, select checkpoints by macro-F1 over the supported classes N/S/V/F; do not substitute zero for Q or describe the selection score as five-class macro-F1. Stop after eight epochs without improvement, evaluate epoch 0, and retain the earliest epoch on a tie.
- The frozen test split lacks F. Report its F metrics as not estimable, and do not claim five-class test macro-F1. Report test macro metrics only over classes with test support, with the included class set and support shown.
- Preserve and report round-0 selection if it wins the predeclared validation rule; investigate rather than silently substitute another checkpoint.
- Use seeds 42–46 for the approved Phase 4 baselines. Report every seed and the mean and standard deviation. Multiple seeds on one split are not independent subject-level validation.

### 4.4 Phase 3 preprocessing freeze

- Use the `MLII` channel at the native 360 Hz sampling rate, checked from each record header.
- Center 253-sample windows on the expert reference annotation, spanning offsets -90 through +162 samples (-0.25 to +0.45 seconds). Drop and count boundary windows.
- Apply no resampling, filtering or baseline removal.
- Fit one global z-score mean and standard deviation using training windows only, then apply those parameters unchanged to validation and test.
- Treat `~` as signal-quality metadata; report it, but do not automatically discard neighboring beats.
- No augmentation or oversampling is used in Phase 3.
- This is a fixed-window adaptation of Kachuee et al. (2018), not a reproduction of their automatic detector/adaptive-window method. With reference annotations, the task is classification conditional on reference beat locations, not end-to-end detection.

## 5. Metrics and analysis

For each applicable model/configuration report:

- accuracy;
- macro and weighted precision, recall and F1;
- per-class precision, recall/sensitivity, F1 and support for N/S/V/F/Q;
- confusion matrix with fixed class order N, S, V, F, Q;
- specificity or false-positive rate where defined and useful;
- AUROC/AUPRC only when the one-vs-rest formulation and class support make them estimable;
- seed-level values and mean/standard deviation; confidence intervals only with an explicitly stated method and valid record/subject-level resampling unit.

Report undefined metrics as `NA`/not estimable with a reason; do not silently replace them with zero. Do not treat beats clustered within a record as independent subjects. Do not interpret MIT-BIH class frequency as clinical prevalence or heartbeat classification as patient-level diagnosis.

## 6. Privacy, encryption, ledger and robustness plans

### 6.1 DP and HE

Before any privacy implementation, approve a threat model specifying assets, adversaries, privacy unit, adjacency, trust assumptions, visible metadata and released transcript. For DP, document the mechanism, clipping/sensitivity, noise, sampling/participation, release count, accountant, epsilon/delta and whether validation-based selection is included. If assumptions do not hold, report no formal DP guarantee.

For CKKS, document library/version, parameters, security estimate source, packed values, key ownership, decryption point, approximation error and ciphertext communication size. State explicitly which party sees the clean aggregate. Compare plaintext, HE-only, DP-only and HE+DP using matched updates/seeds where technically possible.

### 6.2 Audit mechanism

Use the hash-chain ledger as the baseline and plan a local Ganache deployment as the smart-contract prototype, as selected by the research lead. Ganache is not evidence of independent validators, public-chain consensus, or production decentralization. Specify authorization, commitments, duplicate/replay rejection, off-chain data, audit reconstruction and verification. Do not put raw ECG, patient identifiers, update tensors, secret keys or private noise seeds on-chain. A hash proves integrity relative to the hashed bytes, not update honesty.

Measure gas, test-environment fee assumptions, latency, throughput, storage, verification time and failures over repeated trials. Do not invent values or extrapolate test-chain energy claims.

### 6.3 Robust aggregation

Before attack experiments, approve attacker count/fraction, coordination, knowledge, capabilities and success criteria. Compare FedAvg and suitable established baselines with the candidate under clean non-IID, sign-flip, scaling, norm-matched noise/benign outlier conditions, and additional attacks only if feasible. Select methods based on their actual assumptions and client count. Freeze thresholds on development data; use fresh seeds for final attack evaluation. Report malicious detection, honest false positives, clean macro-F1/minority recall and cost.

## 7. Data-use and leakage controls

- No test data use for preprocessing fitting, feature selection, resampling, hyperparameter selection, threshold choice or checkpoint selection.
- Fit any global transformation only on training data. Apply beat oversampling only after the train split and only within training data.
- Reference beat annotations, if used for windows, evaluate classification conditional on reference beat locations; they do not establish end-to-end QRS detection.
- Freeze the mapping, record/group split, primary metrics, model-selection rule, attacks, privacy assumptions and analysis plan before final test evaluation.
- Record deviations; do not retrospectively change the protocol after viewing test metrics.

## 8. Reproducibility and experiment records

Every authorized run must record experiment ID, versioned configuration, dataset version/checksum, mapping version, split-manifest hash, seed, source snapshot/commit, environment, exact command, timestamps, exit status, output directory, model hash, metrics and warnings/failures. Keep historical evidence immutable and use new versioned outputs.

The project is intended to support Colab GPU execution. Before compute-heavy work, record the actual runtime image, Python and package versions, accelerator model, CUDA/PyTorch support, available memory and exact device used. Do not silently fall back from GPU to CPU. Do not install GPU/CUDA packages blindly.

## 9. Phase-specific decisions and documented evidence limits

The research lead approved this Phase 1 protocol and selected the following design defaults:

- five initial client slots, subject to whole-record assignment and review of client class support;
- FedProx as the single planned FL alternative to FedAvg;
- macro-F1 as the primary validation checkpoint-selection metric;
- hash-chain baseline plus a local Ganache smart-contract prototype;
- SVDB retained only as an optional external evaluation, subject to its own approval and frozen protocol.

The following decisions remain open for their applicable later gates:

1. any EC57 clause-specific decisions, if the full licensed text becomes available;
2. training budgets, stopping rule and complete configuration, to be frozen using validation data only;
3. DP privacy unit, adjacency, accountant and predeclared budget/noise sweep;
4. HE parameter set, key ownership and decryption location;
5. robust aggregation baseline set, attacker capabilities and attacker budget;
6. whether to execute SVDB external evaluation, after primary MIT-BIH evaluation is frozen.

No experiment requiring these decisions may proceed until it is resolved at the applicable gate. Phase 2 acquisition/taxonomy and Phase 3 split/preprocessing gates have passed. Phase 4 baselines were executed in full on 15 November 2026 and G4 was not passed because the centralized model achieved 0.000 S-class recall, a limitation formally accepted by the research lead. Phase 5 federated learning is authorised; its IID-like and moderate non-IID FedAvg conditions are complete and the remaining conditions are pending. G5 has not been assessed.

## 10. Approval record

- Research lead: approved by explicit chat confirmation on 13 November 2026
- Research-lead selections recorded: five clients, FedProx, macro-F1 checkpoint selection, hash-chain plus local Ganache plan, optional SVDB external evaluation
- Phase 2/G2 approval: approved mapping and exclusions; use the 44 non-pacemaker-record protocol and exclude records 102, 104, 107 and 217; Q support is 15 annotations across 5 records.
- Protocol version approved: 1.0
- Approval date: 13 November 2026
- Deviations/amendments: approval accepts the disclosed source-access limits; no detailed claims are made about inaccessible full texts
- Phase 1 gate G1: `PASS WITH DOCUMENTED SOURCE-ACCESS LIMITATIONS`
