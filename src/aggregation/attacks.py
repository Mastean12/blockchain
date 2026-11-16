"""Phase 8 attack conditions, implemented per `docs/PHASE_8_ADVERSARY_MODEL.md` §3.

All attacks operate on the flat update vector ``Δ_k`` before aggregation. They never modify local
data, the aggregation rule, the model architecture or the audit ledger.

The ``benign_outlier`` condition is not an attack: it is the control that decides whether a defence
rejects legitimate heterogeneity. It must never be reported as an attack.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import torch


class AttackError(ValueError):
    """Raised when an attack cannot be constructed as specified."""


@dataclass(frozen=True)
class AttackSpec:
    """A named attack condition with its parameters."""

    name: str
    is_attack: bool
    description: str


ATTACK_CONDITIONS: dict[str, AttackSpec] = {
    "clean": AttackSpec("clean", False, "No modification: the honest non-IID condition"),
    "signflip": AttackSpec("signflip", True, "Negate the update: Δ ← −λΔ"),
    "scaling": AttackSpec("scaling", True, "Inflate the update: Δ ← λΔ with λ >> 1"),
    "benign_outlier": AttackSpec(
        "benign_outlier",
        False,
        "Norm-matched random direction: identical norm to the honest update. This is a CONTROL, "
        "not an attack; rejecting it means rejecting honest heterogeneity.",
    ),
}


def sign_flip(update: torch.Tensor, scale: float = 1.0) -> torch.Tensor:
    """Negate the update, optionally scaled.

    With ``scale = 1`` this is the canonical sign-flip attack: the malicious client submits the
    opposite of the direction that would improve the model.
    """
    if scale <= 0:
        raise AttackError("sign-flip scale must be positive")
    return -update.to(torch.float64).mul(scale).to(update.dtype)


def scale_update(update: torch.Tensor, scale: float) -> torch.Tensor:
    """Multiply the update by ``scale``. ``scale`` must exceed 1 to constitute an attack."""
    if scale <= 1.0:
        raise AttackError("update-scaling attack requires scale > 1")
    return update.to(torch.float64).mul(scale).to(update.dtype)


def norm_matched_noise(
    update: torch.Tensor, generator: torch.Generator | None = None
) -> torch.Tensor:
    """Random direction with the same L2 norm as ``update``.

    This is the benign-outlier control. A defence that rejects it is rejecting an update that is
    indistinguishable from an honest one by magnitude.
    """
    flat = update.to(torch.float64).reshape(-1)
    norm = float(torch.linalg.vector_norm(flat))
    if norm == 0.0:
        raise AttackError("Cannot norm-match a zero update")
    if generator is None:
        noise = torch.randn(flat.shape, dtype=torch.float64)
    else:
        noise = torch.randn(flat.shape, dtype=torch.float64, generator=generator)
    direction = noise / torch.linalg.vector_norm(noise)
    return (direction * norm).to(update.dtype).reshape(update.shape)


def apply_attack(
    update: torch.Tensor,
    condition: str,
    *,
    scale: float = 5.0,
    generator: torch.Generator | None = None,
) -> torch.Tensor:
    """Apply a named attack or control condition to one client update."""
    if condition not in ATTACK_CONDITIONS:
        raise AttackError(f"Unknown condition {condition!r}")
    if condition == "clean":
        return update
    if condition == "signflip":
        return sign_flip(update, scale=1.0)
    if condition == "scaling":
        return scale_update(update, scale)
    if condition == "benign_outlier":
        return norm_matched_noise(update, generator)
    raise AttackError(f"Unhandled condition {condition!r}")


def is_attack_condition(condition: str) -> bool:
    """Whether a named condition is an attack (vs a control such as ``benign_outlier``)."""
    if condition not in ATTACK_CONDITIONS:
        raise AttackError(f"Unknown condition {condition!r}")
    return ATTACK_CONDITIONS[condition].is_attack


def select_malicious(
    client_ids: Sequence[str], count: int
) -> list[str]:
    """Choose which clients are malicious.

    Deterministic: the first ``count`` client slots by sorted order. Determinism matters because a
    defence could otherwise appear to work or fail depending on which client was chosen.
    """
    if count < 0:
        raise AttackError("Malicious client count cannot be negative")
    if count >= len(client_ids):
        raise AttackError("All clients cannot be malicious; there would be no honest input")
    return sorted(client_ids)[:count]


def adversarial_updates(
    updates: dict[str, torch.Tensor],
    malicious: Sequence[str],
    condition: str,
    *,
    scale: float = 5.0,
    seed: int = 0,
) -> dict[str, torch.Tensor]:
    """Return updates with the malicious clients transformed.

    Each malicious client uses an independent generator derived from ``(seed, client index)`` so the
    benign-outlier control is reproducible but not identical across clients.
    """
    result = dict(updates)
    generator_base = int(seed)
    for offset, client_id in enumerate(sorted(malicious)):
        if client_id not in updates:
            raise AttackError(f"Malicious client {client_id!r} is not in the update set")
        generator = torch.Generator()
        generator.manual_seed(generator_base * 1000 + offset)
        result[client_id] = apply_attack(
            updates[client_id], condition, scale=scale, generator=generator
        )
    return result
