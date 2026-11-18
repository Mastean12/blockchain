"""Robust aggregation rules for Phase 8.

Every rule here is justified against the frozen client count K = 5 in
``docs/PHASE_8_BASELINE_JUSTIFICATION.md``. Methods whose assumptions fail at this K are refused at
construction time rather than silently returning a wrong answer.

The aggregation operates on **flat update vectors** ``Δ_k = w_local,k − w_global`` so that the same
code serves every rule. ``apply_to_state`` maps the result back onto a state dict without touching
BatchNorm buffers, which are aggregated exactly as in Phases 4–7.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import torch


class AggregationError(ValueError):
    """Raised when a rule cannot be applied to the given inputs."""


# ---------------------------------------------------------------------------------------------
# Baseline: FedAvg (the reference every robust rule is compared against)
# ---------------------------------------------------------------------------------------------
def fedavg(
    updates: Sequence[torch.Tensor], weights: Sequence[float]
) -> torch.Tensor:
    """Sample-count-weighted mean, matching Phases 4–7 exactly."""
    if len(updates) != len(weights):
        raise AggregationError("updates and weights must have equal length")
    if not updates:
        raise AggregationError("Cannot aggregate an empty client set")
    total = float(sum(weights))
    if total <= 0:
        raise AggregationError("Aggregation weights must sum to a positive value")
    stacked = torch.stack([u.to(torch.float64) for u in updates])
    weight_tensor = torch.tensor(weights, dtype=torch.float64).reshape(-1, 1)
    return ((stacked * weight_tensor).sum(dim=0) / total).to(updates[0].dtype)


# ---------------------------------------------------------------------------------------------
# Coordinate-wise median (Yin et al. 2018)
# ---------------------------------------------------------------------------------------------
def coordinate_median(updates: Sequence[torch.Tensor]) -> torch.Tensor:
    """Coordinate-wise median.

    Assumption: fewer than n/2 Byzantine clients. At K = 5 this holds for f <= 2.
    """
    if not updates:
        raise AggregationError("Cannot aggregate an empty client set")
    stacked = torch.stack([u.to(torch.float64) for u in updates])
    return stacked.median(dim=0).values.to(updates[0].dtype)


# ---------------------------------------------------------------------------------------------
# Trimmed mean (Yin et al. 2018)
# ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class TrimmedMean:
    """Coordinate-wise trimmed mean, trimming ``trim`` from each tail.

    Assumption: n > 2·trim. At K = 5 a trim of 1 removes 2 of 5 values, leaving 3.
    """

    trim: int = 1

    def __call__(self, updates: Sequence[torch.Tensor]) -> torch.Tensor:
        count = len(updates)
        if count <= 2 * self.trim:
            raise AggregationError(
                f"Trimmed mean requires n > 2*trim; got n={count}, trim={self.trim}"
            )
        stacked = torch.stack([u.to(torch.float64) for u in updates]).sort(dim=0).values
        kept = stacked[self.trim:count - self.trim]
        return kept.mean(dim=0).to(updates[0].dtype)


# ---------------------------------------------------------------------------------------------
# Krum / Multi-Krum (Blanchard et al. 2017)
# ---------------------------------------------------------------------------------------------
def _pairwise_distances(updates: Sequence[torch.Tensor]) -> torch.Tensor:
    stacked = torch.stack([u.to(torch.float64).reshape(-1) for u in updates])
    # Explicit pairwise squared distances; K is tiny so this is cheap and exact.
    diff = stacked.unsqueeze(0) - stacked.unsqueeze(1)
    return (diff * diff).sum(dim=2)


def krum(updates: Sequence[torch.Tensor], byzantine: int = 1) -> torch.Tensor:
    """Single Krum: return the update with the smallest sum of distances to its nearest
    ``n - f - 2`` neighbours.

    Assumption: ``n >= 2f + 3``. At K = 5 this holds **only for f = 1** (5 >= 5). Requesting
    f = 2 raises, because the selection would be undefined rather than merely weak.
    """
    count = len(updates)
    if count < 2 * byzantine + 3:
        raise AggregationError(
            f"Krum requires n >= 2f+3 (n={count}, f={byzantine}); "
            f"at K=5 only f=1 is admissible"
        )
    distances = _pairwise_distances(updates)
    neighbours = count - byzantine - 2
    scores = []
    for index in range(count):
        own = distances[index].clone()
        own[index] = float("inf")
        nearest, _ = torch.sort(own)[:neighbours]
        scores.append(float(nearest.sum()))
    return updates[int(torch.tensor(scores).argmin())]


def multi_krum(
    updates: Sequence[torch.Tensor],
    weights: Sequence[float],
    byzantine: int = 1,
    selected: int | None = None,
) -> torch.Tensor:
    """Multi-Krum: average the ``selected`` updates with the lowest Krum scores.

    ``selected`` defaults to ``n - f - 2``. At K = 5, f = 1 that is 2; at f = 2 it would be 1,
    which degenerates to single-client selection and is refused.
    """
    count = len(updates)
    if count < 2 * byzantine + 3:
        raise AggregationError(
            f"Multi-Krum requires n >= 2f+3 (n={count}, f={byzantine}); at K=5 only f=1 is admissible"
        )
    choose = selected if selected is not None else count - byzantine - 2
    if choose < 2:
        raise AggregationError(
            f"Multi-Krum would select {choose} client(s); averaging fewer than 2 is degenerate"
        )
    distances = _pairwise_distances(updates)
    neighbours = count - byzantine - 2
    scores = []
    for index in range(count):
        own = distances[index].clone()
        own[index] = float("inf")
        nearest, _ = torch.sort(own)[:neighbours]
        scores.append(float(nearest.sum()))
    order = torch.argsort(torch.tensor(scores))[:choose].tolist()
    chosen_updates = [updates[i] for i in order]
    chosen_weights = [weights[i] for i in order]
    return fedavg(chosen_updates, chosen_weights)


# ---------------------------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------------------------
def _trimmed_mean_factory(**kwargs) -> Callable:
    trim = int(kwargs.get("trim", 1))
    return TrimmedMean(trim=trim)


@dataclass(frozen=True)
class RuleSpec:
    """A named aggregation rule plus the assumption it relies on at the frozen K = 5."""

    name: str
    callable: Callable
    max_byzantine: int
    assumption: str
    reference: str


RULES: dict[str, RuleSpec] = {
    "fedavg": RuleSpec(
        name="fedavg",
        callable=lambda updates, weights: fedavg(updates, weights),
        max_byzantine=0,
        assumption="none (not robust: a single adversary can move the mean arbitrarily)",
        reference="McMahan et al. 2017",
    ),
    "median": RuleSpec(
        name="median",
        callable=lambda updates, weights: coordinate_median(updates),
        max_byzantine=2,
        assumption="f < n/2; at K=5 holds for f<=2",
        reference="Yin et al. 2018",
    ),
    "trimmed_mean": RuleSpec(
        name="trimmed_mean",
        callable=lambda updates, weights: _trimmed_mean_factory()(updates),
        max_byzantine=2,
        assumption="n > 2*trim; trim=1 at K=5 leaves 3 of 5",
        reference="Yin et al. 2018",
    ),
    "krum": RuleSpec(
        name="krum",
        callable=lambda updates, weights: krum(updates, byzantine=1),
        max_byzantine=1,
        assumption="n >= 2f+3; at K=5 valid only for f=1",
        reference="Blanchard et al. 2017",
    ),
    "multi_krum": RuleSpec(
        name="multi_krum",
        callable=lambda updates, weights: multi_krum(updates, weights, byzantine=1),
        max_byzantine=1,
        assumption="n >= 2f+3; at K=5 valid only for f=1, selecting 2 clients",
        reference="Blanchard et al. 2017",
    ),
}

# FLTrust is deliberately excluded: it requires a clean server-side root dataset, which this study
# does not have. §20 forbids including a method whose assumptions are violated. Recorded here so the
# omission is a documented decision, not an oversight.
EXCLUDED_RULES = {
    "fltrust": "requires a clean server-side root dataset; none exists in this study",
}


def get_rule(name: str) -> RuleSpec:
    if name in EXCLUDED_RULES:
        raise AggregationError(
            f"{name} is excluded: {EXCLUDED_RULES[name]}. See PHASE_8_BASELINE_JUSTIFICATION.md"
        )
    if name not in RULES:
        raise AggregationError(f"Unknown aggregation rule {name!r}; available: {sorted(RULES)}")
    return RULES[name]


def check_admissible(name: str, byzantine: int) -> None:
    """Refuse a rule/attack combination that violates the rule's assumption.

    ``fedavg`` is exempt: it is the *reference* that attacks are expected to defeat, so it must be
    run under attack for the comparison to exist. Its ``max_byzantine = 0`` documents that it
    provides no robustness, not that it may not be attacked.
    """
    spec = get_rule(name)
    if spec.name == "fedavg":
        return
    if byzantine > spec.max_byzantine:
        raise AggregationError(
            f"{name} supports at most f={spec.max_byzantine} Byzantine clients "
            f"({spec.assumption}); requested f={byzantine}"
        )


# ---------------------------------------------------------------------------------------------
# Server step size (Phase 8 amendment 3D)
# ---------------------------------------------------------------------------------------------
def apply_server_step(
    aggregate: torch.Tensor, step_size: float
) -> torch.Tensor:
    """Scale an aggregated update by a server step size before applying it.

    Proposal 3D. The Phase 8 failure analysis found that every run which survived had its
    per-round update norm decay to below 40 % of round 1 by round 4, while runs that diverged
    typically grew. A step size below 1 damps the round-to-round feedback that drives that growth.

    This is a *server* operation: it changes how far the global model moves each round, not what
    any aggregation rule computes. ``step_size=1.0`` reproduces the original behaviour exactly and
    is the default, so existing results are unaffected.
    """
    if not (0.0 < float(step_size) <= 1.0):
        raise AggregationError(
            f"step_size must be in (0, 1]; got {step_size}. Values above 1 amplify updates "
            "and are not part of this proposal."
        )
    if float(step_size) == 1.0:
        return aggregate
    return (aggregate.to(torch.float64) * float(step_size)).to(aggregate.dtype)
