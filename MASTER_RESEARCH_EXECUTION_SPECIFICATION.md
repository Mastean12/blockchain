# MASTER RESEARCH EXECUTION SPECIFICATION
## Fresh, reproducible implementation of an AAMI-derived ECG federated-learning study

**Project:** A Blockchain-Enabled Privacy-Preserving Federated Learning Framework for ECG Arrhythmia Classification  
**Document role:** Authoritative research and engineering instructions for the fresh project  
**Version:** 1.0  
**Prepared:** 13 November 2026  
**Primary dataset:** MIT-BIH Arrhythmia Database  
**External dataset:** MIT-BIH Supraventricular Arrhythmia Database (SVDB), only for a separately defined external evaluation unless a separate protocol is approved  
**Approved classification direction:** AAMI-derived five-class heartbeat grouping (N, S, V, F, Q)

---

# PART I — AUTHORITY, SCOPE AND RESEARCH INTEGRITY

## 1. Purpose

This file is the controlling instruction set for the complete fresh implementation. It is intended to be placed in the top-level project folder, above all source-code and documentation directories. Every human contributor and AI coding agent must read it before making changes.

The objective is to produce a scientifically defensible, reproducible research prototype and evaluation. The project is not to be optimized merely for high accuracy, an impressive dashboard, or a large number of implemented technologies. Each research claim must be supported by a valid experiment, a documented method, and traceable evidence.

The study investigates five connected questions:

1. ECG heartbeat classification under an explicitly defined AAMI-derived five-class taxonomy.
2. Centralized versus federated training under IID-like and non-IID client data.
3. Predictive-utility and systems-cost effects of differential privacy (DP) and homomorphic encryption (HE), separately and jointly.
4. Verifiability and auditability of federated training using a blockchain-backed audit mechanism.
5. Robust aggregation against defined malicious-client behaviours without unacceptable harm to honest clients.

## 2. Non-negotiable research rules

1. **No fabricated evidence.** Never invent data, labels, patient identifiers, results, citations, software versions, approvals, privacy guarantees, timing measurements, blockchain properties, or successful tests.
2. **No silent assumptions.** If a required fact is unknown, mark it `UNKNOWN`, explain how it will be established, and stop any dependent experiment until resolved.
3. **No leakage.** Test data must not be used for preprocessing fitting, feature selection, oversampling, threshold selection, hyperparameter tuning, checkpoint selection, or model selection.
4. **No retrospective protocol changes.** Freeze the taxonomy, split, primary metrics, model-selection rule, attacks, privacy accounting assumptions and analysis plan before final test evaluation.
5. **No overwriting historical evidence.** This is a fresh folder, but if historical files are imported for comparison, preserve them read-only and copy only explicitly selected artifacts. Never overwrite the old PC project.
6. **No premature integration.** Validate the dataset, model, federated baseline, privacy components, ledger and robust aggregator independently before combining them.
7. **No unsupported clinical claims.** This is an offline research experiment, not a clinically validated diagnostic device. Do not describe it as clinically safe, clinically deployable, or suitable for patient care.
8. **No unsupported novelty claims.** The existence of FL, DP, HE, blockchain and robust aggregation, individually or in combinations, is established in prior work. Any novelty claim must be narrow, literature-supported and approved.
9. **No accuracy target manipulation.** A lower but valid result is preferable to a high result obtained through leakage or invalid evaluation.
10. **No source-control actions without authorization.** Do not stage, commit, push, reset, clean, force checkout, delete user files or rewrite Git history unless explicitly instructed.
11. **No expensive training without approval gates.** Complete the audit and smoke-test gates first.
12. **No statement that work is complete based only on code generation.** Completion requires executed tests, inspected outputs, reproducibility records and evidence.

## 3. What the study may and may not claim

The study may claim that it implemented and experimentally evaluated particular methods under the specified datasets, partitions, threat models and hardware/software environment.

The study must not claim:
- formal AAMI/EC57 compliance merely because it uses five labels;
- patient-independent evaluation if the split is only record-independent and subject identity is unknown;
- a distributed blockchain when the implementation is a single-node hash chain or local Ganache chain;
- a formal DP guarantee unless the mechanism and accountant assumptions are valid for the implemented release process;
- that HE hides information from the secret-key holder;
- that a ledger proves a model update is truthful merely because a hash was recorded;
- that external-dataset evaluation is multi-dataset federated training;
- clinical generalization from MIT-BIH alone;
- novelty or superiority without appropriate literature review and fair baseline comparisons.

---

# PART II — RESEARCH QUESTIONS AND HYPOTHESES

## 4. Adopted research questions

Use the following exact questions throughout the proposal, protocol, experiment registry, results and defence.

**RQ1 — Classification performance**  
How accurately can deep learning detect and classify ECG heartbeats under the AAMI five-class grouping, using centralized and federated training?

**RQ2 — Federated learning under heterogeneity**  
How does federated learning compare with centralized and local-only training under heterogeneous (non-IID) client data, and which factors explain any performance gap?

**RQ3 — Privacy–utility–cost trade-off**  
What are the effects of differential privacy and homomorphic encryption, individually and jointly, on predictive utility, privacy guarantees, computation, communication and model convergence?

**RQ4 — Auditability and blockchain cost**  
Can a blockchain-backed audit mechanism make federated training operations verifiable and auditable, and what are its gas, latency, throughput, storage and operational costs?

**RQ5 — Robust aggregation**  
Can the proposed aggregation mechanism mitigate specified malicious-client attacks while preserving benign-client utility under non-IID ECG data, and at what computational and communication cost?

## 5. Research question evidence requirements

| Question | Evidence required before answering |
|---|---|
| RQ1 | Taxonomy audit; class counts; split manifest; centralized and federated metrics; confusion matrices; per-class precision, recall, F1 and support |
| RQ2 | Local-only, centralized, IID-like FedAvg, non-IID FedAvg and at least one justified alternative; client distributions; controlled ablations; repeated seeds |
| RQ3 | No-privacy baseline, DP-only, HE-only and HE+DP; exact threat model; privacy accounting; runtime and communication measurements |
| RQ4 | Explicit audit design; valid/invalid transaction tests; verification evidence; measured gas/fees, latency, throughput and storage |
| RQ5 | FedAvg and appropriate robust baselines; frozen proposed method; clean and attack conditions; attack success/detection and false-positive measurements |

Do not write that an RQ is answered merely because the corresponding component exists in code.

---

# PART III — RESEARCH BASIS AND METHOD DECISIONS

## 6. Standards and the AAMI-derived five-class task

### 6.1 What the standard says

ANSI/AAMI EC57:2012/(R)2020 is titled *Testing and reporting performance results of cardiac rhythm and ST segment measurement algorithms*. The ANSI/AAMI preview describes it as a recommended practice for reproducible testing and reporting of cardiac rhythm and ST-segment algorithms. It emphasizes record-by-record presentation and clinically relevant event detection. The standard itself cautions that available databases have limited representation of some arrhythmias, paced patients and artifacts, and that test results are uncertain indicators of clinical performance.

**Important:** EC57 is not simply a five-class deep-learning recipe. A five-class mapping does not establish compliance with every clause. The research team must consult the full licensed standard where required and document which recommendations are followed, adapted or outside scope.

### 6.2 Five-class labels

The common AAMI-derived heartbeat superclasses are:

- `N`: normal and selected normal-related beats;
- `S`: supraventricular ectopic beats;
- `V`: ventricular ectopic beats;
- `F`: fusion beats;
- `Q`: paced, fusion-paced or unclassifiable/other beats, according to the chosen annotation protocol.

A commonly used MIT-BIH mapping, reported in ECG classification literature, groups symbols approximately as follows:

| Target | Commonly mapped MIT-BIH beat symbols | Interpretation |
|---|---|---|
| N | `N`, `L`, `R`, `e`, `j` | Normal, bundle branch block and selected escape beats |
| S | `A`, `a`, `J`, `S` | Supraventricular ectopic beats |
| V | `V`, `E` | Ventricular ectopic/escape beats |
| F | `F` | Fusion of ventricular and normal beat |
| Q | `/`, `f`, `Q` | Paced, fusion-paced and unclassifiable categories in commonly used mappings |

This table is a **candidate mapping**, not a substitute for the full standard or the dataset annotation guide. Verify every symbol against the exact source annotation definitions and selected protocol before implementation. Do not add all unrecognized annotations to Q. Rhythm annotations, noise markers, comments and non-beat events are not automatically beat classes.

The paper by Pham et al. (2023) provides a published table of mappings between beat annotations and AAMI categories. The MIT-BIH annotation files and PhysioNet documentation remain the source for what annotations are actually present in the downloaded data. The full EC57 standard is authoritative for the applicable testing recommendations.

### 6.3 Mapping approval gate

Before training, create:
- a version-controlled mapping file (e.g. `configs/data/aami5_mapping_v1.yaml`);
- a raw-symbol inventory generated from all included annotation files;
- counts for each raw annotation symbol;
- a mapping or exclusion decision for every symbol;
- a reason for every exclusion;
- per-record counts for N/S/V/F/Q;
- total counts for N/S/V/F/Q;
- a report of records containing paced beats;
- unit tests that every included beat annotation maps exactly once;
- tests that no unknown annotation is silently mapped or discarded.

The research lead must approve the exact mapping, paced-record handling and exclusions before training.

### 6.4 Q-class and record exclusions

The Q class may be rare or absent in some record splits. Do not fabricate Q observations, copy samples into the test set, or claim valid five-class performance if the test set has no Q support. If a class has no test support, report its class-specific metrics as not estimable and explain the limitation.

Some AAMI-oriented protocols recommend excluding records from paced patients and segments containing specified rhythms. Do not assume which records to exclude. Establish the rule from the full standard and a selected published protocol, then list the exact record IDs and reasons in the protocol. The rule must be applied before model training and must not be altered after viewing test results.

---

# PART IV — DATASETS, PROVENANCE AND SPLITTING

## 7. Primary dataset: MIT-BIH Arrhythmia Database

The PhysioNet MIT-BIH Arrhythmia Database v1.0.0 contains:
- 48 approximately half-hour, two-channel ambulatory ECG recordings;
- 47 subjects;
- signals sampled at 360 samples/second/channel;
- 11-bit resolution over a 10 mV range;
- expert-reviewed reference annotations;
- approximately 110,000 beat annotations.

Records 201 and 202 originate from the same subject and must never be allocated to different partitions when claiming subject-independent evaluation.

The recordings were collected in 1975–1979. Twenty-three were randomly selected from a larger pool and 25 were selected to include less common, clinically significant arrhythmias. The dataset is a research benchmark, not a population-representative sample. Do not infer real-world disease prevalence from its class proportions.

Official source: https://physionet.org/content/mitdb/1.0.0/

## 8. Secondary/external dataset: SVDB

SVDB may be used for a separately defined external generalization evaluation. It must not be described as a second federated training dataset unless the project actually defines, implements and runs a multi-dataset training protocol.

Before using SVDB:
1. verify the exact dataset release and license/terms;
2. inspect annotation compatibility with the approved five-class mapping;
3. document missing or incompatible labels;
4. document sampling rates, channels and preprocessing;
5. establish a defensible record/subject split if identifiers permit;
6. freeze the evaluation protocol;
7. evaluate a checkpoint selected using MIT-BIH validation only;
8. do not tune the model or mapping on SVDB test labels;
9. report domain shift and label-coverage limitations.

A frozen MIT-BIH model evaluated on SVDB is external evaluation, not cross-dataset federated learning.

## 9. Data acquisition and integrity

For every dataset:
- record official source URL, version, download date and license/terms;
- preserve the original downloaded files as immutable raw data;
- record SHA-256 checksums for every downloaded archive/file;
- keep raw data separate from processed data;
- never edit source annotation files;
- document any corrupted, missing or excluded records;
- record library and preprocessing versions;
- ensure the pipeline can be rerun from raw data.

Recommended project structure:

```text
project-root/
├── MASTER_RESEARCH_EXECUTION_SPECIFICATION.md
├── README.md
├── pyproject.toml
├── requirements-lock.txt
├── .gitignore
├── configs/
│   ├── data/
│   ├── models/
│   ├── federated/
│   ├── privacy/
│   ├── blockchain/
│   └── experiments/
├── data/
│   ├── raw/                 # immutable, normally git-ignored
│   ├── interim/
│   ├── processed/
│   └── splits/
├── src/
│   ├── data/
│   ├── preprocessing/
│   ├── models/
│   ├── training/
│   ├── federated/
│   ├── privacy/
│   ├── blockchain/
│   ├── aggregation/
│   ├── evaluation/
│   └── utils/
├── tests/
├── experiments/
│   ├── configs/
│   ├── logs/
│   └── registry/
├── results/
│   ├── tables/
│   ├── figures/
│   ├── metrics/
│   └── reports/
├── docs/
│   ├── literature/
│   ├── protocol/
│   ├── data_and_labels/
│   ├── threat_model/
│   ├── methodology/
│   └── limitations/
└── scripts/
```

The AI agent may propose a different structure only if it explains why and obtains approval before creating a conflicting structure.

## 10. Split policy and leakage prevention

### 10.1 Split unit

Use record/group-level splitting, not beat-level random splitting. All beats from one record must belong to exactly one of train, validation or test. Records 201 and 202 must be grouped together because they originate from one subject.

If reliable patient IDs are not available for every record, call the design **record-independent** or **record/group-aware**, not fully patient-independent. State the limitation.

### 10.2 Freeze and document

Create a split manifest containing:
- dataset version and checksums;
- mapping version;
- train/validation/test record IDs;
- grouping rules;
- excluded records and reasons;
- class support in each split;
- random seed and split-generation code version;
- SHA-256 hash of the manifest.

The split must be created before model training. Do not choose a split because it produces better metrics.

### 10.3 Preprocessing

Every transformation must be fit only on training data. This includes normalization parameters, imputation, feature selection, dimensionality reduction, data-driven filtering thresholds and resampling procedures.

Per-record signal operations that do not learn from other records may be applied independently, but must still be documented and tested.

If class weighting or oversampling is used:
- derive weights from training labels only;
- apply resampling only within training data;
- never duplicate beats before the train/test split;
- do not use synthetic samples in validation or test;
- document that beat-level oversampling does not create independent patients.

### 10.4 ECG segmentation and signal processing

Do not assume a fixed beat-window length or fiducial-point convention without selecting and citing a protocol. The pipeline must document:
- which lead(s) are used and why;
- how beat locations are obtained (reference annotations or detector output);
- window start/end relative to the annotation;
- boundary-beat handling;
- resampling, if any;
- filtering and filter parameters;
- baseline-wander and power-line handling, if used;
- amplitude normalization;
- handling of missing/invalid signal samples;
- treatment of signal-quality annotations.

If reference beat annotations define windows, state clearly that this evaluates classification conditional on reference beat locations; it does not evaluate end-to-end beat detection. Do not claim QRS detection performance unless a QRS detector is evaluated.

### 10.5 Data quality checks

Tests must verify:
- all expected record files are present;
- signal and annotation lengths/timestamps are consistent;
- sampling frequency is read from metadata, not hardcoded blindly;
- no NaN/Inf values enter model tensors;
- all segments have the expected shape;
- labels are in the approved set;
- no record appears in multiple partitions;
- records 201/202 remain grouped;
- all preprocessing is reproducible;
- class counts match the audit report.

---

# PART V — MODEL DEVELOPMENT AND EXPERIMENT DESIGN

## 11. Model development order

Do not begin with encryption, DP, blockchain or robust aggregation. First establish that the data and classifier are valid.

### Stage 1: Trivial baselines

Implement:
- majority-class predictor;
- optionally a simple classical baseline (e.g. logistic regression or random forest) if the chosen feature representation makes it meaningful.

These baselines expose metric and label bugs. The majority baseline is mandatory.

### Stage 2: Centralized deep-learning baseline

Implement one documented 1D CNN baseline first. Architecture must be defined in a config and source code. Record:
- input dimensions;
- convolutional blocks;
- kernel sizes, strides and channels;
- normalization layers;
- activation;
- dropout;
- pooling;
- classifier head;
- parameter count;
- optimizer and learning rate;
- loss function;
- batch size;
- epochs;
- early stopping/checkpoint policy;
- random seeds;
- CPU/GPU and software environment.

A more complex architecture may be added only after the baseline works. Do not keep changing the model until the test score improves.

### Stage 3: Local-only client models

Train the same architecture independently on each client's training partition. This establishes how much each client can learn without collaboration. Report per-client class support and performance. Do not treat local models as equivalent to a single global model.

### Stage 4: Federated baseline

Implement standard FedAvg as the first federated method. Explicitly define:
- client population and number of clients;
- record-to-client allocation;
- IID/non-IID construction;
- participation fraction;
- local epochs;
- batch size;
- optimizer and optimizer-state policy;
- aggregation weights;
- normalization-layer handling;
- number of rounds;
- client dropout policy;
- validation and checkpoint selection.

The global model must be evaluated with the same frozen test set and same metric code as centralized training.

### Stage 5: Non-IID settings

Create at least:
1. IID-like partition, subject to whole-record grouping constraints;
2. moderate label-skew partition;
3. severe label-skew or class-missing-client partition.

Do not generate client splits by randomly distributing individual beats if this causes beats from the same record to appear across clients or violates the intended subject/record separation.

For each client, report record IDs, number of beats, N/S/V/F/Q counts and absent classes. Explain the partition-generation method. If Dirichlet allocation is used, specify its concentration parameter and how record grouping is reconciled with label allocation. Do not claim exact IID when whole-record assignment cannot make it so; use the term IID-like if appropriate.

### Stage 6: FL alternative

After FedAvg has a stable baseline, implement one justified alternative such as FedProx or a personalization approach. State the motivation and cite the original method. Compare using matched data partitions and a comparable training budget. Do not add many algorithms merely to inflate the experiment count.

### Stage 7: Controlled diagnostics

If FedAvg performs poorly, investigate rather than hiding the result. Run controlled ablations for:
- label distribution and class absence per client;
- local epochs and client drift;
- learning rate;
- optimizer-state reset versus persistence;
- batch normalization strategy;
- client participation;
- aggregation weights;
- class weighting;
- checkpoint-selection rule.

Change one factor at a time where feasible. Log every configuration. Do not select the explanation that merely sounds plausible; require evidence.

## 12. Training, validation and model selection

- Training data is used to fit model parameters.
- Validation data is used for hyperparameter selection, early stopping and checkpoint selection.
- Test data is used once for final evaluation after all choices are frozen.
- Never use test metrics to decide which round, seed, architecture, privacy budget or defense is best.
- Save the selected checkpoint and its SHA-256 hash.
- Save the complete config, seed, data/split manifest hash, software environment and training log.
- If round 0 is selected by the predeclared validation criterion, report it; investigate why training did not improve. Do not silently substitute the last round or a different metric.

At least five seeds are recommended if compute permits. If fewer are used, justify the constraint and report all individual seed results. Multiple seeds on one fixed split do not substitute for independent record/subject validation.

## 13. Required classification metrics

For each model/configuration report:
- accuracy;
- macro precision, recall and F1;
- weighted precision, recall and F1;
- per-class precision, recall/sensitivity, F1 and support for N/S/V/F/Q;
- confusion matrix with a fixed class order;
- specificity or false-positive rate where appropriate and clearly defined;
- AUROC/AUPRC only where the one-vs-rest formulation is valid and class support allows it;
- mean and standard deviation across seeds, plus individual seed results.

Report undefined metrics as `NA`/not estimable with an explanation. Do not silently convert undefined class metrics to zero. State the averaging convention and whether absent classes are included in macro averages.

Because MIT-BIH is not a population-representative sample, do not interpret its class frequencies as clinical prevalence. Do not equate heartbeat classification accuracy with patient-level arrhythmia diagnosis.

---

# PART VI — PRIVACY EXPERIMENTS

## 14. Threat model before privacy implementation

Create `docs/threat_model/PRIVACY_THREAT_MODEL.md` before implementing DP/HE. Specify:
- assets to protect;
- adversaries (curious server, malicious client, colluding clients, external observer);
- trusted parties;
- what each party sees;
- key ownership and lifecycle;
- what metadata is public;
- attack surfaces;
- privacy unit (beat, record, patient or client/institution);
- adjacency relation;
- released outputs/transcript;
- assumptions and out-of-scope threats.

Do not use “patient privacy” if the formal privacy unit is a client slot containing many records. Use the exact privacy unit in all claims.

## 15. Differential privacy

### 15.1 Mechanism specification

Before running DP, define:
- central DP, local DP or another explicitly named model;
- protected unit;
- adjacency (add/remove or replace-one);
- clipping operation and norm;
- sensitivity derivation;
- noise distribution and scale;
- client sampling/participation assumptions;
- number of rounds and releases;
- privacy accountant and supported mechanism;
- epsilon and delta;
- what model/checkpoint/metrics are released;
- whether validation-based checkpoint selection is included in the release analysis;
- random-number generator and whether it is cryptographically secure.

A reproducible seeded PRNG is useful for experiments but is not a production CSPRNG. Do not call a seeded research simulation production-secure.

### 15.2 Accounting rules

Use a recognized accountant compatible with the actual mechanism and sampling assumptions. State the accountant and software version. Do not reuse a published epsilon if the implementation differs. Do not calculate epsilon from a formula whose assumptions are not met.

If the accountant's assumptions do not hold, report no formal DP guarantee. A nominal epsilon is not a guarantee.

For client-level DP, clearly define what a client represents and whether the privacy unit is an institution/client dataset slot. If there are only five fixed clients, do not describe the guarantee as record-level or patient-level DP unless the mechanism actually provides that guarantee.

### 15.3 DP experiments

Only after non-private baselines are stable, run:
- no-DP baseline;
- a predeclared set of DP noise levels/privacy budgets;
- matched seeds and client partitions;
- validation-selected checkpoints;
- final test evaluation after choices are frozen.

Measure:
- epsilon/delta and all assumptions;
- accuracy and all classification metrics;
- convergence and selected round;
- clipping frequency/norm statistics (private diagnostics must not leak into public transcript);
- runtime and communication overhead.

Do not choose epsilon after looking at test utility.

## 16. Homomorphic encryption

### 16.1 Design specification

If CKKS is used, document:
- library and exact version;
- polynomial modulus degree;
- coefficient modulus chain;
- scale;
- security parameters and source of security estimate;
- encrypted quantity;
- vector packing;
- key generation and ownership;
- serialization format;
- operations performed homomorphically;
- decryption location;
- approximation/error measurement;
- ciphertext size and communication payload;
- key rotation and destruction policy, if applicable.

Do not claim that CKKS hides an aggregate from the party holding the secret key. If a trusted decryptor sees the clean aggregate, state that explicitly.

### 16.2 Correct comparison

Compare:
- plaintext aggregation;
- HE-only aggregation;
- DP-only;
- HE+DP.

Use the same model, data partition, client updates and seeds where technically possible. Record the precise point where noise is added relative to clipping, encryption, aggregation and decryption.

Measure encryption time, encrypted communication size, homomorphic aggregation time, decryption time, total round time, approximation error and utility.

An observed approximation error on tested vectors is an empirical measurement, not a universal bound. Do not represent it as a formal CKKS error guarantee unless supported by a derivation and implementation-specific proof.

---

# PART VII — BLOCKCHAIN AND AUDITABILITY

## 17. Define the blockchain claim precisely

A SHA-256 hash-chained local ledger is a tamper-evident log. By itself, it is not a distributed blockchain network with independent nodes and consensus.

A local Ganache EVM deployment can test smart contracts and transaction costs. It is not evidence of a public production network, independent validators or real-world consensus decentralization.

The research must distinguish:
1. hash-chain audit log;
2. local smart-contract prototype;
3. distributed permissioned blockchain with independent nodes/consensus.

Only claim the level actually implemented and measured.

## 18. Audit mechanism design

Before implementation, specify:
- who may submit a transaction;
- identity/authentication mechanism;
- what is committed before aggregation;
- how commitments are verified;
- what is recorded after aggregation;
- how global model hashes are calculated;
- how invalid/missing client commitments are handled;
- how replay, duplicate and unauthorized transactions are rejected;
- what happens if the server and client disagree;
- how ledger records are independently verified;
- what remains off-chain.

Do not store raw ECG, patient identifiers, model update tensors, secret keys, private noise seeds or sensitive counts on-chain. Store only approved non-sensitive metadata and cryptographic commitments.

A hash proves integrity relative to the bytes hashed; it does not prove that the underlying update is honest, correctly computed or clinically meaningful.

## 19. Blockchain experiments and measurements

Retain the hash-chain as the baseline. If adding Ganache:
- deploy a documented contract;
- test authorized and unauthorized writes;
- test correct and incorrect hashes;
- test duplicate/replayed round submissions;
- test missing participant commitments;
- test altered model hash;
- test audit reconstruction;
- test contract failure/revert behaviour.

Measure over repeated trials:
- gas used per transaction;
- gas price assumption;
- estimated transaction fee in the chosen test environment;
- transaction latency;
- throughput;
- on-chain storage consumed;
- off-chain storage consumed;
- validation/verification time;
- failed transaction rate.

Report the Ganache version, chain configuration, block time/gas settings, machine, number of trials and summary statistics. Do not invent gas values or claim public-chain energy savings.

---

# PART VIII — ROBUST AGGREGATION AND SECURITY

## 20. Threat model and baselines

Define the adversary's capabilities before writing attack code:
- number/fraction of malicious clients;
- whether the attacker knows the aggregation rule;
- whether the attacker can coordinate;
- whether the attacker can alter labels/data, model updates or both;
- whether attacker controls client identity;
- whether the attacker can adapt to detection;
- attack objective and success criterion.

Evaluate FedAvg and appropriate established baselines. Candidate methods include coordinate-wise median, trimmed mean, Krum/Multi-Krum and FLTrust, but each has assumptions and limitations. Select baselines based on the actual client count, threat model and data heterogeneity. Do not include an algorithm solely for name recognition if its assumptions are violated.

## 21. Required attack and clean conditions

At minimum, where technically applicable:
- clean non-IID clients;
- sign-flip update attack;
- update scaling attack;
- norm-matched noise or benign outlier condition;
- class-missing honest clients;
- multiple malicious clients if feasible;
- adaptive attack if the scope and implementation allow.

Freeze defense thresholds on development data. Evaluate final settings on fresh seeds not used for threshold selection.

Report:
- clean macro-F1 and minority-class recall;
- attack success or model degradation;
- malicious-client detection rate;
- honest-client false-positive rate;
- per-round validity;
- client contribution/rejection counts;
- runtime and communication overhead;
- seed variability.

A method that blocks attacks but rejects honest non-IID clients or destroys clean utility is not an effective defense. If the candidate does not outperform appropriate baselines, report that outcome and revise or withdraw the proposed-method claim.

---

# PART IX — INTEGRATION, REPRODUCIBILITY AND QUALITY CONTROL

## 22. Required experiment matrix

Do not run every combination immediately. Run in the following order and maintain a registry.

| ID family | Experiment | Purpose |
|---|---|---|
| B0 | Majority baseline | Verify label and metric pipeline |
| B1 | Centralized CNN | Reference utility |
| B2 | Local-only models | Local learning reference |
| F1 | IID-like FedAvg | Federated baseline |
| F2 | Moderate non-IID FedAvg | Heterogeneity effect |
| F3 | Severe non-IID FedAvg | Stress heterogeneity |
| F4 | FedProx or one selected FL alternative | Controlled alternative |
| P1 | DP-only sweep | Privacy–utility curve |
| P2 | HE-only | Encryption overhead and utility |
| P3 | HE+DP | Combined privacy mechanism |
| L1 | Hash-chain audit | Baseline auditability |
| L2 | Ganache smart contract | On-chain audit prototype |
| R1 | Robust baselines | Security comparison |
| R2 | Proposed robust aggregator | Candidate method |
| X1 | Integrated selected configuration | Only after independent component validation |
| E1 | Frozen external SVDB evaluation | External generalization evidence |

Every experiment must have:
- unique experiment ID;
- versioned configuration file;
- dataset version/checksum;
- split manifest hash;
- mapping version;
- random seed;
- source-code commit or source snapshot identifier;
- environment and package versions;
- exact command;
- start/end timestamps;
- exit status;
- output directory;
- metrics and model hashes;
- known warnings/failures;
- protocol deviations.

## 23. Reproducible environment

At project start:
1. inspect laptop OS, CPU, RAM, GPU and available disk;
2. choose a supported Python version based on dependencies;
3. create a project-local virtual environment;
4. pin direct and transitive dependencies where practical;
5. record `python --version`, package versions and hardware;
6. confirm the PyTorch build and device support;
7. ensure every script uses the project environment;
8. provide one documented setup command and one documented test command.

On Windows PowerShell, use the project's virtual environment executable explicitly, e.g.:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip freeze
```

Do not assume `python` resolves to the virtual environment. Do not assume CUDA is available. Do not silently fall back from GPU to CPU without logging the actual device.

## 24. Testing requirements

Unit tests:
- annotation inventory and mapping;
- exclusion rules;
- segmentation and boundary handling;
- split disjointness and record grouping;
- no train/test leakage;
- metric calculations and undefined-class handling;
- deterministic partition generation;
- model input/output shapes;
- FedAvg weighted aggregation;
- DP clipping/noise/accounting interfaces;
- HE encrypt/decrypt and aggregation consistency;
- ledger hash validation and tamper detection;
- smart-contract authorization and replay rejection;
- robust aggregator behaviour on synthetic controlled updates.

Integration tests:
- one short centralized training run;
- one short local-only run;
- one short federated round;
- one DP mechanism smoke test;
- one HE aggregation smoke test;
- one ledger lifecycle smoke test;
- one attack/defense smoke test.

Run the complete test suite before expensive experiments and after any material source change. Preserve the full test output. A passing unit test does not prove scientific validity; it proves only the tested software behaviour.

## 25. Documentation required

Create and maintain:
- `README.md` — purpose, setup, commands and project structure;
- `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` — this file;
- `docs/literature/LITERATURE_REVIEW.md` — evidence-based related work and gap;
- `docs/protocol/RESEARCH_PROTOCOL.md` — frozen experimental protocol;
- `docs/data_and_labels/DATA_PROVENANCE.md` — dataset sources, versions and checksums;
- `docs/data_and_labels/AAMI_MAPPING_AND_EXCLUSIONS.md` — full mapping and annotation audit;
- `docs/data_and_labels/SPLIT_POLICY.md` — record lists, grouping and leakage tests;
- `docs/threat_model/PRIVACY_THREAT_MODEL.md` — DP/HE threat model;
- `docs/threat_model/SECURITY_THREAT_MODEL.md` — malicious clients and blockchain assumptions;
- `docs/methodology/EXPERIMENT_REGISTRY.md` — all experiments;
- `docs/methodology/RESULTS_AND_ANALYSIS.md` — results and interpretation;
- `docs/limitations/LIMITATIONS.md` — known limits and claims not established;
- `docs/reproducibility/REPRODUCIBILITY.md` — environment and commands.

## 26. Reporting and statistical discipline

- Report all planned experiments, including failed and null results.
- Distinguish exploratory from confirmatory experiments.
- Show per-seed values, not only the best seed.
- Do not report only the best checkpoint/seed without describing the selection process.
- Use confidence intervals only with a stated method and valid unit of resampling.
- Do not bootstrap beats as if they were independent patients when they are clustered within records/subjects.
- Where possible, use record/subject-level resampling for uncertainty, with caveats for the small number of records.
- Do not compare metrics from different test partitions as if they were paired.
- State whether a metric is micro, macro, weighted or per-class.
- State the class order for every confusion matrix.
- Keep test predictions and final metrics immutable once the evaluation is declared final.

## 27. Final defence evidence package

Before defence, produce:
1. final protocol and all deviations;
2. data provenance and checksum report;
3. annotation inventory and approved AAMI mapping;
4. split manifest and leakage-validation output;
5. model architecture and hyperparameter specification;
6. centralized/local-only/federated baseline comparison;
7. client class-distribution tables;
8. privacy mechanism and accountant report;
9. HE performance and communication-cost report;
10. blockchain contract and audit verification evidence;
11. robust aggregation threat model and attack results;
12. integrated experiment results;
13. per-class metrics, confusion matrices and seed-level tables;
14. reproducibility instructions and environment lock;
15. limitations and a clear answer to each RQ.

The final report must distinguish:
- what was implemented;
- what was tested;
- what worked;
- what did not work;
- what was measured;
- what is only assumed;
- what remains future work.

---

# PART X — EXECUTION ORDER AND STOP/GO GATES

## 28. Mandatory staged execution

### Phase 0 — Fresh workspace and project audit
- Create the new project folder on the laptop.
- Initialize Git only after confirming the folder is correct.
- Add this specification at the repository root.
- Create the approved directory structure.
- Record machine and software environment.
- Establish `.gitignore` for virtual environments, raw data, secrets, large checkpoints and generated artifacts as appropriate.
- Do not import old source code wholesale. Review and selectively port code only after understanding it.
- Produce `docs/PROJECT_STARTUP_AUDIT.md`.

**Deliverable:** clean project skeleton, environment record and startup audit.

### Phase 1 — Literature and protocol freeze
- Read the cited standards and papers.
- Expand the literature matrix with study objective, data, split protocol, label taxonomy, model, FL design, privacy mechanism, blockchain role, attacks, metrics, limitations and relevance.
- Verify each paper from its publisher or authoritative repository.
- Do not cite search snippets as if they were full-paper evidence.
- Identify which methods are genuinely comparable.
- Freeze the five RQs and protocol.

**Deliverable:** literature review, reference library and approved research protocol.

### Phase 2 — Dataset acquisition and annotation audit
- Download the official MIT-BIH version.
- Verify checksums and file completeness.
- Inventory all annotation symbols.
- Map or explicitly exclude every symbol.
- Verify the candidate AAMI mapping against the selected protocol.
- Report per-record and aggregate class support.
- Decide paced-record and Q-class handling.
- Obtain approval.

**STOP:** no model training before Phase 2 approval.

### Phase 3 — Split and preprocessing validation
- Create group-aware train/validation/test record lists.
- Keep records 201 and 202 together.
- Freeze and hash the split manifest.
- Implement segmentation and signal preprocessing.
- Run data-quality and leakage tests.
- Create client manifests using whole-record assignment.
- Report per-client class distributions and absent classes.

**STOP:** no training if any record leaks across partitions, label is unapproved, or manifest counts do not reconcile.

### Phase 4 — Baseline model validation
- Run majority baseline.
- Run centralized CNN smoke test and full baseline.
- Run local-only clients.
- Validate metric code and checkpoint selection.
- Repeat seeds.
- Investigate failures before continuing.

**STOP:** no DP, HE, blockchain integration or proposed defense if the non-private baseline is not trustworthy.

### Phase 5 — Federated learning
- Run IID-like FedAvg.
- Run moderate non-IID FedAvg.
- Run severe non-IID FedAvg.
- Run one selected FL alternative.
- Diagnose the gap with controlled ablations.
- Freeze baseline results.

### Phase 6 — Privacy
- Approve privacy threat model.
- Validate DP implementation and accountant on toy data.
- Run predeclared DP configurations.
- Validate CKKS operations and numerical error on toy vectors.
- Run HE-only.
- Run HE+DP only after component validation.
- Measure all costs and document key ownership.

### Phase 7 — Blockchain audit
- Validate hash-chain baseline.
- Implement Ganache contract separately.
- Test permissions, commitments, replay, tampering and reconstruction.
- Measure gas, latency, throughput and storage.
- Document local-chain limitations.

### Phase 8 — Robust aggregation
- Approve adversary model.
- Implement selected baselines.
- Freeze candidate thresholds on development seeds.
- Run clean and attack conditions on fresh seeds.
- Report false positives and clean-utility cost.

### Phase 9 — Integration
- Integrate only components that passed individual tests.
- Define the exact combined configuration and threat model.
- Run short integration smoke test.
- Review logs, artifacts and privacy boundaries.
- Run full experiment only after written approval.

### Phase 10 — Final evaluation and defence package
- Freeze final model selection and evaluation code.
- Evaluate test data once for the selected configurations.
- Run external SVDB evaluation separately if approved.
- Generate final tables, figures, limitations and RQ answers.
- Re-run reproducibility commands from a clean environment.
- Archive configurations, logs, hashes and reports.

## 29. Stop/go gates

| Gate | Required evidence to proceed |
|---|---|
| G0 Workspace | Correct fresh folder, environment and source-control safety confirmed |
| G1 Literature/protocol | References verified, RQs frozen, protocol approved |
| G2 Taxonomy | All annotation symbols accounted for, mapping/exclusions approved, class support understood |
| G3 Data | Record/group split validated, records frozen, leakage tests pass, checksums/manifests saved |
| G4 Baselines | Majority, centralized, local-only and initial FL runs validated |
| G5 FL diagnosis | IID/non-IID comparisons and explanatory ablations completed |
| G6 Privacy | Threat model and accountant validated; DP/HE assumptions approved |
| G7 Blockchain | Audit design and tests pass; costs measured |
| G8 Robustness | Attack model, baselines and thresholds frozen; independent evaluation complete |
| G9 Integration | Components pass separately; integration tests pass; privacy boundaries reviewed |
| G10 Defence | All RQs answered with evidence, limitations and reproducibility package complete |

If a gate fails, fix the issue and repeat the gate. Do not bypass it to reach a later phase.

---

# PART XI — AI AGENT OPERATING CONTRACT

## 30. Required behaviour of the AI agent

At the start of each task, the agent must:
1. read this file;
2. inspect the current directory and Git status;
3. identify the current phase and gate;
4. list the relevant files before editing;
5. state the planned changes;
6. distinguish facts from assumptions;
7. ask for approval if the requested change crosses a stop/go gate.

For each completed task, report:
- files created/modified;
- decisions made and supporting sources;
- commands executed;
- tests executed and exact pass/fail counts;
- output paths;
- unresolved issues;
- whether the gate passed;
- next permitted task.

The agent must not:
- run full training when asked only to implement data preparation;
- change research questions without approval;
- change label mapping without approval;
- alter the test split after metrics are observed;
- fabricate a literature review or citations;
- download unverified datasets from unofficial mirrors;
- hide warnings, failures or poor results;
- state “complete” without executed validation;
- stage, commit or push without explicit permission.

## 31. First task to assign the AI agent

The first assignment is **Phase 0 only**.

The agent must:
1. inspect the laptop environment and available disk;
2. create the new project skeleton in the folder specified by the user;
3. place this file at the repository root unchanged;
4. create the documentation placeholders listed in Section 25;
5. create a safe `.gitignore`;
6. create a minimal README explaining that training is not yet authorized;
7. create an environment specification without installing large GPU/CUDA packages blindly;
8. produce `docs/PROJECT_STARTUP_AUDIT.md`;
9. run only structural checks;
10. stop and request approval before downloading datasets, implementing preprocessing or training.

The agent must not implement the entire project in one uncontrolled pass.

---

# PART XII — RESEARCH REFERENCES AND EVIDENCE BASE

## 32. Primary sources to read

The following sources support key decisions in this specification. The literature review must be expanded by reading full papers, not relying only on abstracts or search-result snippets.

### Standards and dataset documentation

1. Association for the Advancement of Medical Instrumentation. (2020). *ANSI/AAMI EC57:2012/(R)2020: Testing and reporting performance results of cardiac rhythm and ST segment measurement algorithms*. ANSI/AAMI.  
   https://webstore.ansi.org/standards/aami/ANSIAAMIEC572012R2020  
   Note: the public preview establishes scope and contents; consult the full licensed standard for detailed requirements.

2. Moody, G. B., & Mark, R. G. (2001). The impact of the MIT-BIH Arrhythmia Database. *IEEE Engineering in Medicine and Biology Magazine, 20*(3), 45–50.  
   https://doi.org/10.1109/51.932724

3. Moody, G., & Mark, R. (2005). *MIT-BIH Arrhythmia Database, version 1.0.0*. PhysioNet.  
   https://doi.org/10.13026/C2F305  
   Official data page: https://physionet.org/content/mitdb/1.0.0/

4. PhysioNet. *MIT-BIH Arrhythmia Database Directory*.  
   https://physionet.org/physiobank/database/html/mitdbdir/

### ECG classification and evaluation

5. de Chazal, P., O'Dwyer, M., & Reilly, R. B. (2004). Automatic classification of heartbeats using ECG morphology and heartbeat interval features. *IEEE Transactions on Biomedical Engineering, 51*(7), 1196–1206.  
   https://doi.org/10.1109/TBME.2004.827359

6. Pham, B.-T., Le, P. T., Tai, T.-C., Hsu, Y.-C., Li, Y.-H., & Wang, J.-C. (2023). Electrocardiogram heartbeat classification for arrhythmias and myocardial infarction. *Sensors, 23*(6), 2993.  
   https://doi.org/10.3390/s23062993  
   Relevance: includes an explicit mapping table between beat annotations and AAMI categories. Read its dataset split and balancing procedure critically; do not assume its metrics are directly comparable to a record-independent design.

7. Silva, G. A. L., Silva, P. H. L., Moreira, G. J. P., Freitas, V. L. de S., Gertrudes, J. C., et al. (2026). A systematic review of ECG arrhythmia classification: embedded feasibility, adherence to standards, and fair evaluation. *Research on Biomedical Engineering*.  
   https://doi.org/10.1007/s42600-026-00485-z  
   Relevance: discusses AAMI recommendations, inter-patient evaluation and fair reporting. Review its search and inclusion method before citing conclusions.

### Privacy-preserving federated healthcare

8. Sen, A., Heng, S.-H., & Tan, S.-C. (2026). A review of recent advances in privacy-preserving federated learning for healthcare applications. *Discover Applied Sciences*.  
   https://doi.org/10.1007/s42452-026-09734-3  
   Relevance: reviews 2024–early 2026 healthcare FL literature, including DP, HE, secure aggregation, blockchain, non-IID data, communication overhead, gradient leakage and poisoning. It is an early online version and may be updated.

9. Bokhari et al. (2025). Fusion of Personalized Federated Learning (PFL) with Differential Privacy (DP) Learning for Diagnosis of Arrhythmia Disease. *PLOS ONE, 20*(7), e0327108.  
   https://doi.org/10.1371/journal.pone.0327108  
   Relevance: arrhythmia, personalized FL and local DP. Verify exact implementation and privacy definition before comparing.

10. Manwal, M., Londhe, G. V., & Purohit, K. C. (2026). Federated learning with update level noise perturbation and blockchain audit logging for privacy-preserving healthcare ECG classification. *Scientific Reports, 16*, Article 35035.  
    https://doi.org/10.1038/s41598-026-75517-w  
    Relevance: directly combines ECG FL, update-level noise and blockchain audit logging on MIT-BIH. **Critical methodological caution:** the article reports beat-level random splitting after duplication-based class balancing, allowing duplicated beats and same-patient beats across train/test; its high accuracy therefore does not establish independent-patient generalization. It also explicitly states its RDP accountant assumptions are not met and makes no formal (epsilon, delta)-DP claim. Read this paper carefully as a close comparator and as an example of why split and accounting methodology matter.

### Further literature search required

The agent/researcher must search IEEE Xplore, PubMed, Scopus or Web of Science, ACM Digital Library, SpringerLink, ScienceDirect and relevant proceedings for:
- original FedAvg and FedProx papers;
- client-level and record-level DP in FL;
- RDP/PLD/GDP privacy accountants appropriate to the chosen mechanism;
- CKKS scheme and TenSEAL/SEAL technical documentation;
- secure aggregation and HE threat models;
- blockchain-enabled FL surveys and primary implementations;
- Krum, Multi-Krum, coordinate median, trimmed mean, RFA and FLTrust;
- ECG FL under non-IID and patient-independent splits;
- adversarial robustness in healthcare FL.

Record search dates, databases, exact search strings, inclusion/exclusion criteria and reasons for excluding studies. Do not call a narrative search a systematic review unless the method follows a recognized systematic-review protocol.

## 33. Evidence-based limitations to carry into the thesis

- MIT-BIH has 48 recordings from 47 subjects, not a large modern multi-hospital cohort.
- The dataset dates from 1975–1979 and is not representative of all contemporary ECG devices or populations.
- Records 201 and 202 share a subject.
- Rare classes and Q-class support may be insufficient in some splits.
- Record-independent is not necessarily patient-independent when identity information is incomplete.
- A beat classifier using reference annotations is not an end-to-end arrhythmia detector.
- High beat-level accuracy may be inflated by beat-level random splitting, duplication-based balancing or other leakage.
- FL clients simulated from one public dataset are not equivalent to independent hospitals with real institutional governance.
- DP guarantees are mechanism- and adjacency-specific.
- HE does not eliminate trust in key holders or all side channels.
- Local Ganache measurements are not production blockchain measurements.
- Robust aggregation can reject honest clients under non-IID data.
- A prototype experiment is not clinical validation.

---

# FINAL AUTHORIZATION RULE

**The AI agent is authorized to execute only the current approved phase. It is not authorized to skip gates, change research decisions, begin expensive training, or claim scientific validity without evidence.**

The first authorized action is Phase 0 only. After the Phase 0 audit is reviewed and approved, authorize Phase 1, then proceed sequentially.

**End of specification.**
