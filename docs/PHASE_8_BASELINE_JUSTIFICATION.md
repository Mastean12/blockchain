# Phase 8 — Baseline Justification

**Status:** Approved 16 November 2026 (with the adversary model).
**Authority:** `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` §20 — *"Do not include an algorithm
solely for name recognition if its assumptions are violated."*
**Purpose:** justify the exact baseline set against the frozen client count **K = 5**.

---

## 1. The binding constraint

The client count is **K = 5**, frozen since G3 and not re-drawable. Every robust aggregator carries a
Byzantine tolerance bound, and at K = 5 most of them are tight or inapplicable.

| Bound | Requirement | At K = 5, f = 1 | At K = 5, f = 2 |
|---|---|---|---|
| Krum (Blanchard et al. 2017) | `n ≥ 2f + 3` | 5 ≥ 5 → **valid** | 5 ≥ 7 → **invalid** |
| Multi-Krum | selects `n − f − 2` | selects 2 → valid | selects 1 → **degenerate** |
| Coordinate median (Yin et al. 2018) | `f < n/2` | 1 < 2.5 → **valid** | 2 < 2.5 → **valid but marginal** |
| Trimmed mean (Yin et al. 2018) | `n > 2·trim` | trim=1 → 5 > 2 → **valid** | trims 2 of 5 → valid but leaves 3 |
| FLTrust (Cao et al. 2021) | needs a clean server root dataset | **no root dataset exists** | same |

These are computed in code (`src/aggregation/rules.py`) and enforced at runtime
(`check_admissible`), so an inadmissible configuration fails rather than silently producing a
plausible-looking wrong answer.

---

## 2. Selected baselines

| Rule | Role | Admissible at | Why included |
|---|---|---|---|
| **FedAvg** | Reference | — | The frozen Phase 5 aggregator; the thing every defence is compared against |
| **Coordinate median** | R1 baseline | f ≤ 2 | Named by §20; assumptions hold at K = 5 |
| **Trimmed mean** (trim = 1) | R1 baseline | f ≤ 2 | Named by §20; assumptions hold and it is the natural middle ground |
| **Krum** | R1 baseline | **f = 1 only** | Named by §20; admissible precisely at the primary condition |
| **Multi-Krum** | R1 baseline | **f = 1 only** | Named by §20; valid where Krum is valid |

## 3. Excluded baselines and why

| Rule | Reason for exclusion | Consequence |
|---|---|---|
| **FLTrust** | Requires a clean server-side root dataset. This study has none, and creating one would introduce a new data-provenance artefact requiring its own approval. | Excluded. Recorded in `EXCLUDED_RULES` and refused at runtime. Must be named in results as a deliberate exclusion, not an oversight. |
| **Bulyan** | Not named by §20, and it composes Krum with trimmed mean, requiring `n ≥ 4f + 3`; at K = 5 that fails for any f ≥ 1. | Not implemented. |

## 4. What the f = 2 condition means for the baseline set

At f = 2 with K = 5:

- **Krum and Multi-Krum are inadmissible** and must not be reported for f = 2.
- **Median and trimmed mean remain admissible**, but median's margin is thin (2 < 2.5) and trimmed
  mean leaves 3 of 5 values.

**Recommendation followed:** f = 1 is the primary condition for all five rules; f = 2 is a secondary
condition for median and trimmed mean only. Reporting Krum at f = 2 would be a methodological error.

## 5. Measured behaviour on synthetic data (sanity, not results)

The following was run to confirm the implementations behave as the literature predicts. It is **not**
a Phase 8 result and must not be reported as one.

Setup: 4 honest updates ~ N(0, 0.1²) in 100 dimensions, 1 malicious. Deviation is L2 distance from the
honest 4-client centroid, relative to that centroid's norm.

| Rule | Scaling attack (λ = 500×) | Sign-flip attack |
|---|---:|---:|
| FedAvg | **200.22** | **1.20** |
| Coordinate median | **0.81** | **0.76** |
| Krum | 1.49 | 1.49 |

**Interpretation.** FedAvg is destroyed by a scaling attack, as expected — a single client can move
an unweighted mean arbitrarily. Median degrades gracefully. Krum performs *worse than median here*
because single Krum returns one client's update rather than an average, so with 4 honest clients it
selects among them and cannot approach their centroid; that is a property of the method, not a bug,
and it is why Multi-Krum exists.

**This is a caution for Phase 8:** "robust" does not mean "closest to the honest centroid". Each rule
optimises a different objective, and reporting a single deviation metric would misrepresent them.
Phase 8 must report the actual classification metrics defined in §21, not this diagnostic.

## 6. Required reporting per rule

Per §21, every rule × condition cell must report: clean macro-F1, minority-class recall (V, with the
S = 0.000 caveat), attack success or degradation, detection rate, honest false-positive rate,
per-round validity, contribution/rejection counts, runtime and communication overhead, and seed
variability.

## 7. Approval

| Item | Status |
|---|---|
| Baseline set justified against K = 5 | **Yes** |
| Excluded methods justified | **Yes** (FLTrust, Bulyan) |
| Admissibility enforced in code | **Yes** (`check_admissible`) |
| Research-lead approval | **APPROVED** 16 November 2026 |
