# Phase 7 — Blockchain Audit: Results and Analysis

**Date:** 16 November 2026
**Status:** EXECUTION COMPLETE — **G7 assessment in §8**
**Conditions executed:** B0 (frozen baseline, reused), B1 (L1 hash chain), B2 (L2 Ganache contract)
**Scope of claim:** a **Level 1 tamper-evident log** and a **Level 2 single-node local EVM prototype**.
**Not claimed:** distributed blockchain, consensus, decentralisation, Byzantine resistance,
production cost, or any confidentiality guarantee.

---

## 0. Summary

| Condition | Audit layer | Test acc | Test macro-F1 | Ledger entries | Verify | Audit time | % of round time |
|---|---|---:|---:|---:|---|---:|---:|
| **B0** frozen baseline | none | 0.8728 | 0.3993 | — | — | — | — |
| **B1** hash chain (L1) | SHA-256 chain | **0.8728** | **0.3993** | 352 | **valid** | 0.401 s | **0.12 %** |
| **B2** Ganache (L2) | chain + contract | **0.8728** | **0.3993** | 352 | **valid** | 13.534 s | **4.03 %** |

**Audit neutrality is proven, not assumed.** All three conditions produce bit-identical test metrics
for the same seed. The audit layer changed nothing about training.

**A finding worth noting:** B1 and B2 produced the **same ledger head hash** (`ea4bc5ec…`). The two
audit layers therefore record identical evidence; what differs is *enforcement* (authorisation) and
*cost*, which is precisely what the B1-vs-B2 comparison was designed to isolate.

---

## 1. What was built

| Component | Path | Purpose |
|---|---|---|
| Closed-whitelist schema | `src/blockchain/schema.py` | Rejects anything outside the allowed field set |
| Commitments | `src/blockchain/commitments.py` | Canonical hashing, scaled privacy attestation |
| L1 ledger | `src/blockchain/ledger.py` | Append-only SHA-256 chain + verifier |
| L2 adapter | `src/blockchain/evm.py` | Ganache deployment, transactions, measurements |
| Contract | `contracts/AuditLog.sol` | Authorisation, commitments, replay rejection |
| Compiler | `tools/blockchain/compile.js` | Pinned solc 0.8.38, hashed ABI/bytecode |
| Runner | `scripts/run_phase7_audit.py` | Records a federated run into L1 and/or L2 |
| Tests | `tests/test_phase7_*.py` | 72 tests |

Toolchain pinned: **ganache 7.9.2**, **solc 0.8.38**, **web3 7.16.0**, Node 24.15.0.

---

## 2. Personal-information controls (the emphasis of this phase)

44 tests enforce the prohibition list from `SECURITY_THREAT_MODEL.md` §3.2. The design is a **closed
whitelist**, not a blacklist: unknown fields are rejected rather than ignored, because a blacklist
fails silently the first time someone invents a new field name.

| Control | Test | Result |
|---|---|---|
| Unknown field rejected | `test_unknown_field_is_rejected_not_ignored` | Pass |
| 25 prohibited field names rejected | `test_prohibited_field_names_are_rejected[25 cases]` | Pass |
| Model tensors rejected (numeric arrays) | `test_deep_scan_rejects_model_tensor_like_arrays` | Pass |
| Record numbers as values rejected | `test_identifier_that_looks_like_a_record_number_is_rejected` | Pass |
| Patient/record IDs as `client_id` rejected | `test_client_id_must_be_a_slot_label_not_a_record_number` | Pass |
| Per-client clipping norms rejected | prohibited-pattern test | Pass |
| Per-client ε contributions rejected | prohibited-pattern test | Pass |
| Keys, seeds, PRNG state rejected | prohibited-pattern test | Pass |
| Absolute paths with usernames rejected | `test_deep_scan_rejects_absolute_paths_with_usernames` | Pass |
| Floats rejected (ambiguous commitments) | `test_floats_are_rejected_in_favour_of_scaled_integers` | Pass |
| Booleans not accepted as integers | `test_booleans_are_not_accepted_as_integers` | Pass |

**What actually reached the ledger.** Inspection of the 352 B1 entries and 282 B2 transactions
confirms only: run id, four hashes, model arch id, seed, round index, participant-set hash, client
slot labels (`client_01`…`client_05`), update hashes, byte counts, model hashes, rule identifiers,
round indices and scaled privacy integers. No waveform, no record number, no tensor, no key, no
seed, no per-client diagnostic, no filesystem path.

---

## 3. Integrity and tamper evidence

### 3.1 What the chain detected

| Test | Injected change | Detected at index | Result |
|---|---|---|---|
| T1 | Alter fields of entry 0, 1, 7 or 19 | Exactly that index | **Pass** |
| T1 | Replace an entry hash directly | Entry 5 | **Pass** |
| T1 | Delete an interior entry 8 | Index 8 | **Pass** |
| T1 | Reorder entries 4 and 5 | Detected | **Pass** |
| Reopen tampered file for append | Refused with `LedgerError` | — | **Pass** |

### 3.2 What the chain did **not** detect — documented, not hidden

| Case | Outcome | Why |
|---|---|---|
| Truncate the last 10 of 20 entries | **Undetected** (chain still valid) | A shorter chain is internally consistent |
| Rewrite every entry consistently | **Undetected** without an anchor | The writer can recompute all hashes |

Both are detected **only** by comparing the head to an out-of-band anchor. `compare_to_anchor` is
implemented and tested; `anchor.json` is written per run. This limitation is a property of hash
chains, not a defect in this implementation, and is stated in `SECURITY_THREAT_MODEL.md` §6.2.

**Residual risk that remains:** with a single writer, an adversary who controls both the ledger and
the anchor can defeat both. The anchor's strength is the strength of repository review.

### 3.3 Contract-level integrity (L2)

| Test | Behaviour | Result |
|---|---|---|
| Authorised write | Succeeds | Pass |
| Unauthorised write (`registerRun`, `commitUpdate`) | Reverts, "not authorised" | Pass |
| Duplicate round opening | Reverts, "already opened" | Pass |
| Duplicate client commitment (replay) | Reverts, "duplicate client commitment" | Pass |
| Duplicate run registration | Reverts | Pass |
| Close round with no commitments | Reverts, "no commitments to close on" | Pass |
| Missing-commitment event with prior commits | Reverts | Pass |
| Commit into a closed round | Reverts | Pass |
| Revert reasons exposed | Specific, not generic | Pass |
| Privacy attestation single-use | Second call reverts | Pass |

---

## 4. Cost measurements

### 4.1 Gas per transaction (30 trials per event type)

| Event | n | Gas mean | Gas SD | Gas min | Gas max |
|---|---:|---:|---:|---:|---:|
| `RunRegistered` | 1 | 161,008 | — | 161,008 | 161,008 |
| `RoundOpened` | 30 | **79,093** | 0 | 79,093 | 79,093 |
| `UpdateCommitted` | 150 | **88,819** | 6,863 | 85,399 | 102,499 |
| `RoundClosed` | 30 | **84,500** | 0 | 84,500 | 84,500 |
| `CheckpointSealed` | 1 | 80,319 | — | 80,319 | 80,319 |
| Rejected transaction | 30 | 0 (reverts consume the call) | — | — | — |

**Gas is deterministic** for a given call; the `UpdateCommitted` spread comes from varying calldata
size. Total for a 50-round, 5-client run: **30,619,319 gas** across 282 transactions.

**Fee:** deliberately not converted to currency. Ganache has no meaningful price, and the master
spec forbids inventing one. Reporting gas alone is the honest choice; any fee figure would require a
stated gas price and must be labelled a local-environment estimate.

### 4.2 Latency

| Event | p50 (ms) | p95 (ms) | mean (ms) |
|---|---:|---:|---:|
| `RoundOpened` | 25.66 | 30.09 | 26.61 |
| `UpdateCommitted` (success) | 28.23 | 33.59 | 28.92 |
| `RoundClosed` | 27.93 | 32.23 | 28.37 |
| Rejected transaction | 8.69 | 9.42 | 8.73 |

Latency distributions are **not normal** (local EVM, instant mining), so p50/p95 are reported
alongside the mean. Rejections cost ~70 % less than successes, as they fail before state writes.

### 4.3 Throughput and storage

| Metric | Value |
|---|---|
| Serial throughput | **38.4 tx/s** (local, instant-mining, single client process) |
| On-chain payload per round | **≈112 bytes** (3 × 32-byte hashes + one uint64) |
| On-chain per 50-round run | **≈5.6 KB** |
| Off-chain per run | `audit_ledger.jsonl` ≈ 135 KB (352 entries) |
| Deployment | 1,528,541 gas; bytecode 6,798 bytes |

The throughput figure is a serial round-trip measurement on one host. It is **not** a network
throughput claim.

---

## 5. Audit neutrality (T13)

| Requirement | Result |
|---|---|
| B1 metrics bit-identical to B0 | **Yes** (0.8728 / 0.3993) |
| B2 metrics bit-identical to B0 | **Yes** (0.8728 / 0.3993) |
| Audit layer consumes training PRNG | **No** — no random call in the audit path |
| B1 and B2 record identical evidence | **Yes** — same head hash `ea4bc5ec…` |

This was a genuine risk: an audit hook that perturbed seeding would have changed every downstream
result in the thesis.

---

## 6. RQ4 — answerable findings

**RQ4:** *Can a blockchain-backed audit mechanism make federated training operations verifiable and
auditable, and what are its gas, latency, throughput, storage and operational costs?*

| Sub-question | Answer | Scope |
|---|---|---|
| Can training operations be made verifiable? | **Yes** — every round and client submission is committed and independently verifiable | L1/L2 |
| Can alteration be detected? | **Yes**, for interior entries, at the exact index | L1/L2 |
| Can truncation be detected? | **Only with an out-of-band anchor** | Limitation |
| Does the audit affect model quality? | **No** — bit-identical metrics | Measured |
| What does an on-chain audit cost? | **≈88k gas per client submission**, 30.6 M gas per 50-round run | Local EVM |
| What is the latency? | **≈28 ms p50** per transaction | Local EVM |
| What is the throughput? | **38.4 tx/s** serial | Local EVM |
| How much storage? | **≈112 B on-chain per round**; ≈135 KB off-chain per run | Measured |
| What does the contract add over hashing? | **Authorisation and replay rejection**; tamper evidence is identical | B1 vs B2 |
| What is the operational overhead? | **0.12 %** (L1) / **4.03 %** (L2) of round time | Measured |

**The central design finding:** hashing alone gives tamper evidence at **0.12 %** overhead. The
contract adds **authorisation and replay rejection** at **4.03 %** plus gas. Whether that 33×
trade is worth it depends entirely on whether the threat model requires rejecting unauthorised
writers — which, for a single-writer local chain, it mostly does not. That tension is a legitimate
research finding and should be reported as such rather than presented as an unambiguous win.

---

## 7. Limitations

1. **Level 2, not Level 3.** Single Ganache node; no consensus, no independent validators, no
   decentralisation. Every cost figure is a local-environment measurement.
2. **The writer is the adversary.** The party who could alter the record also writes the ledger.
   Tamper evidence is real but conditional on the anchor (§3.2).
3. **A hash proves consistency, not honesty.** Nothing here shows an update was computed correctly,
   from real data, or without poisoning.
4. **No confidentiality.** The ledger is public by design. Phase 6's CKKS does not extend to it.
5. **One seed, one partition.** Cost and neutrality were measured on F3 seed 42. Gas is
   deterministic, so cost generalises; latency and neutrality across seeds were not re-measured.
6. **Serial throughput.** 38.4 tx/s is one host, one client, instant mining — not a network figure.
7. **No gas-price assumption.** Deliberately omitted rather than invented; fees are not reported.
8. **S-class limitation carries forward.** Accuracy 0.8728 includes S recall 0.000; nothing in Phase
   7 concerns class S.
9. **µWS fallback.** Ganache warned that its native websocket binding is incompatible with Node 24
   and fell back to a JS implementation, with the note that performance may be degraded. Latency
   figures may therefore be conservative; gas is unaffected.
10. **Anchor is manual.** Publishing the head hash depends on a human committing it and on review.

---

## 8. G7 assessment

Master spec §29 requires for G7: *"Audit design and tests pass; costs measured."*

| G7 requirement | Status | Evidence |
|---|---|---|
| Audit design documented | **Pass** | `PHASE_7_READINESS_REPORT.md`; `SECURITY_THREAT_MODEL.md` approved |
| Audit tests pass | **Pass** | 72 Phase 7 tests; full suite 165 passed / 1 skipped |
| Tamper detection tested | **Pass** | T1 interior alteration, deletion, reordering; T2 truncation documented |
| Authorisation tested | **Pass** | T5/T6 |
| Replay/duplicate tested | **Pass** | T7 |
| Missing commitment tested | **Pass** | T8 |
| Audit reconstruction tested | **Pass** | T10 (chain verify + contract read-back) |
| Altered model hash tested | **Pass** | T9 |
| Contract failure behaviour tested | **Pass** | T11 |
| Costs measured | **Pass** | Gas, latency, throughput, storage (§4) |
| Local-chain limitations documented | **Pass** | §7, `SECURITY_THREAT_MODEL.md` §6 |
| Personal-information controls | **Pass** | 44 tests; §2 |
| Claim discipline enforced | **Pass** | §9 |

**G7: PASSED** — with the scope restriction that the implementation is Level 1 (hash chain) and
Level 2 (single-node local EVM), and that all costs are local-environment measurements.

### 8.1 What G7 does not certify

- That the mechanism is production-ready, decentralised or consensus-backed.
- That audited updates are honest or correct.
- That the ledger protects confidentiality.
- That the anchor is tamper-proof against a repository-level attacker.

---

## 9. Approved claim language for the thesis

**Permitted:**

- "A SHA-256 hash-chained audit log recorded all 50 rounds and 250 client submissions of a federated
  run, and independently verified; alteration of any interior entry was detected at the altered
  index."
- "A local smart-contract prototype on a single-node Ganache instance rejected unauthorised writers
  and replayed submissions at a measured cost of ≈89k gas and ≈28 ms per client submission."
- "The audit layer left model metrics bit-identical to the unaudited baseline."
- "The ledger contains only hashes, slot labels and small integers; no waveform data, patient or
  record identifiers, model parameters, key material or per-client privacy diagnostics."

**Prohibited:** "blockchain" unqualified; "consensus", "decentralised", "Byzantine-resistant";
"immutable" (use *tamper-evident*); "verifies updates are correct"; "encrypted on-chain"; any claim
of privacy, confidentiality or production cost.

---

## 10. Reproduction

```powershell
# Toolchain (pinned)
cd tools\blockchain; npm install
node compile.js

# Start the local chain
.\node_modules\.bin\ganache.cmd --server.port 8545 --chain.chainId 1337 --wallet.totalAccounts 10

# B1 then B2
.\.venv\Scripts\python.exe -m scripts.run_phase7_audit `
    --output-dir experiments/logs/phase7/b1_hash_chain --seed 42 --device cuda
.\.venv\Scripts\python.exe -m scripts.run_phase7_audit `
    --output-dir experiments/logs/phase7/b2_ganache --seed 42 --device cuda --use-contract
```

Tests: `.\.venv\Scripts\python.exe -m pytest tests -q` → **165 passed, 1 skipped**
(the skip is a CPU-only test; contract tests skip with a clear reason if Ganache is not running).

## 11. Artefacts

| Artefact | Path |
|---|---|
| B1 run + ledger + anchor | `experiments/logs/phase7/b1_hash_chain/seed_42/` |
| B2 run + ledger + contract evidence | `experiments/logs/phase7/b2_ganache/seed_42/` |
| Cost trials (30 per event) | `experiments/logs/phase7/cost_trials.json` |
| Compiled contract | `build/AuditLog.json` |
