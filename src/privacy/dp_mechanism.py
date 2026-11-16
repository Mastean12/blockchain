"""Gaussian DP mechanism and privacy accounting for Phase 6.

Implements the mechanism of ``docs/PHASE_6_PRIVACY_MATHEMATICS.md`` §5: clip, then add
``N(0, σ²C² I)`` noise to every coordinate of the trainable-parameter update vector, then
aggregate.

Two randomness modes are supported and must never be confused:

- ``RESEARCH`` — a seeded ``torch.Generator`` so runs are bit-reproducible. This is **not**
  a CSPRNG and provides no production security. All Phase 6 reported results use this mode.
- ``PRODUCTION`` — reserved, unimplemented. ``SIMULATION_ONLY`` is reported in every artefact.

Accounting uses the Rényi-DP accountant (Mironov 2017) via Opacus, with **full
participation and therefore no subsampling amplification**. A toy closed-form check must
pass before any epsilon is reported; see ``validate_accountant``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch

from src.privacy.clipping import PrivacyError, per_client_sensitivity


class RandomnessMode:
    RESEARCH = "research_seeded"
    PRODUCTION = "production_csprng"


@dataclass(frozen=True)
class AccountantReport:
    """A single epsilon report with the assumptions it depends on."""

    epsilon: float
    delta: float
    noise_multiplier: float
    releases: int
    sensitivity: float
    accountant: str
    accountant_version: str
    sample_rate: float
    amplification: str
    composition: str

    def as_dict(self) -> dict[str, object]:
        return {
            "epsilon": self.epsilon,
            "delta": self.delta,
            "noise_multiplier": self.noise_multiplier,
            "releases": self.releases,
            "sensitivity_l2": self.sensitivity,
            "accountant": self.accountant,
            "accountant_version": self.accountant_version,
            "sample_rate": self.sample_rate,
            "amplification": self.amplification,
            "composition": self.composition,
        }


def add_gaussian_noise(
    tensor: torch.Tensor,
    noise_multiplier: float,
    clip_norm: float,
    generator: torch.Generator | None,
) -> torch.Tensor:
    """Add ``N(0, (σC)²)`` noise independently to every coordinate.

    The noise scale is ``σ · C`` where ``C`` is the clipping norm, so that the ratio of
    noise to sensitivity is exactly ``σ`` and epsilon depends only on ``σ`` and the number
    of releases.
    """
    if not math.isfinite(noise_multiplier) or noise_multiplier <= 0.0:
        raise PrivacyError("Noise multiplier must be a finite positive number")
    if not math.isfinite(clip_norm) or clip_norm <= 0.0:
        raise PrivacyError("Clip norm must be a finite positive number")
    scale = float(noise_multiplier) * float(clip_norm)
    noise = torch.empty(tensor.shape, dtype=torch.float32)
    if generator is None:
        torch.nn.init.normal_(noise, mean=0.0, std=1.0)
    else:
        noise.normal_(mean=0.0, std=1.0, generator=generator)
    return (tensor.to(torch.float64) + noise.to(torch.float64) * scale).to(tensor.dtype)


def make_generator(seed: int, round_index: int, client_index: int) -> torch.Generator:
    """Deterministic per-(seed, round, client) generator for research reproducibility."""
    generator = torch.Generator()
    mixed = (int(seed) * 1_000_003 + int(round_index) * 1_007 + int(client_index)) % (2**31 - 1)
    generator.manual_seed(mixed)
    return generator


def validate_accountant(noise_multiplier: float = 4.0, delta: float = 1e-5) -> dict[str, float]:
    """Closed-form check of the RDP accountant on a one-dimensional Gaussian mechanism.

    Compares the accountant's single-release epsilon against the classical
    Gaussian-mechanism bound ``sqrt(2 ln(1.25/delta)) / sigma``. RDP conversion is expected
    to be slightly tighter, never looser. A failing check blocks the phase.
    """
    from opacus.accountants import RDPAccountant

    accountant = RDPAccountant()
    accountant.step(noise_multiplier=float(noise_multiplier), sample_rate=1.0)
    epsilon = float(accountant.get_epsilon(delta=float(delta)))
    analytic = math.sqrt(2.0 * math.log(1.25 / float(delta))) / float(noise_multiplier)
    if not math.isfinite(epsilon) or epsilon <= 0.0:
        raise PrivacyError("Accountant returned an invalid epsilon")
    if epsilon > analytic * (1.0 + 1e-6):
        raise PrivacyError(
            f"Accountant epsilon {epsilon:.4f} exceeds the analytic bound {analytic:.4f}"
        )
    return {
        "epsilon_accountant": epsilon,
        "epsilon_analytic": analytic,
        "ratio": epsilon / analytic,
    }


def compute_epsilon(
    noise_multiplier: float,
    releases: int,
    delta: float,
    sensitivity: float,
    sample_rate: float = 1.0,
) -> AccountantReport:
    """Epsilon for ``releases`` sequential Gaussian releases.

    ``sample_rate`` must be 1.0 because participation is full: subsampling amplification
    would be invalid here and is therefore refused rather than assumed.
    """
    import opacus

    from opacus.accountants import RDPAccountant

    if not math.isclose(float(sample_rate), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise PrivacyError(
            "Sampling amplification is not valid for this study: participation is full. "
            "sample_rate must be 1.0."
        )
    if int(releases) < 1:
        raise PrivacyError("At least one release is required")
    if not 0.0 < float(delta) < 1.0:
        raise PrivacyError("delta must be in (0, 1)")

    accountant = RDPAccountant()
    for _ in range(int(releases)):
        accountant.step(noise_multiplier=float(noise_multiplier), sample_rate=1.0)
    epsilon = float(accountant.get_epsilon(delta=float(delta)))
    return AccountantReport(
        epsilon=epsilon,
        delta=float(delta),
        noise_multiplier=float(noise_multiplier),
        releases=int(releases),
        sensitivity=float(sensitivity),
        accountant="opacus RDPAccountant (RDP -> (eps,delta))",
        accountant_version=str(opacus.__version__),
        sample_rate=1.0,
        amplification="none (full participation, all five clients every round)",
        composition="sequential composition over releases",
    )


def report_sensitivity_pair(clip_norm: float, max_client_weight: float) -> dict[str, float]:
    """Both accounting views, so results can never silently claim the stronger one."""
    return {
        "sensitivity_per_client_view_b": per_client_sensitivity(clip_norm),
        "sensitivity_aggregate_view_a": 2.0 * clip_norm * max_client_weight,
        "headline_view": "b",
    }
