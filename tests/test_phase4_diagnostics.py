"""Tests for the Phase 4 diagnostic ablation module."""

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from src.data.phase3_pipeline import CLASS_ORDER
from src.evaluation.phase4_metrics import classification_metrics
from src.training.phase4_diagnostics import (
    DIAGNOSTIC_EXPERIMENT_IDS,
    balanced_class_weights,
    derive_class_weights,
    load_diagnostic_config,
    selection_score,
    sqrt_tempered_balanced_weights,
    training_label_counts,
    validate_diagnostic_config,
)
from src.training.phase4_data import SplitArrays

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "configs" / "models"
TRAIN_COUNTS = {"N": 63989, "S": 1237, "V": 5900, "F": 788, "Q": 13}


def _metrics(y_true, y_pred, macro_classes):
    scores = np.zeros((len(y_true), len(CLASS_ORDER)), dtype=np.float64)
    scores[np.arange(len(y_true)), np.asarray(y_pred)] = 1.0
    return classification_metrics(
        np.asarray(y_true), scores, class_order=CLASS_ORDER, macro_classes=macro_classes
    )


def test_balanced_weights_follow_inverse_frequency() -> None:
    weights = balanced_class_weights(TRAIN_COUNTS)
    assert set(weights) == set(CLASS_ORDER)
    total = sum(TRAIN_COUNTS.values())
    for name in CLASS_ORDER:
        expected = total / (len(CLASS_ORDER) * TRAIN_COUNTS[name])
        assert weights[name] == pytest.approx(expected)


def test_balanced_weights_reject_missing_class() -> None:
    with pytest.raises(ValueError):
        balanced_class_weights({"N": 10, "S": 1, "V": 1, "F": 1})


def test_sqrt_tempering_preserves_rarity_order_and_is_normalised() -> None:
    weights = sqrt_tempered_balanced_weights(TRAIN_COUNTS)
    ordered = [weights[name] for name in ("Q", "F", "S", "V", "N")]
    assert ordered == sorted(ordered, reverse=True)
    assert float(np.mean([weights[name] for name in CLASS_ORDER])) == pytest.approx(1.0)
    assert weights["Q"] < 4.0


def test_declared_config_weights_match_training_derivation() -> None:
    config = load_diagnostic_config(CONFIG_DIR / "phase4_diag_d1_class_weighted.yaml")
    derived = derive_class_weights("sqrt_tempered_balanced", TRAIN_COUNTS)
    for name in CLASS_ORDER:
        assert float(config["training"]["class_weights"][name]) == pytest.approx(
            derived[name], abs=5e-7
        )


def test_both_diagnostic_configs_validate() -> None:
    for experiment_id in DIAGNOSTIC_EXPERIMENT_IDS:
        config = load_diagnostic_config(CONFIG_DIR / f"{experiment_id}.yaml")
        assert config["experiment_id"] == experiment_id
        assert config["expected_split_manifest_sha256"] == config["expected_split_manifest_sha256"]


def test_d2_keeps_unweighted_loss() -> None:
    config = load_diagnostic_config(CONFIG_DIR / "phase4_diag_d2_selection_balanced_accuracy.yaml")
    assert config["training"]["class_weight_method"] == "none"
    assert config["training"]["class_weights"] is None


def test_diagnostic_config_rejects_baseline_recipe_changes() -> None:
    config = load_diagnostic_config(CONFIG_DIR / "phase4_diag_d1_class_weighted.yaml")
    config["training"]["learning_rate"] = 0.01
    with pytest.raises(ValueError):
        validate_diagnostic_config(config)


def test_diagnostic_config_rejects_wrong_selection_metric() -> None:
    config = load_diagnostic_config(CONFIG_DIR / "phase4_diag_d1_class_weighted.yaml")
    config["training"]["early_stopping"]["metric"] = "validation_supported_class_balanced_accuracy"
    with pytest.raises(ValueError):
        validate_diagnostic_config(config)


def test_balanced_accuracy_rewards_minority_recall_where_macro_f1_does_not() -> None:
    macro = ["N", "S", "V", "F"]
    truth = [0, 1, 1, 2, 2, 3]
    predicts_all_n = [0, 0, 0, 0, 0, 0]
    predicts_all_right = [0, 1, 1, 2, 2, 3]

    collapsed = _metrics(truth, predicts_all_n, macro)
    recovered = _metrics(truth, predicts_all_right, macro)

    # Macro-F1 of an all-N predictor is still non-zero because N recall is perfect
    # (F1_N = 2*(1*1/6)/(1+1/6) = 2/7), which is why it can plateau while S recall is zero.
    assert selection_score(collapsed, "validation_supported_class_macro_f1") == pytest.approx(
        (2 / 7) / 4
    )
    assert collapsed["per_class"]["S"]["recall"] == pytest.approx(0.0)
    assert selection_score(collapsed, "validation_supported_class_balanced_accuracy") == pytest.approx(
        0.25
    )
    assert selection_score(recovered, "validation_supported_class_balanced_accuracy") == pytest.approx(
        1.0
    )
    assert selection_score(recovered, "validation_supported_class_macro_f1") == pytest.approx(1.0)


def test_selection_score_rejects_unknown_metric() -> None:
    metrics = _metrics([0, 1], [0, 1], ["N", "S"])
    with pytest.raises(ValueError):
        selection_score(metrics, "accuracy")


def test_training_label_counts_use_class_order() -> None:
    split = SplitArrays(
        x=np.zeros((4, 253), dtype=np.float32),
        y=np.asarray([0, 0, 1, 4], dtype=np.int64),
        record_ids=np.asarray([1, 1, 1, 1], dtype=np.int16),
        sample_positions=np.asarray([0, 1, 2, 3], dtype=np.int64),
    )
    counts = training_label_counts(split)
    assert counts == {"N": 2, "S": 1, "V": 0, "F": 0, "Q": 1}
