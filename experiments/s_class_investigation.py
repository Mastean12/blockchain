"""S-class representation and distribution-shift investigation (Phase 4).

Descriptive analysis only. No model is trained on test data and no decision is taken
from test results. All exploratory fitting uses the training split. Validation is used
solely within the approved protocol's role (descriptive comparison of checkpoints and
diagnostics already run). Test is used for descriptive reporting only.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = PROJECT_ROOT / "data" / "processed" / "phase3"
OUT = PROJECT_ROOT / "experiments" / "logs" / "phase4" / "s_class_investigation"
CLASSES = ["N", "S", "V", "F", "Q"]

report = {}


def load(split, name):
    return np.load(PROCESSED / f"{split}_{name}.npy", allow_pickle=False)


def record_counts(record_ids, labels, class_index):
    mask = labels == class_index
    return Counter(record_ids[mask].astype(int).tolist())


# ---------------------------------------------------------------- Q1 morphology
def morphology_stats(x, y, record_ids, class_index):
    """Per-record descriptive waveform statistics for one class."""
    stats = {}
    for record in sorted(set(record_ids[y == class_index].astype(int).tolist())):
        mask = (y == class_index) & (record_ids == record)
        waves = x[mask]
        peak = waves.max(axis=1)
        trough = waves.min(axis=1)
        stats[str(record)] = {
            "count": int(mask.sum()),
            "mean_abs": float(np.abs(waves).mean()),
            "std": float(waves.std()),
            "peak_mean": float(peak.mean()),
            "trough_mean": float(trough.mean()),
            "peak_to_peak_mean": float((peak - trough).mean()),
            "energy_mean": float((waves ** 2).mean()),
        }
    return stats


# ------------------------------------------------- Q3 normalisation effect
def amplitude_profile(x, y, class_index, offsets=(-90, 162)):
    """Relative amplitude of one class against N within the same record."""
    return {
        "mean_abs": float(np.abs(x[y == class_index]).mean()) if (y == class_index).any() else None,
    }


def main() -> None:
    data = {split: {name: load(split, name) for name in ("x", "y", "record_ids", "symbols")}
            for split in ("train", "validation", "test")}

    # Q1: morphology per record, all classes, all splits
    morphology = {}
    for split, arrays in data.items():
        morphology[split] = {}
        for index, name in enumerate(CLASSES):
            morphology[split][name] = morphology_stats(
                arrays["x"], arrays["y"], arrays["record_ids"], index
            )
    report["q1_morphology_per_record"] = morphology

    # Q2: record 232 versus training S records
    train = data["train"]
    train_s_records = record_counts(train["record_ids"], train["y"], 1)
    test = data["test"]
    test_s_records = record_counts(test["record_ids"], test["y"], 1)
    train_s_morph = morphology["train"]["S"]
    test_s_morph = morphology["test"]["S"]

    def shift_table(train_keys, test_key):
        rows = {}
        ref = {k: train_s_morph[k] for k in train_keys if k in train_s_morph}
        if test_key not in test_s_morph:
            return {"missing": test_key}
        target = test_s_morph[test_key]
        for metric in ("mean_abs", "std", "peak_to_peak_mean", "energy_mean"):
            values = np.array([ref[k][metric] for k in ref], dtype=float)
            rows[metric] = {
                "train_mean": float(values.mean()),
                "train_sd": float(values.std(ddof=1)) if len(values) > 1 else None,
                "test_value": float(target[metric]),
                "z_vs_train_records": (
                    float((target[metric] - values.mean()) / values.std(ddof=1))
                    if len(values) > 1 and values.std(ddof=1) > 0 else None
                ),
            }
        return rows

    report["q2_record_232_vs_train"] = {
        "train_s_counts_by_record": dict(train_s_records),
        "test_s_counts_by_record": dict(test_s_records),
        "record_232_share_of_test_S": float(
            test_s_records.get(232, 0) / max(1, sum(test_s_records.values()))
        ),
        "shift": shift_table(list(train_s_records), 232),
        "train_s_records_absent_from_morphology": [
            str(k) for k in train_s_records if str(k) not in train_s_morph
        ],
    }

    # Q3: preprocessing / normalisation effect, per split and class
    normalisation = {}
    for split, arrays in data.items():
        normalisation[split] = {}
        for index, name in enumerate(CLASSES):
            mask = arrays["y"] == index
            if not mask.any():
                continue
            waves = arrays["x"][mask]
            n_mask = arrays["y"] == 0
            n_epoch_energy = (arrays["x"][n_mask] ** 2).mean() if n_mask.any() else None
            normalisation[split][name] = {
                "mean_abs": float(np.abs(waves).mean()),
                "std": float(waves.std()),
                "energy_mean": float((waves ** 2).mean()),
                "energy_ratio_vs_N": (
                    float((waves ** 2).mean() / n_epoch_energy) if n_epoch_energy else None
                ),
            }
    report["q3_normalisation"] = {
        "policy": "global z-score, parameters fit on train only (mean -0.2829528, sd 0.4810947)",
        "per_split_class": normalisation,
    }

    # Q4: window boundary analysis, S vs N template energy distribution across offsets
    def boundary_profile(split, class_index):
        arrays = data[split]
        mask = arrays["y"] == class_index
        if not mask.any():
            return None
        waves = arrays["x"][mask]
        energy = (waves ** 2).mean(axis=0)
        total = energy.sum()
        before = energy[:90 + 1].sum() / total
        qrs = energy[91:163].sum() / total
        after = energy[164:].sum() / total
        return {
            "window_samples": int(waves.shape[1]),
            "annotation_offset_index": 90,
            "energy_fraction_pre_annotation": float(before),
            "energy_fraction_qrs": float(qrs),
            "energy_fraction_post": float(after),
            "peak_energy_sample_offset": int(np.argmax(energy) - 90),
        }

    report["q4_boundaries"] = {
        "window": "253 samples, annotation at index 90 (-90..+162 inclusive)",
        "S": {split: boundary_profile(split, 1) for split in data},
        "N": {split: boundary_profile(split, 0) for split in data},
        "V": {split: boundary_profile(split, 2) for split in data},
    }

    # Q4b: how many S windows have their dominant deflection near the window edge
    def edge_risk(split, class_index):
        arrays = data[split]
        mask = arrays["y"] == class_index
        if mask.sum() == 0:
            return None
        waves = arrays["x"][mask]
        absmax_pos = np.abs(waves).argmax(axis=1)
        near_edge = np.mean((absmax_pos < 10) | (absmax_pos > 242))
        return {
            "fraction_absmax_within_10_samples_of_edge": float(near_edge),
            "absmax_position_p10": float(np.percentile(absmax_pos, 10)),
            "absmax_position_p90": float(np.percentile(absmax_pos, 90)),
        }

    report["q4b_edge_risk"] = {
        cls_name: {split: edge_risk(split, cls_index) for split in data}
        for cls_index, cls_name in enumerate(CLASSES)
    }

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "descriptive.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    print("wrote", OUT / "descriptive.json")
    print("test S records:", dict(test_s_records))
    print("train S records:", len(train_s_records))


if __name__ == "__main__":
    main()
