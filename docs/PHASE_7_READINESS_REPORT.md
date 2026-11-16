# Phase 7 — Blockchain Audit: Readiness Report

**Status:** READINESS REVIEW — **AWAITING RESEARCH-LEAD AUTHORISATION**. No code written, no
dependencies installed, no experiments executed, nothing committed.
**Date:** 16 November 2026
**Governing document:** `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` Part VII (§17–19), Phase 7 (§877), G7
**Gate state on entry:** G0–G6 passed (G4 with documented S-class defect, G6 with scope limits).
**Phase 7 is not started beyond this report.**

---

## 0. Executive summary

Phase 7 must establish whether federated training operations can be made **verifiable and
auditable**, and at what cost (RQ4). The work is *not* primarily about building a blockchain — it is
about defining precisely what is claimed, because the specification forbids the four most common
over-claims in this literature.

The single most important finding of this review: **the existing pipeline already produces
cryptographic commitments for every artefact that matters** (config, split, client manifest,
preprocessing report, checkpoint, per-round bytes). Phase 7 therefore does not need to invent
integrity data — it needs to **anchor the existing commitments in a tamper-evident structure** and
measure the cost of doing so.

| Question | Answer |
|---|---|
| Where does blockchain integration belong? | A new `src/blockchain/` audit layer wrapping `run_federated`, not inside it |
| What is the minimum viable claim? | Tamper-evident audit log (Level 1) — achievable and honest |
| Is a hash chain a blockchain? | **No.** It is a tamper-evident log. Must not be called a blockchain (§1) |
| Is Ganache a production blockchain? | **No.** Local EVM; tests contracts and gas, nothing else (§1) |
| Blocking decisions | 9, listed in §11 |

---

## 1. Claim discipline — the four prohibitions

The specification (§17) and the directive both forbid specific over-claims. These are restated as
**hard rules** that every Phase 7 artefact must satisfy.

### 1.1 Three distinct levels — claim only the one implemented

| Level | What it is | What it proves | What it does **not** prove |
|---|---|---|---|
| **L1 — Hash-chained audit log** | Sequential SHA-256 chain over round records in a local file | That a recorded entry has not been altered without breaking the chain | Consensus, distributed trust, authorisation, availability |
| **L2 — Local smart-contract prototype** | Contract deployed to a local Ganache EVM | Contract logic correctness; gas and latency in a simulated EVM | Public network cost, independent validators, real decentralisation |
| **L3 — Distributed permissioned blockchain** | Multiple independent nodes with consensus | Meaningful tamper resistance under a stated trust model | *(Out of scope for this study)* |

**This study can reach L2 at most, on a single-machine Ganache instance.** L3 requires multiple
hosts and is out of scope. No result may be written as if L2 were L3.

### 1.2 A hash proves integrity, not honesty

> A SHA-256 commitment proves that the bytes presented match the bytes committed.
> It does **not** prove the update was computed correctly, honestly, from real data, without
> poisoning, or with any clinical validity.

Phase 7 can therefore prove: *"the model that was aggregated is the model whose hash was
committed"*. It **cannot** prove: *"the client computed that update honestly"*. That is Phase 8
(robust aggregation), and even there only statistically.

### 1.3 Tamper evidence ≠ consensus ≠ authorisation ≠ confidentiality

These are four independent properties and the report must never conflate them.

| Property | Provided by Phase 7? | Mechanism |
|---|---|---|
| **Tamper evidence** | **Yes** (L1/L2) | Hash chain; contract-stored commitments |
| **Consensus** | **No** | Single Ganache node; no independent validators |
| **Authorisation** | **Partially** (L2 only) | Contract access control by address |
| **Confidentiality** | **No** | On-chain data is public by design; confidentiality is Phase 6's CKKS, and that does not extend to the ledger |

### 1.4 What must never go on-chain

Explicitly prohibited (§18), and consistent with the Phase 6 threat model:

- raw ECG waveforms or any window data;
- patient identifiers or record-number *membership* (record IDs are published in manifests, but the
  on-chain record must reference hashes, not lists);
- model parameter tensors or update vectors;
- CKKS secret keys, DP noise seeds, or any PRNG state;
- private per-client sample counts or label distributions.

**Additional subtlety found in review.** The DP accounting uses **client-level sensitivity `2C`**
because each client's noised update is individually visible to the server. Publishing per-client
update hashes on-chain is fine (a hash reveals nothing), but publishing per-client *epsilon
contributions* or *clipping norms* would leak information about individual client updates. Phase 6
already records these **off-chain** in `run_summary.json`; they must stay there.

---

## 2. Existing system architecture

### 2.1 What exists now

```
configs/models/phase4_cnn_v1.yaml          frozen recipe (36,357-param CNN)
configs/federated/*.yaml                   F1-F5 federated conditions
configs/privacy/*.yaml                     P1-ctl, P1-a..d, P2, P3-a/b
data/splits/                               frozen manifests (G3)
src/models/cnn1d.py                        CompactECGCNN
src/federated/fedavg.py                    run_federated: the round loop
src/privacy/                               clipping, dp_mechanism, he_ckks, dp_federated
src/training/phase4.py                     load_config, evaluate_model, _sha256_file
src/evaluation/phase4_metrics.py           support-aware metrics
scripts/run_phase4|5|6_*.py                CLIs
experiments/logs/phase{4,5,6}/             run_metadata, rounds, run_summary, checkpoints
src/blockchain/__init__.py                 PLACEHOLDER (one docstring line)
configs/blockchain/                        DOES NOT EXIST
```

### 2.2 Where blockchain integration belongs

**It does not belong inside `run_federated`.** That function's behaviour underlies the frozen
Phase 5 results and must not change (§9 integrity requirement).

The integration point is a **new audit layer** that observes the round loop:

```
scripts/run_phase7_audit.py
        │
        ├── src/blockchain/ledger.py        L1 hash-chained append-only log
        ├── src/blockchain/commitments.py   canonical serialisation + SHA-256 commitments
        ├── src/blockchain/verifier.py      independent reconstruction/verification
        └── src/blockchain/evm.py           L2 Ganache adapter (optional condition)
                │
                └── contracts/AuditLog.sol
```

The layer subscribes to round events. To avoid modifying `fedavg.py`, Phase 7 should either
(a) re-implement the round loop as in the A1/A2 ablations — already an established, approved pattern
in this repository — or (b) consume existing `rounds.json` artefacts post hoc. Option (a) is
recommended for live measurement; option (b) is sufficient to prove verification works on the
already-frozen Phase 5 runs.

### 2.3 Commitments that already exist

This is the most important architectural finding. From inspection of
`experiments/logs/phase5/f3/seed_42/run_metadata.json` and `run_summary.json`:

| Commitment | Already computed? | Where |
|---|---|---|
| `config_sha256` | **Yes** | `run_metadata.json` |
| `split_manifest_sha256` | **Yes** | `run_metadata.json` |
| `client_manifest_sha256` | **Yes** | `run_metadata.json` |
| `preprocessing_report_sha256` | **Yes** (Phase 4) | `run_metadata.json` |
| `checkpoint_sha256` | **Yes** | `run_summary.json` |
| Round byte counts (`bytes_up`, `bytes_down`) | **Yes** | `rounds.json` |
| `aggregation_weights` per round | **Yes** | `rounds.json` |
| Privacy parameters (ε, δ, σ, C) | **Yes** (Phase 6) | `run_summary.json` |
| HE parameters and ciphertext sizes | **Yes** (Phase 6) | `run_summary.json` |

**Missing** (must be added by Phase 7): per-round **global model hash** and per-client **update
commitment** at the moment of submission. Both are cheap.

---

## 3. Audit events and metadata

### 3.1 Event taxonomy

| ID | Event | When | On-chain? | Content |
|---|---|---|---|---|
| **E0** | `RunRegistered` | Run start | **Yes** | run_id, config_sha256, split_sha256, client_manifest_sha256, model_arch_id, seed |
| **E1** | `RoundOpened` | Round start | **Yes** | run_id, round_index, participant_set_hash |
| **E2** | `UpdateCommitted` | Client submits | **Yes** | run_id, round, client_id, update_sha256, bytes, method_flag |
| **E3** | `RoundClosed` | After aggregation | **Yes** | run_id, round, global_model_sha256, aggregated_from (root of E2 hashes), aggregation_rule_id |
| **E4** | `RoundSkipped` / `MissingCommitment` | If a client fails to commit | **Yes** | run_id, round, expected vs received participant set |
| **E5** | `CheckpointSealed` | On selected checkpoint | **Yes** | run_id, selected_round, checkpoint_sha256 |
| **E6** | `PrivacyAttested` | Run end | **Yes** (digest only) | run_id, ε, δ, σ, C, accountant_id, privacy_unit_id |
| **E7** | Per-round metrics, loss, timings | Per round | **No** | Off-chain `rounds.json` |
| **E8** | Per-client norms, clipping stats | Per client-round | **No** | Off-chain (Phase 6 leak concern, §1.4) |
| **E9** | Full model weights, checkpoint files | Continuous | **No** | Off-chain filesystem, hash only on-chain |

### 3.2 Canonical serialisation (must be specified before implementation)

Commitments are only meaningful if the hashed bytes are canonical. The repository already does this
for manifests (`_canonical_bytes`: `json.dumps(sort_keys=True, separators=(",",":"))`,
UTF-8). Phase 7 must reuse **exactly that convention** for audit records, and must state:

- key ordering: lexicographic, sorted;
- separators: `,` and `:` with no spaces;
- encoding: UTF-8, no BOM;
- number formatting: must be pinned (integers vs floats — floats are a commitment hazard);
- no timestamps inside committed payloads (they belong in the envelope, not the commitment).

**Open decision P7-2 (§11).** Float formatting is a genuine risk: `0.1` vs `0.10000000000000001`
would produce different hashes for semantically identical records.

### 3.3 What the ledger must never contain

Restating as a testable rule, because it is the most likely violation:

| Prohibited | Detection test |
|---|---|
| ECG samples, window tensors | Schema rejects any field >64 bytes that is not a hash |
| Record IDs / patient IDs | Schema rejects `record_ids`, `symbols`, `subject` fields |
| Model parameters | Schema rejects arrays of numerics >8 elements |
| CKKS secret key, DP seed, PRNG state | Schema rejects fields matching `secret|seed|key|nonce` unless whitelisted |
| Per-client epsilon or clipping norms | Schema rejects `clip_norm`, `norm_before_clip` in on-chain payloads |

A **schema validator with these rejection rules** should be a mandatory unit test (§10.3).

---

## 4. On-chain vs off-chain boundary

| Data | Location | Justification |
|---|---|---|
| Commitments (E0–E6) | **On-chain** | Small, non-sensitive, and the point of the audit |
| Full model updates | Off-chain | Tens of kilobytes each; prohibited content |
| Global model checkpoints | Off-chain, hash on-chain | Large; needs confidentiality |
| Per-round metrics and losses | Off-chain, root hash on-chain | Size |
| Per-client privacy diagnostics | Off-chain | §1.4 leak concern |
| Run configuration (full YAML) | Off-chain, hash on-chain | Size |
| Datasets, splits, manifests | Off-chain (frozen), hash on-chain | Size and licence |

**Storage estimate.** Per round, on-chain payload is ~6 fields of ≤66 bytes (hashes) plus small
integers: **< 400 bytes per round, ~20 KB per 50-round run**. Off-chain, the existing
`rounds.json` is roughly 3–8 KB per run. Phase 7 therefore moves a negligible fraction of data
on-chain — which is the correct design, and should be reported as such.

---

## 5. Proposed ledger architecture

### 5.1 Two conditions, both required

| ID | Condition | Level | Purpose |
|---|---|---|---|
| **B0** | No audit (baseline) | — | Frozen Phase 5/6 results; reference for overhead |
| **B1** | Hash-chain audit log | **L1** | Tamper-evident record; near-zero overhead |
| **B2** | Ganache smart contract | **L2** | Authorisation tests and real gas/latency measurement |

Both B1 and B2 are needed: B1 is the honest baseline the specification says to "retain", and B2 is
what provides measurable transaction costs. Comparing B1 to B2 isolates *what the contract adds* —
authorisation and gas — from *what hashing alone gives*, which is tamper evidence. That comparison
is itself a finding.

### 5.2 L1 — hash chain

```
record_n = { "payload": <canonical audit record>,
             "prev_hash": H(record_{n-1}),
             "hash": H(canonical(payload) || prev_hash) }
```

- Append-only file, one JSON object per line (JSONL) for streaming and recovery.
- Genesis record with `prev_hash = 0x00…00`.
- Verification: recompute every hash; report the **first index of divergence**.
- Truncation is detectable only if a head hash is published elsewhere — this is a **real limitation**
  and must be stated: a hash chain alone cannot detect a consistent truncation, only an alteration
  or an interior deletion.

### 5.3 L2 — AuditLog contract

Minimum viable functionality, deliberately small:

| Function | Purpose |
|---|---|
| `registerRun(runId, configHash, splitHash, clientManifestHash)` | One per run; rejects duplicate `runId` |
| `openRound(runId, round, participantSetHash)` | Rejects if round already open/closed |
| `commitUpdate(runId, round, clientId, updateHash)` | Only from an authorised address; rejects duplicates |
| `closeRound(runId, round, globalModelHash, aggregationRuleId)` | Rejects if round not open, or if participant set incomplete |
| `sealCheckpoint(runId, selectedRound, checkpointHash)` | One per run |
| `attestPrivacy(runId, epsScaled, deltaScaled, sigmaScaled, clipScaled, accountantId)` | Stores a **digest**, not free text; scaled integers to avoid float hashing |
| `getRound(runId, round)` / `verifyRun(runId)` | Read-only reconstruction |

**Design notes.** Integers only (scaled where needed) because EVM has no float type — this neatly
solves the float-canonicalisation hazard of §3.2 for on-chain data. Access control via a simple
allow-list mapping; no upgradeability, no token, no economic mechanism.

### 5.4 Justification

A single-node Ganache chain is chosen **because the specification permits it and forbids claiming
more**. Running multiple real nodes would add operational cost without changing what can honestly be
concluded, since the study is not evaluating consensus. The contract is kept deliberately minimal so
that gas numbers are interpretable per-operation rather than swamped by unrelated logic.

---

## 6. Threat model

Master spec §25 requires `docs/threat_model/SECURITY_THREAT_MODEL.md`, which is **currently a
placeholder**. Phase 7 depends on it. Summary of what it must contain, and the Phase 7-specific
adversaries:

### 6.1 Adversaries in scope

| ID | Adversary | Capability | Phase 7 response |
|---|---|---|---|
| **A7-1** | Curious auditor | Reads ledger | Ledger is public; nothing sensitive on it |
| **A7-2** | Server that alters history | Rewrites off-chain logs after the fact | Chain/contract detects alteration of recorded entries |
| **A7-3** | Unauthorised writer | Calls contract without permission | Access control rejects; **tested** |
| **A7-4** | Replay attacker | Resubmits an old round submission | Duplicate rejection; **tested** |
| **A7-5** | Client that omits its commitment | Skips submission | `MissingCommitment` event; round policy enforced; **tested** |
| **A7-6** | Server that substitutes a model | Aggregates something other than what was committed | Model hash mismatch detectable; **tested** |

### 6.2 Out of scope — stated to prevent drift

| Out-of-scope | Reason |
|---|---|
| Malicious client poisoning | Phase 8 |
| Consensus attacks (51 %, forks) | Single node; no consensus to attack |
| Ledger confidentiality | Publicly readable by design |
| Key compromise | Phase 6 trust model |
| Availability / DoS | Not evaluated |
| Production network cost or energy | Local Ganache is not evidence of these |

### 6.3 The honest limit

**A7-2 is only partially addressed.** If the server controls the ledger writer and the chain has one
node, it can in principle rewrite the entire chain from genesis and recompute all hashes
consistently. Detection then depends on a **head hash being published somewhere the server does not
control**. This study should either (a) publish the final head hash in the repository/commit, giving
a real (if manual) external anchor, or (b) state plainly that tamper evidence is **conditional on
the anchor**. Option (a) is recommended and cheap.

---

## 7. Smart-contract functionality required

Derived from §18's twelve required questions:

| Spec question (§18) | Design answer |
|---|---|
| Who may submit? | Allow-listed addresses: 1 aggregator + 5 clients |
| Identity/authentication | Address allow-list; no PKI, no signatures beyond `msg.sender` |
| What is committed before aggregation? | Per-client `update_sha256` (E2) |
| How are commitments verified? | Off-chain recompute; on-chain read-back comparison |
| What is recorded after aggregation? | `global_model_sha256` (E3) |
| How are global model hashes calculated? | SHA-256 over canonical state-dict serialisation (must be pinned) |
| Invalid/missing client commitments? | `RoundClosed` requires the full expected participant set; otherwise `MissingCommitment` |
| Replay/duplicate/unauthorised rejection | `require` guards on `(runId, round, clientId)` uniqueness and sender role |
| Server/client disagreement | Both hashes are on-chain; disagreement is **detectable**, not resolved |
| Independent verification | `verifyRun` read path plus off-chain `verifier.py` |
| What stays off-chain | Everything in §4 |

**Explicit non-goal:** the contract does **not** verify that an update is *correct*. It records that
a specific hash was submitted by an authorised party at a specific round. That is all a ledger can
do without executing the training.

---

## 8. Experimental conditions and metrics

### 8.1 Conditions

| ID | Condition | Audit | Purpose |
|---|---|---|---|
| B0 | Frozen FedAvg (F3, 5 seeds) | None | Baseline — **already measured**, no re-run needed |
| B1 | FedAvg + hash-chain audit | L1 | Overhead of pure tamper evidence |
| B2 | FedAvg + Ganache contract | L2 | Authorisation + real gas/latency |

B1 and B2 must produce **identical model results** to B0 for the same seed. Any accuracy difference
would indicate the audit layer perturbed training — itself a reportable defect, and a required test
(§10.2).

### 8.2 Metrics

**Integrity and auditability**

| Metric | Definition |
|---|---|
| Tamper detection rate | Fraction of injected alterations detected (100 % required) |
| Detection localisation | Whether the first divergent index is correctly identified |
| Verification time | Full-chain verification wall-clock |
| Reconstruction fidelity | Whether an independent verifier reproduces every commitment |
| Unauthorised-write rejection | Pass/fail per test case |

**Cost (spec §19, all required)**

| Metric | Unit |
|---|---|
| Gas per transaction, per event type E0–E6 | gas |
| Gas price assumption | gwei (stated, not invented) |
| Estimated fee in the Ganache environment | wei / ETH-equivalent |
| Transaction latency | ms, per event type |
| Throughput | transactions/second, measured over repeated trials |
| On-chain storage | bytes per round/run |
| Off-chain storage | bytes, B0 vs B1 vs B2 |
| Validation/verification time | ms |
| Failed transaction rate | fraction |
| **Headline overhead** | audit time as a % of round time (baseline ≈6.3 s/round) |

**Required environment record:** Ganache version, chain id, block time / `--blockTime` setting, gas
limit, machine, number of trials. Specifications forbid inventing these.

### 8.3 Trial design

Per-event-type measurements over **≥ 30 repetitions** to report mean, SD and range — not a single
transaction. Latency distributions in a local EVM are not normal; median and IQR must be reported
alongside the mean.

---

## 9. Reproducibility and required tests

### 9.1 Tests that must exist before any measurement is reported

| # | Test | Pass criterion |
|---|---|---|
| T1 | Chain integrity | 1,000 valid records verify; a single-byte alteration at any index is detected at that index |
| T2 | Truncation behaviour | Truncation is **undetected** without an anchor — the test must **document this limitation**, not hide it |
| T3 | Canonical serialisation | Same semantic record → same hash across key order, whitespace and process restarts |
| T4 | Float hazard | Documents that `0.1` and `0.10000000000000001` differ; asserts on-chain path avoids floats |
| T5 | Authorised write | Allow-listed address succeeds |
| T6 | Unauthorised write | Non-allow-listed address reverts |
| T7 | Replay rejection | Duplicate `(runId, round, clientId)` reverts |
| T8 | Missing commitment | `closeRound` reverts when the participant set is incomplete |
| T9 | Altered model hash | Tampered `globalModelHash` fails verification |
| T10 | Audit reconstruction | Independent verifier reproduces every commitment from off-chain artefacts |
| T11 | Contract failure/revert behaviour | Revert reasons are asserted, not merely "it failed" |
| T12 | **No-sensitive-data** | Schema validator rejects ECG, record IDs, tensors, keys, seeds, per-client norms |
| T13 | Audit neutrality | B1/B2 model metrics are bit-identical to B0 for the same seed |
| T14 | Existing suite | All 93 existing tests continue to pass |

### 9.2 Reproducibility requirements

- Ganache version pinned in `requirements-lock.txt` (currently **not installed** — see §11, P7-1).
- Contract compiled with a pinned solc version, ABI and bytecode hashed into the run metadata.
- Chain state export (JSON snapshot) retained per condition so costs can be re-verified.
- Seeds unchanged from Phase 5 (42–46); audit layer must not consume the PRNG.
- Determinism caveat: Ganache block timestamps vary, so **gas is deterministic, latency is not**.

---

## 10. Dependencies, risks and unresolved decisions

### 10.1 Dependencies

| Dependency | Status | Note |
|---|---|---|
| Frozen Phase 5/6 results | **Available** | Baseline B0 needs no re-run |
| Existing commitments | **Available** | §2.3 |
| `docs/threat_model/SECURITY_THREAT_MODEL.md` | **PLACEHOLDER** | Must be written and approved before implementation |
| `src/blockchain/` | Placeholder | To be implemented |
| `configs/blockchain/` | **Does not exist** | To be created |
| Node/Ganache/solc | **Not installed** | Requires authorisation (P7-1) |

### 10.2 Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Claiming L2 is a blockchain | **High — integrity** | §1.1 language fixed in advance |
| Hash chain presented as consensus | **High** | §1.3 explicit table |
| Sensitive data on-chain | **High** | T12 schema validator enforced in tests |
| Server rewrites whole chain | Medium | External head-hash anchor (§6.3) |
| Float canonicalisation mismatch | Medium | Integers only on-chain; T4 |
| Ganache gas not representative of public networks | Medium | State plainly; no extrapolation |
| Audit layer perturbs training | Medium | T13 neutrality test |
| Truncation undetectable | Medium | T2 documents it; anchor mitigates |

### 10.3 Unresolved design decisions requiring approval

| # | Decision | Recommendation |
|---|---|---|
| **P7-1** | Authorise installing Node.js + Ganache + solc into the project environment | Approve; pin versions, record in lockfile |
| **P7-2** | Canonical serialisation: reuse `_canonical_bytes`, integers only for on-chain values | Approve |
| **P7-3** | Live audit wrapper (re-implement round loop) vs post-hoc replay of `rounds.json` | **Both**: post-hoc proves verification, live proves overhead |
| **P7-4** | Contract event granularity: per-client `UpdateCommitted` (5 tx/round) vs one batched `RoundClosed` | Per-client — required to detect a single missing client |
| **P7-5** | External head-hash anchor: publish final hash in the repository commit | **Approve** — otherwise tamper evidence is conditional |
| **P7-6** | Which privacy metadata is attested on-chain (ε, δ, σ, C only) | Approve; keep per-client stats off-chain |
| **P7-7** | Whether B2 runs all 5 seeds or 1 seed for cost measurement | 1 seed for cost (gas is deterministic); 5 seeds only if latency statistics require it |
| **P7-8** | Write `SECURITY_THREAT_MODEL.md` as a Phase 7 deliverable | Approve; it is a hard prerequisite |
| **P7-9** | Gas price assumption to report fees | State the Ganache default and **label the fee as a local-environment estimate**, not a market price |

---

## 11. What Phase 7 will and will not claim

**Will claim (if results support):** "A hash-chained audit log makes the recorded federated training
transcript tamper-evident, and a local smart-contract prototype enforces submitter authorisation and
records verifiable commitments at measured gas and latency costs in a single-node Ganache
environment."

**Will not claim:**
- that a hash chain is a distributed blockchain;
- that Ganache measurements are production costs;
- that hashing proves update honesty or correctness;
- that the ledger provides confidentiality;
- that consensus, decentralisation or Byzantine resistance were evaluated;
- any clinical validity from auditability.

---

## 12. Stop point

Stage A of Phase 7 ends here. Nothing installed, implemented, executed, committed or pushed.

**Awaiting research-lead authorisation on P7-1 … P7-9 and on writing
`docs/threat_model/SECURITY_THREAT_MODEL.md` before any implementation begins.**
