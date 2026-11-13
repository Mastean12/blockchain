# Data Provenance

**Status:** MIT-BIH v1.0.0 acquired and audited; mapping and 44-record policy approved at G2  
**Acquisition date:** 13 November 2026  
**Raw-data policy:** Immutable source archive and extraction; Phase 3 processed windows are generated separately; no model training performed

## Dataset identity and source

- **Dataset:** MIT-BIH Arrhythmia Database, version 1.0.0
- **Official landing page:** https://physionet.org/content/mitdb/1.0.0/
- **Official release files:** https://physionet.org/files/mitdb/1.0.0/
- **Downloaded archive:** https://physionet.org/content/mitdb/get-zip/1.0.0/
- **Published:** 24 February 2005
- **Citation:** Moody, G., & Mark, R. (2005). *MIT-BIH Arrhythmia Database (version 1.0.0)*. PhysioNet. https://doi.org/10.13026/C2F305
- **License:** [Open Data Commons Attribution License v1.0](https://physionet.org/content/mitdb/view-license/1.0.0/)

The license requires attribution and preservation/provision of the license notice when publicly conveying the database or a derivative database. Publicly used produced works also require an appropriate database attribution notice. Preserve the dataset citation and license URI in any public research artifacts derived from this data. The dataset license does not itself establish rights over every individual item of content.

## Download and integrity

- Downloaded ZIP: `data/raw/downloads/mitdb-1.0.0.zip`
- Archive size: 77,030,320 bytes
- Archive SHA-256: `47b26926927c11bd9174154d367c811afc1b186f650f8a205931ca8c520f0a87`
- ZIP integrity check: passed (`ZipFile.testzip()` returned no corrupt member)
- Extracted directory: `data/raw/mit-bih-arrhythmia-database-1.0.0/`
- Extracted files: 705
- SHA-256 coverage: archive plus all 705 extracted files (706 entries)
- Checksum manifest: [MITBIH_v1.0.0_SHA256SUMS.csv](./MITBIH_v1.0.0_SHA256SUMS.csv)
- Raw dataset files are excluded from Git by `.gitignore`; the checksum manifest and audit reports are retained as project evidence.

The source listing did not provide a checksum used for this download. The project computed local SHA-256 values for the archive and each extracted file. Regenerate the checksums and audit reports with:

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_mitdb_annotations
```

Audit environment: Windows, Python 3.12.10, WFDB 4.3.1, NumPy 2.5.4, pandas 3.1.1, SciPy 1.18.1, and PyYAML 6.0.3. No signal preprocessing was performed during the raw-data audit; Phase 3 preprocessing is documented separately.

## Dataset structure and verified records

The extraction contains 48 canonical record headers and the corresponding 48 signal (`.dat`) and 48 reference annotation (`.atr`) files. The audit used WFDB 4.3.1 to read every record and reference annotation.

Observed metadata and integrity checks:

- 48 records; all have two signal channels sampled at 360 Hz.
- Every record has 650,000 samples per channel.
- All decoded signal values are finite.
- All annotation sample positions are within their corresponding signal bounds.
- Records 201 and 202 are documented as originating from the same subject and must remain grouped in any later split.
- Four records contain paced-beat annotations: 102, 104, 107 and 217.
- There are 112,647 total annotations across the 48 `.atr` files.
- The approved protocol excludes records 102, 104, 107 and 217, following the 44 non-pacemaker-record protocol described by de Chazal et al. (2004). The remaining 44 records are the eligible dataset for Phase 3 splitting.
- After these record exclusions, approved mapped support is N=90,125, S=2,781, V=7,009, F=803 and Q=15.

The database was collected in 1975–1979 and deliberately includes records selected for uncommon arrhythmias. Its class proportions must not be interpreted as population prevalence. Do not claim patient-independent evaluation beyond documented subject grouping.

## Audit artifacts

- [Raw annotation-symbol inventory](./MITBIH_RAW_ANNOTATION_INVENTORY.csv)
- [Per-record AAMI class counts](./MITBIH_PER_RECORD_AAMI_COUNTS.csv)
- [Machine-readable audit summary](./MITBIH_AUDIT_SUMMARY.json)
- Approved mapping and record exclusions: [aami5_mapping_v1.yaml](../../configs/data/aami5_mapping_v1.yaml)
- Reproducible audit implementation: [audit_mitdb_annotations.py](../../scripts/audit_mitdb_annotations.py)

Phase 3 generated the split manifests and processed windows described in [SPLIT_POLICY.md](./SPLIT_POLICY.md). No model fitting or training has been performed.
