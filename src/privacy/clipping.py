"""L2 clipping and sensitivity for the Phase 6 client-level DP mechanism.

See ``docs/PHASE_6_PRIVACY_MATHEMATICS.md`` §4 for the derivation this module implements.

The updte vector is the trainable-parameter delta ``Δ_k = w_local,k − w_global``. BatchNorm
buffers and ``num_batches_tracked`` are deliberately excluded (decision D5); including them
would require re-deriving the sensitivity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch


class PrivacyError(ValueError):
    """Raised when a Phase 6 privacy rule is violated."""


@dataclass(frozen=True)
class ClipResult:
    """Outcome of clipping one client update."""

    tensor: torch.Tensor
    norm_before: float
    norm_after: float
    clipped: bool
    scale: float


def l2_norm(tensor: torch.Tensor) -> float:
    """Euclidean norm, computed in float64 for numerical stability."""
    flat = tensor.detach().to(torch.float64).reshape(-1)
    return float(torch.linalg.vector_norm(flat))


def clip_update(tensor: torch.Tensor, clip_norm: float) -> ClipResult:
    """Project a flat update onto the L2 ball of radius ``clip_norm``.

    ``tensor`` must be the concatenation of the trainable-parameter deltas, so that one
    clip is applied to the whole update vector (per-client-vector clipping).
    """
    if not math.isfinite(clip_norm) or clip_norm <= 0.0:
        raise PrivacyError("Clip norm must be a finite positive number")
    if not torch.is_floating_point(tensor):
        raise PrivacyError("Client update must be a floating-point tensor")
    if not torch.isfinite(tensor).all():
        raise PrivacyError("Client update contains non-finite values")

    before = l2_norm(tensor)
    if before <= clip_norm:
        return ClipResult(tensor.clone(), before, before, False, 1.0)
    scale = float(clip_norm) / before
    clipped = (tensor.to(torch.float64) * scale).to(tensor.dtype)
    after = l2_norm(clipped)
    # The float64 -> float32 cast can nudge the norm a few ULPs past the bound; the
    # tolerance is relative to float32 precision, not a relaxation of the guarantee.
    if after > clip_norm * (1.0 + 1e-5):
        raise PrivacyError("Clipping failed to bound the update norm")
    return ClipResult(clipped, before, after, True, scale)


def per_client_sensitivity(clip_norm: float) -> float:
    """L2 sensitivity for the per-client release (view B).

    With no secure aggregation the server observes each client's noised update directly.
    Under replace-one adjacency with the other clients fixed, one client's contribution can
    change by at most ``2 * clip_norm``. This is the headline sensitivity.
    """
    if not math.isfinite(clip_norm) or clip_norm <= 0.0:
        raise PrivacyError("Clip norm must be a finite positive number")
    return 2.0 * float(clip_norm)


def aggregate_sensitivity(clip_norm: float, max_client_weight: float) -> float:
    """L2 sensitivity if only the weighted aggregate were released (view A).

    Achievable only with secure aggregation, which this architecture does not implement.
    Reported as a lower bound, never as the headline guarantee.
    """
    if not 0.0 < max_client_weight <= 1.0:
        raise PrivacyError("max_client_weight must be in (0, 1]")
    return 2.0 * float(clip_norm) * float(max_client_weight)


def frozen_weights(sample_counts: dict[str, int]) -> dict[str, float]:
    """Aggregation weights from the frozen public sample counts (definition 4.1).

    Using fixed constants makes the released aggregate a fixed linear functional of the
    clipped updates, which is what licenses the sensitivity in
    ``per_client_sensitivity``.
    """
    if not sample_counts:
        raise PrivacyError("At least one client is required")
    total = sum(int(count) for count in sample_counts.values())
    if total <= 0:
        raise PrivacyError("Client sample counts must sum to a positive value")
    weights = {client: int(count) / total for client, count in sample_counts.items()}
    if not math.isclose(sum(weights.values()), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise PrivacyError("Frozen weights must sum to one")
    return weights
