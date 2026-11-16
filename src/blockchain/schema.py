"""Closed-whitelist audit schema with personal-information rejection.

Phase 7 may commit only non-sensitive metadata to an audit record. This module is the enforcement
point: an audit payload that does not match the whitelist exactly is **rejected**, not filtered.

Rationale for a closed whitelist rather than a blacklist: a blacklist fails silently the first time
someone invents a new field name. A whitelist fails loudly, which is what an integrity mechanism
needs. The prohibition list in ``docs/threat_model/SECURITY_THREAT_MODEL.md`` §3.2 explains why each
category is barred.

Nothing here may ever accept: ECG samples, patient or record identifiers, beat labels, model
parameter tensors, update vectors, per-client sample counts or clipping norms, key material, noise
seeds, free text, or absolute filesystem paths.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

HASH_HEX_LENGTH = 64
_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")

# ---------------------------------------------------------------------------------------------
# Allowed fields, with the value contract for each (SECURITY_THREAT_MODEL.md §3.3).
# ---------------------------------------------------------------------------------------------
SCHEMAS: dict[str, dict[str, str]] = {
    "RunRegistered": {
        "run_id": "identifier",
        "config_sha256": "hash",
        "split_sha256": "hash",
        "client_manifest_sha256": "hash",
        "model_arch_id": "identifier",
        "seed": "int",
    },
    "RoundOpened": {
        "run_id": "identifier",
        "round_index": "int",
        "participant_set_sha256": "hash",
    },
    "UpdateCommitted": {
        "run_id": "identifier",
        "round_index": "int",
        "client_id": "client_id",
        "update_sha256": "hash",
        "update_bytes": "int",
    },
    "RoundClosed": {
        "run_id": "identifier",
        "round_index": "int",
        "global_model_sha256": "hash",
        "aggregation_rule_id": "identifier",
    },
    "MissingCommitment": {
        "run_id": "identifier",
        "round_index": "int",
        "expected_participant_set_sha256": "hash",
        "received_participant_set_sha256": "hash",
    },
    "CheckpointSealed": {
        "run_id": "identifier",
        "selected_round": "int",
        "checkpoint_sha256": "hash",
    },
    "PrivacyAttested": {
        "run_id": "identifier",
        "epsilon_scaled": "int",
        "delta_scaled": "int",
        "sigma_scaled": "int",
        "clip_scaled": "int",
        "accountant_id": "identifier",
    },
}

# ---------------------------------------------------------------------------------------------
# Prohibition patterns. Defence in depth: these are checked in addition to the whitelist, so that
# a future schema addition cannot quietly reintroduce a barred category.
# ---------------------------------------------------------------------------------------------
FORBIDDEN_KEY_PATTERNS = (
    r"record",            # record_ids, record_number, test_record_ids
    r"patient",
    r"subject",
    r"sample_count",      # per-client dataset size
    r"^n_k$",
    r"clip_norm",         # per-client clipping diagnostic
    r"norm_before",
    r"norm_after",
    r"epsilon_client",
    r"noise_magnitude",
    r"seed_(dp|noise)",
    r"secret",
    r"private_key",
    r"context_key",
    r"galois",
    r"symbol",            # annotation symbols / beat labels
    r"annotation",
    r"waveform",
    r"signal",
    r"tensor",
    r"parameters",
    r"weights",
    r"update_vector",
    r"labels",
    r"class_counts",
    r"path",
    r"filename",
    r"user",
)

# MIT-BIH record numbers are two or three digit values in 100-234. A string value that is exactly a
# record number is a quasi-identifier and is rejected. Integers are allowed because round indices,
# seeds and byte counts are legitimate integers; the value contract (not the value range) governs.
_RECORD_NUMBER = re.compile(r"\A(1\d\d|2[0-3]\d)\Z")


class AuditSchemaError(ValueError):
    """Raised when an audit payload would violate the schema or the information policy."""


@dataclass(frozen=True)
class ValidatedRecord:
    """A validated audit event, safe to commit."""

    event_type: str
    fields: dict[str, Any]


def _check_key(key: str) -> None:
    for pattern in FORBIDDEN_KEY_PATTERNS:
        if re.search(pattern, key, flags=re.IGNORECASE):
            raise AuditSchemaError(
                f"Field {key!r} matches the prohibited pattern {pattern!r}; "
                "see SECURITY_THREAT_MODEL.md §3.2"
            )


def _check_value(key: str, kind: str, value: Any) -> None:
    if kind == "hash":
        if not isinstance(value, str) or not _HEX64.match(value):
            raise AuditSchemaError(f"{key} must be 64 lowercase hex characters")
        return
    if kind == "int":
        # bool is a subclass of int and would slip through silently.
        if isinstance(value, bool) or not isinstance(value, int):
            raise AuditSchemaError(f"{key} must be an integer, got {type(value).__name__}")
        if value < 0:
            raise AuditSchemaError(f"{key} must be non-negative")
        return
    if kind == "identifier":
        if not isinstance(value, str):
            raise AuditSchemaError(f"{key} must be a string identifier")
        if len(value) > 64:
            raise AuditSchemaError(f"{key} exceeds the 64-character identifier limit")
        if not re.match(r"\A[A-Za-z0-9_.:-]+\Z", value):
            raise AuditSchemaError(f"{key} contains characters outside the identifier set")
        if _RECORD_NUMBER.match(value):
            raise AuditSchemaError(
                f"{key} looks like a MIT-BIH record number, which is a quasi-identifier"
            )
        return
    if kind == "client_id":
        if not isinstance(value, str) or not re.match(r"\Aclient_0[1-9]\Z", value):
            raise AuditSchemaError(
                f"{key} must be a client slot label such as client_01, not a record or patient id"
            )
        return
    raise AuditSchemaError(f"Unknown value contract {kind!r} for {key}")


def validate_event(event_type: str, payload: dict[str, Any]) -> ValidatedRecord:
    """Validate one audit event against the closed whitelist.

    Rejects: unknown event types, unknown fields, missing fields, wrong value contracts, and
    anything matching a prohibited pattern.
    """
    if event_type not in SCHEMAS:
        raise AuditSchemaError(f"Unknown event type {event_type!r}")
    schema = SCHEMAS[event_type]

    if not isinstance(payload, dict):
        raise AuditSchemaError("Audit payload must be a mapping")

    extra = set(payload) - set(schema)
    if extra:
        raise AuditSchemaError(
            f"{event_type}: fields not in the closed whitelist: {sorted(extra)}"
        )
    missing = set(schema) - set(payload)
    if missing:
        raise AuditSchemaError(f"{event_type}: missing required fields: {sorted(missing)}")

    for key, kind in schema.items():
        _check_key(key)
        value = payload[key]
        if isinstance(value, (list, tuple, dict)):
            raise AuditSchemaError(
                f"{event_type}.{key}: structured values are not permitted on-chain"
            )
        if isinstance(value, float):
            raise AuditSchemaError(
                f"{event_type}.{key}: floats are not permitted; use scaled integers"
            )
        _check_value(key, kind, value)

    return ValidatedRecord(event_type=event_type, fields=dict(payload))


def assert_no_sensitive_payload(payload: Any, path: str = "$") -> None:
    """Defence-in-depth scan of an arbitrary object before serialisation.

    Used by the ledger writer as a final guard. It rejects numeric arrays (model tensors), deep
    nesting, over-long strings and any prohibited key at any depth.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if not isinstance(key, str):
                raise AuditSchemaError(f"{path}: non-string key {key!r}")
            _check_key(key)
            assert_no_sensitive_payload(value, f"{path}.{key}")
        return
    if isinstance(payload, (list, tuple)):
        if len(payload) > 8:
            raise AuditSchemaError(
                f"{path}: sequence of length {len(payload)} looks like tensor/vector data"
            )
        for index, item in enumerate(payload):
            assert_no_sensitive_payload(item, f"{path}[{index}]")
        return
    if isinstance(payload, str):
        if len(payload) > 128:
            raise AuditSchemaError(f"{path}: string exceeds 128 characters")
        if _RECORD_NUMBER.match(payload):
            raise AuditSchemaError(f"{path}: value looks like a record number")
        if re.search(r"[A-Za-z]:\\|/home/|/Users/", payload):
            raise AuditSchemaError(f"{path}: absolute filesystem path is not permitted")
        return
    if isinstance(payload, bool):
        return
    if isinstance(payload, (int, type(None))):
        return
    if isinstance(payload, float):
        raise AuditSchemaError(f"{path}: floats are not permitted in audit payloads")
    raise AuditSchemaError(f"{path}: unsupported type {type(payload).__name__}")


def allowed_fields(event_type: str) -> dict[str, str]:
    """Read-only view of the whitelist for a given event type."""
    if event_type not in SCHEMAS:
        raise AuditSchemaError(f"Unknown event type {event_type!r}")
    return dict(SCHEMAS[event_type])
