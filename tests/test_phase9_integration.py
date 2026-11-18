"""Phase 9 integration smoke tests (master spec section 24).

These compose already-validated components. They prove the software composes; they do **not** prove
scientific validity, and they do **not** constitute a robustness result (G8 did not pass).
"""

import pytest
import torch

from src.integration import (
    EXCLUDED_FROM_INTEGRATION,
    INTEGRATION_MODES,
    IntegrationError,
    assert_integration_allowed,
    run_integrated,
)

SEED = 61
ROUNDS = 2
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


@pytest.fixture(scope="module")
def federated_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("integration_federated")
    return run_integrated(
        _root(), "federated", seed=SEED, rounds=ROUNDS, device_name=DEVICE,
        ledger_path=out / "ledger.jsonl",
    )


def _root():
    from pathlib import Path

    return Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------ eligibility
def test_robust_aggregation_is_excluded():
    """G8 did not pass, so section 37 forbids integrating it."""
    assert "robust_aggregation" in EXCLUDED_FROM_INTEGRATION
    with pytest.raises(IntegrationError, match="G8 NOT PASSED"):
        assert_integration_allowed("robust_aggregation")


def test_dp_is_excluded_by_recommendation():
    assert "dp" in EXCLUDED_FROM_INTEGRATION
    with pytest.raises(IntegrationError):
        assert_integration_allowed("dp")


def test_unknown_mode_is_rejected():
    with pytest.raises(IntegrationError, match="Unknown integration mode"):
        run_integrated(_root(), "robust", rounds=1, device_name=DEVICE)


def test_all_declared_modes_are_exposed():
    assert set(INTEGRATION_MODES) == {
        "centralized", "local_only", "federated", "federated_he"
    }


# ------------------------------------------------------------ IT-1 / IT-2 / IT-3
def test_it1_centralized_short_run(tmp_path):
    r = run_integrated(_root(), "centralized", seed=SEED, rounds=ROUNDS,
                       device_name=DEVICE, ledger_path=tmp_path / "l.jsonl")
    assert r.test_metrics is not None
    assert 0.0 <= r.test_metrics["accuracy"] <= 1.0
    assert r.validation_history


def test_it2_local_only_short_run(tmp_path):
    r = run_integrated(_root(), "local_only", seed=SEED, rounds=ROUNDS,
                       device_name=DEVICE, ledger_path=tmp_path / "l.jsonl")
    assert r.test_metrics is not None
    assert len(r.validation_history) == 5, "one entry per client"


def test_it3_federated_short_run(federated_run):
    assert federated_run.test_metrics is not None
    assert len(federated_run.validation_history) == ROUNDS
    assert 0.0 <= federated_run.test_metrics["macro_f1"] <= 1.0


# ---------------------------------------------------------------------- IT-5
def test_it5_he_aggregation_smoke(tmp_path):
    r = run_integrated(_root(), "federated_he", seed=SEED, rounds=ROUNDS,
                       device_name=DEVICE, ledger_path=tmp_path / "l.jsonl")
    assert r.he_included is True
    assert r.he_max_relative_error is not None
    assert r.he_max_relative_error < 1e-5, "CKKS approximation must stay below the D7 threshold"
    assert r.he_ciphertext_bytes_per_client > 0


def test_he_does_not_materially_change_metrics(federated_run, tmp_path):
    he = run_integrated(_root(), "federated_he", seed=SEED, rounds=ROUNDS,
                        device_name=DEVICE, ledger_path=tmp_path / "l.jsonl")
    plain = federated_run.test_metrics
    assert abs(plain["accuracy"] - he.test_metrics["accuracy"]) < 1e-2
    assert abs(plain["macro_f1"] - he.test_metrics["macro_f1"]) < 1e-2


# ---------------------------------------------------------------------- IT-6
def test_it6_ledger_lifecycle(federated_run):
    assert federated_run.ledger_valid is True
    assert federated_run.ledger_entries > 0
    assert federated_run.ledger_head is not None
    assert len(federated_run.ledger_head) == 64


# --------------------------------------------------------------- IT-8 / IT-10
def test_it10_determinism_across_reruns(tmp_path):
    first = run_integrated(_root(), "federated", seed=SEED, rounds=ROUNDS,
                           device_name=DEVICE, ledger_path=tmp_path / "a.jsonl")
    second = run_integrated(_root(), "federated", seed=SEED, rounds=ROUNDS,
                            device_name=DEVICE, ledger_path=tmp_path / "b.jsonl")
    assert first.test_metrics["accuracy"] == second.test_metrics["accuracy"]
    assert first.test_metrics["macro_f1"] == second.test_metrics["macro_f1"]
    assert first.ledger_head == second.ledger_head


# ---------------------------------------------------------------------- IT-9
def test_it9_no_sensitive_data_in_integrated_ledger(tmp_path):
    """Re-apply the Phase 7 personal-information assertions to integrated entries."""
    from src.blockchain.ledger import HashChainLedger

    ledger_path = tmp_path / "sensitive_check.jsonl"
    run_integrated(_root(), "federated", seed=SEED, rounds=1, device_name=DEVICE,
                   ledger_path=ledger_path)
    ledger = HashChainLedger(ledger_path)
    assert len(ledger) > 0, "ledger must have been written"
    for entry in ledger:
        keys = " ".join(entry.fields.keys())
        for forbidden in ("record", "patient", "subject", "clip_norm", "secret", "path"):
            assert forbidden not in keys, f"prohibited field {forbidden} present"


# ---------------------------------------------------------------- exclusions
def test_s_class_limitation_visible_in_integrated_output(federated_run):
    """The known S-class defect must remain visible, not hidden by integration."""
    assert federated_run.test_metrics["per_class"]["S"]["recall"] == 0.0


# ---------------------------------------------------------------------- IT-4
def test_it4_dp_mechanism_smoke():
    """IT-4: the DP mechanism composes as software.

    DP is NOT part of the integrated configuration X1 (recommendation 9-DP-a), but master spec
    section 24 lists this smoke test in its own right. It proves the clip -> noise -> accountant
    path runs and produces finite output. It asserts NOTHING about utility or privacy quality;
    the Phase 6 negative result stands separately.
    """
    import math

    import torch

    from src.privacy.clipping import clip_update, frozen_weights, per_client_sensitivity
    from src.privacy.dp_mechanism import (
        add_gaussian_noise,
        compute_epsilon,
        make_generator,
        validate_accountant,
    )

    clip_norm = 3.44
    update = torch.randn(36357) * 25.0  # deliberately above the clip norm

    clipped = clip_update(update, clip_norm)
    assert clipped.clipped is True
    assert clipped.norm_after <= clip_norm * (1 + 1e-5)

    noisy = add_gaussian_noise(clipped.tensor, 1.0, clip_norm, make_generator(61, 1, 0))
    assert torch.isfinite(noisy).all(), "DP output must be finite"
    assert noisy.shape == clipped.tensor.shape

    # Deterministic for a fixed (seed, round, client).
    again = add_gaussian_noise(clipped.tensor, 1.0, clip_norm, make_generator(61, 1, 0))
    assert torch.equal(noisy, again)

    sensitivity = per_client_sensitivity(clip_norm)
    report = compute_epsilon(1.0, 2, 1e-5, sensitivity)
    assert math.isfinite(report.epsilon) and report.epsilon > 0

    gate = validate_accountant()
    assert gate["ratio"] <= 1.0

    weights = frozen_weights({"client_01": 26685, "client_02": 14780,
                              "client_03": 6260, "client_04": 11149, "client_05": 13053})
    assert abs(sum(weights.values()) - 1.0) < 1e-12


# ---------------------------------------------------------------------- IT-7
def test_it7_attack_defence_plumbing_smoke():
    """IT-7: the attack and defence *plumbing* runs end to end.

    This proves the software works. It asserts NOTHING about robustness: G8 did not pass, no
    robust aggregator is integrated, and no defence claim is made.
    """
    import torch

    from src.aggregation.attacks import (
        ATTACK_CONDITIONS,
        adversarial_updates,
        is_attack_condition,
        select_malicious,
    )
    from src.aggregation.defence import (
        RejectionPolicy,
        apply_rejection_policy,
        summarise_accounting,
    )
    from src.aggregation.rules import coordinate_median, get_rule

    clients = [f"client_0{i}" for i in range(1, 6)]
    updates = {cid: torch.randn(36357) * 0.5 for cid in clients}

    malicious = select_malicious(clients, 1)
    assert malicious == ["client_01"]

    attacked = adversarial_updates(updates, malicious, "scaling", scale=5.0, seed=61)
    assert not torch.equal(attacked["client_01"], updates["client_01"])
    assert torch.equal(attacked["client_02"], updates["client_02"])

    kept, accounting = apply_rejection_policy(attacked, RejectionPolicy(3.0), 1)
    assert accounting.accepted, "at least one client must survive"
    summary = summarise_accounting([accounting], malicious)
    assert 0.0 <= (summary["false_positive_rate"] or 0.0) <= 1.0
    assert summary["detection_rate"] is None or 0.0 <= summary["detection_rate"] <= 1.0

    # The aggregation rule composes over the surviving set.
    ordered = sorted(kept)
    aggregated = coordinate_median([kept[c] for c in ordered])
    assert aggregated.shape == (36357,)

    # benign_outlier is a CONTROL, never an attack.
    assert ATTACK_CONDITIONS["benign_outlier"].is_attack is False
    assert is_attack_condition("signflip") is True

    # G8 did not pass, so no robust rule may be presented as validated.
    assert get_rule("median").name == "median"
