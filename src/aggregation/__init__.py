"""Robust aggregation for Phase 8.

Rules are justified against the frozen client count K = 5 in
``docs/PHASE_8_BASELINE_JUSTIFICATION.md``; methods whose assumptions fail at this K are refused at
runtime rather than silently producing a wrong answer.
"""

from src.aggregation.attacks import (
    ATTACK_CONDITIONS,
    AttackError,
    AttackSpec,
    apply_attack,
    adversarial_updates,
    is_attack_condition,
    norm_matched_noise,
    scale_update,
    select_malicious,
    sign_flip,
)
from src.aggregation.defence import (
    DefenceError,
    RejectionPolicy,
    RoundAccounting,
    apply_rejection_policy,
    summarise_accounting,
    update_norms,
)
from src.aggregation.rules import (
    EXCLUDED_RULES,
    RULES,
    AggregationError,
    RuleSpec,
    TrimmedMean,
    check_admissible,
    coordinate_median,
    fedavg,
    get_rule,
    krum,
    multi_krum,
)

__all__ = [
    "ATTACK_CONDITIONS",
    "AggregationError",
    "AttackError",
    "AttackSpec",
    "DefenceError",
    "EXCLUDED_RULES",
    "RULES",
    "RejectionPolicy",
    "RoundAccounting",
    "RuleSpec",
    "TrimmedMean",
    "adversarial_updates",
    "apply_attack",
    "apply_rejection_policy",
    "check_admissible",
    "coordinate_median",
    "fedavg",
    "get_rule",
    "is_attack_condition",
    "krum",
    "multi_krum",
    "norm_matched_noise",
    "scale_update",
    "select_malicious",
    "sign_flip",
    "summarise_accounting",
    "update_norms",
]
