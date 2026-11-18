"""Phase 9 integration layer.

Composes components whose individual gates passed (G3, G4, G5, G6-HE, G7). Robust aggregation is
excluded because G8 did not pass; DP is excluded by recommendation 9-DP-a.
"""

from src.integration.pipeline import (
    EXCLUDED_FROM_INTEGRATION,
    INTEGRATION_MODES,
    IntegrationError,
    IntegrationResult,
    assert_integration_allowed,
    run_integrated,
)

__all__ = [
    "EXCLUDED_FROM_INTEGRATION",
    "INTEGRATION_MODES",
    "IntegrationError",
    "IntegrationResult",
    "assert_integration_allowed",
    "run_integrated",
]
