# Phase 7 — Execution Status

**Last updated:** 16 November 2026
**Stage:** **COMPLETE. G7 PASSED** (Level 1 + Level 2 scope, costs measured).
**G4 / G5 / G6:** all passed (G4 and G6 with documented scope limits).
**Phase 8 (Robust aggregation):** not started.
**Claim level reached:** L1 hash-chained audit log + L2 single-node local EVM prototype.
**Claim level NOT reached:** L3 distributed permissionless/permissioned blockchain.

---

## 0. Where Phase 7 stands

| Item | State |
|---|---|
| Readiness report | Complete — `PHASE_7_READINESS_REPORT.md` |
| Security threat model | **Approved** — `docs/threat_model/SECURITY_THREAT_MODEL.md` |
| L1 hash chain | Implemented — `src/blockchain/ledger.py` |
| L2 contract | Implemented — `contracts/AuditLog.sol`, `src/blockchain/evm.py` |
| PII controls | Implemented — `src/blockchain/schema.py`, 44 tests |
| B1 run | Complete — F3 seed 42, 50 rounds, 352 ledger entries |
| B2 run | Complete — same, 282 contract transactions |
| Cost trials | Complete — 30 trials per event type |
| Test suite | **165 passed, 1 skipped** |
| Committed / pushed | **No** |

## 0.1 Headline results

| Condition | Test acc | Test macro-F1 | Audit time | % round time |
|---|---:|---:|---:|---:|
| B0 baseline | 0.8728 | 0.3993 | — | — |
| **B1** hash chain | 0.8728 | 0.3993 | 0.401 s | **0.12 %** |
| **B2** Ganache | 0.8728 | 0.3993 | 13.534 s | **4.03 %** |

Metrics are **bit-identical across all three**, proving audit neutrality. B1 and B2 produced the
same ledger head hash, so they record identical evidence; the contract adds authorisation and replay
rejection at 33× the overhead.

## 0.2 Cost summary (local Ganache 7.9.2, solc 0.8.38, single node)

| Metric | Value |
|---|---|
| Gas, `UpdateCommitted` | 88,819 mean (n=150) |
| Gas, `RoundOpened` | 79,093 (deterministic) |
| Gas, `RoundClosed` | 84,500 (deterministic) |
| Gas, 50-round 5-client run | 30,619,319 total |
| Latency, p50 | ≈28 ms |
| Throughput, serial | 38.4 tx/s |
| On-chain per round | ≈112 bytes |
| Off-chain per run | ≈135 KB |

Fee in currency is deliberately **not** reported: Ganache has no meaningful gas price and the master
specification forbids inventing one.

## 0.3 G7 position

| G7 requirement (master spec §29) | Status |
|---|---|
| Audit design documented and approved | **Pass** |
| Audit tests pass | **Pass** (72 Phase 7 tests) |
| Costs measured | **Pass** |
| Local-chain limitations documented | **Pass** |

**G7 PASSED.** See `PHASE_7_RESULTS_AND_ANALYSIS.md` §8, including §8.1 on what the gate does not
certify.

## 0.4 Personal-information controls

The research lead specifically required that personal information not leak. Enforcement is by test,
not by discipline:

- Closed-whitelist schema: unknown fields **rejected**, not ignored.
- 25 prohibited field-name patterns rejected (records, patients, subjects, sample counts, clipping
  norms, per-client ε, keys, seeds, symbols, tensors, paths, usernames).
- Numeric arrays > 8 elements rejected (blocks model tensors and update vectors).
- Values resembling MIT-BIH record numbers rejected.
- Floats rejected; only scaled integers for privacy parameters.
- Absolute filesystem paths rejected; `safe_basename` strips account names.
- 44 dedicated tests; see `tests/test_phase7_schema.py`.

Verified on the actual runs: the 352 ledger entries and 282 contract transactions contain only
hashes, client slot labels (`client_01`…`client_05`), small integers and identifiers.

## 0.5 Decisions resolved (from the readiness report)

| # | Decision | Resolution |
|---|---|---|
| P7-1 | Install Node/Ganache/solc | **Done** — pinned in `tools/blockchain/package.json` |
| P7-2 | Canonical serialisation; integers on-chain | **Done** — reuses `canonical_json_sha256` |
| P7-3 | Live wrapper vs post-hoc | **Live wrapper** implemented |
| P7-4 | Per-client `UpdateCommitted` granularity | **Done** — 5 tx/round |
| P7-5 | External head-hash anchor | **Done** — `anchor.json` per run |
| P7-6 | Attest ε, δ, σ, C only on-chain | **Done** — `privacy_attestation` |
| P7-7 | Contract seed count | 1 seed (gas is deterministic) |
| P7-8 | Write `SECURITY_THREAT_MODEL.md` | **Done and approved** |
| P7-9 | Gas price assumption | **Not reported** — gas only, fee omitted |

## 0.6 Next phase

Phase 8 (robust aggregation) is not started. It requires an approved adversary model
(`SECURITY_THREAT_MODEL.md` §4.2 provides the preparation) and fresh-seed evaluation.

**Nothing committed or pushed.**
