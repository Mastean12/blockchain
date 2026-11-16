# AAMI Mapping and Exclusions

**Status:** Research lead approved the mapping, exclusions, and paced-record policy; G2 passed with the documented EC57 access limitation  
**Dataset:** MIT-BIH Arrhythmia Database v1.0.0  
**Audit date:** 13 November 2026  
**Annotation reader:** WFDB 4.3.1

## 1. Method and integrity

The audit read every reference `.atr` file for the 48 canonical records using WFDB. It found 112,647 annotations and 23 distinct raw annotation symbols. The WFDB annotation description table and the [MIT-BIH database directory](https://physionet.org/physiobank/database/html/mitdbdir/intro.htm) were used to distinguish beat labels from rhythm, artifact, signal-quality and comment annotations. The published mapping in Pham et al. (2023) is a cross-check, not authority for this project’s final policy. The licensed EC57 full text was not accessed; no clause-level EC57 or compliance claim is made.

All 23 observed symbols have an explicit approved mapping or exclusion in [aami5_mapping_v1.yaml](../../configs/data/aami5_mapping_v1.yaml). No unobserved WFDB symbol is silently assigned a class, and the audit stops on any observed symbol without a decision.

## 2. Approved five-class mapping

| Class | Raw symbols | Count in all 48 audited records |
|---|---|---:|
| N | `N`, `L`, `R`, `e`, `j` | 90,631 |
| S | `A`, `a`, `J`, `S` | 2,781 |
| V | `V`, `E` | 7,236 |
| F | `F` | 803 |
| Q | `/`, `f`, `Q` | 8,043 |
| **Mapped total before approved record exclusions** |  | **109,494** |

These counts cover all 48 audited records before the approved whole-record exclusions. The final included-dataset counts are listed in Section 4.

## 3. Raw annotation inventory and approved exclusions

| Symbol | WFDB description | Count | Approved decision |
|---|---|---:|---|
| `!` | Ventricular flutter wave | 472 | Exclude: rhythm/event annotation, not a classified heartbeat |
| `"` | Comment annotation | 437 | Exclude: comment metadata |
| `+` | Rhythm change | 1,291 | Exclude: rhythm metadata |
| `/` | Paced beat | 7,028 | Q (in the audited mapping; records containing these beats are excluded) |
| `A` | Atrial premature contraction | 2,546 | S |
| `E` | Ventricular escape beat | 106 | V |
| `F` | Fusion of ventricular and normal beat | 803 | F |
| `J` | Nodal (junctional) premature beat | 83 | S |
| `L` | Left bundle branch block beat | 8,075 | N |
| `N` | Normal beat | 75,052 | N |
| `Q` | Unclassifiable beat | 33 | Q |
| `R` | Right bundle branch block beat | 7,259 | N |
| `S` | Premature or ectopic supraventricular beat | 2 | S |
| `V` | Premature ventricular contraction | 7,130 | V |
| `[` | Start of ventricular flutter/fibrillation | 6 | Exclude: rhythm-segment boundary |
| `]` | End of ventricular flutter/fibrillation | 6 | Exclude: rhythm-segment boundary |
| `a` | Aberrated atrial premature beat | 150 | S |
| `e` | Atrial escape beat | 16 | N |
| `f` | Fusion of paced and normal beat | 982 | Q (in the audited mapping; records containing these beats are excluded) |
| `j` | Nodal (junctional) escape beat | 229 | N |
| `x` | Non-conducted P-wave (blocked APB) | 193 | Exclude: non-conducted event, not a QRS heartbeat |
| `|` | Isolated QRS-like artifact | 132 | Exclude: artifact annotation, not an expert beat-class label |
| `~` | Signal quality change | 616 | Exclude: signal-quality metadata |

The symbol exclusions total 3,153 annotations across all 48 audited records. The research lead approved excluding `x` because it marks a non-conducted P-wave rather than a QRS heartbeat.

Machine-readable symbol descriptions/counts and decisions are in [MITBIH_RAW_ANNOTATION_INVENTORY.csv](./MITBIH_RAW_ANNOTATION_INVENTORY.csv).

## 4. Class support and paced-record sensitivity

All five classes occur in the full dataset under the approved mapping. Class support is uneven: N has 90,631 annotations; F has 803; and the full-dataset Q total is driven mainly by paced symbols `/` and `f`.

The official directory identifies records 102, 104, 107 and 217 as containing paced beats. The raw annotation audit confirms:

| Record | `/` paced | `f` paced-fusion | Candidate Q total (includes `Q`) |
|---|---:|---:|---:|
| 102 | 2,028 | 56 | 2,084 |
| 104 | 1,380 | 666 | 2,064 |
| 107 | 2,078 | 0 | 2,078 |
| 217 | 1,542 | 260 | 1,802 |
| **Total** | **7,028** | **982** | **8,028** |

There are 33 raw `Q` annotations. The candidate Q total is 8,043 because 8,010 annotations are `/` or `f`. If paced beat symbols are excluded while retaining the records, Q support becomes 33 across 9 records. If all four paced records are excluded, candidate Q support falls to 15 across 5 records. The remaining candidate support under that whole-record exclusion scenario is:

| Class | Count after excluding records 102, 104, 107, 217 | Records with support |
|---|---:|---:|
| N | 90,125 | 44 |
| S | 2,781 | 32 |
| V | 7,009 | 33 |
| F | 803 | 17 |
| Q | 15 | 5 |

This table compares the candidate options. The research lead selected whole-record exclusion for the final protocol, as specified below. Report unsupported class metrics as not estimable; do not fabricate or duplicate Q samples.

See [MITBIH_PER_RECORD_AAMI_COUNTS.csv](./MITBIH_PER_RECORD_AAMI_COUNTS.csv) for all 48 per-record counts and [MITBIH_AUDIT_SUMMARY.json](./MITBIH_AUDIT_SUMMARY.json) for the machine-readable summary.

### Approved Phase 2 policy

On 13 November 2026, the research lead selected the 44-non-pacemaker-record protocol described by [de Chazal et al. (2004)](https://doi.org/10.1109/TBME.2004.827359). Its indexed abstract reports using 44 non-pacemaker MIT-BIH recordings. The MIT-BIH directory and this audit identify the paced records as 102, 104, 107 and 217; exclude those records before any split or training.

The approved symbol mapping remains the five-class mapping in Section 2. The `/` and `f` symbols map to Q in the audited taxonomy, but all their observations occur in the four excluded records. In the 44 included records, Q therefore consists of 15 `Q` annotations across 5 records. Aggregate mapped support after record exclusion is N=90,125, S=2,781, V=7,009, F=803, Q=15 (100,733 total mapped annotations). Exclude `!`, `"`, `+`, `[`, `]`, `x`, `|` and `~` with the reasons in Section 3.

This source supports the 44-record non-pacemaker policy; the exact four record IDs are corroborated by the MIT-BIH directory and per-record annotation audit. The full licensed EC57 text remains unavailable, so the project makes no clause-level EC57 or formal compliance claim. The selected published protocol and the Phase 1-approved source-access limitation are documented.

**G2 status:** `PASS`. The research lead approved the exact mapping, exclusions, record policy and Q support limitation. Phase 3 subsequently passed G3. Phase 4 is authorized; a one-batch CPU smoke test has passed, while full baseline training remains in progress under the Phase 4 protocol.
