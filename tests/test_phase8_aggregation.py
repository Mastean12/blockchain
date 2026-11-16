"""Phase 8 tests: aggregation rules, attack conditions, defence accounting, admissibility guards."""

import pytest
import torch

from src.aggregation import (
    ATTACK_CONDITIONS,
    AggregationError,
    AttackError,
    DefenceError,
    RejectionPolicy,
    TrimmedMean,
    adversarial_updates,
    apply_attack,
    apply_rejection_policy,
    check_admissible,
    coordinate_median,
    fedavg,
    get_rule,
    krum,
    multi_krum,
    norm_matched_noise,
    scale_update,
    select_malicious,
    sign_flip,
    summarise_accounting,
    update_norms,
)
from src.aggregation.rules import EXCLUDED_RULES, RULES

DIM = 64


def _honest(count=4, scale=0.1, seed=0):
    torch.manual_seed(seed)
    return [torch.randn(DIM) * scale for _ in range(count)]


# ---------------------------------------------------------------- fedavg
def test_fedavg_matches_weighted_mean():
    updates = [torch.ones(DIM), torch.zeros(DIM)]
    result = fedavg(updates, [3.0, 1.0])
    assert torch.allclose(result, torch.full((DIM,), 0.75), atol=1e-6)


def test_fedavg_rejects_empty_and_bad_weights():
    with pytest.raises(AggregationError):
        fedavg([], [])
    with pytest.raises(AggregationError):
        fedavg([torch.zeros(DIM)], [0.0])


# ---------------------------------------------------------------- median
def test_median_is_coordinate_wise():
    updates = [torch.tensor([1.0, 10.0]), torch.tensor([2.0, 20.0]), torch.tensor([3.0, 30.0])]
    assert torch.allclose(coordinate_median(updates), torch.tensor([2.0, 20.0]))


def test_median_resists_a_single_extreme_update():
    """Median must be substantially more robust than FedAvg, not perfect.

    With 5 honest updates and 1 extreme outlier the median sits between honest values and the
    outlier, so it moves; the meaningful claim is that it moves far less than the mean.
    """
    honest = _honest(count=5, seed=3)
    centroid = fedavg(honest, [1.0] * len(honest))
    corrupt = honest + [torch.full((DIM,), 1e4)]
    median_deviation = float((coordinate_median(corrupt) - centroid).norm() / centroid.norm())
    fedavg_deviation = float(
        (fedavg(corrupt, [1.0] * len(corrupt)) - centroid).norm() / centroid.norm()
    )
    assert median_deviation < fedavg_deviation / 10
    assert fedavg_deviation > 100.0, "an unweighted mean must be destroyed by one extreme update"


# ---------------------------------------------------------- trimmed mean
def test_trimmed_mean_rejects_insufficient_clients():
    with pytest.raises(AggregationError, match="n > 2\\*trim"):
        TrimmedMean(trim=2)([torch.zeros(DIM)] * 4)


def test_trimmed_mean_removes_extremes():
    updates = [torch.tensor([0.0]), torch.tensor([1.0]), torch.tensor([2.0]),
               torch.tensor([3.0]), torch.tensor([1e6])]
    result = TrimmedMean(trim=1)(updates)
    assert float(result) == pytest.approx(2.0)


# ---------------------------------------------------------------- krum
def test_krum_requires_n_at_least_2f_plus_3():
    updates = [torch.zeros(DIM)] * 5
    with pytest.raises(AggregationError, match="2f\\+3"):
        krum(updates, byzantine=2)
    assert krum(updates, byzantine=1).shape == (DIM,)


def test_krum_returns_one_of_the_inputs():
    honest = _honest(count=5, seed=4)
    result = krum(honest, byzantine=1)
    assert any(torch.equal(result, update) for update in honest)


def test_multi_krum_averages_selected_clients():
    honest = _honest(count=5, seed=5)
    result = multi_krum(honest, [1.0] * len(honest), byzantine=1)
    assert result.shape == (DIM,)
    assert not any(torch.equal(result, update) for update in honest), "should be an average"


def test_multi_krum_refuses_degenerate_selection():
    with pytest.raises(AggregationError):
        multi_krum([torch.zeros(DIM)] * 5, [1.0] * 5, byzantine=2)


# ------------------------------------------------------------- registry
def test_all_named_rules_are_registered():
    for name in ("fedavg", "median", "trimmed_mean", "krum", "multi_krum"):
        assert get_rule(name).name == name


def test_fltrust_is_explicitly_excluded():
    assert "fltrust" in EXCLUDED_RULES
    with pytest.raises(AggregationError, match="excluded"):
        get_rule("fltrust")


def test_unknown_rule_is_rejected():
    with pytest.raises(AggregationError, match="Unknown"):
        get_rule("bulyan")


def test_admissibility_guard_matches_rule_bounds():
    check_admissible("krum", 1)
    with pytest.raises(AggregationError):
        check_admissible("krum", 2)
    check_admissible("median", 2)
    with pytest.raises(AggregationError):
        check_admissible("median", 3)


def test_fedavg_is_attackable_because_it_is_the_reference():
    """FedAvg has no robustness, but it must still run under attack as the comparison point."""
    check_admissible("fedavg", 1)
    check_admissible("fedavg", 2)
    assert RULES["fedavg"].max_byzantine == 0, "documented as providing no robustness"


# --------------------------------------------------------------- attacks
def test_attack_registry_marks_benign_outlier_as_control():
    assert ATTACK_CONDITIONS["benign_outlier"].is_attack is False
    assert ATTACK_CONDITIONS["signflip"].is_attack is True
    assert ATTACK_CONDITIONS["scaling"].is_attack is True


def test_sign_flip_negates():
    update = torch.tensor([1.0, -2.0])
    assert torch.allclose(sign_flip(update), torch.tensor([-1.0, 2.0]))


def test_scale_update_requires_scale_above_one():
    with pytest.raises(AttackError):
        scale_update(torch.ones(4), 1.0)
    assert torch.allclose(scale_update(torch.ones(4), 5.0), torch.full((4,), 5.0))


def test_norm_matched_noise_preserves_norm_but_changes_direction():
    update = torch.randn(DIM)
    noisy = norm_matched_noise(update, torch.Generator().manual_seed(0))
    assert float(noisy.norm()) == pytest.approx(float(update.norm()), rel=1e-5)
    assert not torch.allclose(noisy, update)


def test_norm_matched_noise_rejects_zero_update():
    with pytest.raises(AttackError):
        norm_matched_noise(torch.zeros(DIM))


def test_apply_attack_clean_is_identity():
    update = torch.randn(DIM)
    assert torch.equal(apply_attack(update, "clean"), update)


def test_apply_attack_rejects_unknown_condition():
    with pytest.raises(AttackError):
        apply_attack(torch.randn(DIM), "backdoor")


def test_select_malicious_is_deterministic_and_bounded():
    clients = ["client_05", "client_01", "client_03", "client_02", "client_04"]
    assert select_malicious(clients, 1) == ["client_01"]
    assert select_malicious(clients, 2) == ["client_01", "client_02"]
    with pytest.raises(AttackError):
        select_malicious(clients, 5)


def test_adversarial_updates_only_touches_malicious_clients():
    updates = {f"client_0{i}": torch.randn(DIM) for i in range(1, 6)}
    malicious = ["client_02"]
    result = adversarial_updates(updates, malicious, "scaling", scale=10.0, seed=7)
    assert torch.equal(result["client_01"], updates["client_01"])
    assert not torch.equal(result["client_02"], updates["client_02"])


def test_adversarial_updates_rejects_unknown_client():
    updates = {"client_01": torch.randn(DIM)}
    with pytest.raises(AttackError, match="not in the update set"):
        adversarial_updates(updates, ["client_09"], "scaling")


# --------------------------------------------------------------- defence
def test_rejection_policy_validates_ratio():
    with pytest.raises(DefenceError):
        RejectionPolicy(max_norm_ratio=1.0)


def test_rejection_policy_detects_a_scaling_attack():
    updates = {f"client_0{i}": torch.full((DIM,), 1.0) for i in range(1, 6)}
    updates["client_03"] = torch.full((DIM,), 100.0)
    kept, accounting = apply_rejection_policy(updates, RejectionPolicy(3.0), round_index=1)
    assert "client_03" in accounting.rejected
    assert len(accounting.accepted) == 4


def test_rejection_policy_accepts_norm_matched_benign_outliers():
    """The decisive honest-heterogeneity control: a benign outlier must not be rejected."""
    updates = {f"client_0{i}": torch.randn(DIM) for i in range(1, 6)}
    updates["client_04"] = norm_matched_noise(
        updates["client_01"], torch.Generator().manual_seed(1)
    )
    kept, accounting = apply_rejection_policy(updates, RejectionPolicy(3.0), round_index=1)
    assert accounting.rejected == [], "norm-matched honest updates must not be rejected"


def test_rejection_policy_refuses_to_reject_everyone():
    """An attacker larger than every honest client must not cause total rejection."""
    updates = {f"client_0{i}": torch.full((DIM,), 1.0) for i in range(1, 5)}
    updates["client_05"] = torch.full((DIM,), 1e9)
    kept, accounting = apply_rejection_policy(updates, RejectionPolicy(3.0), round_index=1)
    assert "client_05" in accounting.rejected
    assert len(kept) == 4


def test_rejection_policy_handles_degenerate_zero_median():
    """If most updates are zero the threshold must not become a free pass for an outlier."""
    updates = {"client_01": torch.zeros(DIM), "client_02": torch.zeros(DIM),
               "client_03": torch.zeros(DIM), "client_04": torch.full((DIM,), 1.0),
               "client_05": torch.full((DIM,), 1e6)}
    kept, accounting = apply_rejection_policy(updates, RejectionPolicy(3.0), round_index=1)
    assert "client_05" in accounting.rejected
    assert "client_04" in accounting.accepted


def test_update_norms_are_reported():
    updates = {"a": torch.full((4,), 3.0), "b": torch.zeros(4)}
    norms = update_norms(updates)
    assert norms["a"] == pytest.approx(6.0)
    assert norms["b"] == 0.0


def test_accounting_summary_computes_rates():
    from src.aggregation.defence import RoundAccounting

    records = [
        RoundAccounting(1, rejected=["client_02"], accepted=["client_01", "client_03"]),
        RoundAccounting(2, rejected=["client_02"], accepted=["client_01", "client_03"]),
    ]
    summary = summarise_accounting(records, malicious=["client_02"])
    assert summary["detection_rate"] == pytest.approx(1.0)
    assert summary["false_positive_rate"] == pytest.approx(0.0)
    assert summary["malicious_client_rounds"] == 2
    assert summary["honest_client_rounds"] == 4


def test_accounting_summary_flags_false_positives():
    from src.aggregation.defence import RoundAccounting

    records = [RoundAccounting(1, rejected=["client_01"], accepted=["client_03"])]
    summary = summarise_accounting(records, malicious=["client_03"])
    assert summary["false_positive_rate"] == pytest.approx(1.0)
    assert summary["detection_rate"] == pytest.approx(0.0)
