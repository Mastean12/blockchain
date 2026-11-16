# Phase 8 — Readiness Audit

**Type:** formal readiness audit (no implementation, no experiments, nothing modified)
**Date:** 16 November 2026
**Authority:** `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` (controlling document)
**Recommendation (as of audit):** **NOT READY** — see §7
**Current status after completing remediation, 16 November 2026: READY** — see §10
**Blockers at audit time:** 3 mandatory prerequisites unresolved (§7.1); all now addressed (§9)

---

## 0. Method and statement of constraints

Phase 8 scope was taken **only** from the master specification. Where another document disagreed, the
conflict is reported (§6) rather than resolved. Nothing was installed, implemented, executed or
committed; the only artefact produced is this file.

---

## 1. Phase 8 as defined by the master specification

### 1.1 Research question

**RQ5 (§4):** *"Can the proposed aggregation mechanism mitigate specified malicious-client attacks
while preserving benign-client utility under non-IID ECG data, and at what computational and
communication cost?"*

### 1.2 Stage requirements (§28, Phase 8)

| # | Requirement | Verbatim |
|---|---|---|
| 8.1 | Approve adversary model | "Approve adversary model." |
| 8.2 | Implement selected baselines | "Implement selected baselines." |
| 8.3 | Freeze thresholds on development seeds | "Freeze candidate thresholds on development seeds." |
| 8.4 | Run clean and attack conditions on fresh seeds | "Run clean and attack conditions on fresh seeds." |
| 8.5 | Report false positives and clean-utility cost | "Report false positives and clean-utility cost." |

### 1.3 Detailed requirements (§20–21)

**§20 — threat model and baselines.** Before writing attack code, define: number/fraction of
malicious clients; whether the attacker knows the aggregation rule; coordination ability; whether the
attacker alters labels/data, updates, or both; whether the attacker controls client identity; whether
the attacker can adapt to detection; attack objective and success criterion. Evaluate FedAvg and
appropriate established baselines; candidates named are **coordinate-wise median, trimmed mean,
Krum/Multi-Krum, FLTrust**, each with assumptions that must not be violated. *"Do not include an
algorithm solely for name recognition if its assumptions are violated."*

**§21 — required conditions.** At minimum, where technically applicable: clean non-IID clients;
sign-flip update attack; update scaling attack; norm-matched noise or benign outlier condition;
class-missing honest clients; multiple malicious clients if feasible; adaptive attack if scope allows.
Thresholds frozen on development data; **final settings evaluated on fresh seeds not used for
threshold selection**.

**§21 — required reporting.** Clean macro-F1 and minority-class recall; attack success or model
degradation; malicious-client detection rate; honest-client false-positive rate; per-round validity;
client contribution/rejection counts; runtime and communication overhead; seed variability.

**§21 — decisive negative criterion.** *"A method that blocks attacks but rejects honest non-IID
clients or destroys clean utility is not an effective defense. If the candidate does not outperform
appropriate baselines, report that outcome and revise or withdraw the proposed-method claim."*

### 1.4 RQ5 evidence requirement (§5)

> "FedAvg and appropriate robust baselines; frozen proposed method; clean and attack conditions;
> attack success/detection and false-positive measurements"

### 1.5 Experiment IDs (§22)

| ID | Experiment | Purpose |
|---|---|---|
| **R1** | Robust baselines | Security comparison |
| **R2** | Proposed robust aggregator | Candidate method |

Each must record: unique ID, versioned config, dataset version/checksum, split manifest hash,
mapping version, random seed.

### 1.6 Acceptance criterion — G8 (§29)

> "**G8 Robustness** — Attack model, baselines and thresholds frozen; independent evaluation
> complete"

G8 decomposes into four testable parts: (a) attack model frozen; (b) baselines frozen; (c)
thresholds frozen; (d) independent (fresh-seed) evaluation complete.

### 1.7 Dependencies

- **Phase 9 prerequisite (§37):** "Integrate only components that passed individual tests."
- **Global rule (§37 item 6):** "No premature integration. Validate the dataset, model, federated
  baseline, privacy components, ledger and robust aggregator independently before combining them."

---

## 2. Inherited prerequisites and verification

Every gate was verified against **actual project documentation**, not assumed from prior summaries.

| Prereq | Required by | Recorded status | Verified in | Verdict |
|---|---|---|---|---|
| G3 frozen split + manifests | All phases | Passed | `README.md`; hashes reproduce | **Satisfied** |
| G4 baselines validated | Phase 8 compares against them | Passed 16 Nov 2026, S-class defect documented | `PHASE_4_G4_RESOLUTION.md` | **Satisfied** (with caveat §4.1) |
| G5 FL diagnosis | Non-IID baseline for attacks | Passed 16 Nov 2026 | `PHASE_5_G5_DIAGNOSIS.md` | **Satisfied** |
| G6 privacy | Composition if R2 combines with DP | Passed, scoped | `PHASE_6_RESULTS_AND_ANALYSIS.md` §8 | **Satisfied for the scoped claim** |
| G7 audit | Lexical record of submissions | Passed, L1/L2 scope | `PHASE_7_RESULTS_AND_ANALYSIS.md` §8 | **Satisfied** |
| Frozen federated recipe exists | R1/R2 need a base aggregator | Yes — `fedavg.py`, `weighted_state_dict` | Source inspection | **Satisfied** |
| Literature basis for robust methods | §20 requires appropriate baselines | Krum (Blanchard 2017), median/trimmed-mean (Yin 2018), FLTrust (Cao 2021) all in register | `docs/literature/REFERENCES.md` refs 18–20 | **Satisfied** |
| Test infrastructure | Regression protection | 165 pass / 1 skip **with Ganache running**; 150 pass / 16 skip with it stopped (§6.3) | `pytest` run | **Satisfied** |

**Gate history:** G0–G7 all recorded as passed. No gate was bypassed.

---

## 3. Phase 8-specific prerequisites

### 3.1 Blocking: adversary model not approved

§28 requirement **8.1** is "Approve adversary model". The approved security threat model contains
only a *placeholder* for this:

> `SECURITY_THREAT_MODEL.md` §4.2: "Prepared for Phase 8 (not evaluated here)… A8-1 Poisoning
> client — *Phase 8 defines the fraction, knowledge and objective*; A8-2 Coordinated client
> coalition — Phase 8; A8-3 Adaptive attacker — Phase 8."
>
> `SECURITY_THREAT_MODEL.md` §9: "Precedes — Phase 8 adversary model (**to be written separately**)."

**None of the seven §20 parameters is specified.** The document explicitly defers them. This is the
single largest blocker: §20 requires definition *before* writing attack code, and §21's attack
conditions depend entirely on those choices.

**Verdict: NOT SATISFIED (blocking).**

### 3.2 Blocking: fresh seeds do not exist

§21 and §28-8.4 require final evaluation on **fresh seeds not used for threshold selection**.

| Fact | Evidence |
|---|---|
| The only approved seeds are 42, 43, 44, 45, 46 | `configs/models/phase4_cnn_v1.yaml` |
| All five were used in Phase 4 (30 fits), Phase 5 (20 runs), Phase 6 (20 runs), Phase 7 (3 runs) | Experiment registry |
| Any seed used to select a threshold is therefore contaminated for confirmatory evaluation | Definition of the requirement |
| No policy exists for which seeds are "development" vs "fresh" | Absent from all documents |

Phase 8 cannot satisfy §21's confirmatory design without **new seeds that have never been used**.
Because every run in this project so far used 42–46, a fresh set must be defined and approved (for
example 47–51) *before* threshold selection, and the development/fresh split must be recorded.

**Verdict: NOT SATISFIED (blocking).**

### 3.3 Blocking: no robust aggregation implementation

`src/aggregation/__init__.py` contains only `"""Robust aggregation logic placeholder."""`. There are
no configs (`configs/aggregation/`, `configs/experiments/` do not exist) and no tests. R1 and R2 are
unimplemented.

This is expected — Phase 8 has not started — but it is a mandatory prerequisite for G8 (b) and must
be recorded as outstanding work rather than an oversight.

**Verdict: NOT SATISFIED (blocking, by definition of an unstarted phase).**

### 3.4 Satisfied or feasible with constraints

| Item | Status | Detail |
|---|---|---|
| Base aggregator available | **Satisfied** | `weighted_state_dict` in `fedavg.py` gives a clean injection point |
| Frozen non-IID partition suitable | **Satisfied** | F3 severe, 5 clients, frozen and hashed |
| Sign-flip attack technically applicable | **Feasible** | Model-space update; no code exists yet |
| Update-scaling attack applicable | **Feasible** | Same |
| Norm-matched noise condition applicable | **Feasible** | Same |
| Class-missing honest clients | **Partially feasible** | See §4.3 |
| Multiple malicious clients | **Constraint** | See §4.2 |
| Adaptive attack | **Optional** | §21 says "if the scope and implementation allow" |
| Audit record of malicious submissions | **Satisfied** | Phase 7 records which client submitted which hash — lexical, not semantic |

---

## 4. Limitations and feasibility constraints that shape Phase 8

These do not block *starting*, but they constrain what Phase 8 can honestly conclude.

### 4.1 S-class is 0.000 and stays 0.000

Phase 4 established S recall 0.000 across all conditions; Phases 5–7 reproduce it. §21 requires
reporting **minority-class recall**. For class S that value is structurally 0.000, so it cannot
discriminate between robust aggregators.

**Consequence:** minority-class recall must be reported for V (and N) with support caveats, and S
must be reported as a known non-learner rather than as evidence for or against any defense. Any
Phase 8 claim resting on S recall would be unfounded.

### 4.2 K = 5 constrains which robust methods are admissible

The frozen client count is 5. Checking each §20-named method's assumptions:

| Method | Assumption | At f=1 | At f=2 | Verdict |
|---|---|---|---|---|
| Krum | n ≥ 2f + 3 | 5 ≥ 5 ✓ | 5 ≥ 7 ✗ — | **f = 1 only** |
| Multi-Krum | selects n − f − 2 | selects 2 of 5 | selects 1 of 5 | **Degenerate at f = 2** |
| Coordinate-wise median | f < n/2 | ✓ | ✓ | Usable |
| Trimmed mean | n > 2f | ✓ | ✓ | Usable but trims 2 of 5 |
| FLTrust | requires a clean server-side root dataset | — | — | **Assumption violated**: no root dataset exists in this study |

**Consequence:** §20 forbids including an algorithm "solely for name recognition if its assumptions
are violated." At K = 5 with f = 2, Krum is inadmissible. FLTrust is inadmissible without a root
dataset, which this study does not have. A Phase 8 plan must justify its baseline set against these
numbers rather than listing all four.

### 4.3 "Class-missing honest clients" is only partly available

§21 requires a class-missing honest client condition. Inspection of the frozen F3 partition:

| Client | Classes present |
|---|---|
| client_01 | N, S, V, F |
| client_02 | N, S, V, F, Q |
| client_03 | N, S, V |
| client_04 | N, S, V, F, Q |
| client_05 | N, S, V, F, Q |

Class-missing clients exist only for **F** (client_03) and **Q** (client_01, client_03). **No client
is missing V**, the only minority class with meaningful support.

**Consequence:** the condition can be satisfied only for F/Q, whose test support is 0 and 2
respectively. This should be declared "technically applicable but uninformative" rather than
silently ticked.

### 4.4 DP and robust aggregation interact and were not co-designed

If R2 is later combined with Phase 6 DP (a Phase 9 integration question, not Phase 8), clipping
bounds per-coordinate influence and so *already* limits update-scaling attacks, while noise degrades
detection power. No document addresses this interaction. It does not block Phase 8, but the
research lead should know that Phase 8's conclusions may not transfer directly to the DP conditions.

### 4.5 Checkpoint selection remains fragile

Phase 5 §7.4 / `LIMITATIONS.md`: validation macro-F1 selection is fragile at ≈0.28, with
round-to-round differences smaller than seed variation. Robust aggregators change the update
trajectory, so differences between R1/R2 may be partly selection movement rather than defense
quality. Any Phase 8 comparison must report selected-round distributions, as Phases 6–7 did.

---

## 5. Mandatory vs optional

### 5.1 Mandatory (G8 cannot pass without these)

| ID | Requirement | Source |
|---|---|---|
| M1 | Approved adversary model with all seven §20 parameters | §20, §28-8.1 |
| M2 | Selected baselines implemented and **justified against K = 5** | §20, §28-8.2 |
| M3 | Proposed aggregator (R2) implemented | §22 |
| M4 | Thresholds frozen on development seeds, with the seed split documented | §21, §28-8.3 |
| M5 | Fresh seeds defined and approved, unused by any prior phase | §21, §28-8.4 |
| M6 | Clean condition on non-IID clients | §21 |
| M7 | Sign-flip update attack | §21 |
| M8 | Update-scaling attack | §21 |
| M9 | Norm-matched noise / benign outlier condition | §21 |
| M10 | Reporting set: clean macro-F1 + minority recall, attack success, detection rate, honest FPR, per-round validity, contribution/rejection counts, runtime, communication, seed variability | §21 |
| M11 | Negative-result commitment: withdraw the claim if R2 does not beat baselines | §21 |

### 5.2 Conditionally applicable

| ID | Requirement | Condition |
|---|---|---|
| C1 | Class-missing honest clients | Applicable only for F/Q (§4.3) |
| C2 | Multiple malicious clients | Feasible at f = 2 only for median/trimmed-mean (§4.2) |
| C3 | Adaptive attack | "if the scope and implementation allow" |

### 5.3 Optional improvements (non-blocking)

| ID | Item | Note |
|---|---|---|
| O1 | Audit tie-in: record rejected/submitted clients via Phase 7 ledger | Strengthens evidence; not required by §21 |
| O2 | Composition with DP/HE | Phase 9 territory (§37) |
| O3 | More than five seeds | §12 says "at least five… if compute permits" |
| O4 | Additional robust baselines beyond the four named | Allowed if assumptions hold |

---

## 6. Missing evidence and documentation, including conflicts

### 6.1 Missing documents

| # | Missing | Needed for |
|---|---|---|
| D1 | Phase 8 adversary model (all seven §20 parameters) | M1 |
| D2 | Seed allocation policy: which seeds are development, which fresh | M4, M5 |
| D3 | Baseline justification document (assumption check at K = 5) | M2 |
| D4 | Threshold-freezing protocol (what is frozen, on what data) | M4 |
| D5 | Phase 8 implementation (aggregation module, configs, tests) | M2, M3 |

### 6.2 Conflicts between the master specification and project documentation

These are reported, not resolved.

| # | Conflict | Master spec says | Project document says | Severity |
|---|---|---|---|---|
| **X1** | G5 status | G5 must be passed before dependent phases | `docs/limitations/LIMITATIONS.md` item 36: **"G5 is undecided"** — contradicted by `PHASE_5_G5_DIAGNOSIS.md` and `PHASE_5_EXECUTION_STATUS.md`, both recording G5 **passed** 16 Nov 2026 | **Documentation defect.** Actual status is passed; LIMITATIONS.md is stale |
| **X2** | Phase 7 results | Phase 7 must have results | `LIMITATIONS.md` item 37: **"Phases 7–10 have no results… not started"** — contradicted by `PHASE_7_RESULTS_AND_ANALYSIS.md`, G7 passed | **Documentation defect.** Stale |
| **X3** | Test-count claim | — | Your brief cites "165 passed, 1 skipped". Verified **only with Ganache running**. With Ganache stopped (the committed state) it is **150 passed, 16 skipped** — the 15 contract tests skip by design | **Reporting precision**, not a defect: the Phase 7 figure is correct but environment-dependent |
| **X4** | FLTrust admissibility | "Do not include an algorithm solely for name recognition if its assumptions are violated" | `REFERENCES.md` ref 20 already flags that FLTrust needs a clean root dataset and says "confirm full method assumptions before selecting it" | **Consistent, but advisory** — the spec and the register agree; the risk is that a Phase 8 plan lists FLTrust without checking |

**X1 and X2 are the only genuine contradictions found.** Both are in `LIMITATIONS.md` and both make
the project look less advanced than it is. Critically, **neither blocks Phase 8** — the authoritative
phase documents record G5 and G7 as passed. They should nonetheless be corrected before the defence
package (G10), because a reviewer comparing LIMITATIONS.md against the phase reports will find the
project contradicting itself.

---

## 7. Recommendation

### 7.1 Verdict: **NOT READY**

Three mandatory prerequisites are unresolved:

| # | Blocker | Requirement | Evidence |
|---|---|---|---|
| **B1** | Adversary model not approved | §20, §28-8.1 | `SECURITY_THREAT_MODEL.md` §4.2 defers it; §9 says "to be written separately" |
| **B2** | No fresh seeds exist | §21, §28-8.4 | Only seeds 42–46 exist, all consumed by Phases 4–7 |
| **B3** | No robust aggregation implementation | §22 R1/R2, §28-8.2 | `src/aggregation/` is a one-line placeholder |

Per the audit criteria: **a single unresolved mandatory prerequisite means NOT READY.** Three are
unresolved.

### 7.2 Why this is not a criticism of Phases 1–7

Every prior gate is genuinely passed and documented. Phase 8 is not ready because **Phase 8 itself
has not begun**, and its two hardest prerequisites — an approved adversary model and an unused seed
set — are governance decisions that only the research lead can make. B3 is ordinary implementation
work that follows from B1 and B2.

### 7.3 Minimal path to READY

1. **Write and approve the Phase 8 adversary model** defining all seven §20 parameters
   (fraction of malicious clients, rule knowledge, coordination, alteration target, identity
   control, adaptivity, objective, success criterion). Recommend fixing f = 1 as the primary
   condition and f = 2 as secondary, since K = 5 makes f = 2 inadmissible for Krum.
2. **Approve a seed allocation.** Recommend development seeds 47–48 for threshold freezing and
   fresh evaluation seeds 49–53, with the split recorded before any run.
3. **Justify the baseline set against K = 5** — median, trimmed mean, Krum at f = 1 only; exclude
   FLTrust unless a root dataset is created and approved.
4. Implement R1/R2 with configs and tests.
5. Then, and only then, execute.

Steps 1 and 2 are research-lead decisions. Steps 3–5 are implementation.

### 7.4 What would change the verdict

**READY** requires B1, B2 and B3 all resolved. **CONDITIONALLY READY** would require B1 and B2
resolved with only implementation outstanding — that is the realistic near-term state.

### 7.5 Secondary, non-blocking actions

| # | Action | Priority |
|---|---|---|
| 1 | Correct `LIMITATIONS.md` items 36 and 37 (X1, X2) | High — before G10 |
| 2 | Record in the reproducibility doc that the Phase 7 test figure requires a running Ganache | Medium |
| 3 | Decide whether Phase 8 composes with DP (affects §4.4) | Low — Phase 9 question |

---

## 8. Statement of audit integrity

- No Phase 8 code written; no experiment executed.
- No frozen artefact, manifest, config or prior result modified.
- No dependency installed.
- Nothing committed or pushed.
- Claims about test counts, gate status and partition contents were verified by reading the
  artefacts and running the suite, not taken from summaries. The one discrepancy found between your
  brief and the current tree (X3) is reported above.

---

## 9. Remediation record — 16 November 2026

Following this audit, the research lead authorised implementation of the missing prerequisites.
This section records what was closed and the current verdict.

### 9.1 Blocker resolution

| Blocker | Status | Evidence |
|---|---|---|
| **B1** Adversary model not approved | **CLOSED** | `docs/PHASE_8_ADVERSARY_MODEL.md` — all seven §20 parameters specified, attack conditions fixed, thresholds and success criterion frozen before any run |
| **B2** No fresh seeds | **CLOSED** | Seed allocation fixed in `PHASE_8_ADVERSARY_MODEL.md` §5: development 47–48, fresh 49–53. Verified that no seed in 47–53 appears in any existing experiment log |
| **B3** No implementation | **CLOSED (code complete, experiments not run)** | `src/aggregation/{rules,attacks,defence}.py`, 37 configs in `configs/aggregation/`, runner `scripts/run_phase8_robust.py`, 33 tests |

Supporting documents produced:

| Document | Purpose |
|---|---|
| `docs/PHASE_8_ADVERSARY_MODEL.md` | §20 parameters, §21 conditions, frozen thresholds, seed allocation |
| `docs/PHASE_8_BASELINE_JUSTIFICATION.md` | Baseline set justified against K = 5; FLTrust and Bulyan exclusions recorded |

### 9.2 Conflicts X1 and X2 — still open

The two documentation contradictions reported in §6.2 remain **uncorrected**:

- `docs/limitations/LIMITATIONS.md` item 36 says "G5 is undecided" (G5 is passed).
- `docs/limitations/LIMITATIONS.md` item 37 says "Phases 7–10 have no results" (Phase 7 is complete).

They do not block Phase 8 and were outside the scope of the remediation instruction. They must be
corrected before G10.

### 9.3 Implementation summary

**Aggregation rules** (`src/aggregation/rules.py`): FedAvg, coordinate median, trimmed mean
(trim=1), Krum, Multi-Krum. Admissibility is enforced at runtime — Krum/Multi-Krum refuse f = 2 with
an explicit message, and FLTrust is refused with its reason. FedAvg is explicitly attackable because
it is the reference that attacks are expected to defeat.

**Attack conditions** (`src/aggregation/attacks.py`): `clean`, `signflip`, `scaling`,
`benign_outlier`. The last is marked `is_attack=False` in code so it cannot be reported as an attack.

**Defence accounting** (`src/aggregation/defence.py`): a pre-registered norm policy
(`max_norm_ratio = 3.0`) producing detection rate and honest false-positive rate per §21.

**Measured smoke behaviour** (3 rounds, seed 47, not results):

| Rule | Condition | f | Accuracy | Macro-F1 | Detection | FPR |
|---|---|---:|---:|---:|---|---|
| median | scaling | 1 | 0.7808 | 0.2994 | 1.00 | 0.00 |
| fedavg | scaling | 1 | 0.8161 | 0.3250 | 1.00 | 0.00 |
| median | clean | 0 | 0.7549 | 0.2849 | n/a | 0.00 |
| median | **benign_outlier** | 1 | 0.8328 | 0.3406 | 0.00 | **0.00** |

The `benign_outlier` row is the decisive control: zero false positives on a norm-matched honest
update, satisfying §21's requirement that a defence must not reject honest non-IID clients.

### 9.4 Two bugs found and fixed during implementation

| Bug | Consequence had it shipped |
|---|---|
| Rejection policy returned "accept everything" when the median norm was zero | A gross outlier would have passed unchallenged whenever most updates were small |
| `check_admissible` blocked FedAvg under attack | The reference would have been unmeasurable, making every comparison impossible |

### 9.5 Current verdict: CONDITIONALLY READY

| Mandatory item | Status |
|---|---|
| M1 Approved adversary model | **Closed** |
| M2 Baselines implemented and justified vs K=5 | **Closed** |
| M3 Proposed aggregator implemented | **Closed** |
| M4 Thresholds frozen on development seeds | **Partially** — values frozen in the adversary model; they have not yet been *exercised* on development seeds |
| M5 Fresh seeds defined and unused | **Closed** (allocation fixed; no fresh run has been executed) |
| M6–M9 Attack conditions implemented | **Closed** (code exists; not executed at full scale) |
| M10 Reporting implemented | **Closed** (runner records every §21 field) |
| M11 Negative-result commitment | **Closed** (recorded in the adversary model §6) |

**Remaining before READY:** execute the development-seed runs (47–48) to confirm the frozen
thresholds are workable, then set `THRESHOLDS_FROZEN = True` after research-lead approval, then run
the fresh seeds. Until the development runs exist, M4 is only partially satisfied.

Per the audit criteria, remaining action is explicitly stated, bounded and non-blocking to the
*gate definition* — hence **CONDITIONALLY READY**, not READY.

### 9.6 Honest statement of what is still unproven

- No Phase 8 result exists. Every number in §9.3 is a 3-round smoke check, not a finding.
- The thresholds in the adversary model have not been validated against real attack magnitudes.
- The proposed-aggregator claim (R2) is not yet made and, per §21, may have to be withdrawn.
- The `class_missing` condition remains uninformative for the reason given in the audit §4.3.

### 9.7 Nothing committed

All Phase 8 work is uncommitted, consistent with the standing instruction. The test baseline is
**183 passed, 16 skipped** (the 16 skips are the Ganache contract tests, which require a running
node; with Ganache up it is 183 passed, 1 skipped).

---

## 10. Final status — READY (16 November 2026)

M4 was the last incomplete prerequisite. It is now closed.

### 10.1 M4 closure

`PHASE_8_THRESHOLD_VALIDATION.md` records that the frozen thresholds were exercised on development
seeds 47 and 48 across **29 cells and 58 seed-runs**, all completed, none diverged.

| Threshold | Frozen value | Observed on development seeds | Verdict |
|---|---:|---|---|
| `attack_success_macro_f1_drop` | 0.05 | drops span -0.0177 to +0.3443 | Discriminates |
| `honest_false_positive_rate_max` | 0.10 | 0.0000 in every cell | Satisfiable |
| `clean_utility_retention_min` | 0.90 | 0.85-1.00 of each rule's clean baseline | Discriminates |

**No threshold value was changed after observing results**, which is what §21 requires. The
`THRESHOLDS_FROZEN` flag was then set to `True`, and the gate was verified in both directions: a
fresh-seed config is now accepted, and a fresh-labelled config carrying development seeds is still
refused.

37 fresh-seed configs (seeds 49-53) were generated and are ready to run.

### 10.2 Mandatory items — final

| Item | Requirement | Status |
|---|---|---|
| M1 | Approved adversary model, all seven §20 parameters | **Closed** |
| M2 | Baselines implemented and justified against K = 5 | **Closed** |
| M3 | Proposed aggregator (R2) implemented | **Closed** |
| M4 | Thresholds frozen **and exercised** on development seeds | **Closed** (§10.1) |
| M5 | Fresh seeds defined and unused | **Closed** — allocation fixed; verified unused |
| M6 | Clean non-IID condition | **Closed** — 5 rules x 2 seeds |
| M7 | Sign-flip attack | **Closed** — 5 rules x f1, 1 rule x f2 |
| M8 | Update-scaling attack | **Closed** |
| M9 | Norm-matched noise / benign outlier | **Closed** |
| M10 | Full §21 reporting set | **Closed** — runner records every field |
| M11 | Negative-result commitment | **Closed** — adversary model §6 |

### 10.3 Verdict: READY

All mandatory prerequisites for Phase 8 are satisfied. Fresh-seed confirmatory execution may
proceed on research-lead authorisation.

### 10.4 What READY does not mean

**READY means the protocol is executable and correctly gated. It does not mean Phase 8 has results.**
No fresh seed has been run; every Phase 8 number so far is a development-seed observation.

Three findings from the development runs will shape the confirmatory phase and must not be
suppressed:

1. **Krum and Multi-Krum collapsed to macro-F1 0.0108 under both attacks** — they are the *least*
   robust rules at K = 5, contrary to the usual expectation. The `n - f - 2` arithmetic means a
   single malicious client that survives selection determines the model.
2. **The norm rejection policy is blind to sign-flip** — detection 0.00-0.04, because a sign-flipped
   update has a similar norm to an honest one. Scaling attacks are detected perfectly (1.00). Any
   claim that the defence detects poisoning must be restricted to norm-inflating attacks.
3. **Robust rules pay utility for honest heterogeneity under `benign_outlier`** — FedAvg, Krum and
   Multi-Krum lose 0.13-0.27 macro-F1. This is precisely §21's "rejects honest non-IID clients"
   failure mode and is a live risk for the confirmatory claim.

### 10.5 Still open (non-blocking)

- `LIMITATIONS.md` items 36 and 37 (conflicts X1, X2) remain stale and must be corrected before G10.
- `class_missing` remains uninformative for the reason in §4.3.
- No adaptive attack (optional per §21).

### 10.6 Test baseline

**183 passed, 16 skipped** with Ganache stopped; **183 passed, 1 skipped** with the node running.
The 15 contract tests skip by design when no chain is reachable.

Nothing has been committed or pushed.
