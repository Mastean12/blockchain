"""Level 1 tamper-evident audit log: an append-only SHA-256 hash chain.

This is **not** a blockchain. It has one writer, no consensus, no independent nodes and no
authorisation. What it provides is tamper evidence: altering, reordering or deleting an interior
entry breaks the chain at a computable index.

What it does **not** provide, and the study must state:

- *Consistent truncation is undetectable without an external anchor.* Removing trailing entries
  leaves a shorter but perfectly valid chain. ``docs/threat_model/SECURITY_THREAT_MODEL.md`` §6.2
  requires an out-of-band head hash for that reason.
- *A full rewrite from genesis is undetectable* if the writer is the adversary, unless a head hash
  was obtained earlier.

Format: JSON Lines, one record per line, so a partially written file remains parseable up to the last
complete line and an interrupted run can be resumed rather than restarted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from src.blockchain.commitments import canonical_bytes
from src.blockchain.schema import AuditSchemaError, ValidatedRecord, assert_no_sensitive_payload
from src.data.phase3_pipeline import canonical_json_sha256

GENESIS_PREVIOUS_HASH = "0" * 64
LEDGER_SCHEMA_VERSION = 1


class LedgerError(RuntimeError):
    """Raised when the ledger cannot be appended or read safely."""


@dataclass(frozen=True)
class LedgerEntry:
    """One chained record."""

    index: int
    event_type: str
    fields: dict[str, Any]
    previous_hash: str
    entry_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "event_type": self.event_type,
            "fields": self.fields,
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
        }


def _entry_hash(index: int, event_type: str, fields: dict[str, Any], previous_hash: str) -> str:
    return canonical_json_sha256(
        {
            "index": index,
            "event_type": event_type,
            "fields": fields,
            "previous_hash": previous_hash,
            "schema_version": LEDGER_SCHEMA_VERSION,
        }
    )


class HashChainLedger:
    """Append-only tamper-evident log backed by a JSONL file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()
        self._entries = list(self._read())
        self._verify_prefix()

    # ------------------------------------------------------------------ writing
    def append(self, record: ValidatedRecord) -> LedgerEntry:
        """Append one validated event and return the resulting entry."""
        if not isinstance(record, ValidatedRecord):
            raise LedgerError("append() requires a ValidatedRecord, not a raw mapping")
        # Defence in depth: the schema already validated, and this guards against a future
        # schema change that reintroduces a sensitive field.
        assert_no_sensitive_payload(record.fields)

        previous = self._entries[-1].entry_hash if self._entries else GENESIS_PREVIOUS_HASH
        index = len(self._entries)
        digest = _entry_hash(index, record.event_type, record.fields, previous)
        entry = LedgerEntry(
            index=index,
            event_type=record.event_type,
            fields=dict(record.fields),
            previous_hash=previous,
            entry_hash=digest,
        )
        line = json.dumps(entry.as_dict(), sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
        self._entries.append(entry)
        return entry

    # ------------------------------------------------------------------ reading
    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[LedgerEntry]:
        return iter(self._entries)

    def entries(self) -> list[LedgerEntry]:
        return list(self._entries)

    def head_hash(self) -> str:
        return self._entries[-1].entry_hash if self._entries else GENESIS_PREVIOUS_HASH

    def _read(self) -> Iterator[LedgerEntry]:
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as error:
                    raise LedgerError(
                        f"Ledger line {line_number} is not valid JSON: {error}"
                    ) from error
                try:
                    yield LedgerEntry(
                        index=int(payload["index"]),
                        event_type=str(payload["event_type"]),
                        fields=dict(payload["fields"]),
                        previous_hash=str(payload["previous_hash"]),
                        entry_hash=str(payload["entry_hash"]),
                    )
                except (KeyError, TypeError, ValueError) as error:
                    raise LedgerError(
                        f"Ledger line {line_number} has an invalid record shape"
                    ) from error

    def _verify_prefix(self) -> None:
        """Refuse to append to a chain that is already inconsistent."""
        previous = GENESIS_PREVIOUS_HASH
        for position, entry in enumerate(self._entries):
            if entry.index != position:
                raise LedgerError(
                    f"Ledger index discontinuity at line {position + 1}: expected {position}, "
                    f"found {entry.index}"
                )
            if entry.previous_hash != previous:
                raise LedgerError(f"Ledger previous_hash mismatch at entry {entry.index}")
            recomputed = _entry_hash(
                entry.index, entry.event_type, entry.fields, entry.previous_hash
            )
            if recomputed != entry.entry_hash:
                raise LedgerError(f"Ledger entry {entry.index} fails its own hash")
            previous = entry.entry_hash


def verify_ledger(path: str | Path) -> dict[str, Any]:
    """Independently verify a ledger file and localise the first defect.

    Returns a report rather than raising on tampering, because the *detection* is the measurement.
    Structural problems that prevent any verification still raise.
    """
    entries: list[LedgerEntry] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                return {
                    "valid": False,
                    "entries": len(entries),
                    "first_divergent_index": len(entries),
                    "reason": f"line {line_number} is not valid JSON",
                    "head_hash": entries[-1].entry_hash if entries else GENESIS_PREVIOUS_HASH,
                }
            try:
                entries.append(
                    LedgerEntry(
                        index=int(payload["index"]),
                        event_type=str(payload["event_type"]),
                        fields=dict(payload["fields"]),
                        previous_hash=str(payload["previous_hash"]),
                        entry_hash=str(payload["entry_hash"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                return {
                    "valid": False,
                    "entries": len(entries),
                    "first_divergent_index": len(entries),
                    "reason": f"line {line_number} has an invalid record shape",
                    "head_hash": entries[-1].entry_hash if entries else GENESIS_PREVIOUS_HASH,
                }

    previous = GENESIS_PREVIOUS_HASH
    for position, entry in enumerate(entries):
        if entry.index != position:
            return {
                "valid": False,
                "entries": len(entries),
                "first_divergent_index": position,
                "reason": f"index discontinuity: expected {position}, found {entry.index}",
                "head_hash": entries[-1].entry_hash if entries else GENESIS_PREVIOUS_HASH,
            }
        if entry.previous_hash != previous:
            return {
                "valid": False,
                "entries": len(entries),
                "first_divergent_index": position,
                "reason": "previous_hash does not match the preceding entry",
                "head_hash": entries[-1].entry_hash if entries else GENESIS_PREVIOUS_HASH,
            }
        recomputed = _entry_hash(entry.index, entry.event_type, entry.fields, entry.previous_hash)
        if recomputed != entry.entry_hash:
            return {
                "valid": False,
                "entries": len(entries),
                "first_divergent_index": position,
                "reason": "entry hash mismatch",
                "head_hash": entries[-1].entry_hash if entries else GENESIS_PREVIOUS_HASH,
            }
        previous = entry.entry_hash

    return {
        "valid": True,
        "entries": len(entries),
        "first_divergent_index": None,
        "reason": None,
        "head_hash": previous,
    }


def compare_to_anchor(path: str | Path, anchor_hash: str) -> dict[str, Any]:
    """Compare a ledger's head against an out-of-band anchor.

    This is the only mechanism that detects a *consistent* rewrite or truncation; both leave an
    internally valid chain.
    """
    report = verify_ledger(path)
    if len(anchor_hash) != 64:
        raise LedgerError("Anchor must be a 64-character hex hash")
    report["anchor_hash"] = anchor_hash
    report["matches_anchor"] = report["head_hash"] == anchor_hash
    return report


__all__ = [
    "GENESIS_PREVIOUS_HASH",
    "HashChainLedger",
    "LedgerEntry",
    "LedgerError",
    "LedgerSchemaError",
    "canonical_bytes",
    "compare_to_anchor",
    "verify_ledger",
]

LedgerSchemaError = AuditSchemaError
