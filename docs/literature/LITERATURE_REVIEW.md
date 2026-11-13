# Literature Review

**Project:** A Blockchain-Enabled Privacy-Preserving Federated Learning Framework for ECG Arrhythmia Classification  
**Status:** Approved by the research lead on 13 November 2026, with documented source-access limitations  
**Review date:** 13 November 2026

## 1. Scope and evidence standard

This focused review supports five questions: AAMI-derived ECG heartbeat classification; centralized versus federated learning under client heterogeneity; differential privacy (DP) and homomorphic encryption (HE); blockchain-backed auditability; and robust aggregation. It is not a systematic review. References were checked against publisher, standards-body, PhysioNet, or primary-method records where available. Abstracts and bibliographic records are not treated as substitutes for inaccessible full texts.

The existing root-level `Literature%20Review.md` was preserved unchanged. It contains a separate execution sequence and gate structure. This review follows `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md`; any conflict between the two remains a research decision, not an implicit reconciliation.

## 2. Evidence matrix

| Source | Objective, data, taxonomy and method | Privacy, ledger, attacks and reported evaluation | Limits and relevance here |
|---|---|---|---|
| ANSI/AAMI EC57:2012/(R)2020 | Standard for testing and reporting cardiac rhythm and ST-segment algorithms. The ANSI listing confirms the title and edition. | The licensed full text was not accessible for this review. Detailed requirements, exclusions and exact mapping recommendations have not been independently checked. | Governing standard for applicable reporting decisions, but using five labels does not itself establish compliance. Obtain and consult the full standard before claiming conformity. |
| Moody & Mark (2001); Moody & Mark (2005); PhysioNet MIT-BIH documentation | Database history and primary dataset documentation. PhysioNet documents 48 approximately half-hour, two-channel records from 47 subjects, sampled at 360 Hz, recorded in 1975–1979. Records 201 and 202 are from the same subject. | Reference-database descriptions, not an evaluation of this project’s model or privacy/security mechanisms. | Supports provenance and record grouping. Does not support population-prevalence or modern multi-institution generalization claims. The MIT-BIH Directory is a legacy 1997 hypertext edition based on its 1992 third edition. |
| de Chazal, O’Dwyer & Reilly (2004) | Foundational heartbeat-classification paper using ECG morphology and heartbeat-interval features. The title and bibliographic record were verified. | Exact split, taxonomy, model details and metrics were not verified from full text in this review. | Useful historical comparator. Its scores are not a fair direct comparison until its records, labels, and evaluation protocol are checked against this study’s protocol. |
| Pham et al. (2023) | Full text is available through PMC. It reports MIT-BIH ECG classification and publishes an N/S/V/F/Q beat-annotation mapping. | The article describes five-fold MIT-BIH cross-validation, but also contains a five-/ten-fold wording inconsistency. Its described oversampling includes validation data. The split is not clearly established as record/patient-grouped. | A candidate mapping reference, not the authority for the final mapping or a record-independent performance claim. The mapping must be checked against raw PhysioNet annotations and the licensed standard. Its headline metrics are not directly comparable to a group-aware split. |
| Silva et al. (2026) | Systematic-review title and abstract metadata were verified. The abstract identifies standard adherence, inter-patient evaluation and embedded feasibility as topics. | Full text and review methods were inaccessible. Search strategy, selection process and detailed conclusions remain unverified. | A useful review lead, not sufficient evidence for specific conclusions until full methods are read. |
| McMahan et al. (2017), FedAvg | Primary method for communication-efficient federated averaging. Not ECG-specific. | Does not establish privacy, auditability or Byzantine robustness. | Grounding for the first FL baseline. Compare only under the project’s own matched model, partition, validation/test set and budget. |
| Li et al. (2020), FedProx | Primary method addressing statistical and systems heterogeneity in federated optimization. Not ECG-specific. | Does not establish privacy or attack robustness. | Candidate single FL alternative after FedAvg is stable. Any comparison should use the same client data and comparable training budget. |
| Abadi et al. (2016); Mironov (2017) | Primary foundations for differentially private deep learning and Rényi differential privacy (RDP), respectively. | These papers do not determine the project’s privacy unit, sampling assumptions, release transcript or accountant validity. | Use to ground mechanism/accounting choices. A formal guarantee requires a derivation matching the implemented clipping, noise, sampling, composition and releases. |
| Bokhari et al. (2025) | Full text is available. The study describes personalized FL and local DP for a 12-lead, four-label rhythm task on 10,646 recordings, with FedAvg-style aggregation. | Its clipping/noise description alone does not establish a reproducible formal DP guarantee; adjacency, sampling and cumulative accounting require scrutiny. | Relevant to ECG FL/DP design, but its task, data and labels differ from this MIT-BIH five-class beat-classification study. Not a direct metrics comparator. |
| Cheon et al. (2017), CKKS; Microsoft SEAL; TenSEAL | CKKS is an approximate-arithmetic HE scheme. SEAL and TenSEAL are implementation references. | HE does not itself provide DP, integrity, authentication, or protection from a party holding the secret key. Library documentation is not an independent security proof. | Ground HE design and implementation. Document key ownership, decryption location, ciphertext expansion and measured approximation error for the actual pipeline. |
| Kim et al. (2020), “Blockchained On-Device Federated Learning” | Primary-method lead for blockchain-assisted FL; bibliographic metadata verified. | Full IEEE paper was not retrieved in this review. | Relevant background only. It does not show that a local hash-chain or Ganache instance is a production distributed blockchain, nor that blockchain provides data privacy. |
| Blanchard et al. (2017), Krum; Yin et al. (2018), coordinate median/trimmed mean; Cao et al. (2021), FLTrust | Primary sources for established robust-aggregation families. Their assumptions differ. FLTrust requires a clean server-side root dataset; Krum and coordinate-wise methods have their own attacker-count and distribution assumptions. | These methods address adversarial updates under defined assumptions, not all malicious-client behavior. Honest non-IID clients can resemble outliers. | Select baselines based on actual client count, threat model and data heterogeneity. Compare on matched partitions and attacks; report clean utility and honest-client false positives. |
| Sen, Heng & Tan (2026) | Bibliographic metadata and first-online date were verified for a healthcare privacy-preserving FL review. | Full text was inaccessible; its detailed topic coverage and conclusions remain unverified. | Retain as a review lead only. Do not rely on detailed claims until the full article is inspected. |
| Manwal, Londhe & Purohit (2026) | Crossref metadata verifies the article title, authors, journal, volume, article number and first-online date. Full text was inaccessible. | Claims in other project material about its split, duplication-based balancing, accounting assumptions or DP claim status could not be verified here. | A close-comparator lead, but all methodological criticisms and comparisons are provisional until checked against full text or an authoritative manuscript. |

## 3. Comparability rules

1. **Direct project comparisons** use the same approved label mapping, held-out record/group set, metric implementation, model where applicable, and comparable training budgets.
2. **Literature comparisons** are contextual unless their data, labels, record membership, split unit, preprocessing, metric definitions and selection procedure are sufficiently aligned.
3. Beat-level random splits, pre-split duplication/resampling, or validation/test oversampling are not evidence of record-independent generalization.
4. A paper using different ECG leads, a rhythm-level task, different labels, or a different dataset may inform method design but is not a direct performance benchmark.
5. Method families are not interchangeable. In particular, FedAvg versus FedProx, local versus central DP, CKKS versus plaintext aggregation, and Krum versus FLTrust have different assumptions and must be described as such.

## 4. Synthesis and defensible research gap

The literature establishes that federated learning, DP, HE, blockchain-backed logging, and robust aggregation already exist individually and in combinations. The study must not claim novelty merely by combining these components.

The defensible gap is an application-specific, reproducible comparison of how ECG client heterogeneity and class imbalance interact with privacy mechanisms, audit logging, and robust aggregation under a fixed AAMI-derived task, record/group-aware evaluation, explicit threat models, and measured utility and systems costs.

The study can investigate:

- whether apparent centralized/federated gaps persist with group-aware records and transparent per-client class distributions;
- how controlled label-skew conditions and selected FL alternatives affect global and per-class utility;
- the utility and measured cost of DP-only, HE-only, and combined HE+DP under stated trust/accounting assumptions;
- whether a hash-chain baseline and a local smart-contract prototype improve audit verification, and at what measured cost;
- whether a selected robust aggregator mitigates predeclared attacks without disproportionate harm to honest non-IID clients.

**Provisional contribution statement:** The work aims to provide a controlled experimental framework and comparative evaluation for AAMI-derived ECG heartbeat classification under centralized and federated learning, assessing heterogeneity, DP, CKKS-based HE, blockchain-backed audit logging, and a candidate robust aggregator. The contribution is intended to be reproducible integration and measurement, not an unsupported claim that the component techniques are new.

## 5. Evidence gaps and required follow-up

- The research lead reports access to the full licensed EC57 standard. Read and document the relevant clauses before making clause-level or compliance statements.
- Read full texts for sources that were only checked via publisher metadata or abstracts, especially Silva et al. (2026), Sen et al. (2026), Manwal et al. (2026), and the cited IEEE papers.
- Resolve incomplete bibliographic metadata before final thesis citation; do not infer missing author or issue details.
- Expand the search using a recorded date, databases, exact queries and inclusion/exclusion criteria before describing the review as systematic.
- Verify the exact MIT-BIH symbols and annotation meanings against official PhysioNet documentation and the approved annotation protocol during Phase 2.
- Phase 1 source review and protocol are approved. Preserve the access limitations above; do not make unsupported claims about inaccessible papers or EC57 clauses. Proceed to Phase 2 only according to the master specification.

## 6. Source register

See [REFERENCES.md](REFERENCES.md) for checked metadata, authoritative URLs, and access/verification status.
