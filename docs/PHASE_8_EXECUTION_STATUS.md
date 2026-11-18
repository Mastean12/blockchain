# Phase 8 — Execution Status

**Last updated:** 17 November 2026
**Stage:** Confirmatory execution **complete**; failure analysis and protocol amendment prepared;
**G8 remains NOT PASSED** — see §2 and §5
**Phase 9 (Integration):** not started
**Committed / pushed:** No

> **Update, 17 November 2026.** The failed confirmatory gate has been analysed and a separate
> amendment proposed. **G8 is unchanged and remains NOT PASSED.** The original thresholds, cells,
> development results and confirmatory outputs are preserved verbatim. See
> [`PHASE_8_FAILURE_ANALYSIS.md`](PHASE_8_FAILURE_ANALYSIS.md) and
> [`PHASE_8_PROTOCOL_AMENDMENT_PROPOSAL.md`](PHASE_8_PROTOCOL_AMENDMENT_PROPOSAL.md).

---

## 0. Where Phase 8 stands

| Item | State |
|---|---|
| Adversary model | **Approved** — `PHASE_8_ADVERSARY_MODEL.md` |
| Baseline justification | **Complete** — `PHASE_8_BASELINE_JUSTIFICATION.md` |
| Implementation | **Complete** — rules, attacks, defence, runner, 33 tests |
| Development validation | **Complete** — 58 runs (seeds 47–48), thresholds validated |
| Platform/`THRESHOLDS_FROZEN` | **True**, gate verified in both directions |
| **Confirmatory execution** | **Complete** — 145 runs (seeds 49–53), 0 execution failures |
| **Evaluable cells** | **14 of 29** — 15 cells diverged in all 5 seeds |
| Confirmatory report | **Complete** — `PHASE_8_CONFIRMATORY_REPORT.md` |
| Test suite | **183 passed, 16 skipped** |
| Frozen artefacts | **Unchanged** — split, client, F3, thresholds, Phase 1–7 results |

## 0.1 Pre-execution verification

All 7 required checks passed. Two required correction before execution:

| Check | Outcome |
|---|---|
| 1 `THRESHOLDS_FROZEN = True` | PASS |
| 2 Fresh seeds only, not development-labelled | PASS |
| 3 Development-seed gate active | PASS (verified behaviourally) |
| 4 29 fresh configs match frozen matrix | **PASS after deleting 8 contradictory configs** (see below) |
| 5 `LIMITATIONS.md` 36/37 updated | PASS |
| 6 Krum correction + divergence guard present | PASS |
| 7 No frozen artefact modified | PASS |

**Check 4 initially failed.** Eight fresh configs existed with `condition=clean` but
`byzantine_clients=1 or 2` — semantically impossible, since "clean" means f = 0. They were artefacts
of an earlier generator and were removed before any confirmatory run. No approved cell was removed.

## 0.2 Confirmatory outcome

| Metric | Value |
|---|---|
| Runs executed | 145 (29 cells × 5 seeds) |
| Execution failures | 0 |
| Runs that diverged | **75 (51.7 %)** — corrected 18 Nov 2026 |
| Cells fully evaluable | **14 of 29** |
| Cells unmeasurable | **15 of 29** (all 5 seeds diverged) |

**Key result, valid cells only:**

- **Coordinate median is the only rule that resists both attacks** without destroying clean utility
  (scaling drop −0.046 and −0.036; sign-flip drop 0.014 and 0.028).
- **Trimmed mean** resists scaling at f=1 (drop 0.040) but is defeated by sign-flip (0.053, 0.072).
- **FedAvg, Krum and Multi-Krum diverged under every attack** and cannot be compared.
- **Median and trimmed mean reject no honest clients** under the benign-outlier control (FPR 0.0000).
- **Detection: scaling 1.00, sign-flip 0.00–0.12.** The norm policy is blind to sign-flip. No general
  poisoning-detection claim is supportable.

## 0.3 The divergence artefact that must never be tabulated

In every diverged cell, divergence occurred at round 1, so the untrained round-0 model was selected.
Round-0 validation macro-F1 is **bit-identical across rules** (0.007607 on seed 49), because an
untrained model does not depend on aggregation. Three rules reporting the same metric in those cells
is evidence that **no aggregation occurred**, not that the rules behave equivalently.

This is preserved in every per-seed summary via `diverged_at_round` and `selected_round = 0`.

## 1. G8 position

| G8 requirement | Status |
|---|---|
| Attack model, baselines, thresholds frozen | **PASS** |
| Independent evaluation complete | **FAIL** — 51.7 % of cells unmeasurable |

**G8 is not passed.** The blocker is not missing execution but an unmeasurable design: at K = 5 the
attacks destroy several rules outright, so no comparison exists.

**R2 is not claimed.** No proposed aggregator is defined in this study; the matrix evaluates
established baselines only.

## 2. Required decisions before Phase 8 can be re-evaluated

| # | Decision | Recommendation |
|---|---|---|
| P8-1 | How to report unmeasurable cells | Mark them `unmeasurable`, exclude from rule comparison, report divergence as the finding |
| P8-2 | Whether to add a divergence-robust condition | Add bounded-norm clipping before aggregation, or reduce λ, so attacks degrade rather than annihilate |
| P8-3 | Whether the detection claim is acceptable as stated | State narrowly: norm threshold detects norm-inflating attacks, not sign-flip |
| P8-4 | Whether to add a direction-aware detection statistic | Requires a new approved condition; not implemented |

**None of these changes a frozen threshold.** They change reporting of unmeasurable cells and what
conditions are run next.

## 3. Documents produced

| Document | Content |
|---|---|
| `PHASE_8_CONFIRMATORY_REPORT.md` | Full per-seed and aggregated analysis, divergence investigation, G8 assessment |
| `experiments/logs/phase8/confirmatory_analysis.json` | Machine-readable consolidated results |
| `experiments/logs/phase8/confirmatory/*/seed_*/` | 145 per-seed summaries |

## 4. Integrity statement

- Development seeds 47–48 were **never** used in confirmatory results; the gate was verified active.
- No threshold, attack parameter, rule, evaluation criterion or selection procedure was changed after
  seeing results.
- All divergent runs are preserved and reported; none was deleted or averaged away.
- No poisoning-detection or Byzantine-robustness claim is made beyond the tested five-client
  configuration.
- Frozen split (`bbcfa25c…`), client manifest (`71dbcac3…`) and F3 partition (`da8b96fa…`) are
  unchanged.

Awaiting research-lead decision on P8-1 … P8-4 before any further Phase 8 work.

---

## 5. Failure analysis and protocol amendment (17 November 2026)

### 5.1 G8 status: unchanged

**G8 remains NOT PASSED.** Nothing in the failure analysis or the amendment revises that decision,
reclassifies an original cell, or changes a frozen threshold.

### 5.2 Root cause established from existing logs

The 75 divergent confirmatory runs resolve into three mechanisms, not one:

| Mechanism | Runs | Cause supported by the evidence |
|---|---:|---|
| **A** rejection collapse | 25 | Rejecting a client at K = 5 leaves 3–4; trimmed mean then keeps a single value |
| **B** gradual drift | 50 | Attack prevents post-round-1 recovery; loss climbs until non-finite |
| **C** scale-dependent threshold | both | Threshold = 3 × median, and the median moves ~4× during training |

**Decisive measurement:** round-1 median update norms are **identical across clean and all attack
conditions** (13.27, 12.95, 12.73 for seeds 49–51). Clean training recovers from ~13 to ~3.4 and
never diverges; attacked runs do not recover. **Attack magnitude (λ = 5) is therefore not the primary
cause**, contrary to the intuitive reading.

### 5.3 Proposed interventions — none implemented

| ID | Proposal | Status |
|---|---|---|
| 3A | Bounded clipping (stability) | Proposed only |
| 3B | Reduced λ sensitivity analysis | Proposed only |
| 3C | Direction-aware detection | Proposed only |

Each is a separate experiment and must not be combined.

### 5.4 Amendment status

`PHASE_8_PROTOCOL_AMENDMENT_PROPOSAL.md` defines a separate protocol with its own gate
(**G8-amended**), new seeds (development 54–55, confirmatory 56–60, verified unused), and
additive criteria. It does **not** replace the original protocol and does **not** pass G8.

### 5.5 Decisions awaited

| # | Decision |
|---|---|
| A8-1 | Accept the amendment as a separate protocol |
| A8-2 | Choose at most one intervention (3B recommended as least invasive) |
| A8-3 | Approve seed allocation 54–55 / 56–60 |
| A8-4 | Accept measurable/unmeasurable classification rules |
| A8-5 | Accept the additive honest clip/reject cap of 0.10 |

**No amended experiment may run until A8-1 … A8-5 are resolved.**

### 5.6 Integrity statement

- No intervention implemented; no configuration changed; no run executed.
- Original development results, confirmatory outputs, frozen thresholds and partitions untouched.
- Development and confirmatory data are not pooled anywhere.
- Round-zero metrics are classified as invalid for aggregation comparison throughout.

---

## 6. Amended proposal 3D — server step-size damping (18 November 2026)

Following a request to make G8 pass, a further amendment was proposed and executed. It does **not**
make G8 pass.

**Evidence basis.** Every run that survived had norm(round 4)/norm(round 1) in [0.26, 0.40], while
diverging runs averaged 1.73. This identifies a positive-feedback loop: large updates worsen the
optimum, producing larger updates, until BatchNorm or the loss overflows.

**Intervention.** A server step size applied after aggregation (pply_server_step), tested at 0.25
and 0.5 with everything else unchanged including lambda = 5.0.

**Result (development seeds 54-55, 116 runs, 0 failures):**

| Step | Divergence | Cells measurable |
|---|---:|---:|
| baseline 1.0 | 51.7 % | 14 / 29 (48 %) |
| 0.5 | 50.0 % | 14 / 29 (48 %) |
| 0.25 | **36.2 %** | **18 / 29 (62 %)** |
| criterion | — | >= 27 / 29 (93 %) |

**Criterion NOT met.** Step 0.25 is a genuine improvement but well short of the target. Krum was
completely unaffected at every step size, because damping reduces an update's magnitude but not its
direction, and Krum's failure is a selection failure rather than an amplification one.

**Decision.** The amended 3D confirmatory phase (seeds 56-60) was **not run**: the development result
already falls far short of the pre-registered criterion, and spending ~10 h would not change the
conclusion.

**G8 remains NOT PASSED.** See PHASE_8_AMENDED_3D_PROPOSAL.md.
