# Phase 9 — Combined Configuration and Threat Model

**Status:** written 18 November 2026 for G9. **Awaiting research-lead approval (P9-4).**
**Purpose:** define the *exact combined* configuration X1 and its threat model, as required by
master spec §28 Phase 9: *"Define the exact combined configuration and threat model."*
**Relationship to prior models:** this document composes, and does not replace,
`PHASE_6_PRIVACY_THREAT_MODEL.md` (DP/HE) and `docs/threat_model/SECURITY_THREAT_MODEL.md` (ledger).

---

## 1. The exact combined configuration

### 1.1 X1-a — FedAvg + L1 audit

| Element | Value | Source |
|---|---|---|
| Partition | F3 severe, `da8b96fa…` | frozen G3 |
| Clients | 5 (client_01…client_05) | frozen |
| Model | `compact_cnn_v1`, 36,357 trainable params | frozen |
| Rounds / epochs | 50 / 2 | frozen |
| Aggregation | FedAvg, sample-count weighted | G5 |
| Privacy mechanism | **none** | §2.1 |
| Encryption | **none** | — |
| Audit | L1 SHA-256 hash chain | G7 |
| Selection | validation macro-F1, round 0 evaluated, earliest on tie | frozen |

### 1.2 X1-b — FedAvg + CKKS HE + L1 audit

As X1-a, plus:
- CKKS, N = 8192, `[60,40,40,60]`, scale 2^40, 9 ciphertexts (G6 / D6);
- clients encrypt their updates; the server computes `Σ p_k · c_k` homomorphically;
- a decryptor holds the secret key and recovers the aggregate each round.

### 1.3 Explicitly not in the combined configuration

| Excluded | Reason |
|---|---|
| Robust aggregation (R1 rules) | G8 NOT PASSED; §37 forbids |
| R2 proposed aggregator | Not defined, not validated |
| DP | Recommendation 9-DP-a: mechanism validated, result negative |
| Attack conditions | Belong to the failed Phase 8 protocol |
| L2 contract | Available but not part of X1 by default |

---

## 2. What the combined configuration actually is

### 2.1 It has no differential privacy

This must be stated first because the thesis title contains "privacy-preserving".

| Mechanism | Provides DP? | Why |
|---|---|---|
| FedAvg | No | — |
| CKKS HE | **No** | Encryption is not a privacy guarantee; the decryptor sees plaintext |
| L1 hash chain | **No** | Tamper evidence; ledger is public-by-design |
| DP | **Not present** | Excluded (9-DP-a); its evaluation was negative |

**X1 provides no differential privacy guarantee of any kind.** The only privacy properties present
are:

1. **Encryption-in-transit confidentiality** of individual client updates against a key-blind server
   (X1-b only);
2. **Tamper evidence** of the training record (both variants).

Neither is a formal privacy guarantee about individuals or institutions.

### 2.2 What the "privacy-preserving" claim can support

The thesis may say: *"The framework evaluates privacy-preserving mechanisms (DP and HE) as
independent components; HE is deployable at low cost, DP is not viable at this client scale, and the
audit layer records training without exposing sensitive data."*

The thesis may **not** say that the integrated system is differentially private.

---

## 3. Threat model for the combined configuration

### 3.1 Assets

| ID | Asset | Present in X1? | Protection |
|---|---|---|---|
| A1 | Client dataset contents | — | **Unprotected** (no DP) |
| A2 | Individual client updates in transit | Yes | Encrypted (X1-b only) |
| A3 | The aggregated model | Yes | Public research artefact |
| A4 | Training record integrity | Yes | Hash chain (tamper-evident) |
| A5 | The final model checkpoint | Yes | Released; hash committed |
| A6 | Key material | X1-b | Held by decryptor; never written to artefacts |
| A7 | Identity of participating institutions | Yes | **Public** by frozen manifest |

### 3.2 Adversaries

| ID | Adversary | Sees | X1 response | Residual risk |
|---|---|---|---|---|
| **AX-1** | Honest-but-curious server (X1-a) | Every update in cleartext | **None** — no DP, no encryption | **Full exposure of client updates** |
| **AX-2** | Key-blind server (X1-b) | Ciphertexts only | CKKS confidentiality | Aggregates decryptable by the key holder |
| **AX-3** | Key holder / decryptor (X1-b) | Plaintext aggregate each round | **None** | Aggregate fully visible |
| **AX-4** | History-altering party | Off-chain logs | Hash chain detects interior alteration | **Consistent rewrite/truncation undetectable without the anchor** |
| **AX-5** | Curious auditor | Ledger | Nothing sensitive on-chain | None |
| **AX-6** | Malicious client | — | **Not addressed** | Poisoning is a Phase 8 problem; G8 failed |

### 3.3 The composition-specific risk (the reason this document exists)

Combining HE with a ledger creates a risk that neither component has alone:

> **The ledger records, in public and permanently, which client submitted which update hash in which
> round.** In X1-b, this means the *ciphertext* hash is public. That is harmless alone — a hash of a
> ciphertext reveals nothing. But it creates a **public, immutable participation timeline**.

| Risk | Mechanism | Mitigation in X1 |
|---|---|---|
| Participation inference | Anyone can see client_03 submitted in rounds 1–50 | **None** — participation is already public in the frozen manifest |
| Size inference | `update_bytes` is committed | Constant at 145,428 B (36,357 × 4), so it reveals nothing |
| Correlation over runs | Same client id + same run id across runs | Run ids are distinct per run; no linkage created |
| Future key compromise | If the CKKS secret key later leaks, ciphertext hashes become checkable against decrypted updates | **Real but out of scope**; key destruction policy not formalised |

**The fourth row is the genuine finding of this composition analysis.** A hash chain that is
tamper-evident and permanent converts a temporary confidentiality failure (key exposure) into a
*verifiable* one. This is not a defect in X1 — X1-b's decryptor already sees everything — but it
means the ledger makes key compromise more consequential, not less. It must be recorded as a
limitation of the combination.

### 3.4 Trust assumptions

| Party | Trust |
|---|---|
| Clients | Honest (poisoning out of scope) |
| Server (X1-a) | Honest-but-curious; **sees all updates** |
| Server (X1-b) | Honest-but-curious and key-blind |
| Decryptor | Trusted for correctness, **not** for privacy — it sees the aggregate |
| Ledger writer | Same party as the server; the anchor mitigates slightly |
| Anchor (committed head hash) | Trusted to be out-of-band |

### 3.5 Out of scope

Poisoning and Byzantine clients (Phase 8, failed); consensus and decentralisation (no blockchain);
record- or patient-level privacy (never claimed); key compromise; availability; clinical validity;
inference attacks against the released model.

---

## 4. Privacy boundaries in the combined system

| Data | Location | Protected by |
|---|---|---|
| ECG windows | Off-chain, never transmitted | — (never leaves the client process) |
| Raw client updates | In transit | **Nothing in X1-a**; CKKS in X1-b |
| Update hashes | On-chain | Public by design; reveal nothing alone |
| Model checkpoints | Off-chain, hash on-chain | — |
| CKKS secret key | In-process only | Never written to artefacts |
| Per-client diagnostics (clip norms, ε) | **Off-chain only** | Phase 6/7 prohibition, enforced by schema |

**The last row is enforced in code**, not merely documented: the Phase 7 schema rejects `clip_norm`
and per-client ε fields, and `tests/test_phase9_integration.py::test_it9...` re-checks it on
integrated ledgers.

---

## 5. Approved claim language for the combined configuration

**Permitted:**

- "X1-a records federated training in a tamper-evident hash chain with bit-identical model metrics to
  the unaudited baseline."
- "X1-b additionally encrypts client updates homomorphically; the CKKS approximation error was
  1.41e-07 and did not materially change metrics (Δ macro-F1 ≤ 5.2e-04)."
- "The combined configuration provides encryption-in-transit confidentiality (X1-b) and tamper
  evidence (both), and **no differential privacy**."
- "The ledger contains no waveform data, identifiers, model parameters, key material or per-client
  privacy diagnostics."

**Prohibited:**

- "The integrated system is privacy-preserving" without immediately qualifying that no DP is present;
- "differentially private federated learning" for X1;
- "blockchain" for the L1 hash chain;
- "Byzantine-robust" (G8 failed);
- any claim that HE protects against the key holder.

---

## 6. Approval

| Item | Status |
|---|---|
| Combined configuration defined | Yes (§1) |
| Threat model defined | Yes (§3) |
| Composition-specific risk identified | Yes (§3.3) |
| Privacy boundaries reviewed | Yes (§4) |
| **Research-lead approval (P9-4)** | **PENDING** |

Until approved, no text from §5 may enter the thesis.
