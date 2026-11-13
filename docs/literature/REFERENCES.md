# Phase 1 Reference Register

**Checked:** 13 November 2026  
**Status:** Phase 1 register approved by the research lead on 13 November 2026; not an exhaustive systematic-review bibliography.

“Metadata verified” means the bibliographic record was checked against a publisher, standards body, DOI/Crossref or official dataset record. It does not mean the full paper or standard was read. Access limits and unresolved metadata are stated rather than inferred.

## Standards and dataset

1. Association for the Advancement of Medical Instrumentation. (2020). *ANSI/AAMI EC57:2012/(R)2020: Testing and reporting performance results of cardiac rhythm and ST segment measurement algorithms*. [ANSI listing](https://webstore.ansi.org/standards/aami/ANSIAAMIEC572012R2020). Title/edition verified; the licensed full text was not provided or accessed in this workspace. Do not make clause-level or compliance claims.
2. Moody, G. B., & Mark, R. G. (2001). The impact of the MIT-BIH Arrhythmia Database. *IEEE Engineering in Medicine and Biology Magazine, 20*(3), 45–50. [DOI](https://doi.org/10.1109/51.932724). Metadata verified; full IEEE text was not accessed.
3. Moody, G., & Mark, R. (2005). *MIT-BIH Arrhythmia Database (version 1.0.0)*. PhysioNet. [DOI](https://doi.org/10.13026/C2F305) | [official dataset page](https://physionet.org/content/mitdb/1.0.0/).
4. *MIT-BIH Arrhythmia Database Directory*. PhysioNet, hypertext edition dated 24 May 1997, based on the 1992 third edition. [Official directory](https://physionet.org/physiobank/database/html/mitdbdir/). Treat as legacy documentation, not a separately dated dataset release.

## ECG classification and review

5. de Chazal, P., O’Dwyer, M., & Reilly, R. B. (2004). Automatic classification of heartbeats using ECG morphology and heartbeat interval features. *IEEE Transactions on Biomedical Engineering, 51*(7), 1196–1206. [DOI](https://doi.org/10.1109/TBME.2004.827359). Metadata verified; split details require full-text review.
6. Pham, B.-T., Le, P. T., Tai, T.-C., Hsu, Y.-C., Li, Y.-H., & Wang, J.-C. (2023). Electrocardiogram heartbeat classification for arrhythmias and myocardial infarction. *Sensors, 23*(6), 2993. [Full text at PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10051525/) | [DOI](https://doi.org/10.3390/s23062993). Full text accessed. Use mapping only as a candidate; inspect split and resampling limitations in the review.
7. Silva, G. A. L., Silva, P. H. L., Moreira, G. J. P., Freitas, V. L. de S., Gertrudes, J. C., et al. (2026). A systematic review of ECG arrhythmia classification: embedded feasibility, adherence to standards, and fair evaluation. *Research on Biomedical Engineering, 42*(3). [DOI](https://doi.org/10.1007/s42600-026-00485-z). Metadata/abstract checked; full text and review methods inaccessible.

## Federated learning

8. McMahan, B., Moore, E., Ramage, D., Hampson, S., & Agüera y Arcas, B. (2017). Communication-efficient learning of deep networks from decentralized data. *Proceedings of AISTATS, 54*, 1273–1282. [PMLR full text](https://proceedings.mlr.press/v54/mcmahan17a.html).
9. Li, T., Sahu, A. K., Talwalkar, A., & Smith, V. (2020). Federated optimization in heterogeneous networks. *Proceedings of Machine Learning and Systems, 2*. [Proceedings record](https://proceedings.mlsys.org/paper_files/paper/2020/hash/1f5fe83998a09396ebe6477d9475ba0c-Abstract.html). FedProx primary-method source.

## Privacy and homomorphic encryption

10. Abadi, M., et al. (2016). Deep learning with differential privacy. *Proceedings of the ACM Conference on Computer and Communications Security*, 308–318. [arXiv full text](https://arxiv.org/abs/1607.00133) | [ACM DOI](https://doi.org/10.1145/2976749.2978318).
11. Mironov, I. (2017). Rényi differential privacy. *2017 IEEE 30th Computer Security Foundations Symposium*, 263–275. [arXiv full text](https://arxiv.org/abs/1702.07476) | [IEEE DOI](https://doi.org/10.1109/CSF.2017.11).
12. Bokhari et al. (2025). Fusion of Personalized Federated Learning (PFL) with Differential Privacy (DP) Learning for Diagnosis of Arrhythmia Disease. *PLOS ONE, 20*(7), e0327108. [Full text](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0327108) | [DOI](https://doi.org/10.1371/journal.pone.0327108). Full text accessed; task differs from the project’s MIT-BIH five-class beat classification.
13. Cheon, J. H., Kim, A., Kim, M., & Song, Y. (2017). Homomorphic encryption for arithmetic of approximate numbers. *ASIACRYPT 2017, Lecture Notes in Computer Science, 10624*, 409–437. [IACR full text](https://eprint.iacr.org/2016/421) | [Springer DOI](https://doi.org/10.1007/978-3-319-70694-8_15).
14. Microsoft. *Microsoft SEAL*. [Official project](https://github.com/microsoft/SEAL). Implementation documentation, not an independent security proof.
15. OpenMined. *TenSEAL*. [Official project](https://github.com/OpenMined/TenSEAL). Implementation documentation, not an independent security proof.
16. Sen, A., Heng, S.-H., & Tan, S.-C. (2026). A review of recent advances in privacy-preserving federated learning for healthcare applications. *Discover Applied Sciences*. [DOI](https://doi.org/10.1007/s42452-026-09734-3). Metadata and first-online date checked; full text inaccessible.

## Blockchain and robust aggregation

17. Kim et al. (2020). Blockchained on-device federated learning. *IEEE Communications Letters, 24*(6), 1279–1283. [DOI](https://doi.org/10.1109/LCOMM.2019.2921755). Metadata checked; full IEEE text was not retrieved.
18. Blanchard, P., El Mhamdi, E. M., Guerraoui, R., & Stainer, J. (2017). Machine learning with adversaries: Byzantine tolerant gradient descent. *Advances in Neural Information Processing Systems*. [NeurIPS record](https://proceedings.neurips.cc/paper/2017/hash/f4b9ec30ad9f68f89b29639786cb62ef-Abstract.html). Krum primary-method source.
19. Yin, D., Chen, Y., Kannan, R., & Bartlett, P. (2018). Byzantine-robust distributed learning: Towards optimal statistical rates. *Proceedings of ICML, 80*. [PMLR record](https://proceedings.mlr.press/v80/yin18a.html). Coordinate median and trimmed-mean primary-method source.
20. Cao, X., Fang, M., Liu, J., & Gong, N. Z. (2021). FLTrust: Byzantine-robust federated learning via trust bootstrapping. *Network and Distributed System Security Symposium*. [NDSS record](https://www.ndss-symposium.org/ndss-paper/fltrust-byzantine-robust-federated-learning-via-trust-bootstrapping/). Requires a clean server-side root dataset; confirm full method assumptions before selecting it.
21. Manwal, M., Londhe, G. V., & Purohit, K. C. (2026). Federated learning with update level noise perturbation and blockchain audit logging for privacy-preserving healthcare ECG classification. *Scientific Reports, 16*, Article 35035. [DOI](https://doi.org/10.1038/s41598-026-75517-w). Bibliographic record checked; full text inaccessible. Methodological details and any claims about its split or DP accounting remain unverified.

## Citation work remaining

- Verify complete author metadata for any source whose publisher record was incomplete before final thesis citation.
- Obtain full text for sources marked inaccessible and record the actual split, labels, preprocessing, metrics and threat model.
- Expand the bibliography through a documented database search before describing the work as a systematic review.
