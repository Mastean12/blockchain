# Phase 6 — Implementation Plan (Stage A)

**Status:** STAGE A PROPOSAL — **AWAITING RESEARCH-LEAD APPROVAL**. No privacy code runs and no
full experiment starts until the threat model, privacy parameters and this protocol are approved.
**Date:** 16 November 2026
**Authorised by:** research-lead authorisation message, 16 November 2026 (Phase 6 Stage A only)
**G4:** remains NOT PASSED. **G5:** evidence submitted, decision pending. **G6:** not assessable yet.
**Phase 7:** not started.

---

## 1. Scope and non-goals

### 1.1 In scope (this phase)
P1 DP-only, P2 HE-only, P3 HE+DP, each compared against the frozen no-privacy federated baselines,
on the frozen partitions and seeds, measuring utility, privacy parameters, compute, communication
and convergence.

### 1.2 Out of scope
Secure aggregation/MPC (threat model OUT-2); poisoning/robust aggregation (Phase 8); blockchain
audit (Phase 7); external SVDB evaluation (E1); any change to the G3 split or Phase 5 results.

## 2. What already exists and must be reused unchanged

| Component | Path | Phase 6 use |
|---|---|---|
| `compact_cnn_v1` (36,357 params) | `src/models/cnn1d.py` | Unchanged |
| Verified data loader (re-checks frozen hashes) | `src/training/phase4_data.py` | Unchanged |
| FedAvg/FedProx loop, weighted aggregation, resume | `src/federated/fedavg.py` | Extended via new hooks, existing functions untouched |
| Frozen partitions F1/F2/F3 | `data/splits/phase5/*.json` | Unchanged |
| Support-aware metrics | `src/evaluation/phase4_metrics.py` | Unchanged |
| `src/privacy/` | placeholder docstring | New code goes here |

**Rule:** `run_federated` in `fedavg.py` must not be modified in place. Phase 6 adds a privacy
wrapper (`src/privacy/dp_federated.py`, `src/privacy/he_aggregation.py`) and a new runner
(`scripts/run_phase6_privacy.py`). Any code change to `fedavg.py` requires explicit approval,
because its behaviour underlies the already-frozen Phase 5 results.

## 3. State geometry that fixes the privacy design

Measured from the frozen model (`state_dict`):

| Group | Elements | Count | Notes |
|---|---|---:|---|
| Trainable parameters | conv/BN/linear weights+biases | 36,357 | Clipped and noised |
| Float buffers (BN running_mean/var) | 32+32+64+64+128+128 | 448 | **Not noised** (see D5) |
| Integer buffers (`num_batches_tracked`) | 3 | 3 | **Not transmitted** |

The DP mechanism operates on the **update vector** `Δ = w_local − w_global` over the 36,357
trainable parameters. This is the `param-only` state representation.

## 4. P1 — Differential privacy design

### 4.1 Mechanism: Gaussian mechanism, client-side, per round

Per client, per round:

1. `Δ_k = w_local − w_global` (trainable parameters only).
2. Clip: `Δ_k ← Δ_k · min(1, C / ||Δ_k||₂)`.
3. Noise: `Δ̃_k = Δ_k + n_k`, `n_k ~ N(0, σ²C²I)` over all 36,357 coordinates.
4. Server aggregates the noised updates exactly as FedAvg does today.

This is the classic DP-SGD-style Gaussian mechanism applied to the **whole-model update**, which
is the standard "user-level DP-FedAvg" construction (Abadi et al. 2016 mechanism; McMahan et al.
2018 for the FL instantiation).

### 4.2 Sensitivity

With L2 clipping at `C`, one client's contribution has `||Δ_k||₂ ≤ C`. The full derivation is in
[`PHASE_6_PRIVACY_MATHEMATICS.md`](PHASE_6_PRIVACY_MATHEMATICS.md) §4. Summary of the result, and
of a defect the draft did not catch:

- **Aggregate-release view (A):** if only the sum were released, sensitivity would be
  `S_A = 2C·p_max = 0.742·C` on F3 (`p_max = 0.371`), and `S = 2C/K = 0.4·C` under uniform weights.
  The approved weighted aggregator is therefore **1.855× more sensitive** than uniform.
- **Per-client-release view (B) — the implemented architecture:** there is **no secure
  aggregation**, so the server sees each `Δ̃_k` individually. For one client with the others fixed
  the sensitivity is `S_B = 2C`, independent of `p_k`. **`S_B > S_A`, so view B is the honest
  accounting and is the headline figure.**

**Correction to the earlier draft:** the draft reported only `2C·p_max` and implicitly assumed an
aggregate-only release, which would understate `ε`. Both views are now reported (`S_B` headline,
`S_A` as the secure-aggregation bound).

**Separate defect found and fixed (D1′):** `p_k = n_k/Σn` uses `n_k` accumulated during local
training (`fedavg.py:150`), so the weights are data-dependent and `2C·p_max` is not a valid bound
under an adjacency that changes dataset size. Fix: define the release with the **frozen public**
weights `n_k^0/N^0`. Because equal-cardinality replacement leaves `n_k` unchanged, this computes
**identical numbers** to the current code — it fixes the derivation, not the experiment. Equal
cardinality is now part of the adjacency definition.

**Chosen (recommendation D1′):** keep the sample-weighted aggregate for Phase 5 comparability,
use frozen weights, per-client-vector clipping, and account under view B.

### 4.3 But: per-client sample count leaks

If the server weights by sample count, it learns `n_k` (client training size) — public here, since
the manifests are published. **Not an additional leak in this study**, but recorded because in a
real deployment it would be.

### 4.4 Choice of `C`

`C` is a genuine methodological decision because the update L2 norm changes over rounds and across
conditions. Proposal (D2):

1. Run a **clip-calibration dry pass** on the frozen F3 partition with no noise, logging
   `||Δ_k||₂` per client per round for all five seeds (this is a diagnostic, not a result).
2. Set `C` to a **fixed pre-registered quantile** of those norms (proposed: the **median** of
   all-client all-round norms in the last round the baseline would select), rounded to a
   power-of-ten-friendly value.
3. Freeze `C` **before** looking at any DP utility, and use the **same `C` for all DP conditions**
   so the privacy–utility curve is comparable.

Rejected alternative: per-round adaptive clipping (needs a further noisy signal and complicates
accounting). Documented as future work.

### 4.5 Noise multiplier and the ε sweep (pre-registered)

Candidate σ grid (D3), targeting approximate client-level ε at `δ = 1e-5` (a common research
choice at n = 5; **not** a regulatory value):

| Config | σ | Rounds R | Notes |
|---|---:|---:|---|
| P1-a | 0.5 | 50 | low noise, weak guarantee |
| P1-b | 1.0 | 50 | moderate |
| P1-c | 2.0 | 50 | strong noise, expect utility collapse on S/V |

ε is **computed after** the fact by the accountant and **reported, never targeted** to a
convenient value. Budgets are **not** tuned to produce a "nice" curve. If ε is unacceptable, the
cell is reported as-is (this is a finding, not a failure).

### 4.6 Accountant and composition (D4)

- **Sampling:** full participation (all five clients every round) → **no subsampling amplification**.
  Any accountant assuming Poisson sampling would be invalid here.
- **Composition type:** **Rényi DP → (ε, δ)-DP conversion** (Mironov 2017), against a Gaussian
  mechanism with sensitivity `S` at scale `σS`, over **R = 50** rounds, composed **sequentially**
  (each round is one release of the aggregate).
- **Library:** **Opacus `RDPAccountant`** (installed from PyPI, version pinned at implementation
  time). Opacus is an *implementation*; the mathematical claim rests on the RDP→DP conversion
  with the stated sensitivity and no amplification.
- **What is included in the release count:** only the **50 aggregate releases**. Validation-based
  checkpoint selection consumes the released aggregate (a post-processing step) and therefore
  **does not add to ε** by the post-processing property — *but* validation accuracy is computed on
  the aggregate, so selecting on it is allowed. This must be stated explicitly in results.
- **What is excluded:** any intermediate per-client update (never released in the private
  design — it is sent only to the server; if we model the server as the adversary, the per-client
  transmission *is* a release, which is itself DP-protected by client-side noise).

**Validity test that must pass before any result is reported:** verify the accountant on a toy
one-dimensional Gaussian problem with a known closed-form ε before using it on the model. A
failing toy test blocks the phase.

### 4.7 What DP does NOT do here

- Does not protect a record or a patient (§5.2 of threat model).
- Does not prevent a colluding server from seeing each noised update separately (no secure
  aggregation).
- Does not guarantee anything if a client fails to add noise.

## 5. P2 — Homomorphic encryption design

### 5.1 Scheme and library

**CKKS** (Cheon-Kim-Kim-Song 2017) via **TenSEAL 0.3.18** (Microsoft SEAL 4.x backend;
`tenseal-0.3.18-cp312-cp312-win_amd64.whl` verified downloadable for this environment). Library
version is pinned in the experiment metadata; the security estimate source is the HE-standard
table shipped with SEAL, **not** an independent proof.

### 5.2 Parameter set (D6)

Two candidate profiles; the final choice is approved before running.

| Param | Profile "HE-128" | Profile "HE-256" | Rationale |
|---|---|---|---|
| `poly_modulus_degree` | 8192 | 16384 | N=8192 caps total coeff-modulus bits at 218 (128-bit); N=16384 caps at 438 |
| `coeff_mod_bit_sizes` | `[60,40,40,60]` | `[60,40,40,40,40,60]` | total 200 bits at N=8192; 280 bits at N=16384 — both under their caps. Enough levels for one homomorphic add-chain plus one plaintext-multiply |
| `global_scale` (2^s) | 2^40 | 2^40 | precision vs modulus budget |
| Security estimate source | HE standard / SEAL table | same | stated, not derived |

**Recommendation:** run **HE-128 (8192)** as the primary profile; it is the standard 128-bit
choice for tensors of this size and keeps ciphertext size manageable on 4 GB VRAM. HE-256 is an
optional sensitivity check on one seed.

### 5.3 Packing and what is encrypted

- Each parameter tensor is flattened and split into chunks of `N/2` values (`N =
  poly_modulus_degree`), packed into one or more ciphertexts. 36,357 values ⇒ **9 ciphertexts at
  N = 8192** (4,096 slots each, last chunk partially filled) or **5 at N = 16384** (8,192 slots).
- Only **trainable parameters** are encrypted. BatchNorm buffers and `num_batches_tracked` are
  handled outside the ciphertext (see D5).
- The server performs **homomorphic weighted addition**: `Σ p_k · c_k` using plaintext weights
  `p_k`. Weighted sum is linear, so no non-linear operation on ciphertext is needed — this is why
  CKKS (approximate arithmetic) is the right scheme and why the operation count (one
  `mul_plain` + `add` per chunk) is small and predictable.

### 5.4 Keys and trust

- One key pair per experiment, generated by the **decryptor** at the start of a run.
- **Public/context key** distributed to all clients; **secret key held only by the decryptor**.
- **Decryption point:** after the server's homomorphic sum, on the decryptor, every round.
- **The decryptor sees the clean aggregate each round** — stated in every P2 result.
- Key rotation/destruction policy: keys are generated per run, never reused across conditions, and
  the secret key is not written to any released artefact (only a hash of the public context is
  recorded).

### 5.5 Precision and approximation error (D7)

- CKKS is approximate. The study measures `||decrypt(Σ enc(Δ_k)) − Σ Δ_k||₂ / ||Σ Δ_k||₂` per
  chunk per round, and reports mean and max relative error over the run.
- Scale `2^40` is expected to give ~1e-9 to 1e-7 relative error on tensors of this magnitude;
  **this is to be measured, not assumed**, and is reported as an **empirical** observation, not a
  formal bound.
- If relative error is not negligible against the update magnitude, the result is reported and the
  parameter set is revised **before** P3, with a recorded protocol deviation.

### 5.6 What HE does NOT do here

- Does not hide the aggregate from the decryptor (stated as an explicit limitation).
- Does not protect against a malicious client or a malicious server (server is key-blind but can
  still drop/modify ciphertexts; integrity is not provided).
- Does not by itself give DP — encryption is not a privacy guarantee against the key holder.

## 6. P3 — Combined HE+DP information flow

```
client k:
  Δ_k  = w_local − w_global
  Δ_k  ← clip(Δ_k, C)                       # DP
  Δ̃_k  = Δ_k + N(0, σ²C²I)                  # DP
  c_k  = CKKS_enc(Δ̃_k)                      # HE
server:
  C_agg = Σ p_k · c_k                        # homomorphic weighted sum, no key
decryptor:
  w_new = w_global + CKKS_dec(C_agg)         # sees only noised aggregate
```

Order is fixed (threat model §8): **clip → noise → encrypt → aggregate → decrypt**. DP therefore
still holds against the decryptor; HE still hides intermediate client updates from the server.

**Critical check:** because noise is added *before* encryption, P3's DP guarantee is **identical**
to P1's at the same `(C, σ, R)` — P3 must **not** claim a stronger DP guarantee than P1. P3's claim
is: "same DP guarantee as P1, plus confidentiality of individual client updates against a
key-blind server, at the cost measured."

## 7. Baselines and conditions (D8)

The authoritative condition list, seeds, pre-registered parameters, execution order and stop
conditions are in [`PHASE_6_EXPERIMENT_MATRIX.md`](PHASE_6_EXPERIMENT_MATRIX.md). Summary:

| ID | Condition | Priority |
|---|---|---|
| **P0** | Frozen F3 FedAvg (no privacy) — **already measured**, 0.8523 / 0.3752 | done |
| **P1-ctl** | Clip-only, no noise — separates clipping loss from noise loss | required |
| **P1-a/b/c** | DP-only, σ ∈ {0.5, 1.0, 2.0} | required |
| **P2** | HE-only, CKKS N=8192 | required |
| **P3-a/b** | HE+DP at σ ∈ {1.0, 2.0} | required |

**35 runs to execute** (P0 reused, not re-run) × 51 rounds ≈ 2,040 federated rounds.

**P1-ctl is essential.** Without it we cannot say whether a utility drop is due to clipping or to
noise, and the master spec (§11 Stage 7, §15.3) requires identifying which factor explains the gap.

## 8. Metrics

### 8.1 Utility (same code as Phases 4/5)
Accuracy, macro/weighted precision/recall/F1, per-class P/R/F1/support, confusion matrix (order
N,S,V,F,Q), validation selection round, and **S recall** reported explicitly. S remains expected
to be 0.000; **a DP or HE run that beats baseline on S is a finding to investigate, not a win to
report**, and the same record-232 caveat applies.

### 8.2 Privacy
ε at δ = 1e-5 per condition, accountant name/version, C, σ, R, sensitivity S, and the exact
composition statement. **No ε is reported without its assumptions.**

### 8.3 Compute
Wall-clock per round and per run; client-side clip+noise time; encrypt time; homomorphic aggregate
time; decrypt time; total DP/HE overhead as a multiple of the P0 round time.

### 8.4 Communication
Bytes per round = Σ chunk ciphertext size for HE conditions vs plaintext update size for P0/P1.
Report ciphertext expansion factor (expected ≈ 50–200× for N=8192 at 60-bit limbs) **as measured**.

### 8.5 Convergence
Validation macro-F1 per round (mean ± SD across seeds), P0 vs P1/P2/P3 overlaid; selected-round
distribution (already known to be fragile in Phase 5 §7.4 — a privacy mechanism that shifts the
selected round must be reported as such, not interpreted as a learning improvement).

## 9. Seeds, budget estimate, and hardware

- Seeds 42–46, matching Phases 4/5.
- Measured P0 cost on this machine: **≈453 s per 51 rounds** (GTX 1650, 4 GB).
- Estimated per-run overhead: DP ≈ +5–15 % (clip+noise on 36k floats is cheap); HE ≈ +50–300 %
  (9 ciphertext ops/round, plus serialization); P3 ≈ sum of both.
- **Budget estimate: 35 runs ≈ 5–9 hours** on the local GTX 1650, or proportionally less on Colab
  T4. HE is CPU-bound; it will dominate P2/P3 wall time.
- **VRAM constraint:** 4 GB with ~650 MB already used by desktop. HE ciphertexts live in host RAM,
  not VRAM; plaintext runs already fit. No change to batch size is proposed (it is frozen).

## 10. Implementation deliverables (after approval)

| File | Purpose |
|---|---|
| `src/privacy/clipping.py` | L2 clip, norm statistics, sensitivity helper |
| `src/privacy/dp_mechanism.py` | Gaussian noise, seeded PRNG, param-only extraction |
| `src/privacy/accounting.py` | RDP→DP wrapper over Opacus accountant + **toy validation test** |
| `src/privacy/he_ckks.py` | CKKS context, pack/unpack, encrypt/decrypt, homomorphic weighted sum, error measurement |
| `src/privacy/dp_federated.py` | Privacy-parameterised wrapper around the existing round loop |
| `scripts/run_phase6_privacy.py` | CLI, one condition/seed at a time, refuses overwrite, resume |
| `configs/privacy/phase6_*.yaml` | One config per condition, with approval record field |
| `tests/test_phase6_clipping.py`, `test_phase6_dp.py`, `test_phase6_accounting.py`, `test_phase6_ckks.py` | Unit + toy smoke tests |

**Gate:** the toy tests (accountant closed-form check; CKKS round-trip and aggregation consistency
on synthetic vectors) must pass before any real run.

## 11. Unresolved decisions requiring approval

| # | Decision | Recommendation | Blocking? |
|---|---|---|---|
| **D1′** | Frozen public weights `p_k = n_k^0/N^0`; per-client-vector clipping; **view B sensitivity `2C`** as headline | **Approve** | Yes |
| **D2** | Clipping constant `C` by Rule 4.1 of the experiment matrix (median of selected-round norms), fixed before DP utility | **Approve rule, value after calibration** | Yes |
| **D3** | σ ∈ {0.5, 1.0, 2.0}; δ = 1e-5; R = 50 | **Approve** | Yes |
| **D3′** | Stricter alternative `δ = 1/(10N) ≈ 1.4e-6` | Optional; default 1e-5 | No |
| **D4** | Opacus `RDPAccountant`, sequential composition, **no amplification** | **Approve**, with toy validation gate | Yes |
| **D4′** | Report ε under per-client view B as headline; view A as secure-agg bound | **Approve** | Yes |
| **D5** | BatchNorm running statistics **excluded** from DP vector and ciphertexts; leak disclosed | **Approve** | Yes |
| **D6** | CKKS profile HE-128 (N=8192, `[60,40,40,60]`, scale 2^40) | **Approve** | Yes |
| **D7** | Precision acceptance: relative error < 1e-5 on the aggregate | **Approve** | Yes |
| **D8** | 8 conditions: P0, P1-ctl, P1-a/b/c, P2, P3-a/b | **Approve** | Yes |
| **D9** | F3 only for Stage B; F1/F2 out of scope | **Approve** | No |

### 11.1 The D5 decision explained (because it is subtle and important)

BatchNorm `running_mean`/`running_var` are 448 floats that depend on client data. Two choices:

- **Include them in the DP vector** → they must be noised, and noisy BN statistics can badly
  destabilise evaluation (BN statistics are used at inference). Sensitivity doubles in practice
  because they are also aggregated weighted.
- **Exclude them** → they are aggregated unnoised, exactly as Phase 5. This **leaks some
  distributional information** about each client's activations.

**Recommendation:** exclude, aggregate as Phase 5, and **state the leak as a limitation** — this
is the standard DL-with-DP-in-FL compromise when doing param-only DP. Including them is defensible
and would be a stronger design, but materially changes the mechanism and the utility comparison.
If the research lead prefers the stronger design, D5 flips and a fresh `C`, σ grid and accountant
pass are required.

## 12. Master-specification conformance audit

Every Phase 6 requirement in `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` and where it is addressed.

| Spec ref | Requirement | Addressed in | Status |
|---|---|---|---|
| §14 | Threat model before DP/HE: assets, adversaries, trusted parties, what each party sees, key ownership, public metadata, attack surfaces, privacy unit, adjacency, released outputs, out-of-scope | `PHASE_6_PRIVACY_THREAT_MODEL.md` §3–8 | Written |
| §14 | Do not say "patient privacy" when the unit is a client slot | Threat model §5.2, §9 | Enforced |
| §15.1 | Mechanism: central/local/named model | Mathematics §5 | Written |
| §15.1 | Protected unit, adjacency (add/remove vs replace-one) | Mathematics §2 | Written |
| §15.1 | Clipping operation and norm, sensitivity derivation | Mathematics §4 | Written + **defect D-1 found** |
| §15.1 | Noise distribution and scale | Mathematics §5.3 | Written |
| §15.1 | Client sampling/participation assumptions | Mathematics §6.2 | Written |
| §15.1 | Rounds and number of releases | Matrix §3 | Written |
| §15.1 | Accountant and supported mechanism | Mathematics §6.1 | Written |
| §15.1 | ε, δ | Matrix §4.2–4.4 | Written (ε computed later, by design) |
| §15.1 | What is released; whether validation-selection is in the release analysis | Mathematics §6.5 | Written |
| §15.1 | RNG and whether cryptographically secure | Mathematics §5.3 | Written (**not** CSPRNG) |
| §15.2 | Recognised accountant compatible with the actual mechanism | Mathematics §6.1, §6.6 toy gate | Written |
| §15.2 | Do not reuse a published ε | Matrix §4.2 | Enforced |
| §15.2 | Report no formal guarantee if assumptions fail | Mathematics §6.5, §10 | Enforced |
| §15.2 | Client-level unit only if the mechanism provides it | Threat model §5 | Enforced |
| §15.3 | DP experiments only after non-private baselines are stable | P0 frozen; G4/G5 recorded | Satisfied with caveat (§13) |
| §15.3 | Predeclared noise levels; matched seeds/partitions; validation-selected checkpoints; final test once | Matrix §3–5 | Written |
| §15.3 | Do not choose ε after seeing test utility | Matrix §4.2, §5 | Enforced |
| §16.1 | CKKS: library/version, degree, coeff modulus chain, scale, security source, encrypted quantity, packing, key ownership, serialization, ops, decryption location, error, ciphertext size, key rotation | Mathematics §7; plan §5 | Written (serialization/rotation to be finalised in Stage C) |
| §16.1 | Do not claim CKKS hides the aggregate from the secret-key holder | Mathematics §7.5; plan §5.6 | Enforced |
| §16.2 | Compare plaintext, HE-only, DP-only, HE+DP | Matrix §3 | Written |
| §16.2 | Same model, partition, updates, seeds | Matrix §2, §5 | Written |
| §16.2 | Record where noise is added relative to clip/encrypt/aggregate/decrypt | Mathematics §8.1 | Written |
| §16.2 | Measure encrypt time, encrypted size, HE aggregation, decrypt, total round, approximation error, utility | Matrix §6 | Written |
| §16.2 | Approximation error is empirical, not a formal bound | Mathematics §7.4, §10 | Enforced |
| §22 | Every experiment records ID, config, dataset/checksum, split hash, mapping, seed, source snapshot, environment, command, timestamps, exit status, output dir, metrics, model hash, warnings, deviations | Plan §10; reuse of Phase 4/5 runner conventions | Written |
| §24 | Tests: DP clipping/noise/accounting; HE encrypt/decrypt/aggregation consistency | Plan §10; Matrix §5 | Written |
| §24 | Integration smoke: one DP mechanism test, one HE aggregation test | Plan §10 gate | Written |
| §29 G6 | Threat model and accountant validated; DP/HE assumptions approved | This plan; status doc | **Pending approval** |

### 12.1 Conflicts and omissions found in the Stage A draft

| # | Issue | Severity | Resolution |
|---|---|---|---|
| **C-1** | Sensitivity `2C·p_max` was asserted without derivation and is invalid under a size-changing adjacency (`n_k` is data-dependent) | **High — would invalidate ε** | Fixed: frozen weights + equal-cardinality adjacency; Mathematics §4 |
| **C-2** | Draft accounted only the aggregate release, but with no secure aggregation the server sees each client update | **High — would understate ε** | Fixed: per-client view B is the headline; Mathematics §5.2 |
| **C-3** | BatchNorm leakage was mentioned only as a decision, not quantified in the claim | Medium | Fixed: explicit parameter-level disclosure table; Mathematics §9 |
| **C-4** | Draft said 10 ciphertexts; correct value is 9 | Low | Corrected in both documents |
| **C-5** | Draft's `P1-ctl` was described as `C = ∞, σ = 1.0` — that is noise-only, **not** clip-only, so it would not isolate clipping | Medium | Renamed and corrected: clip with `C`, **no** noise |
| **C-6** | Draft claimed 7 conditions / 1,750 rounds; the corrected matrix has 8 conditions / 2,040 rounds (35 to execute) | Low | Corrected |
| **C-7** | Master spec §15.3 says DP runs "only after non-private baselines are stable", but G4 never passed (S recall 0.000) | **Governance** | See §13 — requires explicit research-lead acknowledgement |

## 13. Governance caveat that must be acknowledged

Master specification §15.3 and Phase-4 gate G4 state that DP experiments should only run after the
non-private baseline is **stable and trustworthy**. G4 was **not passed** (S recall 0.000, three
mechanisms tried), and G5 is submitted but not decided.

Phase 6 therefore proceeds on a baseline that is stable in loss/accuracy terms but
**known-defective on class S**. This is permissible only as an explicit research-lead decision,
and its consequences must be stated in every Phase 6 result:

- S recall will be reported as ~0.000 and **cannot** be attributed to DP/HE;
- no Phase 6 result may claim to improve minority-class performance;
- if DP or HE changes S recall away from 0.000, that is an anomaly to investigate, not a win.

**This is recorded as decision G-1 and must be approved before Stage B.**

## 14. Stop point

Stage A ends here. Deliverables: this plan, `PHASE_6_PRIVACY_THREAT_MODEL.md`,
`PHASE_6_PRIVACY_MATHEMATICS.md`, `PHASE_6_EXPERIMENT_MATRIX.md`,
`PHASE_6_EXECUTION_STATUS.md`. No privacy code, no DP/HE install, no experiment. Awaiting
resolution of **TM-1..TM-7**, **D1′..D9**, and **G-1**. Phase 7 is not started. Nothing committed.
