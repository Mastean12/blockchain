# Security Threat Model

**Status:** **APPROVED** 16 November 2026 (research-lead authorisation for Phase 7, decision P7-8).
**Scope:** malicious clients (Phase 8 preparation) and blockchain/audit assumptions (Phase 7).
**Companion documents:** `PHASE_6_PRIVACY_THREAT_MODEL.md` (DP/HE unit, adjacency, adversaries).
This document does not restate that model and must not contradict it.

---

## 1. Purpose and a hard boundary

This model separates two questions that are routinely conflated:

1. **Can a client make the model worse?** — an *integrity of training* question. Phase 8.
2. **Can a party change the training record without detection?** — an *integrity of evidence*
   question. Phase 7 (this document).

**A ledger answers question 2 only.** Recording a malicious update faithfully produces a perfectly
auditable record of an attack. Tamper evidence is not defence.

## 2. What Phase 7 can and cannot prove

| Property | Provided | Mechanism | Limit |
|---|---|---|---|
| Tamper evidence of recorded entries | **Yes** | SHA-256 hash chain; contract commitments | Conditional on an external anchor (§6.3) |
| Detection of alteration of an interior entry | **Yes** | Hash recomputation | — |
| Detection of consistent full-chain rewrite | **No** (without anchor) | — | Single writer can recompute from genesis |
| Detection of consistent truncation | **No** (without anchor) | — | Smaller chain is still internally valid |
| Submitter authorisation | **Partially** | Contract address allow-list | Only in L2; absent in L1 |
| Consensus / decentralisation | **No** | Single Ganache node | Out of scope |
| Update honesty or correctness | **No** | — | Hashing does not verify computation |
| Confidentiality of ledger contents | **No** | — | Ledger is public by design |
| Availability | **No** | — | DoS not evaluated |

## 3. Assets and the on-chain boundary

### 3.1 Assets protected by Phase 7 (evidential)

| ID | Asset | Protection |
|---|---|---|
| EA-1 | The record that a specific run used a specific configuration, split and client manifest | Commitment at run registration |
| EA-2 | The record that a specific client submitted an update for a specific round | Per-client commitment |
| EA-3 | The record that a specific global model was produced from those commitments | Round-close commitment |
| EA-4 | The record that a specific checkpoint was selected | Seal commitment |
| EA-5 | The privacy parameters actually used | Attestation digest |
| EA-6 | Ordering and completeness of rounds and participants | Chain order + participant-set checks |

### 3.2 Personal and sensitive information — prohibition list

**Nothing in this category may enter a commitment payload, an on-chain record, or an audit log.**
MIT-BIH records are public research data, but the project must behave as though they were not, and
must not create *new* linkage or inference surfaces.

| Prohibited item | Why | Enforced by |
|---|---|---|
| ECG waveform samples, window tensors | Raw health data | Schema validator rejects numeric arrays > 8 elements |
| Patient/subject identifiers | Direct identifier | Field-name rejection |
| MIT-BIH record numbers (`record_ids`, `101`, `232`, …) | Quasi-identifier; links a client to specific patients | Field-name rejection **and** value-scan for record-number patterns |
| Annotation symbols / beat labels | Beat-level health data | Field-name rejection |
| Per-client sample counts (`sample_count`, `n_k`) | Reveals client dataset size; in Phase 6 `p_k` is public by manifest, but the ledger must not become a second distribution point for it | Field-name rejection |
| Per-client clipping norms (`norm_before_clip`, `clip_norm`) | **Leaks information about an individual client's update**, which Phase 6 deliberately keeps off any public channel | Field-name rejection |
| Per-client ε contributions or noise magnitudes | Same — attributable to one client | Field-name rejection |
| Model parameter tensors, update vectors | Prohibited by master spec §18 | Numeric-array rejection |
| CKKS secret key, public context key material | Key material | Field-name rejection |
| DP noise seeds, PRNG state | Would destroy the DP guarantee if published | Field-name rejection |
| Absolute filesystem paths | Reveals username/machine (`C:\Users\<name>\…`) | Path normalisation; only basenames or hashes committed |
| Free-text fields | Unbounded channel for accidental leakage | Not permitted in on-chain schema |

**Design consequence.** The on-chain schema is a **closed whitelist of fields**, not an open
dictionary with blacklisted keys. Unknown fields are rejected rather than ignored. This is the only
reliable way to prevent gradual leakage.

### 3.3 Allowed on-chain fields (closed list)

`run_id`, `config_sha256`, `split_sha256`, `client_manifest_sha256`, `model_arch_id`, `seed`,
`round_index`, `participant_set_sha256`, `client_id`, `update_sha256`, `update_bytes`,
`global_model_sha256`, `aggregation_rule_id`, `selected_round`, `checkpoint_sha256`,
`epsilon_scaled`, `delta_scaled`, `sigma_scaled`, `clip_scaled`, `accountant_id`.

Every hash is 64 hex characters. Every identifier is a bounded enumeration or an integer.
`client_id` is the frozen manifest label (`client_01`…`client_05`), which is a **slot identifier, not
a patient identifier** — it identifies an institution position, and the mapping from slot to records
is already public in the frozen manifest and is deliberately **not** repeated on-chain.

## 4. Adversaries

### 4.1 In scope (Phase 7)

| ID | Adversary | Capability | Phase 7 response | Residual risk |
|---|---|---|---|---|
| **A7-1** | Curious auditor | Reads ledger | Nothing sensitive present | None, by construction |
| **A7-2** | History-altering server | Rewrites off-chain logs | Chain detects alteration of recorded entries | Full rewrite undetectable without anchor |
| **A7-3** | Unauthorised writer | Calls contract without permission | Access control reverts | None in L2; **absent in L1** |
| **A7-4** | Replay attacker | Resubmits an old submission | `(runId, round, clientId)` uniqueness | None |
| **A7-5** | Omitting client | Skips its commitment | `MissingCommitment`; close-round guard | Round cannot silently complete |
| **A7-6** | Model-substituting server | Aggregates something other than committed | Hash mismatch on read-back | Detection, not prevention |

### 4.2 Phase 8 adversary model — now specified elsewhere

The Phase 8 adversary model was approved on 16 November 2026 and lives in
[`../PHASE_8_ADVERSARY_MODEL.md`](../PHASE_8_ADVERSARY_MODEL.md). It supplies the seven §20
parameters this section previously deferred: fraction of malicious clients (f = 1 primary, f = 2
secondary), white-box rule knowledge, coordination, alteration target (updates only), no identity
control, static (non-adaptive) primary conditions, and the objective and success criterion.

Phase 7's role for Phase 8 remains **lexical**: it can record that client `client_03` submitted
update `0xabc…` in round 12. Whether that update was malicious is an aggregation question, answered
in the Phase 8 document.

### 4.3 Out of scope

Consensus attacks and forks (no consensus exists); 51 % attacks; eclipse attacks; ledger
confidentiality; key compromise; availability/DoS; production-network cost, energy or latency;
regulatory compliance; smart-contract upgrade governance (contract is immutable by design).

## 5. Trust assumptions

| Party | Trust | Notes |
|---|---|---|
| Aggregator/server | **Honest-but-curious, may attempt history alteration** | Motivating adversary for A7-2 |
| Clients | Honest for Phase 7 | Their honesty is a Phase 8 question |
| Ledger writer | Single party (server) in L1 and L2 | **This is the central weakness**; §6.3 |
| External anchor | Trusted to be out-of-band | A repository commit, under authorisation |
| Ganache node | Single local process | No independent validation |
| Clock/timing | Not modelled | Latency is measured, not trusted |

## 6. Security limitations stated plainly

### 6.1 The writer is the adversary

In both L1 and L2 the same party that could alter the training record is also the party that writes
the ledger. A ledger written entirely by the suspect proves little on its own. **This study must say
so.** The value of the layer is that it converts *silent* alteration into alteration requiring
*consistent recomputation*, which is expensive and detectable if any hash is published out of band.

### 6.2 Tamper evidence is conditional

Without an external anchor the evidence is: *"if the head hash you hold matches the chain, the chain
was not altered after you obtained the head hash."*

### 6.3 The anchor (decision P7-5, approved)

The final head hash is written to a file that is committed to the repository. This gives a genuine,
if manual, out-of-band anchor. Its strength is the strength of the repository history, which is
outside the writer's unilateral control only if commits are reviewed — a governance assumption that
must be stated, not assumed.

### 6.4 Gas is not price

Ganache gas is deterministic and useful for comparing operations. It says nothing about mainnet
cost. Any fee figure is labelled a **local-environment estimate**.

### 6.5 L1 has no authorisation

The hash chain cannot reject an unauthorised append; it can only make unauthorised appends visible.
Authorisation exists only in L2. This difference is exactly what the B1-vs-B2 comparison measures.

## 7. Approved claim language

**Permitted:**

- "A SHA-256 hash-chained audit log recorded every round and client submission, and alteration of
  any recorded entry was detected at the altered index."
- "A local smart-contract prototype on a single-node Ganache instance rejected unauthorised writers
  and duplicate submissions, at a measured gas cost of [value] per transaction in a local
  environment."
- "The ledger contains no waveform data, patient identifiers, model parameters, key material or
  per-client privacy diagnostics."

**Prohibited:**

- "blockchain" without qualifying it as a single-node local prototype;
- "consensus", "decentralised" or "Byzantine-resistant";
- "verifies that updates are correct/honest/uncorrupted" — it verifies *consistency with a
  commitment*;
- "immutable" — say *tamper-evident*;
- "encrypted on-chain" — nothing sensitive is on-chain, and the ledger is public;
- any claim that the ledger provides privacy or confidentiality.

## 8. Personal-information controls (summary)

| Control | Location |
|---|---|
| Closed-whitelist on-chain schema; unknown fields rejected | `src/blockchain/schema.py` |
| Field-name rejection for the §3.2 prohibition list | `src/blockchain/schema.py` |
| Numeric-array rejection (blocks tensors and update vectors) | `src/blockchain/schema.py` |
| Record-number pattern scan in string values | `src/blockchain/schema.py` |
| Path normalisation (no absolute paths, no usernames) | `src/blockchain/commitments.py` |
| Unit tests asserting every prohibition | `tests/test_phase7_schema.py` |
| Peer review of any schema change | Process |

Any proposed schema change that adds a field must be reviewed against §3.2 before merge. The test
suite is the enforcement mechanism, not the discipline of the implementer.

## 9. Approval

| Item | Status |
|---|---|
| Threat model written | 16 November 2026 |
| Research-lead approval | **APPROVED** 16 November 2026 (P7-8) |
| Constrains | All Phase 7 implementation and claims |
| Precedes | Phase 8 adversary model — **written and approved 16 Nov 2026** (\PHASE_8_ADVERSARY_MODEL.md\) |
