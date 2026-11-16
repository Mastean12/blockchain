"""Phase 6 HE tests: CKKS packing, encryption, homomorphic aggregation, precision."""

import pytest
import torch

from src.privacy.clipping import PrivacyError
from src.privacy.he_ckks import (
    COEFF_MOD_BIT_SIZES,
    HEConfig,
    HEContext,
    SLOTS,
    ciphertext_bytes,
    ciphertext_count,
    homomorphic_weighted_sum,
    relative_l2_error,
)

TRAINABLE_PARAMETERS = 36357


@pytest.fixture(scope="module")
def he() -> HEContext:
    return HEContext(HEConfig())


# ------------------------------------------------------------------- packing
def test_slots_for_approved_degree() -> None:
    assert SLOTS == 4096


def test_ciphertext_count_for_model_vector() -> None:
    assert ciphertext_count(TRAINABLE_PARAMETERS) == 9


def test_ciphertext_count_rejects_zero() -> None:
    with pytest.raises(PrivacyError):
        ciphertext_count(0)


def test_approved_parameter_profile() -> None:
    config = HEConfig()
    assert config.poly_modulus_degree == 8192
    assert list(config.coeff_mod_bit_sizes) == COEFF_MOD_BIT_SIZES == [60, 40, 40, 60]
    assert sum(COEFF_MOD_BIT_SIZES) <= 218, "128-bit classical security cap at N=8192"


# ------------------------------------------------------------- key separation
def test_context_has_secret_key_and_public_context_does_not(he: HEContext) -> None:
    assert he.has_secret_key()
    assert he.public_context.is_public()


# --------------------------------------------------------------- round trip
def test_encrypt_decrypt_round_trip_precision(he: HEContext) -> None:
    torch.manual_seed(0)
    vector = torch.randn(TRAINABLE_PARAMETERS) * 0.05
    ciphertexts = he.encrypt_chunks(vector)
    assert len(ciphertexts) == 9
    recovered = he.decrypt_chunks(ciphertexts, TRAINABLE_PARAMETERS)
    assert relative_l2_error(recovered, vector) < 1e-5


def test_encryption_rejects_non_finite(he: HEContext) -> None:
    with pytest.raises(PrivacyError):
        he.encrypt_chunks(torch.tensor([1.0, float("nan")]))


# --------------------------------------------------------- weighted aggregation
def test_homomorphic_weighted_sum_matches_plaintext(he: HEContext) -> None:
    torch.manual_seed(1)
    updates = {f"c{i}": torch.randn(TRAINABLE_PARAMETERS) * 0.05 for i in range(5)}
    weights = {"c0": 0.371001, "c1": 0.205486, "c2": 0.087033,
               "c3": 0.155004, "c4": 0.181476}
    encrypted = {client: he.encrypt_chunks(vector) for client, vector in updates.items()}
    aggregated = homomorphic_weighted_sum(encrypted, weights)
    decrypted = he.decrypt_chunks(aggregated, TRAINABLE_PARAMETERS)
    exact = sum(updates[client] * weights[client] for client in updates)
    assert relative_l2_error(decrypted, exact) < 1e-5


def test_single_client_aggregation_is_identity(he: HEContext) -> None:
    vector = torch.full((TRAINABLE_PARAMETERS,), 0.01)
    encrypted = {"only": he.encrypt_chunks(vector)}
    aggregated = homomorphic_weighted_sum(encrypted, {"only": 1.0})
    decrypted = he.decrypt_chunks(aggregated, TRAINABLE_PARAMETERS)
    assert relative_l2_error(decrypted, vector) < 1e-6


def test_aggregation_rejects_weight_mismatch(he: HEContext) -> None:
    vector = torch.zeros(16)
    encrypted = {"a": he.encrypt_chunks(vector)}
    with pytest.raises(PrivacyError):
        homomorphic_weighted_sum(encrypted, {"b": 1.0})


def test_aggregation_rejects_empty() -> None:
    with pytest.raises(PrivacyError):
        homomorphic_weighted_sum({}, {})


# ------------------------------------------------------------- communication
def test_ciphertext_is_larger_than_plaintext(he: HEContext) -> None:
    vector = torch.zeros(TRAINABLE_PARAMETERS)
    ciphertexts = he.encrypt_chunks(vector)
    assert ciphertext_bytes(ciphertexts) > TRAINABLE_PARAMETERS * 4


def test_relative_error_rejects_zero_reference() -> None:
    with pytest.raises(PrivacyError):
        relative_l2_error(torch.zeros(4), torch.zeros(4))

# ------------------------------------------------- payload semantics (regression)
def test_absolute_payload_aggregation_is_not_added_to_global() -> None:
    """HE-only sends absolute parameters; DP sends deltas.

    Regression for a defect where the HE-only path added the decrypted absolute
    parameters to the global model, double-counting the weights each round
    (validation loss 5.4 -> 61.6 -> 271.1 over three rounds).
    """
    from src.federated.fedavg import weighted_state_dict

    weights = {"a": 0.6, "b": 0.4}
    states = [
        ({"w": torch.tensor([10.0, 20.0])}, 6),
        ({"w": torch.tensor([0.0, 0.0])}, 4),
    ]
    # Absolute-parameter aggregation: the result *is* the new model value.
    absolute = weighted_state_dict(states)
    assert torch.allclose(absolute["w"], torch.tensor([6.0, 12.0]))

    # Delta aggregation: the result must be added to the current global value.
    global_value = torch.tensor([1.0, 2.0])
    as_delta = global_value + absolute["w"]
    assert torch.allclose(as_delta, torch.tensor([7.0, 14.0]))
    assert not torch.allclose(as_delta, absolute["w"])


def test_weighted_sum_of_absolute_parameters_preserves_scale() -> None:
    """sum p_k w_k with p summing to 1 must stay within the range of the inputs."""
    from src.federated.fedavg import weighted_state_dict

    states = [
        ({"w": torch.full((8,), 1.0)}, 3),
        ({"w": torch.full((8,), 3.0)}, 1),
    ]
    result = weighted_state_dict(states)
    assert float(result["w"].min()) >= 1.0
    assert float(result["w"].max()) <= 3.0
    assert torch.allclose(result["w"], torch.full((8,), 1.5))

def test_decrypted_delta_reference_distinguishes_delta_from_absolute() -> None:
    """Regression: the exact reference must match the encrypted payload.

    In DP+HE the encrypted payload is the update (w_local - w_global); in HE-only it is the
    absolute parameters. Comparing an encrypted delta against an absolute reference produced a
    spurious 52% 'approximation error' while the CKKS primitive itself was accurate to 1.4e-7.
    """
    he = HEContext(HEConfig())
    global_flat = torch.full((TRAINABLE_PARAMETERS,), 0.5)
    local_flat = global_flat + 0.01
    weights = {"a": 1.0}

    delta = local_flat - global_flat
    encrypted = {"a": he.encrypt_chunks(delta)}
    decrypted = he.decrypt_chunks(homomorphic_weighted_sum(encrypted, weights), TRAINABLE_PARAMETERS)

    assert relative_l2_error(decrypted, delta) < 1e-5
    # Against the absolute reference the error is large, which is exactly the bug.
    assert relative_l2_error(decrypted, local_flat) > 0.4
