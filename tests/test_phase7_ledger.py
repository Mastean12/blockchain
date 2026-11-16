"""Phase 7 ledger integrity tests: tamper detection, localisation, and documented limits."""

import json

import pytest

from src.blockchain.commitments import participant_set_commitment
from src.blockchain.ledger import (
    GENESIS_PREVIOUS_HASH,
    HashChainLedger,
    LedgerError,
    compare_to_anchor,
    verify_ledger,
)
from src.blockchain.schema import validate_event


def _run(run_id="r1"):
    return validate_event(
        "RunRegistered",
        {
            "run_id": run_id,
            "config_sha256": "a" * 64,
            "split_sha256": "b" * 64,
            "client_manifest_sha256": "c" * 64,
            "model_arch_id": "compact_cnn_v1",
            "seed": 42,
        },
    )


def _update(round_index, client_id="client_01"):
    return validate_event(
        "UpdateCommitted",
        {
            "run_id": "r1",
            "round_index": round_index,
            "client_id": client_id,
            "update_sha256": "d" * 64,
            "update_bytes": 145428,
        },
    )


def _build(path, count=20):
    ledger = HashChainLedger(path)
    ledger.append(_run())
    for index in range(1, count):
        ledger.append(_update(index))
    return ledger


# --------------------------------------------------------------- T1 integrity
def test_valid_chain_verifies_and_reports_head(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger = _build(path)
    report = verify_ledger(path)
    assert report["valid"] is True
    assert report["entries"] == len(ledger)
    assert report["head_hash"] == ledger.head_hash()


def test_altering_any_interior_entry_is_detected_at_that_index(tmp_path):
    for victim in (0, 1, 7, 19):
        path = tmp_path / f"ledger_{victim}.jsonl"
        _build(path)
        lines = path.read_text(encoding="utf-8").splitlines()
        payload = json.loads(lines[victim])
        payload["fields"]["round_index"] = 999
        lines[victim] = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        report = verify_ledger(path)
        assert report["valid"] is False
        assert report["first_divergent_index"] == victim


def test_altering_a_hash_directly_is_detected(tmp_path):
    path = tmp_path / "ledger.jsonl"
    _build(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[5])
    payload["entry_hash"] = "f" * 64
    lines[5] = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = verify_ledger(path)
    assert report["valid"] is False
    assert report["first_divergent_index"] == 5


def test_deleting_an_interior_entry_is_detected(tmp_path):
    path = tmp_path / "ledger.jsonl"
    _build(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    del lines[8]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = verify_ledger(path)
    assert report["valid"] is False
    assert report["first_divergent_index"] == 8


def test_reordering_entries_is_detected(tmp_path):
    path = tmp_path / "ledger.jsonl"
    _build(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[4], lines[5] = lines[5], lines[4]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert verify_ledger(path)["valid"] is False


# ------------------------------------- T2 truncation: documented limitation
def test_truncation_is_undetectable_without_an_anchor(tmp_path):
    """A shorter chain is internally valid. This is a stated limitation, not a bug.

    SECURITY_THREAT_MODEL.md §6.2: detection requires an out-of-band head hash.
    """
    path = tmp_path / "ledger.jsonl"
    _build(path, count=20)
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[:10]) + "\n", encoding="utf-8")
    report = verify_ledger(path)
    assert report["valid"] is True, "truncation must leave an internally valid chain"
    assert report["entries"] == 10

    # With the anchor held from before truncation, the same file is detected.
    anchored = compare_to_anchor(path, "0" * 64)
    assert anchored["matches_anchor"] is False


def test_anchor_match_is_reported_when_chain_is_intact(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger = _build(path, count=12)
    anchored = compare_to_anchor(path, ledger.head_hash())
    assert anchored["matches_anchor"] is True
    assert anchored["valid"] is True


def test_anchor_detects_a_full_consistent_rewrite(tmp_path):
    """Rewriting every entry consistently still fails the anchor check."""
    path = tmp_path / "ledger.jsonl"
    ledger = _build(path, count=8)
    original_head = ledger.head_hash()

    rewritten = tmp_path / "rewritten.jsonl"
    fresh = HashChainLedger(rewritten)
    fresh.append(_run(run_id="forged"))
    for index in range(1, 8):
        fresh.append(_update(index))
    assert verify_ledger(rewritten)["valid"] is True  # internally consistent
    assert compare_to_anchor(rewritten, original_head)["matches_anchor"] is False


# ------------------------------------------------- structural guards on write
def test_ledger_refuses_to_append_to_a_tampered_file(tmp_path):
    path = tmp_path / "ledger.jsonl"
    _build(path, count=5)
    lines = path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[2])
    payload["fields"]["round_index"] = 777
    lines[2] = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(LedgerError):
        HashChainLedger(path)


def test_ledger_rejects_raw_mappings(tmp_path):
    ledger = HashChainLedger(tmp_path / "ledger.jsonl")
    with pytest.raises(LedgerError, match="ValidatedRecord"):
        ledger.append({"run_id": "r"})  # type: ignore[arg-type]


def test_genesis_previous_hash_is_all_zero(tmp_path):
    ledger = HashChainLedger(tmp_path / "ledger.jsonl")
    entry = ledger.append(_run())
    assert entry.previous_hash == GENESIS_PREVIOUS_HASH
    assert entry.index == 0


def test_append_is_idempotently_reloadable(tmp_path):
    path = tmp_path / "ledger.jsonl"
    first = _build(path, count=6)
    reopened = HashChainLedger(path)
    assert len(reopened) == len(first)
    assert reopened.head_hash() == first.head_hash()


def test_participant_set_commitment_is_order_independent():
    a = participant_set_commitment(["client_02", "client_01", "client_03"])
    b = participant_set_commitment(["client_03", "client_01", "client_02"])
    assert a == b
