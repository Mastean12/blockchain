# ECG Federated Learning Research Project

This project follows the research execution plan in `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md`.

Phases 0–3 are complete. MIT-BIH data were acquired, audited, split and preprocessed under approved policies. Model training has not started; later experiments remain subject to their own stop/go gates.

## Project objective

A Blockchain-Enabled Privacy-Preserving Federated Learning Framework for ECG Arrhythmia Classification under an AAMI-derived five-class taxonomy.

## Governance

- The authoritative specification is `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md`.
- All project changes must align with the stop/go gates and execution order in that document.
- The approved Phase 2 mapping and Phase 3 data manifests are frozen. Model training and evaluation remain governed by the Phase 4 gate and subsequent experiment approvals.

## Repository layout

```text
project-root/
├── MASTER_RESEARCH_EXECUTION_SPECIFICATION.md
├── README.md
├── pyproject.toml
├── requirements-lock.txt
├── .gitignore
├── configs/
├── data/
├── src/
├── tests/
├── experiments/
├── results/
├── docs/
├── scripts/
└── .venv/                  # Local virtual environment, not tracked
```

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
```

## Google Colab workflow

This project is designed to be compatible with a Google Colab runtime that has a dedicated GPU. Use the repository as a mounted working directory and install the pinned dependencies before model training.

```python
# Example Colab setup
!python --version
!nvidia-smi
!pip install -r requirements-lock.txt
```

For a drive-mounted repo:

```python
from google.colab import drive
drive.mount('/content/drive')
# then work from /content/drive/MyDrive/.../blockchain
```

## Validation

Run focused validation with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\python.exe -m scripts.create_phase3_splits
.\.venv\Scripts\python.exe -m scripts.preprocess_mitdb_phase3
```

These commands validate the mapping, regenerate the deterministic split, and rebuild the processed arrays. They do not train a model.

## Current status

Status: Phases 0–3 are complete; G3 passed. The research lead approved the AAMI mapping and 44 non-pacemaker-record policy at G2. Split and preprocessing manifests are frozen; no model training has started.

Important Phase 3 limitation: Q is absent from validation and F is absent from test. Those class-specific metrics are not estimable for the affected partitions; the split was not redrawn to improve metrics.

Project documents:
- [Literature review](docs/literature/LITERATURE_REVIEW.md)
- [Reference register](docs/literature/REFERENCES.md)
- [Approved research protocol](docs/protocol/RESEARCH_PROTOCOL.md)
- [MIT-BIH provenance](docs/data_and_labels/DATA_PROVENANCE.md)
- [AAMI mapping and approval report](docs/data_and_labels/AAMI_MAPPING_AND_EXCLUSIONS.md)
- [Approved mapping configuration](configs/data/aami5_mapping_v1.yaml)
- [Phase 3 split policy and preprocessing audit](docs/data_and_labels/SPLIT_POLICY.md)
- [Frozen split manifest](data/splits/phase3_split_manifest.json)
- [Training-client manifest](data/splits/client_manifests.json)
- [Preprocessing audit report](docs/data_and_labels/PHASE3_PREPROCESSING_AUDIT.json)
