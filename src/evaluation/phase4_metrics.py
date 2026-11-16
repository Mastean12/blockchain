"""Support-aware metrics for the frozen five-class Phase 4 evaluation."""

from collections.abc import Iterable

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


def classification_metrics(
    y_true: np.ndarray,
    y_scores: np.ndarray,
    class_order: Iterable[str],
    macro_classes: Iterable[str] | None = None,
) -> dict[str, object]:
    classes = tuple(class_order)
    if not classes or len(classes) != len(set(classes)):
        raise ValueError("Class order must be non-empty and contain unique names")

    labels = np.asarray(y_true)
    scores = np.asarray(y_scores, dtype=np.float64)
    if labels.ndim != 1 or labels.size == 0:
        raise ValueError("Ground-truth labels must be a non-empty 1D array")
    if not np.issubdtype(labels.dtype, np.integer):
        raise ValueError("Ground-truth labels must use integer class indices")
    if scores.shape != (labels.size, len(classes)):
        raise ValueError(
            f"Scores must have shape ({labels.size}, {len(classes)}), got {scores.shape}"
        )
    if not np.isfinite(scores).all():
        raise ValueError("Scores contain non-finite values")
    if (scores < 0.0).any() or (scores > 1.0).any():
        raise ValueError("Scores must be probabilities in [0, 1]")
    if (labels < 0).any() or (labels >= len(classes)).any():
        raise ValueError("Ground-truth label index is outside the configured class order")

    row_sums = scores.sum(axis=1)
    if not np.allclose(row_sums, 1.0, rtol=1e-5, atol=1e-6):
        raise ValueError("Each score row must contain probabilities summing to one")
    predictions = scores.argmax(axis=1)
    confusion = np.zeros((len(classes), len(classes)), dtype=np.int64)
    np.add.at(confusion, (labels.astype(np.int64), predictions), 1)

    requested_macro = tuple(macro_classes) if macro_classes is not None else classes
    if not requested_macro or len(requested_macro) != len(set(requested_macro)):
        raise ValueError("Macro classes must be non-empty and contain unique names")
    unknown_classes = set(requested_macro) - set(classes)
    if unknown_classes:
        raise ValueError(f"Macro classes are not in the class order: {sorted(unknown_classes)}")

    per_class: dict[str, dict[str, int | float | None]] = {}
    supported_classes: list[str] = []
    precision_classes: list[str] = []
    auroc_classes: list[str] = []
    auprc_classes: list[str] = []
    for index, class_name in enumerate(classes):
        true_positive = int(confusion[index, index])
        support = int(confusion[index, :].sum())
        predicted_support = int(confusion[:, index].sum())
        false_positive = predicted_support - true_positive
        false_negative = support - true_positive
        true_negative = int(confusion.sum()) - true_positive - false_positive - false_negative

        if support == 0:
            precision = recall = f1 = specificity = auroc = auprc = None
        else:
            precision = (
                float(true_positive / predicted_support) if predicted_support > 0 else None
            )
            recall = float(true_positive / support)
            f1_denominator = 2 * true_positive + false_positive + false_negative
            f1 = float(2 * true_positive / f1_denominator) if f1_denominator else None
            specificity_denominator = true_negative + false_positive
            specificity = (
                float(true_negative / specificity_denominator)
                if specificity_denominator
                else None
            )

            binary_truth = labels == index
            if binary_truth.any() and (~binary_truth).any():
                class_scores = scores[:, index]
                auroc = float(roc_auc_score(binary_truth, class_scores))
                auprc = float(average_precision_score(binary_truth, class_scores))
                auroc_classes.append(class_name)
                auprc_classes.append(class_name)
            else:
                auroc = auprc = None

        per_class[class_name] = {
            "support": support,
            "predicted_support": predicted_support,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "specificity": specificity,
            "auroc_ovr": auroc,
            "auprc_ovr": auprc,
        }
        if support > 0:
            supported_classes.append(class_name)
            if precision is not None:
                precision_classes.append(class_name)

    averaged_classes = [
        name for name in requested_macro if per_class[name]["support"] > 0
    ]
    defined_precision_classes = [
        name for name in averaged_classes if per_class[name]["precision"] is not None
    ]
    support_weight = sum(int(per_class[name]["support"]) for name in averaged_classes)
    precision_weight = sum(
        int(per_class[name]["support"]) for name in defined_precision_classes
    )

    def mean_metric(names: list[str], metric_name: str) -> float | None:
        if not names:
            return None
        return float(np.mean([float(per_class[name][metric_name]) for name in names]))

    def weighted_metric(
        names: list[str],
        metric_name: str,
        denominator: int,
    ) -> float | None:
        if denominator == 0:
            return None
        return float(
            sum(
                int(per_class[name]["support"]) * float(per_class[name][metric_name])
                for name in names
            )
            / denominator
        )

    return {
        "accuracy": float(np.trace(confusion) / labels.size),
        "macro_precision": mean_metric(defined_precision_classes, "precision"),
        "macro_recall": mean_metric(averaged_classes, "recall"),
        "macro_f1": mean_metric(averaged_classes, "f1"),
        "weighted_precision": weighted_metric(
            defined_precision_classes, "precision", precision_weight
        ),
        "weighted_recall": weighted_metric(
            averaged_classes, "recall", support_weight
        ),
        "weighted_f1": weighted_metric(averaged_classes, "f1", support_weight),
        "macro_auroc_ovr": mean_metric(auroc_classes, "auroc_ovr"),
        "macro_auprc_ovr": mean_metric(auprc_classes, "auprc_ovr"),
        "macro_classes_requested": list(requested_macro),
        "macro_classes_included": averaged_classes,
        "precision_classes_included": defined_precision_classes,
        "per_class": per_class,
        "confusion_matrix": confusion.tolist(),
        "class_order": list(classes),
        "sample_count": int(labels.size),
        "absent_true_classes": [name for name in classes if name not in supported_classes],
    }
