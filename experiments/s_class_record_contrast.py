"""Additional checks: per-record S/N contrast and cross-record generalisation of S."""

import json
from pathlib import Path

import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import recall_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = PROJECT_ROOT / "data" / "processed" / "phase3"
OUT = PROJECT_ROOT / "experiments" / "logs" / "phase4" / "s_class_investigation"


def load(split, name):
    return np.load(PROCESSED / f"{split}_{name}.npy", allow_pickle=False)


def main() -> None:
    x = load("train", "x")
    y = load("train", "y").astype(int)
    records = load("train", "record_ids").astype(int)
    out = {}

    # Per-record S-versus-N contrast: is S distinguishable from its own N beats?
    # Separability measured as the per-record gap in normalised energy between S and N.
    contrast = {}
    for record in sorted(set(records.tolist())):
        mask = records == record
        s_mask = mask & (y == 1)
        n_mask = mask & (y == 0)
        if s_mask.sum() == 0 or n_mask.sum() == 0:
            continue
        s_energy = (x[s_mask] ** 2).mean(axis=1)
        n_energy = (x[n_mask] ** 2).mean(axis=1)
        pooled = np.sqrt((s_energy.var(ddof=1) + n_energy.var(ddof=1)) / 2)
        contrast[str(record)] = {
            "s_count": int(s_mask.sum()),
            "n_count": int(n_mask.sum()),
            "s_energy_mean": float(s_energy.mean()),
            "n_energy_mean": float(n_energy.mean()),
            "cohens_d": float((s_energy.mean() - n_energy.mean()) / pooled) if pooled > 0 else None,
        }
    out["per_record_S_vs_N_energy_contrast"] = contrast

    # S-only cross-record generalisation: train on some S records, test on held-out S records.
    # This isolates whether S morphology transfers between patients.
    s_records = sorted(set(records[y == 1].tolist()))
    transfer = {}
    if len(s_records) >= 5:
        s_keep = np.isin(y, [1, 0])  # S versus N only
        xs, ys, rs = x[s_keep], y[s_keep], records[s_keep]
        gkf = GroupKFold(n_splits=5)
        rec_list, f1s, recalls = [], [], []
        for train_idx, test_idx in gkf.split(xs, ys, groups=rs):
            held = sorted(set(rs[test_idx].tolist()))
            tr_s = int((ys[train_idx] == 1).sum())
            te_s = int((ys[test_idx] == 1).sum())
            if tr_s < 20 or te_s < 5:
                rec_list.append({"held": held, "skipped": True})
                continue
            from sklearn.linear_model import LogisticRegression
            model = LogisticRegression(max_iter=2000, class_weight="balanced")
            model.fit(xs[train_idx].reshape(len(train_idx), -1), ys[train_idx])
            pred = model.predict(xs[test_idx].reshape(len(test_idx), -1))
            rec_list.append({
                "held": held,
                "s_train": tr_s,
                "s_test": te_s,
                "s_recall": float(recall_score(ys[test_idx], pred, labels=[1], average="macro", zero_division=0)),
            })
        transfer["held_out_s_record_svsn"] = rec_list

    out["s_record_transfer"] = transfer

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "record_contrast.json").open("w", encoding="utf-8") as file:
        json.dump(out, file, indent=2)

    values = [v["cohens_d"] for v in contrast.values() if v["cohens_d"] is not None]
    print("per-record S vs N Cohen's d: median", round(float(np.median(values)), 3),
          "min", round(float(min(values)), 3), "max", round(float(max(values)), 3),
          "records with |d|>0.8:", sum(1 for v in values if abs(v) > 0.8), "/", len(values))
    for row in transfer.get("held_out_s_record_svsn", []):
        print(row)


if __name__ == "__main__":
    main()
