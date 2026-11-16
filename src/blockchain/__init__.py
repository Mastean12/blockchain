"""Phase 7 blockchain audit layer.

The implemented artefact is a **Level 1 tamper-evident hash chain** and a **Level 2 local
smart-contract prototype** on a single-node Ganache instance. It is not a distributed blockchain,
and this package must never be described as one.
"""

from src.blockchain.commitments import (
    CommitmentError,
    commitment,
    file_commitment,
    participant_set_commitment,
    privacy_attestation,
    safe_basename,
    update_commitment,
)
from src.blockchain.ledger import (
    GENESIS_PREVIOUS_HASH,
    HashChainLedger,
    LedgerEntry,
    LedgerError,
    compare_to_anchor,
    verify_ledger,
)
from src.blockchain.schema import (
    AuditSchemaError,
    ValidatedRecord,
    allowed_fields,
    assert_no_sensitive_payload,
    validate_event,
)

__all__ = [
    "AuditSchemaError",
    "CommitmentError",
    "GENESIS_PREVIOUS_HASH",
    "HashChainLedger",
    "LedgerEntry",
    "LedgerError",
    "ValidatedRecord",
    "allowed_fields",
    "assert_no_sensitive_payload",
    "commitment",
    "compare_to_anchor",
    "file_commitment",
    "participant_set_commitment",
    "privacy_attestation",
    "safe_basename",
    "update_commitment",
    "validate_event",
    "verify_ledger",
]
