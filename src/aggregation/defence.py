"""Phase 8 defence wrapper: robust aggregation plus per-client accept/reject accounting.

§21 requires reporting the malicious-client detection rate, the honest-client false-positive rate and
per-client contribution/rejection counts. This module produces those numbers by comparing a robust
rule against a norm-based reference, so that "detection" is a defined quantity rather than an
impression.

**Important scope note.** The rejection rule implemented here is a simple, pre-registered norm
heuristic used to *measure* false positives. It is not claimed to be a novel defence, and the
primary comparison remains the aggregation rules themselves (``rules.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import torch


class DefenceError(ValueError):
    """Raised when a defence configuration is invalid."""


@dataclass(frozen=True)
class RejectionPolicy:
    """Pre-registered norm heuristic for accept/reject accounting.

    ``max_norm_ratio``: reject an update whose L2 norm exceeds this multiple of the median honest
    norm. Frozen before any Phase 8 run at 3.0, matching the Phase 6 clipping analysis where
    updates beyond ~3× the median were rare.
    """

    max_norm_ratio: float = 3.0

    def __post_init__(self) -> None:
        if self.max_norm_ratio <= 1.0:
            raise DefenceError("max_norm_ratio must exceed 1")


@dataclass
class RoundAccounting:
    """Per-round accept/reject record."""

    round_index: int
    rejected: list[str] = field(default_factory=list)
    accepted: list[str] = field(default_factory=list)
    median_norm: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "round": self.round_index,
            "rejected": list(self.rejected),
            "accepted": list(self.accepted),
            "median_norm": self.median_norm,
        }


def update_norms(updates: dict[str, torch.Tensor]) -> dict[str, float]:
    return {
        client_id: float(torch.linalg.vector_norm(update.to(torch.float64).reshape(-1)))
        for client_id, update in updates.items()
    }


def apply_rejection_policy(
    updates: dict[str, torch.Tensor],
    policy: RejectionPolicy,
    round_index: int,
) -> tuple[dict[str, torch.Tensor], RoundAccounting]:
    """Reject updates whose norm exceeds ``policy.max_norm_ratio`` × median norm.

    The median is used rather than the mean so that a small number of scaling attacks cannot move
    the threshold. The policy is deliberately simple and is measured, not optimised.
    """
    norms = update_norms(updates)
    if not norms:
        raise DefenceError("Cannot apply a rejection policy to an empty update set")
    median = float(torch.tensor(sorted(norms.values())).median())
    if median <= 0.0:
        # Degenerate median: half or more of the updates are exactly zero, so a median-relative
        # threshold is meaningless. Fall back to the smallest non-zero norm: a gross outlier is
        # then still rejected relative to the smallest credible update.
        non_zero = sorted(norm for norm in norms.values() if norm > 0.0)
        if not non_zero:
            return dict(updates), RoundAccounting(round_index, [], sorted(updates), median)
        median = non_zero[0]

    threshold = median * policy.max_norm_ratio
    accounting = RoundAccounting(round_index=round_index, median_norm=median)
    kept: dict[str, torch.Tensor] = {}
    for client_id, norm in sorted(norms.items()):
        if norm > threshold:
            accounting.rejected.append(client_id)
        else:
            accounting.accepted.append(client_id)
            kept[client_id] = updates[client_id]

    if not kept:
        raise DefenceError("Rejection policy rejected every client; no aggregation possible")
    return kept, accounting


def summarise_accounting(
    records: Sequence[RoundAccounting],
    malicious: Sequence[str],
) -> dict[str, object]:
    """Compute detection rate and false-positive rate from per-round accounting.

    - detection rate: fraction of *malicious client-rounds* that were rejected
    - false-positive rate: fraction of *honest client-rounds* that were rejected
    """
    malicious_set = set(malicious)

    malicious_rejected = sum(
        len([c for c in record.rejected if c in malicious_set]) for record in records
    )
    honest_rejected = sum(
        len([c for c in record.rejected if c not in malicious_set]) for record in records
    )
    malicious_total = sum(
        len([c for c in (record.accepted + record.rejected) if c in malicious_set])
        for record in records
    )
    honest_total = sum(
        len([c for c in (record.accepted + record.rejected) if c not in malicious_set])
        for record in records
    )

    detection_rate = (
        malicious_rejected / malicious_total if malicious_total else None
    )
    false_positive_rate = honest_rejected / honest_total if honest_total else None

    return {
        "rounds": len(records),
        "malicious_client_rounds": malicious_total,
        "malicious_rejected": malicious_rejected,
        "honest_client_rounds": honest_total,
        "honest_rejected": honest_rejected,
        "detection_rate": detection_rate,
        "false_positive_rate": false_positive_rate,
        "per_round": [record.as_dict() for record in records],
    }
