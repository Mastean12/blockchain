# ECG Federated Learning Research Project

This repository is a clean boilerplate for the research project defined in `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md`.

The project is intentionally scaffolded only to the Phase 0 specification. No dataset acquisition, preprocessing, model training, privacy experiments, blockchain integration, or robust-aggregation implementation is authorized yet.

## Project objective

A Blockchain-Enabled Privacy-Preserving Federated Learning Framework for ECG Arrhythmia Classification under an AAMI-derived five-class taxonomy.

## Governance

- The authoritative specification is `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md`.
- All project changes must align with the stop/go gates and execution order in that document.
- Training, data wrangling, and evaluation are not authorized until the research protocol, mapping audit, split manifest, and gate approvals are complete.

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

## Local setup (placeholder)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
```

## Google Colab workflow

This project is designed to be compatible with a Google Colab runtime that has a dedicated GPU. Use the repository as a mounted working directory and install dependencies in the notebook before any data or model work begins.

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

The project contains reproducible dataset-audit tooling, but no signal preprocessing or model-training code. Training is blocked until the Phase 3 split and preprocessing gate passes.

## Current status

Status: Phases 0–2 are complete. The research lead approved the audited AAMI mapping and 44 non-pacemaker-record policy at G2. Phase 3 split and preprocessing validation may begin; no training has started.

Phase 1 documents:
- [Literature review](docs/literature/LITERATURE_REVIEW.md)
- [Reference register](docs/literature/REFERENCES.md)
- [Approved research protocol](docs/protocol/RESEARCH_PROTOCOL.md)
- [MIT-BIH provenance](docs/data_and_labels/DATA_PROVENANCE.md)
- [AAMI mapping and approval report](docs/data_and_labels/AAMI_MAPPING_AND_EXCLUSIONS.md)
- [Approved mapping configuration](configs/data/aami5_mapping_v1.yaml)
