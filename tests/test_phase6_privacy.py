"""Phase 6 tests: clipping, DP mechanism, accounting, CKKS and the combined flow."""

import math

import pytest
import torch

from src.privacy.clipping import (
    PrivacyError,
    aggregate_sensitivity,
    clip_update,
    frozen_weights,
    l2_norm,
    per_client_sensitivity,
)
from src.privacy.dp_mechanism import (
    add_gaussian_noise,
    compute_epsilon,
    make_generator,
    report_sensitivity_pair,
    validate_accountant,
)


# ------------------------------------------------------------------ clipping
def test_clip_leaves_small_updates_unchanged() -> None:
    tensor = torch.tensor([3.0, 4.0])  # norm 5
    result = clip_update(tensor, 5.0)
    assert not result.clipped
    assert torch.equal(result.tensor, tensor)
    assert result.scale == 1.0


def test_clip_projects_onto_the_ball() -> None:
    tensor = torch.tensor([3.0, 4.0])  # norm 5
    result = clip_update(tensor, 2.5)
    assert result.clipped
    assert result.norm_before == pytest.approx(5.0)
    assert result.norm_after == pytest.approx(2.5, rel=1e-6)
    assert result.scale == pytest.approx(0.5)


def test_clip_preserves_direction() -> None:
    tensor = torch.tensor([1.0, 2.0, 3.0])
    result = clip_update(tensor, 1.0)
    cosine = torch.dot(result.tensor, tensor) / (
        torch.linalg.vector_norm(result.tensor) * torch.linalg.vector_norm(tensor)
    )
    assert float(cosine) == pytest.approx(1.0, abs=1e-6)


def test_clip_rejects_non_positive_norm() -> None:
    with pytest.raises(PrivacyError):
        clip_update(torch.ones(3), 0.0)


def test_clip_rejects_non_finite_update() -> None:
    with pytest.raises(PrivacyError):
        clip_update(torch.tensor([1.0, float("inf")]), 1.0)


def test_clip_bounds_a_large_high_dimensional_update() -> None:
    torch.manual_seed(0)
    tensor = torch.randn(36357) * 10.0
    result = clip_update(tensor, 3.44)
    assert result.clipped
    assert l2_norm(result.tensor) <= 3.44 * (1 + 1e-9)


# ----------------------------------------------------------------- sensitivity
def test_per_client_sensitivity_is_twice_the_clip_norm() -> None:
    assert per_client_sensitivity(3.44) == pytest.approx(6.88)


def test_aggregate_sensitivity_uses_the_max_weight() -> None:
    sensitivity = aggregate_sensitivity(3.44, 0.371001)
    assert sensitivity == pytest.approx(2 * 3.44 * 0.371001)
    assert sensitivity < per_client_sensitivity(3.44)


def test_sensitivity_pair_declares_view_b_as_headline() -> None:
    pair = report_sensitivity_pair(3.44, 0.371001)
    assert pair["headline_view"] == "b"
    assert pair["sensitivity_per_client_view_b"] > pair["sensitivity_aggregate_view_a"]


def test_aggregate_sensitivity_rejects_bad_weight() -> None:
    with pytest.raises(PrivacyError):
        aggregate_sensitivity(3.44, 0.0)
    with pytest.raises(PrivacyError):
        aggregate_sensitivity(3.44, 1.5)


# --------------------------------------------------------------------- weights
def test_frozen_weights_sum_to_one_and_ignore_order() -> None:
    counts = {"client_01": 26685, "client_02": 14780, "client_03": 6260,
              "client_04": 11149, "client_05": 13053}
    weights = frozen_weights(counts)
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-12)
    assert weights["client_01"] == pytest.approx(0.371001, abs=1e-5)


def test_frozen_weights_reject_empty() -> None:
    with pytest.raises(PrivacyError):
        frozen_weights({})


# ----------------------------------------------------------------------- noise
def test_noise_is_deterministic_for_the_same_seed() -> None:
    tensor = torch.zeros(1000)
    first = add_gaussian_noise(tensor, 1.0, 3.44, make_generator(42, 1, 0))
    second = add_gaussian_noise(tensor, 1.0, 3.44, make_generator(42, 1, 0))
    assert torch.equal(first, second)


def test_noise_differs_across_clients_and_rounds() -> None:
    tensor = torch.zeros(1000)
    base = add_gaussian_noise(tensor, 1.0, 3.44, make_generator(42, 1, 0))
    other_client = add_gaussian_noise(tensor, 1.0, 3.44, make_generator(42, 1, 1))
    other_round = add_gaussian_noise(tensor, 1.0, 3.44, make_generator(42, 2, 0))
    assert not torch.equal(base, other_client)
    assert not torch.equal(base, other_round)


def test_noise_scale_matches_sigma_times_clip_norm() -> None:
    torch.manual_seed(0)
    tensor = torch.zeros(200000)
    noisy = add_gaussian_noise(tensor, 2.0, 3.44, None)
    assert float(noisy.std()) == pytest.approx(2.0 * 3.44, rel=0.02)


def test_noise_rejects_non_positive_multiplier() -> None:
    with pytest.raises(PrivacyError):
        add_gaussian_noise(torch.zeros(4), 0.0, 3.44, None)


# ----------------------------------------------------------------- accounting
def test_accountant_toy_gate_passes() -> None:
    report = validate_accountant(noise_multiplier=4.0, delta=1e-5)
    assert report["ratio"] <= 1.0
    assert report["epsilon_accountant"] > 0.0


def test_epsilon_increases_with_more_releases() -> None:
    single = compute_epsilon(1.0, 1, 1e-5, 6.88)
    many = compute_epsilon(1.0, 50, 1e-5, 6.88)
    assert many.epsilon > single.epsilon


def test_epsilon_decreases_with_more_noise() -> None:
    weak = compute_epsilon(0.5, 50, 1e-5, 6.88)
    strong = compute_epsilon(4.0, 50, 1e-5, 6.88)
    assert strong.epsilon < weak.epsilon


def test_epsilon_does_not_depend_on_sensitivity() -> None:
    """C cancels in a relative-noise accountant: C affects utility, not epsilon."""
    small = compute_epsilon(1.0, 50, 1e-5, 3.16)
    large = compute_epsilon(1.0, 50, 1e-5, 6.88)
    assert small.epsilon == pytest.approx(large.epsilon)


def test_epsilon_matches_published_grid() -> None:
    assert compute_epsilon(2.0, 50, 1e-5, 6.88).epsilon == pytest.approx(22.02, rel=1e-3)
    assert compute_epsilon(4.0, 50, 1e-5, 6.88).epsilon == pytest.approx(9.23, rel=1e-3)


def test_accounting_refuses_subsampling_amplification() -> None:
    with pytest.raises(PrivacyError):
        compute_epsilon(1.0, 50, 1e-5, 6.88, sample_rate=0.5)


def test_accounting_rejects_bad_delta_and_releases() -> None:
    with pytest.raises(PrivacyError):
        compute_epsilon(1.0, 50, 0.0, 6.88)
    with pytest.raises(PrivacyError):
        compute_epsilon(1.0, 0, 1e-5, 6.88)


def test_report_records_assumptions() -> None:
    report = compute_epsilon(1.0, 50, 1e-5, 6.88)
    payload = report.as_dict()
    assert payload["amplification"].startswith("none")
    assert payload["sample_rate"] == 1.0
    assert "opacus" in payload["accountant"].lower()
    assert payload["releases"] == 50
