# Phase 6 — Execution Status

**Last updated:** 16 November 2026
**Stage:** **COMPLETE. G6 PASSED (limited scope — see §0.5).** All Phase 6 experimental conditions
executed and measured; the threat model is formally approved; the DP arm is closed as a documented
negative result.
**G6 (Privacy gate):** **PASSED with documented scope limits** — approval recorded 16 November 2026
(decisions G6-a, G6-b, G6-c). See §0.3 and §0.5.
**G4:** **PASSED 16 November 2026** with the S-class defect documented as an accepted limitation (`PHASE_4_G4_RESOLUTION.md`). **G5:** **PASSED 16 November 2026.**
**Phase 7 (Blockchain):** not started — the next authorised phase.
**Phase 8 (Robustness):** not started.

> **Final headline (16 Nov 2026).** **HE is functionally lossless** — P2 macro-F1 0.3681 ± 0.0482 vs
> plaintext 0.3752 ± 0.0448, at a measured **20.5× communication cost** (≈2.98 MB vs 145 KB per
> client) and ≈4 % round-time overhead. **DP destroys** this classifier at every tested whole-model
> client-level configuration: P3-a macro-F1 0.1847 (ε = 57.30), P3-b 0.1648 (ε = 22.02). P3's ε is
> **identical** to the corresponding DP-only values, confirming HE adds confidentiality but no
> differential privacy. Full analysis:
> [`PHASE_6_RESULTS_AND_ANALYSIS.md`](PHASE_6_RESULTS_AND_ANALYSIS.md).

> **D-2 diagnostic headline (retained).** σ=0.01: macro-F1 0.2924 at ε=44,111.78. σ=0.05: macro-F1
> 0.2327 with V recall 0.000 at ε=1,871.78. No defensible operating point in the explored region.
> [`PHASE_6_DP_FRONTIER_DIAGNOSTIC.md`](PHASE_6_DP_FRONTIER_DIAGNOSTIC.md).

> **Stage B headline (retained).** `C = 3.44` adopted (global p99) after Rule 4.1's `C = 1.58` was
> shown to clip 88 % of updates in the rounds validation selects.
> `PHASE_6_CALIBRATION_REPORT.md` §4–6.

---

## 0. Where Phase 6 stands

| Item | State |
|---|---|
| Stage A design (4 documents) | Written; threat model **not approved** |
| Stage B calibration | Complete — `C = 3.44`, ε table computed |
| Stage C implementation (DP, HE, HE+DP) | **Complete**, tests passing |
| D-2 DP frontier diagnostic | Complete — σ ∈ {0.01, 0.05}, seed 42, 8 rounds |
| **P2 HE-only** | **Complete — 5/5 seeds** |
| **P3-a HE+DP σ=1.0** | **Complete — 5/5 seeds** |
| **P3-b HE+DP σ=2.0** | **Complete — 5/5 seeds** |
| P1-ctl clip-only | Complete (1 seed, full 50 rounds) |
| Approved σ grid {0.5, 1.0, 2.0, 4.0} | **NOT RUN** — see §0.2 (σ=1.0, 2.0 effectively covered by P3) |
| `src/privacy/` | Implemented: clipping, dp_mechanism, he_ckks, dp_federated, calibration |
| DP/HE libraries | `opacus==1.6.0`, `tenseal==0.3.18` in `.venv` only |
| Test suite | **93 passed, 1 skipped** |
| Tracked-file diffs | **0** |
| Committed / pushed | **No** |

## 0.1 Measured results — all executed conditions

| Condition | n | Test acc | Test macro-F1 | S recall | V recall | HE err | ε |
|---|---:|---|---|---:|---:|---:|---:|
| **P0** plaintext | 5 | 0.8523 ± 0.0380 | **0.3752 ± 0.0448** | 0.000 | 0.970 | — | n/a |
| P1-ctl clip-only | 1 | 0.8358 | 0.3420 | 0.000 | 0.954 | — | n/a (no noise) |
| **P2 HE-only** | 5 | 0.8471 ± 0.0370 | **0.3681 ± 0.0482** | 0.000 | 0.969 | **1.38e-07** | n/a (no DP) |
| **P3-a HE+DP σ=1.0** | 5 | 0.5672 ± 0.2638 | 0.1847 ± 0.0562 | 0.003 | 0.200 | 1.58e-07 | **57.302** |
| **P3-b HE+DP σ=2.0** | 5 | 0.4876 ± 0.2412 | 0.1648 ± 0.0453 | 0.014 | 0.200 | 1.59e-07 | **22.020** |
| P1 diag σ=0.01 | 1 | 0.7714 | 0.2924 | 0.000 | 0.946 | — | 44,111.78 |
| P1 diag σ=0.05 | 1 | 0.8707 | 0.2327 | 0.000 | 0.000 | — | 1,871.78 |

Cost: HE ≈4 % of round time; **20.5× communication expansion** (145 KB → 2.98 MB per client);
DP ≈0.4 s per run.

## 0.2 Why the approved σ grid was not executed

Verified noise-to-signal at aggregate level is `σ·√(d·Σp²)`, `d = 36,357`: **47× (σ=0.5), 94×
(σ=1.0), 188× (σ=2.0), 377× (σ=4.0)**. The model is destroyed by construction. An eight-round probe
at σ=4.0 reached validation loss 6.9 × 10⁹. D-2 was authorised in place of the sweep.

**σ = 1.0 and 2.0 are nevertheless demonstrated** — they are the two σ values used by P3-a and P3-b,
each with 5 seeds, and they collapse as predicted. The approved configs remain on disk unmodified;
their status is **not run**, not failed and not passed.

## 0.3 G6 position

| G6 requirement | Status |
|---|---|
| Threat model validated | **YES** — approved 16 Nov 2026 (G6-a) |
| Accountant validated on toy data | **YES** — 1.0126 vs analytic 1.2112 |
| DP assumptions approved | **YES** — TM-1..TM-7 accepted as written (G6-a) |
| DP predeclared configurations run | **YES, with approved substitution** — D-2 diagnostic plus P3 at σ=1.0/2.0 (G6-b) |
| CKKS validated on toy vectors | **YES** — 2.12e-07 / 5.19e-07 |
| HE-only run | **YES** — 5 seeds |
| HE+DP after component validation | **YES** — 5 seeds each |
| Costs measured | **YES** |
| Key ownership documented | **YES** |

## 0.5 G6 approval record (16 November 2026)

Approved by the research lead. Gate result: **G6 PASSED, limited scope.**

| # | Decision | Resolution |
|---|---|---|
| **G6-a** | Formally approve the threat model (TM-1..TM-7) | **APPROVED as written.** `docs/PHASE_6_PRIVACY_THREAT_MODEL.md` marked approved; `docs/threat_model/PRIVACY_THREAT_MODEL.md` redirects to it |
| **G6-b** | Accept the D-2 substitution for the DP grid | **ACCEPTED.** σ=1.0 and 2.0 demonstrated with 5 seeds each through P3-a/P3-b; σ=0.5 and 4.0 not run and recorded as such |
| **G6-c** | Accept the DP arm as a negative result | **ACCEPTED.** Recorded in `PHASE_6_RESULTS_AND_ANALYSIS.md` §7, scoped to whole-model client-level DP |
| G6-d | Authorise a mechanism change | **Not taken.** No per-layer DP, central DP or DP-SGD was implemented |

### 0.5.1 What the passed gate does and does not certify

**Certifies:** the privacy threat model, accountant and CKKS parameters are validated and approved;
DP, HE and HE+DP were each executed and measured on the frozen split with the frozen recipe; costs
are measured; key ownership is documented; RQ3 is answerable for the implemented mechanisms.

**Does not certify:** that a useful DP operating point exists (none was found); that the results
generalise beyond F3, five clients, or whole-model client-level DP; or that any DP configuration is
deployment-appropriate. The negative DP finding stands and must appear in the thesis as a result,
not be quietly dropped.

**Recorded omissions (approved):** σ = 0.5 and 4.0 of the approved grid were not executed; per-layer
DP, central DP and DP-SGD were not implemented. Both are recorded in
`PHASE_6_RESULTS_AND_ANALYSIS.md` §5 and §7.

## 0.4 Decisions required from the research lead

**All Phase 6 decisions are resolved (16 November 2026).** G6-a, G6-b and G6-c were approved; G6-d
was not taken and no mechanism change was implemented. The record is in §0.5.

Nothing further is required from the research lead to close Phase 6. A future mechanism change
(G6-d) would require a new authorisation and a revised threat model and sensitivity derivation.

---

## 1. Defects found and fixed during P2/P3 execution

Three implementation defects were found only when the HE paths were first exercised end to end.
All were fixed before any reported run, and each now has a regression test.

| # | Defect | Symptom | Fix |
|---|---|---|---|
| **H-1** | HE-only payload is *absolute* parameters but was added to the global model as if it were a delta | Validation loss 5.4 → 61.6 → 271.1 over three rounds; accuracy 0.475 | Branch on `do_clip`: deltas add, absolutes assign (`dp_federated.py`) |
| **H-2** | `transformed` unbound in the DP+HE branch | `UnboundLocalError` on first P3 run | Assign `transformed = payload` in the DP branch |
| **H-3** | HE error reference compared a decrypted *delta* against *absolute* parameters | Spurious 52 % "approximation error" while the CKKS primitive was accurate to 1.4e-07 | Compute the reference in the same space as the payload |

After the fixes: P2 reproduces the P0 validation curve within rounding (0.2488 / 0.2845 / 0.2766 vs
0.2488 / 0.2846 / 0.2759 over rounds 1–3), and all HE approximation errors are ≈1.4e-07.

---

## 2. Stage B results (retained from calibration, 16 Nov 2026)

### 1.1 Gates

| Gate | Result |
|---|---|
| Environment (Python 3.12.10, torch 2.14.1+cu126, GTX 1650, CUDA 12.6) | Verified |
| Opacus accountant vs analytic Gaussian bound (R=1, σ=4) | 1.0126 vs 1.2112 — **PASS** |
| TenSEAL CKKS round-trip relative error | **2.12e-07** — PASS |
| TenSEAL CKKS weighted sum of 5, relative error | **5.19e-07** — PASS (D7 margin ~19×) |
| Calibration reproduces Phase 5 F3 seed-42 curve | **Exact match** — equivalence proven |
| Existing test suite | 53 passed, 1 skipped |

### 1.2 Calibration (5 seeds, 1,250 client-round norms)

| Statistic | Value |
|---|---|
| Norm min / median / mean / SD | 1.127 / 1.549 / 1.608 / 0.370 |
| p95 / p99 / max | 2.223 / **3.347** / 4.351 |
| Rule 4.1 (pooled selected-round median) | **1.58** → clips **37.2 %** overall, **88 %** in rounds 1–5 |
| Recommended | **3.44** (global p99) → clips **0.9 %** |

### 1.3 ε for the approved σ grid (δ=1e-5, R=50, no amplification)

| σ | ε |
|---:|---:|
| 0.5 | 166.04 |
| 1.0 | 57.30 |
| 2.0 | 22.02 |
| **4.0 (proposed addition)** | **9.23** |
| 8.0 | 4.11 |

`C` does **not** affect ε under this accountant; it affects only utility.

**Important:** the ε values in §1.3 are **projections at R = 50 for configurations that were never
run**. They must not be cited as evaluated results. The only ε values actually evaluated are those
in §0.1: 44,111.78 (σ=0.01, R=8) and 1,871.78 (σ=0.05, R=8).

## 3. Stage C implementation and D-2 diagnostic (16 November 2026)

### 2.1 Implementation

All Phase 6 mechanisms implemented and unit-tested; no approved code or configuration modified:

| Module | Purpose |
|---|---|
| `src/privacy/clipping.py` | L2 per-client-vector clipping, sensitivity helpers, frozen weights |
| `src/privacy/dp_mechanism.py` | Gaussian noise, seeded generator, RDP accountant wrapper, toy gate |
| `src/privacy/he_ckks.py` | CKKS context, packing, encrypt, homomorphic weighted sum, decrypt, error |
| `src/privacy/dp_federated.py` | P1/P2/P3/P1-ctl round loop with instability guard |
| `src/privacy/calibration.py` | No-noise norm measurement (Stage B) |
| `scripts/run_phase6_privacy.py` | CLI with config gate separating approved vs diagnostic σ |

### 2.2 Diagnostic execution (D-2 authorised)

Six pre-execution checks were performed and **all passed**, confirming the implementation matches
the approved mathematics: sensitivity derivation, weighted-aggregation sensitivity with the actual
`p_max = 0.371001`, clipping location and noise calibration, accountant and composition (R = 8, no
amplification), noise-to-signal computation, and no test-data use in selection. Details in
`PHASE_6_DP_FRONTIER_DIAGNOSTIC.md` §1.

Results are in §0.1. Interpretation:

1. **No defensible operating point exists in the explored region.** σ = 0.01 preserves utility
   approximately but has ε = 44,111.78; σ = 0.05 has ε = 1,871.78 and destroys class V.
2. **σ = 0.05 accuracy of 0.8707 is misleading** — it is the majority-class rate; macro-F1 falls to
   0.2327 and V recall is exactly 0.000.
3. **Clipping and noise are separable costs**: clipping alone costs 0.0573 macro-F1 at a 1.2 %
   clip rate; noise adds 0.0496 (σ=0.01) and 0.1093 (σ=0.05).
4. **The instability guard did not fire** (max loss 10.18 « 1e6); no condition was halted.
5. **Mechanism-specific finding**: these results describe whole-model client-level DP at `d = 36,357`
   with five clients. They are not a statement about all DP mechanisms.

## 4. Stage B/C decision register (CAL)

**Resolved (approved 16 November 2026, Stage C then executed):**

| # | Decision | Resolution |
|---|---|---|
| CAL-1 | Reject `C = 1.58`; adopt `C = 3.44` (global p99) | **Adopted** — used in all Stage C work |
| CAL-2 | Add σ = 4.0 to the grid | **Adopted**, though this cell was not run (see §0.2) |
| CAL-3 | Keep δ = 1e-5 | **Kept** |
| CAL-4 | Report large ε as a finding, not a defect | **Acknowledged** in the diagnostic |
| CAL-5 | P1-ctl reports ε as "not applicable (no noise)" | **Acknowledged** |

**Outstanding:** see §0.4 (G6-a … G6-d).

### 4.1 Why CAL-1 matters

`C = 1.58` is a defensible *median* but a destructive *clipping constant*: rounds 1–5 have median
norms of 3.34 and 2.89, and three of five seeds select round 2 for the reported checkpoint. At
`C = 1.58`, P1-ctl would measure a clipping cost dominated by near-total projection of the
updates that determine the headline model, confounding its purpose. `C = 3.44` is the global p99,
spares the early rounds, and — because `C` cancels in the accountant — costs **nothing** in ε.

### 4.2 Why CAL-2 matters

At R = 50 with five fixed clients and no subsampling, client-level ε cannot be small. The
projection gave ε ≥ 22 for the approved σ values. The D-2 diagnostic subsequently showed the real
barrier is not ε but the noise-to-signal ratio: at those σ the model is destroyed by construction,
whatever the guarantee. CAL-2 was therefore superseded in practice by D-2, and no σ = 4.0 condition
was run (§0.2).

## 5. Coverage of the Stage A documents

The Stage A deliverable rows, defect list C-1..C-7, and decision register (TM-1..TM-7, D1′..D9,
G-1) are retained below for the audit trail and are unchanged by Stages B and C. Section numbers in
the archived block below (A1–A7) refer to the Stage A document's own numbering, not to this
document's.

<!-- ===== BEGIN ARCHIVED STAGE A RECORD (numbering A1–A7) ===== -->

<!-- Stage A record retained below unchanged -->


### A1. What Stage A produced

Four design documents plus this status file. Nothing else changed. The frozen split, client and
partition manifests, the Phase 4/5 configs and the Phase 5 results are untouched. Nothing committed.

### A2. Verification performed during Stage A (facts, not assumptions)

| Fact | How it was established |
|---|---|
| `opacus` latest 1.6.0 | `pip index versions opacus` |
| `tenseal` 0.3.18 has a `cp312 win_amd64` wheel | `pip download tenseal==0.3.18` succeeded |
| Neither library is installed in `.venv` | `import` fails for both |
| Trainable params 36,357; float buffers 448; int buffers 3 | Inspected `state_dict` |
| 36,357 values ⇒ **9** CKKS ciphertexts at N=8192 (4,096 slots) | Recomputed; earlier "10" was wrong |
| F3 weights: `p_max = 0.371001`; `2C·p_max = 0.742C` | Recomputed from the frozen manifest |
| Weighted aggregator is **1.855×** more sensitive than uniform | `0.742 / 0.4` |
| `n_k` is **data-dependent** in `fedavg.py:150` | Read the implementation |
| P0 (F3) = 0.8523 ± 0.0380 acc, 0.3752 ± 0.0448 macro-F1 | Frozen Phase 5 result |
| P0 cost ≈ 453 s per 51 rounds on this GTX 1650 | Phase 5 logs |

### A3. Defects found in the Stage A draft and corrected

| # | Defect | Severity | Correction |
|---|---|---|---|
| **C-1** | Sensitivity `2C·p_max` asserted, not derived; invalid under a size-changing adjacency because `n_k` is data-dependent | **High — would invalidate ε** | Frozen public weights + equal-cardinality adjacency; derivation in Mathematics §4; arithmetic unchanged |
| **C-2** | Only the aggregate release was accounted, but with no secure aggregation the server sees each client update | **High — would understate ε** | Per-client view B (`S = 2C`) is now the headline |
| **C-3** | BatchNorm leakage noted but not quantified in the claim | Medium | Parameter-level disclosure table (Mathematics §9) |
| **C-4** | "10 ciphertexts" | Low | 9, verified and propagated |
| **C-5** | `P1-ctl` described as `C = ∞, σ = 1.0` — that is noise-only, so it would not isolate clipping | Medium | Corrected: clip at `C`, **no noise** |
| **C-6** | 7 conditions / 1,750 rounds | Low | 8 conditions / 2,040 rounds total, 35 to execute |
| **C-7** | Spec §15.3 requires stable non-private baseline, but G4 never passed | **Governance** | Raised as **G-1**, requires explicit acknowledgement |

### A4. Decision register

### 4.1 Threat-model decisions

| # | Decision | Recommendation | Evidence | Approval |
|---|---|---|---|---|
| TM-1 | Privacy unit = **client slot** | Approve | Clients are fixed groupings of public records; membership is published | **Pending** |
| TM-2 | Adjacency = **replace-one, equal cardinality** | Approve | Equal cardinality required for finite sensitivity (Math §4.2) | **Pending** |
| TM-3 | Descriptive client-distribution analysis, never formal DP | Approve as descriptive only | Avoids faking record-level DP | **Pending** |
| TM-4 | **No secure aggregation** in scope; limitation recorded | Approve | Architecture has no MPC; OUT-2 | **Pending** |
| TM-5 | Single trusted decryptor for P2/P3 | Approve | Required by CKKS design | **Pending** |
| TM-6 | Seeded research PRNG; no production-security claim | Approve for research only | Master spec §15.1 requires the disclosure | **Pending** |
| TM-7 | Out-of-scope list OUT-1..7 | Approve | Prevents scope creep into Phases 7/8 | **Pending** |

### 4.2 Protocol decisions

| # | Decision | Recommendation | Evidence | Approval |
|---|---|---|---|---|
| D1′ | Frozen weights, per-client-vector clipping, **view B (`S=2C`)** headline | Approve | Math §4.3–4.5, §5.2 | **Pending** |
| D2 | `C` by pre-registered Rule 4.1 (median of selected-round norms) | Approve rule; value after calibration | Matrix §4.1 | **Pending** |
| D3 | σ ∈ {0.5, 1.0, 2.0}; δ = 1e-5; R = 50 | Approve | Matrix §4.2 | **Pending** |
| D3′ | Stricter `δ = 1/(10N) ≈ 1.4e-6` | Optional; default 1e-5 | Math §6.3 | **Pending** |
| D4 | Opacus RDP accountant, sequential composition, **no amplification** | Approve, with toy gate | Math §6.1–6.2, §6.6 | **Pending** |
| D4′ | Report ε under view B as headline; view A as secure-agg bound | Approve | Math §5.2 | **Pending** |
| D5 | BN buffers **excluded** from DP/HE; leak disclosed | Approve | Math §9 | **Pending** |
| D6 | CKKS N=8192, `[60,40,40,60]`, scale 2^40 | Approve | Math §7.1 | **Pending** |
| D7 | `rel_err < 1e-5` acceptance | Approve | Math §7.4 | **Pending** |
| D8 | 8 conditions: P0, P1-ctl, P1-a/b/c, P2, P3-a/b | Approve | Matrix §3 | **Pending** |
| D9 | F3 only for Stage B | Approve | Budget control | **Pending** |
| **G-1** | Proceed on a baseline known-defective on class S (G4 not passed) | **Approve explicitly** | Plan §13 | **Pending** |

### A5. Governance note requiring explicit approval (G-1)

Master spec §15.3 and gate G4 require DP work to follow a **stable and trustworthy** non-private
baseline. G4 was never passed: S recall is 0.000 across three mechanisms, and G5 is undecided.

Proceeding to Phase 6 means running privacy experiments on a baseline whose minority-class
behaviour is known to be broken. This is defensible only if recorded and if every Phase 6 result
carries the caveat:

- S recall ~0.000 cannot be attributed to DP or HE;
- no Phase 6 result may claim minority-class improvement;
- an S recall change away from 0.000 is an anomaly to investigate, not a success.

**This is decision G-1 and blocks Stage B until approved.**

> **G-1 resolution, 16 November 2026.** G-1 was acknowledged by the research lead when Stage B was
> authorised, and is now **closed**: **G4 passed on 16 November 2026** with the S-class defect
> documented as an accepted limitation (`PHASE_4_G4_RESOLUTION.md`). The baseline is therefore
> validated in the sense G4 requires — "stable and trustworthy" in that the defect is characterised,
> reproduced on independent hardware, and explained by two rejected ablations — while S itself
> remains unlearned. The caveat that no Phase 6 result may be read as improving or worsening class S
> continues to apply.

### A6. How this directive's Stage A requirements map to deliverables

| Directive requirement | Deliverable section |
|---|---|
| §3.1 privacy unit + adjacency formally defined | Mathematics §2; threat model §5 |
| §3.2 TM-1..TM-7 with confidentiality/integrity distinction | Threat model §4, §6, §10.10 |
| §3.3 derive sensitivity, do not accept `2C·max_weight` | Mathematics §4 (**defect found**) |
| §3.4 calibration design with pre-fixed selection rule | Matrix §4.1; Plan §4.4 |
| §3.5 D1–D9, accountant, composition, transcript accounting | Mathematics §5–6; Matrix §4 |
| §3.6 BatchNorm decision with leak analysis | Mathematics §9; threat model §5.5 |
| §3.7 CKKS parameters, verified ciphertext count | Mathematics §7 |
| §3.8 DP+HE flow and P3-not-stronger-than-P1 | Mathematics §8 |
| §3.9 condition matrix incl. P1-ctl | Matrix §3 |
| Decision register | This document §4 |
| Conflicts with master spec identified | Plan §12.1, §13 (C-1..C-7, G-1) |

### A7. Next authorised task (after approval)

*(Historical: this section described the Stage A → Stage B hand-off and is retained for the audit
trail. Stages B and C have since been executed; the current outstanding actions are §0.4.)*

Stage B, in this order:
1. Verify Python/platform/dependency compatibility; pin and record Opacus and TenSEAL versions.
2. Install into `.venv` only.
3. Run the no-noise calibration pass on F3 (all five seeds, frozen config).
4. Produce `docs/PHASE_6_CALIBRATION_REPORT.md` with the norm distribution and proposed `C`.
5. Recompute sensitivity and the ε outcomes for the σ grid.
6. **Stop for research-lead approval before Stage C.**

**No Phase 7 work. No commits. No full privacy run before approval.**

---

## 6. Status summary

**All Phase 6 experimental executions are complete; G6 is NOT passed.**

| Stage | Status |
|---|---|
| A — design (5 documents) | Complete; **threat model not approved** |
| B — calibration | Complete; `C = 3.44` |
| C — implementation | Complete; **93 tests pass, 1 skipped** |
| D — execution: P0, P1-ctl, D-2 diagnostic, **P2 HE-only**, **P3-a**, **P3-b** | Complete |
| E — analysis | Complete — `PHASE_6_RESULTS_AND_ANALYSIS.md` |
| F — G6 assessment | **Performed; G6 NOT passed** (§0.3) |

The master-spec §16.2 four-way comparison (plaintext / HE-only / DP-only / HE+DP) **is now
answerable for the implemented mechanisms**, with five seeds per federated condition. RQ3 can be
answered within that scope (see `PHASE_6_RESULTS_AND_ANALYSIS.md` §7).

**G6 was passed on 16 November 2026 with documented scope limits** (G6-a, G6-b, G6-c; §0.5). The
gate certifies the threat model, accounting and CKKS parameters, the execution of DP/HE/HE+DP, cost
measurement and key-ownership documentation. It does not certify that a useful DP operating point
exists — none was found — nor that results generalise beyond F3, five clients and whole-model
client-level DP.

Phase 6 is closed. The next authorised phase is Phase 7 (blockchain audit), which has not started.

No implementation, configuration, frozen manifest or Phase 1–5 historical result was modified by
this report. Nothing was committed or pushed.
