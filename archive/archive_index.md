# Archive Index — Phase 10 Defence Package

**Created:** 18 November 2026
**Purpose:** the reproducibility and evidence package for external review.

## Contents

| File | Description |
|---|---|
| `freeze_manifest.json` | SHA-256 of 18 source modules, 201 configs, 3 frozen manifests |
| `final_results.json` | Per-seed and aggregate results for the 8 selected configurations, with checkpoint hashes |
| `EXCLUDED_FROM_RESULTS.md` | Everything deliberately excluded, and why |
| `archive_index.md` | This file |

## Canonical frozen identifiers

| Artifact | SHA-256 |
|---|---|
| Split manifest | `bbcfa25c7f0e0d903a6de44ccbaa6eb3fa0716253ff1ea730c912f99534d6f96` |
| Client manifest | `71dbcac37e2a605d5edcd0ce280acec60068a1f1defb4f403bc32a5e1cb8eba3` |
| F3 partition | `da8b96fa118e53bf53bee50b4f56bb6c281c65093b3c690058664f7b0cf8bbd4` |

## What is NOT in this archive

Model checkpoint binaries are large and are recorded **by SHA-256 only** in `final_results.json`.
They remain at their original paths under `experiments/logs/`, which is git-ignored. Anyone
requiring the binaries must obtain them from the project workstation.

**F1 and F2 checkpoints do not exist** — see `final_results.json` under `evidence_gaps`.

## Reproducibility entry points

- Dependencies: `requirements-lock.txt` (pinned; verified installable in a clean venv)
- Test suite: `pytest tests` → 198 passed, 16 skipped
- Reproduction commands: `docs/reproducibility/REPRODUCIBILITY.md`
- Full test output: `docs/test_output/pytest_full_phase9.txt`

## Status declared in this package

- G0–G7 passed (G4 and G6 with documented scope limits)
- **G8 NOT PASSED**
- G9 passed
- G10 passed with declared gaps
- External SVDB evaluation not run
