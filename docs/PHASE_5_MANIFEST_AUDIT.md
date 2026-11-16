# Phase 5 — Client Manifest Audit Report

**Date:** 15 November 2026  
**Trigger:** Phase 5 Stage A discovered that stored `class_counts` in the frozen Phase 3 client
manifest do not reconcile with the frozen label arrays.  
**Outcome:** Root cause identified and fully reconciled. The Phase 3 artefacts are **correct for
their stated purpose and remain unmodified.** No correction to any approved artefact is required.

---

## 1. Summary for the research lead

| Question | Answer |
|---|---|
| Is the manifest wrong? | **No.** The stored counts are correct annotation counts. |
| Why do they differ from the arrays? | The arrays exclude boundary windows that lack a full 253-sample window; annotations do not. |
| Does the discrepancy affect Phase 4? | **No.** Phase 4 trains from the arrays and never reads `class_counts`. |
| Does it affect Phase 5? | **No**, provided Phase 5 derives support from the arrays, which it does. |
| Must any approved artefact be changed? | **No.** |
| Is a documentation clarification advisable? | Yes — see section 6. This is a wording issue, not a data error. |

## 2. Observed discrepancy

The frozen client manifest (`data/splits/client_manifests.json`, SHA-256
`71dbcac37e2a605d5edcd0ce280acec60068a1f1defb4f403bc32a5e1cb8eba3`) stores per-client
`class_counts`. Summed across clients and compared with the frozen training label array:

| Class | Summed stored counts | Array counts | Difference |
|---|---:|---:|---:|
| N | 64,015 | 63,989 | **−26** |
| S | 1,237 | 1,237 | 0 |
| V | 5,901 | 5,900 | **−1** |
| F | 789 | 788 | **−1** |
| Q | 13 | 13 | 0 |

Every client is affected in N, and two clients also in V or F:

| Client | Stored (N, S, V, F, Q) | Array-derived | Difference |
|---|---|---|---|
| client_01 | 11139, 337, 1040, 378, 2 | 11131, 337, 1040, 377, 2 | −8 N, −1 F |
| client_02 | 11678, 68, 1520, 364, 0 | 11673, 68, 1520, 364, 0 | −5 N |
| client_03 | 13186, 118, 1155, 22, 5 | 13181, 118, 1154, 22, 5 | −5 N, −1 V |
| client_04 | 14743, 320, 1180, 22, 4 | 14740, 320, 1180, 22, 4 | −3 N |
| client_05 | 13269, 394, 1006, 3, 2 | 13264, 394, 1006, 3, 2 | −5 N |

## 3. Root cause

`scripts/create_phase3_splits.py` builds `class_counts` from
`docs/data_and_labels/MITBIH_PER_RECORD_AAMI_COUNTS.csv` (the `mapped_<class>_count` columns),
which counts **annotation events**:

```
record_class_counts[record_id] = {
    class_name: int(row[f"mapped_{class_name}_count"]) for class_name in CLASS_ORDER
}
...
group_class_counts[group_id] = {name: sum(record_class_counts[r][name] for r in record_ids) ...}
```

The processed arrays store **classification windows**. A beat whose window would extend past the
start or end of its record cannot be represented, so `scripts/preprocess_mitdb_phase3.py`
drops it under the approved policy *"boundary_windows: drop and count by approved class; never
pad or wrap"* and records the loss in `boundary_excluded_by_class`.

The audit report already quantifies this exactly:

| Split | F | N | Q | S | V |
|---|---:|---:|---:|---:|---:|
| train | 1 | 26 | 0 | 0 | 1 |

**Train boundary exclusions (26 N, 1 V, 1 F = 28) exactly equal the observed discrepancy.**

## 4. Verification performed

1. Recomputed each client's counts directly from `MITBIH_PER_RECORD_AAMI_COUNTS.csv` by summing
   the client's record IDs: matched the stored manifest **exactly**, for all five clients.
2. Recomputed each client's counts from `train_record_ids.npy` and `train_y.npy`: matched the
   array-derived counts exactly.
3. Confirmed the difference equals `boundary_excluded_by_class["train"]` per class.
4. Confirmed the record-to-client assignment is complete and disjoint (31 records, union equals
   the frozen training records, no duplicates).

So the discrepancy is **semantic, not a data fault**: annotation counts versus window counts.

## 5. Impact assessment

| Consumer | Uses | Impact |
|---|---|---|
| Phase 4 centralized/local-only training | arrays | None |
| Phase 4 metrics/reports | arrays, manifests' record IDs | None |
| Phase 3 split/hash integrity | record ID lists | None — record IDs are unaffected |
| Phase 5 partitions (new) | arrays; derives counts itself | None — Phase 5 records array-derived counts |
| `SPLIT_POLICY.md` published table | displays stored counts | Counts shown are annotation counts, not window counts |

No approved artefact was modified. No hash changes.

## 6. Recommended documentation clarification (for research-lead decision, not applied)

Two labels would remove future ambiguity. Both are documentation-only and would not alter any
manifest or hash:

1. In `data/splits/client_manifests.json` semantics: state that `class_counts` are **annotation
   counts**, not window counts.
2. In `docs/data_and_labels/SPLIT_POLICY.md`: retitle the client table's N/S/V/F/Q columns as
   "annotation counts" and add a line that window counts are lower by
   `boundary_excluded_by_class`.

I have **not** edited either file, because both are approved Phase 3 artefacts.

## 7. Consequence for Phase 5

Phase 5 partition manifests are generated from the frozen arrays
(`src/federated/partitions.py::record_class_counts`), so every Phase 5 client distribution
quoted in the plan and results uses **window counts**. The test
`test_partition_class_counts_come_from_arrays_not_stored_manifest` asserts both that Phase 5
reconciles with the arrays and that the Phase 3 stored counts still differ, so a future silent
change to either side will fail the suite rather than pass unnoticed.
