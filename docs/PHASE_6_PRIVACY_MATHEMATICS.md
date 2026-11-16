# Phase 6 — Privacy Mathematics

**Status:** STAGE A — **NOT APPROVED**
**Date:** 16 November 2026
**Purpose:** Formal definitions and derivations sufficient to justify every privacy parameter used
in Phase 6. Any number in the Phase 6 results must trace back to a definition here.
**Authority:** `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` §14–16; `RESEARCH_PROTOCOL.md` §6.1

---

## 0. Purpose and a found defect

The Phase 6 Stage A draft proposed the sensitivity `2·C·max_k(p_k)` without deriving it. The
directive requires derivation. Deriving it exposed a **real defect in the proposed design**, which
is recorded here rather than hidden:

> **Defect D-1 (sensitivity derivation is not valid as written).** In `src/federated/fedavg.py`,
> a client's aggregation weight is `p_k = n_k / Σ_j n_j`, where `n_k` is the number of training
> windows the client actually processed. `n_k` is **data-dependent**: it is accumulated during
> local training (`fedavg.py:132–153`). Under a replace-one adjacency in which a client's dataset
> may change *size*, both its own weight and every other client's weight change. The released
> quantity is then not a fixed linear combination of the clipped updates, and `2C·p_max` is not
> the sensitivity.

Section 4 resolves this defect by fixing the release function. Section 3 proves the adversary
sees `n_k` regardless, which makes the fix lossless rather than a compromise.

---

## 1. Notation

| Symbol | Meaning |
|---|---|
| `K` | Number of clients; `K = 5` (frozen) |
| `U = {1,…,K}` | Client index set |
| `D_k` | Training dataset of client k (a set of 253-sample windows) |
| `n_k = \|D_k\|` | Number of training windows held by client k |
| `N = Σ_k n_k` | Total training windows, `N = 71,927` (frozen, F3 partition) |
| `w_global` | Global model parameters at round start (`R^d`, `d = 36,357`) |
| `w_local,k` | Client k's parameters after local training |
| `Δ_k = w_local,k − w_global` | Client k's update (`R^d`) |
| `C` | L2 clipping norm, `C > 0` |
| `Π_C(x) = x·min(1, C/‖x‖₂)` | L2 clipping operator |
| `σ` | Noise multiplier (noise SD `= σC` per coordinate) |
| `R` | Number of communication rounds / releases; `R = 50` |
| `ε, δ` | Approximate DP parameters |

**Fixed for all of Phase 6:** `K = 5`, `N = 71,927`, `d = 36,357`, `R = 50`.

---

## 2. The client dataset and replace-one adjacency

### 2.1 What one client dataset is

`D_k` is the multiset of Phase 3 windows whose source record appears in client k's frozen record
list (F3: e.g. client_01 holds records 114,117,200,201,202,205,209,222,223,233,234, giving
`n_1 = 26,685`). Windows are those produced by the frozen Phase 3 pipeline; no window is shared
between clients (verified in `phase4_data.py` and the Phase 5 tests).

### 2.2 Adjacency — definition

> **Definition 2.1 (Replace-one adjacency, equal cardinality).** `D = (D_1,…,D_K)` and
> `D' = (D'_1,…,D'_K)` are **adjacent**, written `D ~_RO D'`, iff there is exactly one index
> `j ∈ U` with:
> 1. `D'_k = D_k` for all `k ≠ j`; and
> 2. `D'_j` is an arbitrary dataset with **`|D'_j| = |D_j|`**.

**Why equal cardinality is required.** See §4.2: it makes `n_j` invariant, so the aggregation
weights are identical on neighbouring inputs and the release is a fixed linear functional. Without
it no finite sensitivity exists for the weighted release at all.

**Why replace-one rather than add/remove.** `K` and participation are fixed and public, so a
"client was added/removed" event does not correspond to anything this architecture can produce.
Replace-one models "the institution's dataset was swapped", which it can.

### 2.3 What is protected, what is public

| Item | Status | Justification |
|---|---|---|
| `D_k` contents (which windows/records/labels) | **Protected** | Subject of the adjacency |
| `U`, `K`, participation schedule | **Public** | Frozen manifests; published by design |
| `n_k` (client sizes) | **Public in this study** | Published in the F3 manifest (`sample_count`); see §3 |
| Architecture, `d`, hyperparameters, `R` | **Public** | Required for reproducibility |
| `C`, `σ`, `ε`, `δ`, accountant | **Public** | Required for auditability |
| Final model, metrics | **Public** | Deliberate research release |
| Validation/test data | **Never released** | Used only for selection/evaluation |

**Claim boundary.** The guarantee is over the **complete released transcript** = the sequence of
`R` aggregate models. Individual client updates are transmitted to the server; under the threat
model's no-secure-aggregation assumption (§5) each transmitted update is itself a release, and it
is protected by the *client-side* noise of §5.2. Both must be accounted (see §6.4).

---

## 3. `n_k` is not secret — established, not assumed

Three independent facts:

1. **Manifest publication.** `data/splits/phase5/phase5_f3_severe.json` lists `sample_count` per
   client. `n_k` is literally in the repository.
2. **The server computes it from the received update flow.** In `fedavg.py`, `samples` is returned
   with the update and used to form weights, so the server holds `n_k` in cleartext.
3. **It is recoverable from the model itself.** `num_batches_tracked` is summed across clients and
   the local step count per client is `⌈n_k/256⌉ · local_epochs`, so `n_k` is inferable from the
   aggregated integer buffer to within one batch.

**Consequence:** treating `n_k` as public costs **no** privacy in this study. This is what licenses
the §4.2 fix. It must be re-examined if the study is ever extended to a setting where client sizes
are private.

---

## 4. Release function and sensitivity — the derivation

### 4.1 The actual release (as implemented)

From `fedavg.py:76–82`, for each floating tensor:

```
w_new = Σ_{k∈P} (n_k / Σ_{j∈P} n_j) · (w_local,k)                … over participating set P
```

Note this averages the **models**, not the updates; equivalently, since weights sum to 1,

```
w_new − w_global = Σ_{k∈P} p_k · Δ_k ,      p_k = n_k / Σ_{j∈P} n_j
```

With full participation (`P = U`, the approved setting), `p_k = n_k / N`.

### 4.2 Why the naive expression fails, and the fix

`n_k` is data-dependent (§3). If `D'_j` may have a different size, then `Σ n` changes, so **every**
`p_k` changes and the map `(Δ_1,…,Δ_K) ↦ Σ p_k Δ_k` is not fixed. Sensitivity is then unbounded in
the parameter `C` — clipping does not bound it, because clipping bounds `‖Δ_k‖`, not the weight.

**Fix (recommended, decision D1′):** fix the weights to the **public, frozen** sample counts:

> **Definition 4.1 (Release function).** Let `p_k = n_k^0 / N^0` where `n_k^0, N^0` are the frozen
> manifest counts (published constants), **independent of the realised dataset**. The released
> aggregate is
> `G(Δ_1,…,Δ_K) = Σ_{k=1}^{K} p_k · Δ_k`.

`G` is then a **fixed** linear functional. This is a one-line change at implementation time
(pass the frozen weights rather than the realised `n_k`) and **does not change** the arithmetic:
because equal-cardinality adjacency keeps `n_k` invariant, `n_k = n_k^0` on every input anyway, so
`G` computes exactly the same numbers as the current code. **The fix changes the derivation, not
the experiment.**

### 4.3 Sensitivity theorem

> **Theorem 4.2.** Let `D ~_RO D'` (Definition 2.1) and let per-client updates be clipped so that
> `‖Δ_k‖₂ ≤ C` for all k on both `D` and `D'`. Then for `G` of Definition 4.1,
> ```
> ‖G(D) − G(D')‖₂ ≤ 2 C p_max ,      p_max = max_k p_k .
> ```

*Proof.* Only client `j` differs. Write `x = Δ_j(D)`, `y = Δ_j(D')`, both with norm ≤ `C`; all
other `Δ_k` identical.

```
G(D) − G(D') = p_j (x − y)
‖G(D) − G(D')‖₂ = p_j ‖x − y‖₂ ≤ p_j (‖x‖₂ + ‖y‖₂) ≤ p_j · 2C ≤ 2C p_max .  ∎
```

The bound is tight: take `x = C·u`, `y = −C·u` for a unit vector `u` and `j = argmax_k p_k`.

> **Corollary 4.3 (Gaussian mechanism).** Adding `ξ ~ N(0, S²σ² I_d)` with `S = 2C p_max` to `G`
> yields `(ε, δ)`-DP with `ε` given by the RDP composition of §6, for the stated adjacency.

### 4.4 Numerical values for the frozen F3 partition

Frozen counts and weights (`p_k = n_k^0 / N^0`):

| Client | `n_k^0` | `p_k` |
|---|---:|---:|
| client_01 | 26,685 | **0.371001** |
| client_02 | 14,780 | 0.205486 |
| client_03 | 6,260 | 0.087033 |
| client_04 | 11,149 | 0.155004 |
| client_05 | 13,053 | 0.181477 |
| **Total** | **71,927** | 1.000000 |

Therefore

```
S = 2 · C · p_max = 2 · C · 0.371001 = 0.742002 · C
```

For comparison, a uniform (unweighted-mean) aggregator would give `S = 2C/K = 0.4·C`; the approved
weighted aggregator is **1.855×** more sensitive. The directive's instruction to retain weighted
aggregation therefore costs **1.855× in noise** for the same `ε`. This is a real, quantified trade
and is presented as decision **D1′**.

### 4.5 Per-tensor vs per-vector clipping

The directive asks explicitly. Three choices:

| Rule | What is bounded | Sensitivity | Notes |
|---|---|---|---|
| **Per-coordinate** (clip each coordinate) | `\|Δ_k[i]\| ≤ C` | `2C p_max √d` | Very loose as an L2 bound; `√36357 ≈ 190.7×` worse |
| **Per-tensor** (clip each tensor separately) | `‖Δ_k^{(t)}‖₂ ≤ C` per tensor | `2C p_max · √(#tensors)` | There are ~19 float tensors ⇒ ≈4.36× worse |
| **Per-client vector (whole update)** | `‖Δ_k‖₂ ≤ C` | **`2C p_max`** | **Chosen** |

**Chosen: per-client vector clipping**, because it gives the tightest L2 bound for a *single*
released vector, which is what `G` uses. Per-tensor clipping would be preferred only if bandwidth
or per-layer control mattered; it does not here.

---

## 5. The DP mechanism

### 5.1 Where clipping happens

```
client k, round r:  Δ_k = w_local,k − w_global          (d = 36,357 trainable params)
                    Δ̂_k = Π_C(Δ_k) = Δ_k · min(1, C/‖Δ_k‖₂)
                    Δ̃_k = Δ̂_k + b_k ,   b_k ~ N(0, σ²C² I_d)
server:             w_global ← w_global + Σ_k p_k Δ̃_k
```

Clipping is **before** noise, per client, per round, on the whole parameter vector. `p_k` are the
frozen public weights of Definition 4.1.

### 5.2 Two accounting views (both must be reported)

**(a) Aggregate release.** The server's released model each round is `Σ p_k Δ̃_k`, with sensitivity
`S = 2C p_max` (§4.3). `R = 50` releases compose sequentially.

**(b) Per-client transmission (threat model has no secure aggregation).** Each `Δ̃_k` is individually
transmitted. For client k alone with the other four fixed, the per-client release has sensitivity
`2C` (not `2C p_k`) because the adversary sees `Δ̃_k` unpremultiplied. `R = 50` releases compose.

> **(b) dominates.** `S_b = 2C > S_a = 0.742C`, so the honest accounting must use view (b) unless
> secure aggregation is added (it is not — threat model OUT-2).

**This is an important correction to the draft.** The draft implicitly assumed only the aggregate
was released, which would understate `ε` by a factor related to `1/p_max`. **Recommendation
(D4′):** report **ε under view (b)** as the headline privacy number, and note `ε` under view (a) as
a lower bound achievable only with secure aggregation. A colluding-server variant is reported as an
upper bound (§6.4).

### 5.3 Noise generation and randomness

- `b_k ~ N(0, σ²C²I_d)`, i.i.d. per coordinate, per client, per round.
- **Reproducibility mode:** a seeded `torch.Generator` derived from `(seed, round, client_id)`, so
  runs are bit-reproducible.
- **Production-security mode:** a CSPRNG and no seed logging. **Not implemented in this study.**
- The study records explicitly: *a seeded PRNG is not a CSPRNG; results demonstrate the method, not
  production security.* This is a required disclosure per master spec §15.1.

---

## 6. Privacy accounting

### 6.1 Mechanism and accountant

- Mechanism: **Gaussian**, sensitivity `S`, noise scale `σ`, over `R` sequential releases.
- Accountant: **Rényi DP (Mironov 2017)** for the Gaussian mechanism, converted to `(ε,δ)`, via
  **Opacus `RDPAccountant`** (version pinned at implementation).
- **RDP of one Gaussian release** with sensitivity `S` and noise `σS`:
  `ε_RDP(α) = α · S² / (2 (σS)²) = α / (2σ²)` for integer `α > 1`.
- Composition over `R` independent releases: `ε_RDP^{total}(α) = Σ_r ε_RDP(α) = R·α/(2σ²)`.
- Conversion to `(ε,δ)`: `ε = min_α [ R·α/(2σ²) + log(1/δ)/(α−1) ]`.

> **Note the cancellation:** `σ` here is the *relative* noise multiplier, so `S` cancels in the
> per-release RDP. This is why `ε` depends on `σ` and `R` but **not** on `C` or `p_max` directly —
> `C` and `p_max` scale both signal and noise. **`C` affects utility, not `ε`.** This is a
> non-obvious fact worth stating, because it means changing `C` cannot be used to "buy" privacy.

### 6.2 Sampling and participation assumptions

- `P = U` every round: **full participation, fraction 1.0.**
- Therefore **no subsampling amplification**. Any accountant assuming Poisson sampling would be
  **invalid** and must not be used.
- Client availability is deterministic. No client dropout (approved: `client_dropout_policy:
  none_beyond_declared_participation_fraction`).

### 6.3 δ

- `δ = 1e-5`.
- Justification: `δ` should be ≪ `1/Σ_k n_k = 1/71,927 ≈ 1.4e-5`; `1e-5` satisfies this with
  margin and is a conventional research choice.
- **`δ` is not a regulatory value.** No GDPR/HIPAA claim is made.
- Alternative considered: `δ = 1/(10N) ≈ 1.4e-6`, stricter; rejected only for comparability with
  common FL-DP literature. **Decision D3′** — research lead may prefer the stricter value.

### 6.4 Composition over the complete transcript

Three accounting views, **all reported**:

| View | Sensitivity per release | Multiplier | Meaning |
|---|---|---:|---|
| A. Aggregate only | `2C p_max = 0.742C` | `×0.742` | Achievable **only** with secure aggregation (not used) |
| **B. Per-client transmission (headline)** | **`2C`** | **×1.000** | Matches the implemented architecture |
| C. Colluding server + t clients | Untrusted clients' updates *known exactly*, so their noise gives no protection against the colluder | **no valid bound** | Reported as failure of the assumption |

View C is the honest statement that collusion breaks the guarantee: if the server knows client
j's true update from colluders, it can subtract it and `Δ̃_j` is the only source of uncertainty — but
`Δ̃_j` is itself a release of client j's data under noise, which is still protected by view B for
**client j**. The colluders learn *other* clients' noised updates, each still DP-protected. So view
C is *not* a failure; the correct statement is: **collusion does not break the per-client guarantee,
because the guarantee never relied on secrecy of other clients' updates.** This must be stated
carefully rather than hand-waved; see §10 limitation 3.

### 6.5 What the accountant does and does not cover

**Covers:** `R` aggregate/per-client releases of the DP-protected parameter vector.

**Does not cover:**
- **BatchNorm statistics** (decision D5) — transmitted unnoised.
- **`n_k`** — public (§3).
- **Validation-based checkpoint selection** — post-processing of a released quantity, so it adds
  no privacy loss; but it *is* a use of the released model, which is allowed under post-processing.
- **The final model's own leakage** (membership inference against the model) — out of scope.

### 6.6 Validity gate

Before any `ε` is reported as a guarantee, a **toy test** must pass: for `d = 1`, `R = 1`, compute
`ε` by the accountant and compare against the analytic Gaussian-mechanism bound
`ε = (S/σS)·√(2 ln(1.25/δ))`. Agreement within tolerance is required. A failing toy test **blocks
the phase**.

---

## 7. Homomorphic encryption mathematics

### 7.1 Scheme and parameters

CKKS (Cheon–Kim–Kim–Song 2017) via TenSEAL 0.3.18 / SEAL 4.x.

| Parameter | Value | Note |
|---|---|---|
| `poly_modulus_degree N` | 8,192 | total coeff-modulus ≤ 218 bits for 128-bit classical security |
| `coeff_mod_bit_sizes` | `[60,40,40,60]` | total 200 bits ≤ 218 |
| `global_scale` | `2^40` | precision vs level budget |
| security source | HE-standard / SEAL table | stated, not derived |

### 7.2 Packing and ciphertext count — verified arithmetic

- Slots per ciphertext: `N/2 = 4,096` (a complex slot holds one real number under conjugation).
- `d = 36,357` ⇒ `⌈36357/4096⌉ =` **9 ciphertexts** (8 full + 1 with 3,653 slots used).

This is verified arithmetic, not the "ten" in the earlier draft (corrected), and must be
**re-verified against the implementation** in Stage C by asserting `len(ciphertexts) == 9`.

### 7.3 Operations performed homomorphically

Only **weighted addition**:
```
C_agg = Σ_k p_k · c_k        (p_k public plaintext scalars; mul_plain + add)
```
`mul_plain` and `add` are exact-up-to-CKKS-approximation; **no ciphertext–ciphertext
multiplication**, so no relinearisation and no bootstrapping are needed, and depth is 1.

### 7.4 Approximation error

For decrypted `Ĝ` vs plaintext `G`:
```
rel_err = ‖Ĝ − G‖₂ / ‖G‖₂
```
Scale `2^40` predicts `rel_err ~ 1e-9..1e-7`; **must be measured, not assumed**. Acceptance
threshold `rel_err < 1e-5` (decision D7); otherwise revise parameters before P3.

### 7.5 What HE provides and does not provide

- **Provides:** confidentiality of individual client updates `c_k` against a key-blind server, and
  of the aggregate against everyone except the decryptor.
- **Does not provide:** confidentiality of the aggregate against the decryptor (the decryptor
  decrypts it); integrity or authenticity (a server can drop or replay ciphertexts); protection
  against a malicious client; any DP guarantee.
- **CKKS does not hide the aggregate from the secret-key holder.** Stated in every result.

---

## 8. Combined DP+HE

### 8.1 Information flow (fixed)

```
1. Δ_k  = w_local,k − w_global
2. Δ̂_k = Π_C(Δ_k)
3. Δ̃_k = Δ̂_k + N(0,σ²C²I)
4. c_k  = CKKS_Enc(pk, Δ̃_k)
5. C_agg = Σ_k p_k · c_k                    (server, no key)
6. Ĝ = CKKS_Dec(sk, C_agg)                   (decryptor)
7. w_global ← w_global + Ĝ
```

### 8.2 Guarantee statement for P3

> **P3 provides the same `(ε,δ)` client-level guarantee as P1 at identical `(C, σ, R)`**, because
> the DP noise is added before encryption and encryption is a data-independent bijection on the
> noise distribution's support. It additionally hides individual `Δ̃_k` from the server.

**P3 must not be claimed stronger than P1.** Any implementation deviation (e.g. noise after
encryption, or a different `σ`) invalidates this equivalence and must be re-accounted.

### 8.3 Numerical composition

HE approximation error perturbs the *noised* aggregate. Because DP guarantees hold for all
outputs of the mechanism and CKKS decryption is data-independent post-processing, the DP guarantee
is unaffected by approximation error. The approximation error only affects **utility**.

---

## 9. What exactly is protected — parameter-level disclosure table

| Model component | Elements | Clipped+noised | Encrypted (P2/P3) | Aggregated | Released |
|---|---:|:---:|:---:|:---:|:---:|
| Conv/BN/Linear weights & biases | 36,357 | **Yes** | **Yes** | weighted | yes |
| BN `running_mean`, `running_var` | 448 | **No** | **No** | weighted (as Phase 5) | yes |
| `num_batches_tracked` | 3 | No | No | summed | yes |
| `n_k` | 5 | n/a | n/a | n/a | yes (published) |

> **Disclosure:** the 448 BatchNorm buffers are transmitted, aggregated and released **without DP
> noise or encryption**. They are functions of client data. This is the D5 compromise; it is
> quantified as residual risk in §10 and must appear in every privacy claim.

---

## 10. Limitations of the mathematics

1. **Equal-cardinality adjacency** (§2.2) is a restriction. Replace-one with arbitrary size has no
   finite sensitivity for a sample-weighted release; the study therefore explicitly excludes it.
2. **`C` does not affect `ε`** (§6.1) but does affect utility; changing `C` post hoc changes
   results, not privacy, and is therefore a *utility* tuning knob that must stay pre-registered.
3. **Collusion:** with no secure aggregation, the guarantee rests on per-update noise, not on
   hiding the sum. Collusion among clients does not break client j's guarantee (§6.4 view C), but
   it does mean "the server learns only the aggregate" is **false** in this architecture.
4. **No record/patient-level guarantee** (§ threat model §5.2). `K = 5` is a very coarse universe.
5. **BatchNorm buffers are unprotected** (§9), a genuine leak of activation-distribution statistics.
6. **Seeded PRNG** is not a CSPRNG; no production-security claim.
7. **`δ` and `ε` are research parameters**, not compliance values.
8. **HE gives confidentiality only against the key-blind server**; the decryptor sees plaintext.
9. **CKKS error is empirical**, not a formal bound.
10. **Nothing here addresses integrity, authenticity or availability** — only confidentiality.
