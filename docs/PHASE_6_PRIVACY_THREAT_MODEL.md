# Phase 6 — Privacy Threat Model

**Status:** **APPROVED** by the research lead on 16 November 2026 (decision G6-a). TM-1..TM-7 are
accepted as written. This is the authoritative privacy threat model for the study.
**Date:** written 16 November 2026; approved 16 November 2026
**Phase:** 6 (Privacy)
**Authority:** `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` §14–16, `RESEARCH_PROTOCOL.md` §6.1
**Canonical path:** this file. `docs/threat_model/PRIVACY_THREAT_MODEL.md` redirects here.
**Governs:** P1 (DP-only), P2 (HE-only), P3 (HE+DP) — all executed under this model.

---

## 1. Why this document exists

The master specification requires an approved threat model **before** any DP/HE implementation.
The specific failure it guards against is claiming "patient privacy" while the formal privacy unit
is actually a client slot containing many records. This document fixes the privacy unit, the
adjacency relation, the trust assumptions and the released transcript so that every later privacy
claim can be traced to exactly one of them.

## 2. The system being protected

Five simulated clients hold **disjoint whole-record training partitions** of MIT-BIH (frozen in
`data/splits/phase5/*.json`). A central server coordinates FedAvg/FedProx rounds. Each round a
client trains locally from the global model and returns an updated model state; the server
aggregates and returns the new global model.

**What is actually private here is a client's record set, not a patient.** MIT-BIH records are
public. A simulated client is a grouping of public records. The meaningful threat is therefore
about **the update channel and the audit trail**, not about protecting raw ECG from disclosure of
public data.

## 3. Assets to protect

| # | Asset | Where it lives | Sensitivity in this study |
|---|---|---|---|
| A1 | The exact record membership of each client (which records client_k holds) | Client manifests (frozen, published) | **Not secret.** Published by design. Listed for completeness. |
| A2 | Each client's training-set *label distribution* and per-beat information, to the extent inferable from its update | Client update vector | **Protected by DP**, partially. This is the real DP target. |
| A3 | Whether a specific record (or beat) participated in a given client's training | Client update / membership | **Protected subject to the stated privacy unit** (§5). |
| A4 | Client update tensors in transit and at rest on the server | Network / server memory | **Protected by HE** in P2/P3 only where the key holder is absent. |
| A5 | Model parameters and the final checkpoint | Server, released artefact | Public research artefact; released deliberately. |
| A6 | Privacy budget records (ε, δ, clip C, σ, accountant) | Run metadata | **Must be released** for auditability. |
| A7 | Noise seeds / PRNG state | Client process | Must **never** be released or logged. |
| A8 | Validation/test labels | Local only | Not transmitted. Used for checkpoint selection only. |

**Not an asset in this study:** raw ECG waveform, patient identity, hospital identity. The dataset
is public and contains no identifying information beyond record numbers already published.

## 4. Adversaries

### 4.1 In scope

| ID | Adversary | Capability | What it sees |
|---|---|---|---|
| **ADV-1** | **Honest-but-curious server** (DP) | Sees every client update in cleartext each round; follows the protocol; may attempt to infer training-set properties from updates | Full update vectors, round metadata, participation sets |
| **ADV-2** | **Honest-but-curious server** (HE) | Sees only ciphertexts and public metadata; does not hold the secret key | Ciphertexts, sizes, timing, round structure |
| **ADV-3** | **Colluding clients** (up to t) | Share their received global models and their own updates | Global model per round |
| **ADV-4** | **External observer** | Sees communication volume, timing and any released transcript | Sizes, timing, released metadata |
| **ADV-5** | **Key holder / decryptor (HE)** | Holds the CKKS secret key; sees the decrypted **aggregate every round** | Clean federated aggregate |
| **ADV-6** | **Audit-trail reader** (Phase 7 link) | Reads on-chain commitments | Hashes and metadata only |

### 4.2 Out of scope (explicitly, so no later claim drifts)

| ID | Out-of-scope threat | Reason |
|---|---|---|
| OUT-1 | **Malicious client** sending crafted updates to poison or to attack DP | Phase 8 topic (RQ5). Phase 6 assumes honest clients. |
| OUT-2 | **MPC-based secure aggregation** against a colluding server + clients | Not implemented; therefore client updates are visible between client and server. This is why DP is applied **client-side** before transmission. |
| OUT-3 | **Model extraction / inversion attacks** against the released final model | Not evaluated. Would require a separate study. |
| OUT-4 | **Side-channel attacks** against CKKS (timing, power, cache) | Out of scope; HE library assumed constant-behaviour as documented, not independently verified. |
| OUT-5 | **Compromise of the key holder** | Trust assumption §6: the decryptor is honest-but-curious, not compromised. |
| OUT-6 | **Real institutional governance / regulatory compliance** | Simulated clients from a public dataset are not independent hospitals. |
| OUT-7 | **Privacy of validation/test data** | Never leaves the process; not part of any released update. |

## 5. Privacy unit and adjacency — the central definition

### 5.1 Privacy unit: the CLIENT (institution slot)

**The privacy unit is one client's entire training dataset**, i.e. the set of records assigned to
that client. With five clients, this is a **five-unit** universe.

This is a deliberate and honest choice, not a convenience:

- The five clients are fixed and their record membership is **published** in the frozen manifests.
  A privacy guarantee that protected record membership would be meaningless because the
  membership is not secret.
- What DP can meaningfully protect in this setup is **whether a given client's data was used and
  what it contained**, i.e. participation and dataset-content influence on the released model.
- Defining the unit as a client makes the guarantee a **client-level (a.k.a. user-level) DP**
  guarantee, which is exactly what a naive "one hospital withdrew" adjacency models.

### 5.2 What this is NOT

It is **not** record-level DP and **not** patient-level DP. The mechanism adds one noise vector
per client per round; within a client, thousands of beats from several records contribute to the
same clipped update. Nothing in this design bounds the influence of an individual record or an
individual patient.

**Therefore this project must never claim:**
- "record-level differential privacy";
- "patient-level privacy";
- "protects individual ECG beats or patients";
- a HIPAA/GDPR-style guarantee.

Approved claim language is given in §9.

### 5.3 Adjacency relation

Two neighbouring client datasets `D_k` and `D'_k` are adjacent iff one client's dataset is
**replaced** by any other dataset of the **same cardinality** (`replace-one`, equal-cardinality
adjacency), with all other four clients held fixed.

- **Chosen:** `replace-one` with equal cardinality on a single client slot.
- **Not chosen:** add/remove adjacency.

**Formal definition, proof of sensitivity and the reason equal cardinality is required are in
[`PHASE_6_PRIVACY_MATHEMATICS.md`](PHASE_6_PRIVACY_MATHEMATICS.md) §2–4.** In summary:
`p_k = n_k / Σn` is data-dependent in the current implementation, so an adjacency that changed a
client's dataset *size* would leave the weighted release without a finite sensitivity. Fixing the
weights to the frozen public counts (identical arithmetic, because equal-cardinality replacement
leaves `n_k` unchanged) restores a valid derivation.

**Consequence that must be documented:** replace-one adjacency with a fixed, published client
set is a weaker privacy notion than add/remove in one specific respect — it does not hide
*presence* of a client, only the *content* of that client's contribution. This is stated again as
a limitation in §10.

### 5.4 Which information is protected

| Protected | Public |
|---|---|
| The contents of a client's dataset (which windows, which labels) | Client identities and count (`K = 5`) |
| The client's contribution to the released model | Participation schedule (all five every round) |
| | Client sizes `n_k` (published in the frozen manifest) |
| | Architecture, hyperparameters, `C`, `σ`, `ε`, `δ`, accountant |

**The guarantee covers the complete released transcript**, defined as the `R = 50` round models.
It does **not** extend to the 448 BatchNorm buffers (§5.5) or to inference against the final model
(out of scope, OUT-3).

### 5.5 Model components, and what is actually protected

| Component | Elements | DP-protected | HE-encrypted |
|---|---:|:---:|:---:|
| Trainable parameters | 36,357 | **Yes** | **Yes** |
| BatchNorm `running_mean`/`running_var` | 448 | **No — disclosed leak** | **No** |
| `num_batches_tracked` | 3 | No | No |

The 448 BatchNorm buffers depend on client data and are aggregated unnoised, exactly as in
Phase 5. This is the standard param-only DP compromise in FL, and it is a **residual leak of
activation-distribution statistics** that must appear in every privacy claim. Decision D5 in the
plan.

## 6. Trust assumptions

| Party | Trust level | Notes |
|---|---|---|
| Clients | **Honest** (semi-honest computation, no poisoning) | Poisoning is Phase 8. |
| Clients, DP noise generation | **Trusted to sample noise correctly** | A malicious client could omit noise. With no secure aggregation or central DP, *any* client can lie about its noise. This is a real limitation, not an assumption we can wave away — see OUT-2 and §10. |
| Server, DP | **Honest-but-curious** (ADV-1) | Must not be able to invert updates to recover client data beyond the DP guarantee. |
| Server, HE | **Honest-but-curious and key-blind** (ADV-2) | Does not hold the CKKS secret key. |
| HE key holder / decryptor | **Honest-but-curious, trusted for correctness, NOT trusted with privacy** (ADV-5) | Sees the clean aggregate. **CKKS does not hide the aggregate from the key holder.** This must never be claimed otherwise. |
| CKKS key distribution | Public key available to all clients; secret key held only by the decryptor | Key rotation/destruction policy stated per experiment. |
| PRNG | Seeded and reproducible **for research**, NOT cryptographically secure | A seeded research PRNG is not a CSPRNG. The study records this and makes no production-security claim. |
| Clock / network | Not modelled | Timing side channels out of scope (OUT-4). |

**Critical trust note for P3 (HE+DP):** the decryptor (ADV-5) sees the noisy aggregate every
round. Under client-side DP, the noise is already in the ciphertext, so the key holder learns only
the DP-protected aggregate — which is the intended design. But the key holder also sees the
aggregate **before** any post-processing that might shrink noise. That is acceptable only because
DP is applied before encryption; it is recorded so the transcript's trust boundary is explicit.

## 7. What each party sees — the released transcript

| Spectator | Per-round view | Final release |
|---|---|---|
| Client k | Global model, own data, own noise seed | Global model, metrics |
| Server (P1 DP-only) | **All client updates in cleartext, each already noised** | Aggregated model |
| Server (P2 HE-only) | Ciphertexts only, cannot decrypt | Cannot decrypt |
| Server (P3 HE+DP) | Ciphertexts containing noised updates | Cannot decrypt |
| Decryptor (P2/P3) | **Clean (P2) or noised (P3) aggregate plaintext each round** | Aggregate model |
| External observer | Ciphertext/update byte sizes, timing, round count | Published artefacts |
| Audit reader (Phase 7) | Commitments/hashes | Verification evidence |
| Anyone | ε, δ, C, σ, accountant name/version, participation plan, round count | Same |

**Public metadata (deliberately released):** number of clients, which clients participated in
which round, round count, model architecture, parameter count, ciphertext byte sizes, timings,
privacy parameters, checkpoint hashes.

## 8. Where noise is added — the information flow

The precise location of noise relative to clipping, encryption and aggregation determines whether
the guarantee is valid. For P1 and P3 the order is **fixed** as:

```
client k:  Δ_k = w_local - w_global
           Δ_k ← Δ_k / max(1, ||Δ_k||_2 / C)        (clip to L2 norm C)
           Δ̃_k = Δ_k + N(0, σ²C²I)                   (Gaussian noise)
P3 only:   c_k = CKKS_encrypt(Δ̃_k)
server:    aggregate (plaintext sum for P1; homomorphic sum for P3)
```

Noise is added **after** clipping and **before** encryption and aggregation. There is no
post-aggregation re-noising. This is what makes the accountant valid for client-level replace-one
adjacency with Gaussian noise. Any implementation that clips after aggregating, or noises the
aggregate centrally, is a **different mechanism** with a **different** guarantee and must be
re-accounted, not silently substituted.

## 9. Approved claim language

Only after results are in, and only if accounting is valid, the study may state (examples):

- "We evaluate **client-level** (user-level) differential privacy with replace-one adjacency,
  five clients, Gaussian mechanism with L2 clipping at C, and [accountant] reporting
  δ = [value] at ε = [value] over [R] rounds."
- "Homomorphic aggregation uses CKKS with the parameter set in Table [n]; the decryptor sees the
  plaintext aggregate, so CKKS provides no confidentiality against the key holder."

The study must **not** state (non-exhaustive):

- "record-level", "patient-level" or "beat-level" differential privacy;
- "formal DP guarantee" if the accountant's assumptions are not met (see the Phase 6 plan §6);
- "HE hides the model from the server" without saying which server role holds the key;
- "privacy-preserving" as a bare adjective without naming the unit, the adversary and the cost.

## 10. Limitations and residual risks carried into the thesis

1. **Replace-one, fixed published client set**: hides content, not the existence of a client.
2. **No secure aggregation**: a colluding server observes every noised client update individually,
   not just their sum. Correlated noise across clients is therefore not averaged out before the
   adversary sees it. Client-level DP with per-client noise still bounds each client's influence,
   but the adversary has strictly more information than under secure aggregation.
3. **The client is trusted to add its own noise.** Without secure aggregation or a trusted
   aggregator, a cheating client voids its own contribution's guarantee. This is documented, not
   solved.
4. **Five privacy units is a very small universe.** ε interpretation at n = 5 is coarse;
   user-level DP with five users is a weak practical guarantee even at moderate ε.
5. **DP protects the update channel, not the published model.** The final model is released; any
   inference from the model itself is out of scope.
6. **HE protects confidentiality against the key-blind server only.** The decryptor is trusted for
   privacy against itself, which is a contradiction if the decryptor is also the auditor — the
   experiment must state who the decryptor is per condition.
7. **CKKS approximation error is empirical**, measured on the actual tensors used; it is not a
   formal error bound.
8. **S-class limitation carries forward unchanged.** DP and HE may further reduce minority-class
   performance; any such result is reported, not hidden, and is not used to claim privacy
   mechanisms improve classification.

## 11. Decisions requiring research-lead approval before any implementation

| # | Decision | Recommendation | Why it matters |
|---|---|---|---|
| **TM-1** | Privacy unit = client slot (not record/patient) | **Approve client-level** | Defines every downstream claim; the alternative is not defensible with 5 fixed clients |
| **TM-2** | Adjacency = replace-one on one client, others fixed | **Approve replace-one** | Determines accountant compatibility |
| **TM-3** | Whether to add a *secondary* report-only analysis at the **client-distribution** level | **Approve as descriptive only**, never as formal DP | Gives the thesis something to say about skew without faking record-level DP |
| **TM-4** | Accept that no secure aggregation is in scope | **Approve, with limitation §10.2 recorded in every DP result** | Prevents an over-claim about what the server sees |
| **TM-5** | Accept decryption point = single trusted decryptor | **Approve** | Required for P2/P3; must be named per experiment |
| **TM-6** | Is the seeded research PRNG acceptable for *this* study? | **Approve for research only**; no production-security claim | Master spec §15.1 requires this to be stated |
| **TM-7** | Accept out-of-scope list OUT-1..7 | **Approve** | Prevents scope creep into Phases 7/8 |

**No Phase 6 implementation may begin until TM-1..TM-7 are resolved and this document is marked
APPROVED.**
