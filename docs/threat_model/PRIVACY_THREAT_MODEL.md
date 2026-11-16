# Privacy Threat Model

**Status:** **APPROVED** 16 November 2026 (research-lead decision G6-a).

The authoritative privacy threat model for this study is maintained at:

**[`../PHASE_6_PRIVACY_THREAT_MODEL.md`](../PHASE_6_PRIVACY_THREAT_MODEL.md)**

That document defines the assets, adversaries, trust assumptions, public metadata, privacy unit
(client slot), replace-one equal-cardinality adjacency, released transcript, approved claim
language, and out-of-scope threats. Decisions TM-1 through TM-7 were accepted as written on
16 November 2026.

This file exists because `MASTER_RESEARCH_EXECUTION_SPECIFICATION.md` §25 names this path. It is a
pointer, not a second specification; the two must not diverge.

## Key points carried forward

- **Privacy unit:** the client (institution slot), not a record, patient or heartbeat.
- **Adjacency:** replace-one with equal cardinality, other four clients fixed.
- **Not claimed:** record-level, patient-level or beat-level differential privacy.
- **CKKS** hides ciphertexts from the key-blind server; it does **not** hide the aggregate from the
  secret-key holder, and provides no integrity or authenticity.
- **No secure aggregation:** the server observes each client's noised update, so the per-client
  (view B) sensitivity `2C` is the honest accounting.
- **BatchNorm buffers (448 floats)** are neither DP-protected nor encrypted — a disclosed leak.
