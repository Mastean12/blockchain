import numpy as np
import pytest

from src.evaluation.phase4_metrics import classification_metrics
from src.data.phase3_pipeline import CLASS_ORDER


def _one_hot(labels):
    scores = np.zeros((len(labels), len(CLASS_ORDER)), dtype=np.float64)
    scores[np.arange(len(labels)), labels] = 1.0
    return scores


def test_validation_macro_f1_excludes_absent_q_and_marks_its_metrics_not_estimable():
    y_true = np.asarray([0, 0, 1, 2, 3], dtype=np.int64)

    metrics = classification_metrics(
        y_true,
        _one_hot(y_true),
        CLASS_ORDER,
        macro_classes=["N", "S", "V", "F"],
    )

    assert metrics["macro_f1"] == pytest.approx(1.0)
    assert metrics["macro_classes_included"] == ["N", "S", "V", "F"]
    assert metrics["absent_true_classes"] == ["Q"]
    assert metrics["per_class"]["Q"]["support"] == 0
    assert metrics["per_class"]["Q"]["precision"] is None
    assert metrics["per_class"]["Q"]["recall"] is None
    assert metrics["per_class"]["Q"]["f1"] is None


def test_test_macro_f1_uses_only_supported_classes_and_does_not_zero_fill_f():
    y_true = np.asarray([0, 1, 2, 4], dtype=np.int64)

    metrics = classification_metrics(y_true, _one_hot(y_true), CLASS_ORDER)

    assert metrics["macro_classes_included"] == ["N", "S", "V", "Q"]
    assert metrics["macro_f1"] == pytest.approx(1.0)
    assert metrics["absent_true_classes"] == ["F"]
    assert metrics["per_class"]["F"]["support"] == 0
    assert metrics["per_class"]["F"]["f1"] is None


def test_supported_class_with_no_predictions_has_na_precision_but_zero_f1():
    y_true = np.asarray([0, 1], dtype=np.int64)
    scores = np.asarray(
        [
            [0.0, 1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )

    metrics = classification_metrics(y_true, scores, CLASS_ORDER)

    assert metrics["per_class"]["N"]["support"] == 1
    assert metrics["per_class"]["N"]["precision"] is None
    assert metrics["per_class"]["N"]["recall"] == 0.0
    assert metrics["per_class"]["N"]["f1"] == 0.0
    assert "N" not in metrics["precision_classes_included"]


def test_metrics_reject_non_probability_rows_and_invalid_labels():
    with pytest.raises(ValueError, match="summing to one"):
        classification_metrics(
            np.asarray([0], dtype=np.int64),
            np.asarray([[0.5, 0.5, 0.5, 0.5, 0.5]]),
            CLASS_ORDER,
        )

    with pytest.raises(ValueError, match="outside"):
        classification_metrics(
            np.asarray([5], dtype=np.int64),
            _one_hot([0]),
            CLASS_ORDER,
        )
