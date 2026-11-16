"""CKKS homomorphic aggregation for Phase 6 (P2 HE-only and P3 HE+DP).

Implements ``docs/PHASE_6_PRIVACY_MATHEMATICS.md`` §7:

- packing of the trainable-parameter update vector into ``ceil(d / (N/2))`` ciphertexts;
- client-side encryption of each clipped/noised update;
- server-side homomorphic weighted sum using public plaintext weights;
- decryption only by the key holder;
- measurement of the relative L2 approximation error.

Security boundary, stated once and repeated in results: CKKS hides ciphertexts from the
key-blind server. It does **not** hide the decrypted aggregate from the secret-key holder,
and it provides no integrity or authenticity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import torch

from src.privacy.clipping import PrivacyError

# Approved profile (decision D6): 128-bit classical security, enough depth for one
# homomorphic add-chain plus one plaintext multiply.
POLY_MODULUS_DEGREE = 8192
COEFF_MOD_BIT_SIZES = [60, 40, 40, 60]
GLOBAL_SCALE_BITS = 40
SLOTS = POLY_MODULUS_DEGREE // 2


def ciphertext_count(elements: int) -> int:
    """Number of ciphertexts needed to pack ``elements`` real values."""
    if elements <= 0:
        raise PrivacyError("Element count must be positive")
    return math.ceil(elements / SLOTS)


@dataclass(frozen=True)
class HEConfig:
    poly_modulus_degree: int = POLY_MODULUS_DEGREE
    coeff_mod_bit_sizes: tuple[int, ...] = tuple(COEFF_MOD_BIT_SIZES)
    global_scale_bits: int = GLOBAL_SCALE_BITS

    def as_dict(self) -> dict[str, Any]:
        return {
            "scheme": "CKKS",
            "library": "tenseal",
            "poly_modulus_degree": self.poly_modulus_degree,
            "coeff_mod_bit_sizes": list(self.coeff_mod_bit_sizes),
            "global_scale": 2**self.global_scale_bits,
            "slots_per_ciphertext": self.poly_modulus_degree // 2,
            "security_source": "HE standard coefficient-modulus table (SEAL); not independently derived",
        }


class HEContext:
    """A CKKS context plus the key separation used by the experiments.

    The public context (with the public key) is what clients receive. The secret key stays
    inside this object and is never serialised or logged.
    """

    def __init__(self, config: HEConfig | None = None) -> None:
        import tenseal as ts

        self._ts = ts
        self.config = config or HEConfig()
        ctx = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=self.config.poly_modulus_degree,
            coeff_mod_bit_sizes=list(self.config.coeff_mod_bit_sizes),
        )
        ctx.global_scale = 2**self.config.global_scale_bits
        ctx.generate_galois_keys()
        self._secret_context = ctx
        # Server-side context: no secret key.
        self.public_context = ctx.copy()
        self.public_context.make_context_public()
        if self.public_context.is_public():
            pass
        else:
            raise PrivacyError("Failed to create a public-only context")

    def has_secret_key(self) -> bool:
        return not self._secret_context.is_public()

    def encrypt_chunks(self, tensor: torch.Tensor) -> list[Any]:
        """Encrypt a flat update vector, returning one ciphertext per chunk."""
        if not torch.is_floating_point(tensor):
            raise PrivacyError("Only floating-point updates can be encrypted")
        if not torch.isfinite(tensor).all():
            raise PrivacyError("Update contains non-finite values")
        flat = tensor.detach().to(torch.float64).reshape(-1).tolist()
        chunks = [
            flat[start:start + SLOTS] for start in range(0, len(flat), SLOTS)
        ]
        return [self._ts.ckks_vector(self.public_context, chunk) for chunk in chunks]

    def decrypt_chunks(self, ciphertexts: list[Any], size: int) -> torch.Tensor:
        """Decrypt and reassemble a flat vector of length ``size``.

        Ciphertexts produced under the public context carry no secret key, so they are
        re-linked to the secret context before decryption. This is why only the holder of
        the secret key can decrypt, and why ``public_context`` can be distributed freely.
        """
        values: list[float] = []
        for ciphertext in ciphertexts:
            if ciphertext.context().is_public():
                linked = self._ts.ckks_vector_from(self._secret_context, ciphertext.serialize())
            else:
                linked = ciphertext
            values.extend(linked.decrypt())
        if len(values) < size:
            raise PrivacyError("Decrypted vector is shorter than expected")
        return torch.tensor(values[:size], dtype=torch.float32)


def homomorphic_weighted_sum(
    client_ciphertexts: dict[str, list[Any]],
    weights: dict[str, float],
) -> list[Any]:
    """Server-side ``Σ_k p_k · c_k`` using only plaintext weights.

    Only ``mul_plain`` and ``add`` are used, so depth is one and no relinearisation or
    bootstrapping is required.
    """
    if not client_ciphertexts:
        raise PrivacyError("No client ciphertexts to aggregate")
    client_ids = sorted(client_ciphertexts)
    lengths = {len(client_ciphertexts[client]) for client in client_ids}
    if len(lengths) != 1:
        raise PrivacyError("Client ciphertext lists have inconsistent lengths")
    if set(weights) != set(client_ids):
        raise PrivacyError("Weights must cover exactly the participating clients")

    chunk_count = lengths.pop()
    aggregated: list[Any] = []
    for index in range(chunk_count):
        total = None
        for client in client_ids:
            scaled = client_ciphertexts[client][index] * float(weights[client])
            total = scaled if total is None else total + scaled
        aggregated.append(total)
    return aggregated


def relative_l2_error(approximate: torch.Tensor, exact: torch.Tensor) -> float:
    """Relative L2 error between a decrypted result and the exact plaintext result."""
    difference = approximate.to(torch.float64) - exact.to(torch.float64)
    denominator = torch.linalg.vector_norm(exact.to(torch.float64))
    if float(denominator) == 0.0:
        raise PrivacyError("Cannot compute relative error against a zero reference")
    return float(torch.linalg.vector_norm(difference) / denominator)


def ciphertext_bytes(ciphertexts: list[Any]) -> int:
    """Serialised ciphertext size in bytes, as transmitted."""
    return sum(len(ciphertext.serialize()) for ciphertext in ciphertexts)
