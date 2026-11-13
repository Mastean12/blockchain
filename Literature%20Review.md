# Literature Review and Research Execution Specification
## A Blockchain-Enabled Privacy-Preserving Federated Learning Framework for ECG Arrhythmia Classification

**Version:** 1.0 | **Research review date:** 13 November 2026  
**Status:** Approved research direction; implementation and taxonomy verification pending.

## 1. Purpose and authority

This document is both a focused literature review and the controlling research specification for the next training cycle. It directs human researchers and AI coding agents working in this repository.

The study evaluates: (1) AAMI-derived five-class ECG heartbeat classification; (2) centralized and federated training under IID/non-IID client distributions; (3) differential privacy (DP) and homomorphic encryption (HE); (4) blockchain-backed auditability and operational costs; and (5) robust aggregation under clean and adversarial conditions.

**Authority rule:** Do not silently override this specification. If code, historical documentation or artifacts conflict with it, preserve historical evidence, report the conflict and request a research decision. Never invent labels, patient IDs, metrics, approvals, privacy guarantees or experimental outcomes.

**Standards caution:** ANSI/AAMI EC57:2012 (R2020) is a recommended practice for testing and reporting cardiac rhythm and ST-segment algorithms. The N/S/V/F/Q heartbeat grouping is widely used as an AAMI-derived grouping in ECG classification. Mapping five classes alone does not establish compliance with every EC57 clause. The exact annotation policy, record exclusions, beat matching and reporting procedure must be checked against the licensed standard and relevant protocol literature.

## 2. Adopted research questions

**RQ1 — Classification performance:** How accurately can deep learning detect and classify ECG heartbeats under the AAMI five-class grouping, using centralized and federated training?

**RQ2 — Federated learning under heterogeneity:** How does federated learning compare with centralized and local-only training under heterogeneous (non-IID) client data, and which factors explain any performance gap?

**RQ3 — Privacy–utility–cost trade-off:** What are the effects of differential privacy and homomorphic encryption, individually and jointly, on predictive utility, privacy guarantees, computation, communication and model convergence?

**RQ4 — Auditability and blockchain cost:** Can a blockchain-backed audit mechanism make federated training operations verifiable and auditable, and what are its gas, latency, throughput, storage and operational costs?

**RQ5 — Robust aggregation:** Can the proposed aggregation mechanism mitigate specified malicious-client attacks while preserving benign-client utility under non-IID ECG data, and at what computational and communication cost?

| RQ | Required evidence |
|---|---|
| RQ1 | AAMI mapping audit, class support, record/group-aware split, centralized/federated metrics, confusion matrices, per-class precision/recall/F1 |
| RQ2 | Local-only, centralized, IID FedAvg, non-IID FedAvg and justified FL alternative; client distributions; matched budgets; seed variability |
| RQ3 | Non-private baseline, DP sweep, HE-only, HE+DP; accounting assumptions; encryption/noise timings; communication volume |
| RQ4 | Hash-chain baseline and Ganache smart-contract prototype; valid/invalid transaction tests; measured gas, latency, throughput and storage |
| RQ5 | FedAvg and established robust baselines versus frozen candidate; clean/non-IID/attack settings; detection and false-positive metrics |

## 3. Literature review

### 3.1 Standardized ECG classification

The MIT-BIH Arrhythmia Database contains 48 approximately half-hour, two-channel recordings from 47 subjects, sampled at 360 Hz, with expert-reviewed annotations. Records 201 and 202 are from the same subject and must be grouped during splitting.

ANSI/AAMI EC57:2012 (R2020) is the current edition identified in the ANSI catalogue. It provides recommended practices for testing and reporting cardiac rhythm and ST-segment algorithm performance. The five-class N/S/V/F/Q grouping is widely used in ECG heartbeat-classification studies.

Candidate mapping (must be validated against raw annotation files and the selected protocol):

| Class | Meaning | Candidate MIT-BIH symbols |
|---|---|---|
| N | Normal and related normal/escape beats | N, L, R, e, j |
| S | Supraventricular ectopic beats | A, a, J, S |
| V | Ventricular ectopic beats | V, E |
| F | Fusion of normal and ventricular beat | F |
| Q | Paced/unknown group under the selected protocol | /, f, Q |

**Do not blindly map all remaining symbols to Q.** Distinguish beat annotations from rhythm annotations, noise markers, signal-quality annotations and non-beat events. Explicitly decide the treatment of `f`, `/`, `Q`, paced records and exclusions. Published implementations differ. The exact mapping must be approved before training.

AAMI grouping improves comparability but does not solve class imbalance. N is dominant and S/F may be scarce. Accuracy alone can conceal poor minority-class performance.

Silva et al. (2026) systematically review ECG arrhythmia classification and identify inconsistent standard adherence, inter-patient evaluation and embedded-feasibility reporting. de Chazal et al. (2004) is a foundational five-class MIT-BIH study using separate record groups for configuration selection and independent performance assessment.

**Implication:** use record/group-aware splits; disclose record lists and class supports; report per-class sensitivity, precision and F1; never randomly split beats from the same record across train and test.

### 3.2 Centralized and federated ECG learning

Prior studies have applied federated CNN and recurrent models to ECG classification and explored local fine-tuning, personalization and non-IID client distributions. FedAvg is not guaranteed to match centralized training under heterogeneous clients. Recent 2026 studies specifically investigate patient-independent ECG evaluation and rare-beat detection under class-missing clients.

Guo, Yin and Hu (2024) evaluate a multiscale convolutional causal-attention network on MIT-BIH and report accuracy, precision, sensitivity and F1. Their balancing strategy is relevant, but resampling must be confined to training data; applying SMOTE before splitting risks leakage. Recent studies on class-missing clients are especially relevant to the previous project's N/V prediction collapse.

**Implication:** first establish trustworthy baselines and diagnose federated collapse. Include local-only training, IID and non-IID partitions, and a justified alternative such as FedProx or personalization. Choose methods using validation data only.

### 3.3 Differential privacy

DP depends on the protected unit, adjacency, clipping/sensitivity, noise mechanism, sampling, number of releases/rounds, accountant and released transcript. Epsilon alone does not define a privacy guarantee.

ECG privacy literature examines DP at signal, feature, model and federated-training levels. A 2025 PLOS ONE study combines personalized federated learning with local DP for arrhythmia diagnosis. Local DP and noise added to a weighted aggregate after trusted decryption are different mechanisms; their epsilon values are not directly comparable.

The previous project tested one client-slot DP configuration with epsilon approximately 7.98 and poor utility; the combined HE+DP run selected round 0. This shows the tested configuration did not produce a useful selected model. It does not prove DP is inherently unusable.

**Implication:** conduct a predeclared privacy–utility sweep only after validating the non-private baseline and accountant. For every run report privacy unit, adjacency, clipping, sensitivity, noise multiplier, rounds, sampling assumptions, accountant, epsilon, delta, released transcript and trust model. Do not compare epsilon values across incompatible mechanisms.

### 3.4 Homomorphic encryption and HE+DP

CKKS supports approximate arithmetic over encrypted values but introduces approximation error, ciphertext expansion, encryption/decryption cost and key-management assumptions. HE does not itself provide DP, integrity, participant authentication or protection from every key holder.

Recent ECG and healthcare studies combine FL with CKKS/HE; 2026 work also reports secure multimodal FL combining CKKS and DP. Therefore, the mere combination of FL, HE and DP is not a novelty claim.

**Implication:** compare HE-only, DP-only and HE+DP under a common ECG task, client partition, model and evaluation protocol. Measure encryption, aggregation, decryption, noise generation, communication payload, utility and convergence. State who holds the secret key and who sees the clean aggregate. An empirical maximum CKKS error over a finite run is not a universal error bound and must not be treated as one in the DP accountant without proof.

### 3.5 Blockchain-backed federated learning

A 2025 IEEE Access survey reviews blockchain-enabled FL in healthcare, including consensus, cryptographic protocols, storage topologies, convergence delay, computation overhead and ledger scalability. A 2026 e-health framework combines anomaly detection, robust aggregation and blockchain logging for traceability. Thus, blockchain logging in healthcare FL is already established.

Ganache can support a local EVM smart-contract prototype and reproducible transaction-cost measurements. It is not a production permissioned blockchain or proof of distributed consensus. Recording a hash does not prove that the server aggregated the claimed updates unless participant commitments, authorization and verification are properly designed.

**Implication:** retain the existing hash-chain ledger as a baseline and add a Ganache-backed smart-contract audit prototype. Store only approved metadata and commitments on-chain; keep ECG, tensors, keys and private noise artifacts off-chain. Measure gas, latency, throughput, storage and verification outcomes. Do not claim production security or real public-chain energy consumption.

### 3.6 Robust aggregation

Krum, Multi-Krum, coordinate-wise median, trimmed mean, RFA and FLTrust are established robust aggregation families. Their assumptions and tolerance to non-IID data, collusion and adaptive attacks differ. Recent healthcare-oriented research reports cases where adaptive attackers evade distance-based filters.

**Implication:** compare the candidate clipping/cosine/norm-screening method against suitable baselines. Freeze thresholds using development data, then evaluate on fresh seeds. Include benign non-IID clients, class-missing clients, sign-flip, scaling, norm-matched noise and, if feasible, adaptive/multiple attackers. Report detection rate, false-positive rate, clean macro-F1, minority recall and cost. Do not claim novelty or superiority without a complete review and fair comparison.

## 4. Research gaps and contribution

The literature does not support claiming that nobody has combined FL, HE, DP, blockchain or robust aggregation. Several papers combine subsets. The defensible gap is empirical and application-specific:

**Overarching gap:** There is a need for a reproducible evaluation of how federated ECG classification under heterogeneous and imbalanced client data interacts with DP, HE, blockchain-backed auditability and robust aggregation. The evaluation must use a fixed AAMI-derived task, record/group-aware partitions, comparable baselines, explicit threat models and measured predictive, privacy and systems costs.

- **G1 — Standardized ECG evaluation:** inconsistent taxonomies, patient/record splits, class support and metrics. Use an explicit AAMI-derived mapping, group-aware splits and per-class reporting.
- **G2 — Explaining non-IID degradation:** the previous FedAvg collapse is reproducible but unexplained. Compare centralized, local-only, IID and non-IID FedAvg; isolate client drift, label skew, optimizer state, normalization and checkpoint selection.
- **G3 — Comparable privacy–utility–cost evidence:** compare no privacy, DP-only, HE-only and HE+DP under one task with explicit accounting and measured overhead.
- **G4 — Application-specific blockchain evidence:** compare the existing hash-chain with Ganache and measure gas, latency, throughput, storage and verification.
- **G5 — Robustness under ECG heterogeneity:** test the candidate against established baselines under benign non-IID and predeclared attacks, with frozen thresholds and fresh seeds.

**Provisional contribution statement:** This study contributes a controlled experimental framework and comparative evaluation for AAMI-derived ECG heartbeat classification under centralized and federated learning. It assesses the interaction of client heterogeneity, DP, CKKS-based HE and blockchain-backed audit logging, while separately evaluating a candidate robust aggregation mechanism. The contribution is reproducible integration and measurement of predictive utility, privacy assumptions, auditability, robustness and operational costs—not an unsupported claim that each technique is new.

## 5. AAMI task definition — mandatory before retraining

### 5.1 Candidate mapping

| Target | Description | Candidate MIT-BIH symbols |
|---|---|---|
| N | Normal and related normal beats | N, L, R, e, j |
| S | Supraventricular ectopic beats | A, a, J, S |
| V | Ventricular ectopic beats | V, E |
| F | Fusion of normal and ventricular beat | F |
| Q | Paced/unknown group | /, f, Q |

This is a candidate mapping to validate, not permission to map every annotation. Audit all raw symbols and distinguish beat annotations from rhythm/noise markers and non-beat events. Explicitly document `f`, `/`, `Q`, paced records and exclusions. The researcher must approve the exact policy.

### 5.2 Taxonomy audit deliverable

Before training, create a machine-readable mapping configuration and report containing: all unique annotation symbols; counts per raw symbol; target mapping; excluded symbols and reasons; per-record and aggregate N/S/V/F/Q support; paced-record handling; tests that every included symbol maps exactly once; and tests that unexpected annotations are never silently assigned.

### 5.3 Q-class warning

Q may be absent or sparse in an inter-patient split. Do not fabricate Q samples, oversample before splitting, or claim five-class test performance if Q has no test support. Report unsupported metrics as not estimable. If paced records are excluded, state the consequence and scope.

## 6. Data and evaluation protocol

### 6.1 Datasets

- Primary: MIT-BIH Arrhythmia Database, exact version and checksums.
- External: SVDB as separate external evaluation unless a separately approved federated-training design is established. Testing a frozen MIT-BIH checkpoint on SVDB is not federated training on a second dataset.
- Record provenance, preprocessing version, mapping version, split hash and record membership.

### 6.2 Record/group separation

MIT-BIH has 48 records from 47 subjects; records 201 and 202 are from the same subject. Group them. If explicit patient IDs are unavailable for other records, describe the split as record/group-aware or inferred grouping—not verified patient-level independence. Never split beats from the same record across train/validation/test. Freeze exact record lists before training.

### 6.3 Federated partitions

Start with five clients for historical comparability. Assign whole records/groups to clients. Create reproducible IID-like and at least two non-IID settings (moderate and severe label skew). Report record IDs, sample counts and class distributions per client, including absent classes. Keep test records outside all training and validation.

### 6.4 Required baselines

1. Majority-class predictor.
2. Centralized CNN.
3. Local-only training (one model per client).
4. IID FedAvg.
5. Non-IID FedAvg.
6. One justified alternative (e.g. FedProx or personalization).
7. DP-only.
8. HE-only.
9. HE+DP.
10. Blockchain logging on an otherwise identical configuration.
11. Proposed robust aggregation against FedAvg and suitable robust baselines.

Never compare incompatible taxonomies/splits as one leaderboard.

### 6.5 Training fairness

Match architecture and budgets where possible; document unavoidable differences. Select hyperparameters only on training/validation. Predefine checkpoint selection; consider validation macro-F1 or a justified composite alongside loss because classes are imbalanced. Do not silently fall back to round 0. If round 0 is genuinely selected, report and investigate. Use at least five seeds if feasible; seeds on one fixed split do not replace independent split validation.

### 6.6 Required metrics

Report accuracy; macro/weighted precision, recall and F1; per-class precision, recall/sensitivity, F1 and support for N/S/V/F/Q; confusion matrix; specificity where meaningful; AUROC/AUPRC only when defined and supported; and seed mean/standard deviation or justified confidence intervals. Accuracy must not be the only headline metric.

## 7. Experiments by research question

### RQ1
Run majority, centralized and local-only baselines first. Verify mapping, class counts, split and training pipeline. Then compare centralized/federated models. Exit when performance can be explained by class and record and reproduced across seeds. No predetermined accuracy may be forced through leakage or test tuning.

### RQ2
Compare centralized, local-only, IID FedAvg and non-IID FedAvg. Add FedProx or personalization. Ablate label skew, client drift, optimizer state, normalization and participation. Exit when the performance gap is supported by controlled evidence.

### RQ3
Compare no privacy, DP-only with multiple predeclared budgets, HE-only and HE+DP. Record all accounting parameters and who sees clean aggregates. Measure crypto/noise timings and communication. Exit with a valid privacy–utility–cost analysis and explicit threat model.

### RQ4
Retain hash-chain baseline. Add Ganache smart contract recording experiment/round IDs, authorized identity/role, approved metadata, update commitments and global model hashes. Keep sensitive data off-chain. Measure gas, gas-price assumptions, fee, latency, throughput, storage and failures. Ganache is local test-chain evidence, not production consensus or public-chain energy.

### RQ5
Compare FedAvg, suitable robust baselines and candidate. Freeze thresholds on development seeds. Test clean non-IID, sign-flip, scaling, norm-matched noise and adaptive/multiple attackers if feasible. Report attack effect/detection, false positives, clean macro-F1, minority recall, excluded data and cost. If the method does not outperform suitable baselines, report and revise/withdraw the contribution.

## 8. AI-agent execution rules

1. Inspect repository status, configs, source, tests and artifacts before edits.
2. Preserve historical results and dirty worktree; never reset, clean, delete or overwrite them.
3. Use versioned outputs for new taxonomy, split, model, privacy and blockchain experiments.
4. Never use test data for tuning, preprocessing fitting, resampling, threshold selection or model selection.
5. Do not silently map unknown annotations to Q or discard symbols.
6. Do not claim patient independence beyond available metadata.
7. Do not claim clinical diagnosis, utility or deployment readiness.
8. Do not claim DP without explicit mechanism/accountant assumptions; do not claim HE protects against key holders.
9. Do not put raw ECG, client tensors, keys or private seeds on-chain.
10. Do not call a hash chain a distributed blockchain; do not invent gas/energy measurements.
11. Do not claim novelty without completed literature review and fair comparison.
12. Use `.venv\\Scripts\\python.exe`; add tests; run targeted and full suites.
13. Record experiment ID, config, seed, data/split hash, command, output path and exit status.
14. Do not launch expensive training before taxonomy, data validation and approval gates.
15. Do not stage, commit or push unless explicitly requested.

### Required repository artifacts

Create/update:
- `docs/Literature Review.md` — this specification.
- `docs/RESEARCH_PROTOCOL.md`
- `docs/DATA_AND_LABEL_POLICY.md`
- `docs/EXPERIMENT_REGISTRY.md`
- `docs/THREAT_MODEL.md`
- `docs/ACCEPTANCE_CRITERIA.md`
- Versioned mapping configuration and taxonomy audit report.
- Versioned split metadata and client partition manifests.
- Metrics reports with per-class precision, recall, F1 and support.

## 9. Execution sequence and stop/go gates

1. Audit repository and preserve all existing artifacts.
2. Audit raw MIT-BIH annotation symbols and produce mapping/count/exclusion report. **Do not train.**
3. Obtain approval for Q handling, exclusions, record split and client partitions.
4. Create a new versioned AAMI dataset/split without overwriting 15-class artifacts; validate group separation and hashes.
5. Run majority, centralized and local-only smoke tests; validate metrics and checkpoint selection.
6. Run approved IID/non-IID FedAvg and explain any collapse.
7. After baseline validation and privacy approval, run DP sweep, HE-only and HE+DP.
8. Implement and benchmark Ganache separately.
9. Freeze robust aggregation thresholds on development data and evaluate on fresh seeds.
10. Integrate only independently validated components; update RQ answers and reproducibility.

| Gate | Required before proceeding |
|---|---|
| G1 Taxonomy | Raw annotations classified; exclusions justified; Q support understood; mapping approved |
| G2 Data | Group-aware split validated; records frozen; no leakage; manifest/hash generated |
| G3 Baselines | Centralized/local-only/IID/non-IID runs execute and metrics validated |
| G4 Privacy | Mechanism, accountant, privacy unit and trust assumptions approved |
| G5 Blockchain | Contract tests pass; gas/latency methodology documented |
| G6 Robustness | Threat model, baselines, thresholds and independent seeds frozen |
| G7 Integration | Components work independently; integration preserves privacy assumptions |

## 10. Verified starting bibliography

The following items were checked against publisher, standards-body, PubMed/PMC or PhysioNet pages on 13 November 2026. This is a starting bibliography, not an exhaustive systematic-review corpus. Do not invent missing authors, pages, issue numbers or DOIs.

1. Association for the Advancement of Medical Instrumentation. (2020). *ANSI/AAMI EC57:2012 (R2020): Testing and reporting performance results of cardiac rhythm and ST segment measurement algorithms*. https://webstore.ansi.org/standards/aami/ANSIAAMIEC572012R2020
2. Moody, G. B., & Mark, R. G. (2001). The impact of the MIT-BIH Arrhythmia Database. *IEEE Engineering in Medicine and Biology Magazine, 20*(3), 45–50. https://doi.org/10.1109/51.932724
3. Moody, G., & Mark, R. (2005). *MIT-BIH Arrhythmia Database (version 1.0.0)*. PhysioNet. https://doi.org/10.13026/C2F305
4. de Chazal, P., O'Dwyer, M., & Reilly, R. B. (2004). Automatic classification of heartbeats using ECG morphology and heartbeat interval features. *IEEE Transactions on Biomedical Engineering, 51*(7), 1196–1206. https://doi.org/10.1109/TBME.2004.827359
5. Pham, B.-T., Le, P. T., Tai, T.-C., Hsu, Y.-C., Li, Y.-H., & Wang, J.-C. (2023). Electrocardiogram heartbeat classification for arrhythmias and myocardial infarction. *Sensors, 23*(6), 2993. https://doi.org/10.3390/s23062993
6. Guo, C., Yin, B., & Hu, J. (2024). An electrocardiogram classification using a multiscale convolutional causal attention network. *Electronics, 13*(2), 326. https://doi.org/10.3390/electronics13020326
7. Silva, G. A. L., Silva, P. H. L., Moreira, G. J. P., Freitas, V. L. de S., Gertrudes, J. C., et al. (2026). A systematic review of ECG arrhythmia classification: Embedded feasibility, adherence to standards, and fair evaluation. *Research on Biomedical Engineering, 42*, Article 42. https://doi.org/10.1007/s42600-026-00485-z
8. *Blockchain-enabled federated learning in healthcare: Survey and state-of-the-art*. (2025). *IEEE Access, 13*, 119922–119945. https://doi.org/10.1109/ACCESS.2025.3587345
9. Alruwaili, E., & Moulahi, T. (2026). A robust and verifiable federated learning framework for preventing data poisonous threats in e-health. *Frontiers in Public Health, 14*, 1762346. https://doi.org/10.3389/fpubh.2026.1762346
10. *FedShield: Configurable mean–median robust aggregation for poisoning-resilient federated healthcare-IoT learning*. (2026). *IEEE Access, 14*, 133801–133815. https://doi.org/10.1109/ACCESS.2026.3728130. Verify full author metadata before final thesis citation.
11. *A secure multi-modal federated transfer learning system for ECG classification*. (2026). *Neurocomputing, 681*, 133402. https://doi.org/10.1016/j.neucom.2026.133402. Verify author metadata from publisher.
12. *Federated learning with homomorphic encryption for secure real time ECG anomaly detection: A multi institutional privacy preserving framework*. (2026). *Biomedical Signal Processing and Control*. https://doi.org/10.1016/j.bspc.2026.109557. Verify author/issue metadata from publisher.
13. *Fusion of Personalized Federated Learning (PFL) with Differential Privacy (DP) Learning for Diagnosis of Arrhythmia Disease*. (2025). *PLOS ONE*. https://doi.org/10.1371/journal.pone.0327108. Verify complete author metadata from publisher.

**Verification note:** Several publisher search records did not expose complete author metadata in the accessible preview. Those entries are explicitly marked for verification. An earlier DP review search result had an incomplete arXiv identifier and is omitted until its exact record is verified. The full AAMI standard may require purchase/institutional access; this document does not reproduce it.

## 11. Final research standard

The project is ready for defence only when the mapping is approved and tested; record/group separation is transparent; centralized/local-only/IID/non-IID baselines are fairly compared; round-0 selection and model collapse are explained; DP claims match the implemented accountant; HE assumptions are explicit; Ganache auditability is measured; the robust aggregator is fairly evaluated; every RQ is answered with evidence; and the literature review is complete.

**Integrity rule:** A lower but valid score is preferable to a high score produced by leakage, invalid splitting, post-hoc test tuning or unsupported claims. No accuracy target is guaranteed.
