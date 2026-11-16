# Phase 3 Split and Preprocessing Policy

**Status:** G3 passed; split and preprocessing manifests frozen before model training  
**Approval date:** 13 November 2026  
**Dataset:** MIT-BIH Arrhythmia Database v1.0.0  
**Eligible records:** 44, after excluding paced records 102, 104, 107 and 217

## Frozen group-aware split

The split uses seed `42` to shuffle the 43 record groups, then allocates groups by largest remainder to target proportions 70/15/15. There were no metric-based retries. Records 201 and 202 form one group; every other eligible record is a separate group. Other patient identities are not inferred, so this is record/group-aware, not a fully patient-independent evaluation.

| Partition | Groups | Records | Record IDs | N | S | V | F | Q |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Train | 30 | 31 | 105, 106, 113, 114, 115, 116, 117, 121, 123, 124, 200, 201, 202, 203, 205, 207, 208, 209, 212, 213, 214, 215, 219, 220, 222, 223, 228, 230, 231, 233, 234 | 64,015 | 1,237 | 5,901 | 789 | 13 |
| Validation | 6 | 6 | 100, 103, 108, 109, 210, 221 | 13,007 | 61 | 647 | 14 | 0 |
| Test | 7 | 7 | 101, 111, 112, 118, 119, 122, 232 | 13,103 | 1,483 | 461 | 0 | 2 |

Q is absent from validation and F is absent from test. Those class-specific metrics are not estimable for those partitions; do not redraw the split to improve results or claim full five-class performance from the unsupported partition.

The authoritative, machine-readable split manifest includes dataset and mapping checksums, exclusions, record/group assignments, per-partition class support, seed, generator version and its canonical SHA-256:

- [Split manifest](../../data/splits/phase3_split_manifest.json): `bbcfa25c7f0e0d903a6de44ccbaa6eb3fa0716253ff1ea730c912f99534d6f96`

The separate training-client manifest is linked to that split hash:

- [Client manifests](../../data/splits/client_manifests.json): `71dbcac37e2a605d5edcd0ce280acec60068a1f1defb4f403bc32a5e1cb8eba3`

## Five training clients

Clients contain training records only. A deterministic greedy assignment balances mapped class counts and record load while keeping groups intact. It is an IID-like allocation, not proof of IID data.

| Client | Records | N | S | V | F | Q | Absent classes |
|---|---|---:|---:|---:|---:|---:|---|
| client_01 | 117, 124, 208, 220, 222, 230 | 11,139 | 337 | 1,040 | 378 | 2 | — |
| client_02 | 113, 116, 123, 200, 213, 228 | 11,678 | 68 | 1,520 | 364 | 0 | Q |
| client_03 | 105, 205, 207, 212, 231, 233 | 13,186 | 118 | 1,155 | 22 | 5 | — |
| client_04 | 114, 115, 201, 202, 203, 223, 234 | 14,743 | 320 | 1,180 | 22 | 4 | — |
| client_05 | 106, 121, 209, 214, 215, 219 | 13,269 | 394 | 1,006 | 3 | 2 | — |

## Segmentation and signal preprocessing

The selected method is a documented adaptation of Kachuee et al. (2018), which uses Lead II and beat extraction for MIT-BIH classification. This project uses expert reference annotation positions and a fixed window rather than that paper's automatic detector and adaptive-window procedure.

- Use the `MLII` channel; it is present in all 44 included records.
- Read sampling frequency from each record header; require 360 Hz and retain native sampling.
- Center each window on its reference annotation, with offsets `-90` through `+162` samples inclusive (`-0.25` to `+0.45` seconds; 253 samples).
- Drop windows extending beyond signal boundaries; count these by class. No padding or wraparound.
- Apply no resampling, filtering or baseline removal.
- Fit one global z-score mean and standard deviation from training-window samples only; apply the frozen values to validation and test.
- Treat `~` as signal-quality metadata, not a beat class. Report its count, but do not automatically remove neighboring beats.
- No augmentation or oversampling is performed.

This evaluates beat classification conditional on expert reference beat locations; it is not end-to-end beat detection. The adaptation and its limitations are specified in the [research protocol](../protocol/RESEARCH_PROTOCOL.md).

## Preprocessing validation

The audit extracted 100,694 in-bounds windows of shape `(253,)`:

| Partition | Windows | N | S | V | F | Q | Boundary drops by class |
|---|---:|---:|---:|---:|---:|---:|---|
| Train | 71,927 | 63,989 | 1,237 | 5,900 | 788 | 13 | N=26, V=1, F=1 |
| Validation | 13,722 | 13,000 | 61 | 647 | 14 | 0 | N=7 |
| Test | 15,045 | 13,099 | 1,483 | 461 | 0 | 2 | N=4 |

The window counts reconcile to the approved annotation counts after the 39 boundary drops. All extracted values and standardized tensors were checked for finite values and expected shape. Records are disjoint across partitions, 201/202 remain together, and no validation/test values were used to fit normalization.

Training-only normalization parameters: mean `-0.2829528302450724`, standard deviation `0.48109470198424287`.

- [Preprocessing audit report](./PHASE3_PREPROCESSING_AUDIT.json): `5e363d0eb41747649d46442412dc2009fe93c5c220bb7e8a5d18003775d10025`
- Processed arrays are generated under `data/processed/phase3/` and are excluded from Git. Recreate them and their hashes with:

```powershell
.\.venv\Scripts\python.exe -m scripts.create_phase3_splits
.\.venv\Scripts\python.exe -m scripts.preprocess_mitdb_phase3
```

## Gate and next stage

**G3: PASS.** Split/client manifests are frozen and hashed; partition membership, subject grouping, label reconciliation, segment shapes and finite values were validated. At G3 completion, no model training had started. Phase 4 baselines have since been executed in full (G4 not passed because of 0.000 S-class recall) and Phase 5 federated learning is in progress; see [the Phase 4 execution status](../PHASE4_EXECUTION_STATUS.md) and [the Phase 5 execution status](../PHASE_5_EXECUTION_STATUS.md). The split and its hashes are unchanged.

Note on the client table above: the N/S/V/F/Q columns are **annotation counts** from the per-record audit. Processed window counts are lower because boundary windows without a full 253-sample window are dropped (training: 26 N, 1 V, 1 F). See [the Phase 5 manifest audit](../PHASE_5_MANIFEST_AUDIT.md).
