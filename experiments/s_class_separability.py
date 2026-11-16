"""Q5: feature-space separability of S vs N vs V, training data only.

Exploratory, unsupervised-from-labels feature analysis plus simple labelled classifiers
fit and evaluated by record-grouped cross-validation *within the training split*.
Test data is not read by this script.
"""

import json
from pathlib import Path

import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, recall_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = PROJECT_ROOT / "data" / "processed" / "phase3"
OUT = PROJECT_ROOT / "experiments" / "logs" / "phase4" / "s_class_investigation"


def load(name):
    return np.load(PROCESSED / f"train_{name}.npy", allow_pickle=False)


def features(x):
    """Fixed morphology features, no fitting on evaluation data."""
    peak = x.max(axis=1)
    trough = x.min(axis=1)
    absx = np.abs(x)
    argmax = x.argmax(axis=1) - 90
    argmin = x.argmin(axis=1) - 90
    # coarse shape descriptor: 14-bin mean over the window
    bins = np.array_split(np.arange(x.shape[1]), 14, axis=0)
    binned = np.stack([absx[:, b].mean(axis=1) for b in bins], axis=1)
    return np.column_stack([
        peak, trough, peak - trough, absx.mean(axis=1), x.std(axis=1),
        (x ** 2).mean(axis=1), argmax, argmin, binned,
    ]).astype(np.float64)


def main() -> None:
    x = load("x")
    y = load("y").astype(int)
    records = load("record_ids").astype(int)

    keep = np.isin(y, [0, 1, 2])  # N, S, V
    x, y, records = x[keep], y[keep], records[keep]
    feats = features(x)

    results = {"feature_count": int(feats.shape[1]), "train_windows": int(len(y))}

    gkf = GroupKFold(n_splits=5)
    models = {
        "logistic_regression": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "lda": LinearDiscriminantAnalysis(),
        "random_forest": RandomForestClassifier(
            n_estimators=200, min_samples_leaf=5, class_weight="balanced", random_state=42, n_jobs=-1
        ),
    }

    per_model = {}
    for name, model in models.items():
        s_recall, s_f1, macro_f1, acc = [], [], [], []
        for train_idx, test_idx in gkf.split(feats, y, groups=records):
            scaler = StandardScaler().fit(feats[train_idx])
            xtr, xte = scaler.transform(feats[train_idx]), scaler.transform(feats[test_idx])
            model.fit(xtr, y[train_idx])
            pred = model.predict(xte)
            s_recall.append(recall_score(y[test_idx], pred, labels=[1], average="macro", zero_division=0))
            s_f1.append(f1_score(y[test_idx], pred, labels=[1], average="macro", zero_division=0))
            macro_f1.append(f1_score(y[test_idx], pred, average="macro", zero_division=0))
            acc.append(float((pred == y[test_idx]).mean()))
        per_model[name] = {
            "s_recall_mean": float(np.mean(s_recall)),
            "s_recall_folds": [round(float(v), 4) for v in s_recall],
            "s_f1_mean": float(np.mean(s_f1)),
            "macro_f1_mean": float(np.mean(macro_f1)),
            "accuracy_mean": float(np.mean(acc)),
        }
    results["record_grouped_cv_5fold"] = per_model

    # Feature-space geometry: how separable are the class centroids for S vs N and S vs V
    scaler = StandardScaler().fit(feats)
    z = scaler.transform(feats)
    centroids = {c: z[y == c].mean(axis=0) for c in (0, 1, 2)}
    spread = {c: float(np.mean(np.linalg.norm(z[y == c] - centroids[c], axis=1))) for c in (0, 1, 2)}
    results["centroid_geometry"] = {
        "dist_S_vs_N": float(np.linalg.norm(centroids[1] - centroids[0])),
        "dist_S_vs_V": float(np.linalg.norm(centroids[1] - centroids[2])),
        "dist_N_vs_V": float(np.linalg.norm(centroids[0] - centroids[2])),
        "mean_within_class_radius": {str(c): spread[c] for c in spread},
        "separation_ratio_S_vs_N": float(
            np.linalg.norm(centroids[1] - centroids[0]) / (spread[1] + spread[0])
        ),
        "separation_ratio_S_vs_V": float(
            np.linalg.norm(centroids[1] - centroids[2]) / (spread[1] + spread[2])
        ),
    }

    # Nearest-centroid confusion restricted to S/N/V in training (no fitting beyond centroid)
    labels = np.array([0, 1, 2])
    cents = np.stack([centroids[c] for c in labels])
    dist = np.linalg.norm(z[:, None, :] - cents[None, :, :], axis=2)
    nearest = labels[dist.argmin(axis=1)]
    matrix = np.zeros((3, 3), dtype=int)
    for t, p in zip(y, nearest):
        matrix[labels.tolist().index(t), labels.tolist().index(p)] += 1
    results["nearest_centroid_confusion_train"] = {
        "class_order": ["N", "S", "V"],
        "matrix": matrix.tolist(),
        "S_recall": float(matrix[1, 1] / matrix[1].sum()) if matrix[1].sum() else None,
        "S_predicted_as_N": int(matrix[1, 0]),
        "S_predicted_as_V": int(matrix[1, 2]),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "separability.json").open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
