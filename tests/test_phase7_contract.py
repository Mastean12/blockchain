"""Phase 7 contract behaviour tests (T5-T11).

These require a running Ganache instance on 127.0.0.1:8545. They are skipped with a clear reason if
no chain is reachable, so the suite stays green on machines without the toolchain, but a real run
must never silently pass without them — ``scripts/run_phase7_audit.py`` fails if they are skipped.
"""

import pytest

from src.blockchain.commitments import participant_set_commitment

pytestmark = pytest.mark.phase7_evm


def _contract():
    from src.blockchain.evm import AuditContract, GanacheError

    try:
        return AuditContract.deploy()
    except GanacheError as error:
        pytest.skip(f"Ganache unavailable: {error}")


@pytest.fixture(scope="module")
def chain():
    return _contract()


RUN = "test_run"


def _register(contract, run_id=RUN):
    return contract.register_run(run_id, "a" * 64, "b" * 64, "c" * 64)


def _open(contract, run_id=RUN, round_index=1, clients=None):
    clients = clients or [f"client_0{i}" for i in range(1, 6)]
    return contract.open_round(run_id, round_index, participant_set_commitment(clients))


# --------------------------------------------------------------------- T5
def test_authorised_writer_succeeds(chain):
    assert _register(chain).success is True


# --------------------------------------------------------------------- T6
def test_unauthorised_writer_is_rejected(chain):
    measurement = chain.register_run(
        "unauth_run", "a" * 64, "b" * 64, "c" * 64, sender=chain.unauthorised
    )
    assert measurement.success is False
    assert "not authorised" in (measurement.revert_reason or "")


def test_unauthorised_commit_is_rejected(chain):
    _register(chain, "unauth_commit")
    _open(chain, "unauth_commit")
    measurement = chain.commit_update(
        "unauth_commit", 1, "client_01", "d" * 64, 145428, sender=chain.unauthorised
    )
    assert measurement.success is False


# --------------------------------------------------------------------- T7
def test_replayed_round_opening_is_rejected(chain):
    _register(chain, "replay_open")
    assert _open(chain, "replay_open").success is True
    second = _open(chain, "replay_open")
    assert second.success is False
    assert "already opened" in (second.revert_reason or "")


def test_duplicate_client_commitment_is_rejected(chain):
    _register(chain, "replay_commit")
    _open(chain, "replay_commit")
    first = chain.commit_update("replay_commit", 1, "client_01", "d" * 64, 100)
    second = chain.commit_update("replay_commit", 1, "client_01", "e" * 64, 100)
    assert first.success is True
    assert second.success is False
    assert "replay" in (second.revert_reason or "").lower()


def test_duplicate_run_registration_is_rejected(chain):
    _register(chain, "dup_run")
    assert _register(chain, "dup_run").success is False


# --------------------------------------------------------------------- T8
def test_closing_a_round_without_commitments_is_rejected(chain):
    _register(chain, "empty_close")
    _open(chain, "empty_close", round_index=3)
    measurement = chain.close_round("empty_close", 3, "f" * 64, "fedavg")
    assert measurement.success is False
    assert "no commitments" in (measurement.revert_reason or "")


def test_missing_commitment_event_requires_no_prior_commits(chain):
    _register(chain, "missing_ok")
    _open(chain, "missing_ok", round_index=2)
    ok = chain.report_missing(
        "missing_ok", 2, participant_set_commitment(["client_01"])
    )
    assert ok.success is True

    _register(chain, "missing_bad")
    _open(chain, "missing_bad", round_index=2)
    chain.commit_update("missing_bad", 2, "client_01", "d" * 64, 10)
    bad = chain.report_missing(
        "missing_bad", 2, participant_set_commitment(["client_01"])
    )
    assert bad.success is False


def test_round_commit_count_matches_submissions(chain):
    _register(chain, "count_run")
    _open(chain, "count_run", round_index=1)
    for index in (1, 2, 3):
        chain.commit_update("count_run", 1, f"client_0{index}", "d" * 64, 10)
    assert chain.read_round_count("count_run", 1) == 3


# --------------------------------------------------------------------- T9
def test_committed_hash_is_readable_and_a_different_hash_is_detectable(chain):
    _register(chain, "hash_run")
    _open(chain, "hash_run", round_index=1)
    committed = "d" * 64
    chain.commit_update("hash_run", 1, "client_01", committed, 100)
    chain.close_round("hash_run", 1, "e" * 64, "fedavg")

    stored = chain.contract.functions.roundGlobalModelHash(
        chain.contract.functions.roundKey(
            chain.run_key("hash_run"), 1
        ).call()
    ).call()
    assert stored.hex() == "e" * 64
    assert stored.hex() != "0" * 64


def test_commit_into_closed_round_is_rejected(chain):
    _register(chain, "closed_round")
    _open(chain, "closed_round", round_index=1)
    chain.commit_update("closed_round", 1, "client_01", "d" * 64, 10)
    chain.close_round("closed_round", 1, "e" * 64, "fedavg")
    late = chain.commit_update("closed_round", 1, "client_02", "d" * 64, 10)
    assert late.success is False


# -------------------------------------------------------------------- T10
def test_run_reconstruction_returns_committed_hashes(chain):
    _register(chain, "recon_run")
    _open(chain, "recon_run", round_index=1)
    chain.commit_update("recon_run", 1, "client_01", "d" * 64, 10)
    chain.close_round("recon_run", 1, "e" * 64, "fedavg")
    chain.seal_checkpoint("recon_run", 1, "f" * 64)
    state = chain.read_run("recon_run")
    assert state["registered"] is True
    assert state["config_hash"] == "a" * 64
    assert state["checkpoint_hash"] == "f" * 64
    assert state["selected_round"] == 1


def test_privacy_attestation_is_stored_and_single_use(chain):
    _register(chain, "privacy_run")
    first = chain.attest_privacy("privacy_run", 57_301_692_825, 10_000,
                                 1_000_000_000, 3_440_000_000, "opacus_rdp_1.6.0")
    assert first.success is True
    second = chain.attest_privacy("privacy_run", 1, 1, 1, 1, "other")
    assert second.success is False
    assert chain.read_run("privacy_run")["privacy_attested"] is True


# -------------------------------------------------------------------- T11
def test_revert_reasons_are_specific_not_generic(chain):
    """Every negative case must expose a reason, so a failure is diagnosable."""
    before = len(chain.measurements)
    chain.commit_update("nonexistent_run", 1, "client_01", "d" * 64, 10)
    failed = [m for m in chain.measurements[before:] if not m.success]
    assert failed, "expected a failed transaction"
    assert failed[0].revert_reason, "a revert must carry a reason"


def test_gas_is_recorded_for_every_successful_transaction(chain):
    before = len(chain.measurements)
    _register(chain, "gas_run")
    _open(chain, "gas_run")
    chain.commit_update("gas_run", 1, "client_01", "d" * 64, 10)
    chain.close_round("gas_run", 1, "e" * 64, "fedavg")
    recent = chain.measurements[before:]
    assert all(m.success for m in recent)
    assert all(m.gas_used > 0 for m in recent)
