"""Commitment construction for Phase 7 audit records.

Canonicalisation reuses the repository's existing convention
(``src.data.phase3_pipeline.canonical_json_sha256``): ``json.dumps(sort_keys=True,
separators=(",", ":"))`` encoded as UTF-8. Reusing it means audit commitments and the frozen
manifest commitments are computed the same way, so a verifier needs one rule, not two.

Two hazards are handled explicitly:

1. **Floats.** A float commitment is ambiguous (``0.1`` vs ``0.10000000000000001``). Audit payloads
   reject floats entirely; privacy parameters are committed as scaled integers.
2. **Paths.** A model checkpoint path contains the machine's username. Commitments never include
   paths; callers pass a basename or a hash.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from src.blockchain.schema import (
    AuditSchemaError,
    ValidatedRecord,
    assert_no_sensitive_payload,
    validate_event,
)
from src.data.phase3_pipeline import canonical_json_sha256

# Fixed scale for privacy parameters. 1e-9 resolution is far finer than any epsilon or delta this
# study reports, and keeps every value inside a 256-bit EVM integer.
PRIVACY_SCALE = 1_000_000_000


class CommitmentError(ValueError):
    """Raised when a commitment cannot be formed safely."""


def canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    """The single canonical encoding used for every Phase 7 commitment."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def commitment(payload: Mapping[str, Any]) -> str:
    """SHA-256 over the canonical encoding.

    Guards the payload against sensitive content before hashing, so that a prohibited field cannot
    be committed even accidentally.
    """
    assert_no_sensitive_payload(dict(payload))
    digest = canonical_json_sha256(dict(payload))
    if digest != hashlib.sha256(canonical_bytes(payload)).hexdigest():
        raise CommitmentError("Canonical hashing disagreed with the shared implementation")
    return digest


def safe_basename(path: str | Path) -> str:
    """Reduce a path to a bare filename.

    Absolute paths embed the account name (``C:\\Users\\<name>\\...``), which is personal data. Only
    the basename may ever be referenced in audit metadata.
    """
    name = Path(path).name
    if not name:
        raise CommitmentError("Path has no basename")
    if len(name) > 128:
        raise CommitmentError("Basename exceeds 128 characters")
    return name


def file_commitment(path: str | Path) -> str:
    """SHA-256 of a file's bytes, without recording the path."""
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def participant_set_commitment(client_ids: Iterable[str]) -> str:
    """Commitment over a set of client slot labels.

    Sorted so that participant order cannot alter the commitment, and validated as client slots so
    that a record or patient identifier cannot be smuggled in here.
    """
    labels = sorted(client_ids)
    if not labels:
        raise CommitmentError("Participant set must not be empty")
    for label in labels:
        validate_event(
            "UpdateCommitted",
            {
                "run_id": "validation",
                "round_index": 0,
                "client_id": label,
                "update_sha256": "0" * 64,
                "update_bytes": 0,
            },
        )
    return commitment({"participants": labels})


def update_commitment(tensor_bytes: bytes) -> str:
    """Commitment over an update's serialised bytes.

    Accepts only the serialised form. The tensor itself is never inspected, stored or committed —
    hashing a byte string leaves no recoverable tensor in the ledger.
    """
    if not isinstance(tensor_bytes, (bytes, bytearray)):
        raise CommitmentError("Update commitment requires serialised bytes")
    return hashlib.sha256(bytes(tensor_bytes)).hexdigest()


def scale_privacy_value(value: float) -> int:
    """Convert a privacy parameter to a scaled integer for on-chain attestation."""
    if value != value or value in (float("inf"), float("-inf")):
        raise CommitmentError("Privacy parameter must be finite")
    if value < 0:
        raise CommitmentError("Privacy parameter must be non-negative")
    scaled = int(round(float(value) * PRIVACY_SCALE))
    if scaled < 0:
        raise CommitmentError("Scaled privacy parameter overflowed")
    return scaled


def make_event(event_type: str, payload: Mapping[str, Any]) -> ValidatedRecord:
    """Validate a payload and return the record ready for ledger append."""
    return validate_event(event_type, dict(payload))


def privacy_attestation(
    run_id: str,
    epsilon: float,
    delta: float,
    sigma: float,
    clip_norm: float,
    accountant_id: str,
) -> ValidatedRecord:
    """Build the single privacy attestation for a run.

    Only run-level scalars are committed. Per-client epsilon contributions, clipping norms and
    noise magnitudes stay off-chain: they are attributable to individual clients and are exactly the
    kind of diagnostic that Phase 6 kept out of public channels.
    """
    return make_event(
        "PrivacyAttested",
        {
            "run_id": run_id,
            "epsilon_scaled": scale_privacy_value(epsilon),
            "delta_scaled": scale_privacy_value(delta),
            "sigma_scaled": scale_privacy_value(sigma),
            "clip_scaled": scale_privacy_value(clip_norm),
            "accountant_id": accountant_id,
        },
    )
