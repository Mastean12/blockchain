# Phase 3 Final Evaluation: Split Limitations

**Review date:** 13 November 2026  
**Status:** Focused evaluation complete; the research lead retained the frozen G3 split  
**Scope:** Class-support limitations of the frozen G3 split and feasibility of a prospective group-aware alternative  
**Training:** Not started; Phase 4 has not begun

## Executive finding

The missing classes in the frozen split are a consequence of assigning whole record groups without class stratification. The approved split is valid under its stated design and passed G3, but validation has no Q examples and test has no F examples. These absences do not indicate a label-mapping or preprocessing failure.

A record/group-aware alternative with all five classes present in validation and test is feasible without splitting beats or records across partitions. One explicit proposal is given below. It provides 5 Q and 14 F validation windows, and 2 Q and 362 F test windows after the existing boundary-window policy. However, the two test Q annotations come from one record, and all test F annotations come from one record. Class presence therefore does not establish reliable cross-record performance.

**Recommendation:** Preserve the approved split as the primary frozen evaluation unless the research lead explicitly approves a replacement before any Phase 4 model fitting. If the current split is retained, report unsupported class metrics as “not estimable”; do not report a five-class macro metric as if all five classes were evaluated. If the candidate is approved, regenerate and freeze its manifests, preprocessing arrays, train-only normalizer, and audit report before Phase 4.

## Evidence and method

This review uses the frozen [Phase 3 split manifest](../data/splits/phase3_split_manifest.json), [training-client manifest](../data/splits/client_manifests.json), [per-record annotation audit](./data_and_labels/MITBIH_PER_RECORD_AAMI_COUNTS.csv), [preprocessing audit](./data_and_labels/PHASE3_PREPROCESSING_AUDIT.json), and [approved split policy](./data_and_labels/SPLIT_POLICY.md). The approved group rule joins records 201 and 202; no patient identity is inferred for other records.

The current split and client manifest hashes were verified against their contents:

- Split: `bbcfa25c7f0e0d903a6de44ccbaa6eb3fa0716253ff1ea730c912f99534d6f96`
- Clients: `71dbcac37e2a605d5edcd0ce280acec60068a1f1defb4f403bc32a5e1cb8eba3`

The record-level tables below report mapped annotation counts before boundary-window drops. Client counts likewise describe mapped training annotations, not processed windows. Processed window counts are reported separately.

## Why Q is absent from validation

There are only 15 eligible Q annotations, concentrated in five record groups:

| Record | Q annotations | Frozen partition |
|---:|---:|---|
| 101 | 2 | Test |
| 105 | 5 | Train |
| 203 | 4 | Train |
| 208 | 2 | Train |
| 214 | 2 | Train |

No Q-bearing group landed in the six-group validation partition. The split generator shuffled groups and allocated them to 70/15/15 proportions; it did not stratify or retry against class support. Under a uniform shuffle of 43 groups with five Q-bearing groups, the chance that all six validation groups contain no Q-bearing group is about **45.3%**. This is an allocation consequence of very sparse Q support, not evidence that Q labels were lost in validation preprocessing.

The `/` and `f` symbols that map to Q occur only in the four excluded paced records. The 15 Q observations in the eligible dataset are the mapped `Q` annotations listed above.

## Why F is absent from test

The eligible dataset has 803 F annotations across 17 records, or 16 groups after grouping 201/202. The frozen validation set contains 14 F annotations from records 108, 109, and 210. The training set contains the remaining 789. None of the seven test groups contains an F annotation:

`108, 109, 114, 124, 200, 201/202, 203, 205, 208, 210, 213, 214, 215, 219, 223, 233`

The test allocation therefore has zero F support despite F being present in many eligible groups. Under a uniform shuffle of the 43 groups, with 16 F-bearing groups and seven test groups, the chance of selecting no F-bearing group for test is about **2.76%**. This is less likely than the Q/validation absence, but is possible under the frozen unstratified algorithm.

These probabilities describe the fixed-size group shuffle only. They are not hypothesis tests and do not justify redrawing the split after observing model results.

## Frozen record-level class distribution

Counts are mapped annotations in class order N/S/V/F/Q. Zero-count rows are retained so the support gap is visible for every record.

### Train

| Record | N | S | V | F | Q |
|---:|---:|---:|---:|---:|---:|
| 105 | 2,526 | 0 | 41 | 0 | 5 |
| 106 | 1,507 | 0 | 520 | 0 | 0 |
| 113 | 1,789 | 6 | 0 | 0 | 0 |
| 114 | 1,820 | 12 | 43 | 4 | 0 |
| 115 | 1,953 | 0 | 0 | 0 | 0 |
| 116 | 2,302 | 1 | 109 | 0 | 0 |
| 117 | 1,534 | 1 | 0 | 0 | 0 |
| 121 | 1,861 | 1 | 1 | 0 | 0 |
| 123 | 1,515 | 0 | 3 | 0 | 0 |
| 124 | 1,536 | 31 | 47 | 5 | 0 |
| 200 | 1,743 | 30 | 826 | 2 | 0 |
| 201 | 1,635 | 128 | 198 | 2 | 0 |
| 202 | 2,061 | 55 | 19 | 1 | 0 |
| 203 | 2,529 | 2 | 444 | 1 | 4 |
| 205 | 2,571 | 3 | 71 | 11 | 0 |
| 207 | 1,543 | 107 | 210 | 0 | 0 |
| 208 | 1,586 | 2 | 992 | 373 | 2 |
| 209 | 2,621 | 383 | 1 | 0 | 0 |
| 212 | 2,748 | 0 | 0 | 0 | 0 |
| 213 | 2,641 | 28 | 220 | 362 | 0 |
| 214 | 2,003 | 0 | 256 | 1 | 2 |
| 215 | 3,195 | 3 | 164 | 1 | 0 |
| 219 | 2,082 | 7 | 64 | 1 | 0 |
| 220 | 1,954 | 94 | 0 | 0 | 0 |
| 222 | 2,274 | 209 | 0 | 0 | 0 |
| 223 | 2,045 | 73 | 473 | 14 | 0 |
| 228 | 1,688 | 3 | 362 | 0 | 0 |
| 230 | 2,255 | 0 | 1 | 0 | 0 |
| 231 | 1,568 | 1 | 2 | 0 | 0 |
| 233 | 2,230 | 7 | 831 | 11 | 0 |
| 234 | 2,700 | 50 | 3 | 0 | 0 |

### Validation

| Record | N | S | V | F | Q |
|---:|---:|---:|---:|---:|---:|
| 100 | 2,239 | 33 | 1 | 0 | 0 |
| 103 | 2,082 | 2 | 0 | 0 | 0 |
| 108 | 1,740 | 4 | 17 | 2 | 0 |
| 109 | 2,492 | 0 | 38 | 2 | 0 |
| 210 | 2,423 | 22 | 195 | 10 | 0 |
| 221 | 2,031 | 0 | 396 | 0 | 0 |

### Test

| Record | N | S | V | F | Q |
|---:|---:|---:|---:|---:|---:|
| 101 | 1,860 | 3 | 0 | 0 | 2 |
| 111 | 2,123 | 0 | 1 | 0 | 0 |
| 112 | 2,537 | 2 | 0 | 0 | 0 |
| 118 | 2,166 | 96 | 16 | 0 | 0 |
| 119 | 1,543 | 0 | 444 | 0 | 0 |
| 122 | 2,476 | 0 | 0 | 0 | 0 |
| 232 | 398 | 1,382 | 0 | 0 | 0 |

### Partition and processed-window totals

| Partition | Records | Raw N | Raw S | Raw V | Raw F | Raw Q | Processed windows (N/S/V/F/Q) |
|---|---:|---:|---:|---:|---:|---:|---|
| Train | 31 | 64,015 | 1,237 | 5,901 | 789 | 13 | 63,989 / 1,237 / 5,900 / 788 / 13 |
| Validation | 6 | 13,007 | 61 | 647 | 14 | 0 | 13,000 / 61 / 647 / 14 / 0 |
| Test | 7 | 13,103 | 1,483 | 461 | 0 | 2 | 13,099 / 1,483 / 461 / 0 / 2 |

Preprocessing dropped 39 boundary windows. Thus F remains absent from test and Q remains absent from validation after preprocessing.

## Frozen training-client distribution

Clients contain training groups only; there are no validation or test clients in the approved design. Counts below are mapped training annotations.

| Client | Training records | N | S | V | F | Q | Absent classes |
|---|---|---:|---:|---:|---:|---:|---|
| client_01 | 117, 124, 208, 220, 222, 230 | 11,139 | 337 | 1,040 | 378 | 2 | — |
| client_02 | 113, 116, 123, 200, 213, 228 | 11,678 | 68 | 1,520 | 364 | 0 | Q |
| client_03 | 105, 205, 207, 212, 231, 233 | 13,186 | 118 | 1,155 | 22 | 5 | — |
| client_04 | 114, 115, 201, 202, 203, 223, 234 | 14,743 | 320 | 1,180 | 22 | 4 | — |
| client_05 | 106, 121, 209, 214, 215, 219 | 13,269 | 394 | 1,006 | 3 | 2 | — |

The client allocation spreads Q across four clients, but client_02 has no Q. This is expected under record-level allocation and should be reported when evaluating local models or federated client behavior.

## Feasible prospective alternative

The following deterministic whole-group swaps preserve the existing 30/6/7 group allocation and retain records 201/202 together:

1. Move record 105 from train to validation; move record 100 from validation to train.
2. Move record 213 from train to test; move record 111 from test to train.

The resulting groups are disjoint, all 44 approved records appear exactly once, and no beat-level assignment or copying is introduced.

| Partition | Candidate record IDs |
|---|---|
| Train (30 groups, 31 records) | 100, 106, 111, 113, 114, 115, 116, 117, 121, 123, 124, 200, 201, 202, 203, 205, 207, 208, 209, 212, 214, 215, 219, 220, 222, 223, 228, 230, 231, 233, 234 |
| Validation (6 groups, 6 records) | 103, 105, 108, 109, 210, 221 |
| Test (7 groups, 7 records) | 101, 112, 118, 119, 122, 213, 232 |

| Partition | Raw N | Raw S | Raw V | Raw F | Raw Q | Processed windows (N/S/V/F/Q) |
|---|---:|---:|---:|---:|---:|---|
| Train | 63,210 | 1,242 | 5,642 | 427 | 8 | 63,183 / 1,242 / 5,641 / 426 / 8 |
| Validation | 13,294 | 28 | 687 | 14 | 5 | 13,289 / 28 / 687 / 14 / 5 |
| Test | 13,621 | 1,511 | 680 | 362 | 2 | 13,616 / 1,511 / 680 / 362 / 2 |

The candidate places all five classes in both validation and test. Validation Q comes from record 105 (5 annotations); test Q still comes only from record 101 (2 annotations). Test F comes only from record 213 (362 annotations). F therefore has many test beats but only one test record; Q remains extremely sparse. These are not 362 independent patient examples or a reliable estimate of F generalization across records.

The candidate also reduces training support from 13 to 8 Q annotations and from 789 to 427 F annotations. Its deterministic five-client assignment leaves Q absent from clients 03 and 05:

| Candidate client | Training records | N | S | V | F | Q | Absent classes |
|---|---|---:|---:|---:|---:|---:|---|
| client_01 | 113, 114, 123, 207, 208, 234 | 10,953 | 177 | 1,251 | 377 | 2 | — |
| client_02 | 111, 116, 117, 203, 215, 222 | 13,957 | 216 | 718 | 2 | 4 | — |
| client_03 | 100, 200, 209, 228, 230, 231 | 12,114 | 450 | 1,193 | 2 | 0 | Q |
| client_04 | 106, 115, 205, 214, 219, 223 | 12,161 | 83 | 1,384 | 27 | 2 | — |
| client_05 | 121, 124, 201, 202, 212, 220, 233 | 14,025 | 316 | 1,096 | 19 | 0 | Q |

### Prospective candidate hashes

These hashes were calculated in memory from the current manifest schema using proposal-only metadata and the deterministic client allocator. They are not written manifests, are not approved, and do not replace the frozen G3 hashes:

- Proposed split payload SHA-256: `1906bbf4956486c96590eba51757d320a3393dc08cbb749ca0a5caf91ee921e1`
- Proposed client payload SHA-256: `f19766fcc63e530026036ccf426321ebaf9cb1b41a3d9a3311800b73c6f3b3fa`

The candidate split hash identifies the exact swaps, record assignments, class counts, and proposal-only marker. The client hash is linked to that candidate split hash and uses the existing deterministic greedy client-allocation rule. If approved, the implementation must generate and validate the actual manifests before Phase 4; any implementation-version or payload change must be reflected in newly computed hashes.

No candidate arrays or candidate preprocessing report were created. The candidate processed class counts above were reconstructed from the existing record-ID and label arrays; the candidate train-only normalization parameters and artifact checksums must be recomputed from raw signals if this split is approved. No existing Phase 3 artifacts or manifests were changed.

## Evaluation implications and recommendation

### If the frozen split is retained

- Report validation Q and test F metrics as **not estimable**, not as zero.
- For validation checkpoint selection, predeclare a metric over the supported classes N/S/V/F and label it explicitly as four-class validation macro-F1. Do not describe it as five-class validation performance.
- Report test per-class metrics for N/S/V/Q only. Any aggregate must be explicitly named as an aggregate over test-supported classes; do not present it as five-class macro-F1.
- Publish class support and confusion matrices alongside the metrics. Do not use beat-level resampling as if beats were independent records.

### If the candidate is approved

- Approve the exact record swap and the changed training/client distributions before any model fitting.
- Implement the candidate as a versioned split-generation path, write new manifests separately, verify no group/record overlap and client coverage, and recompute preprocessing and train-only normalization from raw signals.
- Freeze the metric definitions and class-support reporting before model fitting. Although all five classes would be present in both validation and test, Q is only 5/2 beats and F test support is concentrated in one record. Report these as severe support limitations; do not imply five-class patient-independent performance.
- Keep records 201/202 together. The dataset does not establish subject identity for all other records, so neither the original nor proposed design supports an unconditional patient-independent claim.

**Disposition:** The research lead chose to retain the frozen G3 split. The proposal-only alternative was not adopted. No split has been changed, no model has been trained, and Phase 4 has not begun. This decision does not authorize Phase 4.
