"""Diagnostic ablations for the frozen Phase 4 centralized baseline.

These runs isolate why the approved recipe never predicts class S. They reuse the
verified frozen data loader, the compact CNN, the metric code and the training loop
from the Phase 4 baseline, changing exactly one factor per experiment:

- D1 ``phase4_diag_d1_class_weighted``: class-weighted cross-entropy, weights derived
  from training label counts only.
- D2 ``phase4_diag_d2_selection_balanced_accuracy``: unweighted loss, but the
  checkpoint-selection score is validation balanced accuracy over supported classes.

The approved baseline config and recipe are never modified by this module.
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from torch import nn

from src.data.phase3_pipeline import CLASS_ORDER
from src.evaluation.phase4_metrics import classification_metrics
from src.training.phase4 import (
    _cpu_state_dict,
    _loader,
    _model,
    _sha256_file,
    _validate_selection_support,
    environment_metadata,
    evaluate_model,
    seed_everything,
    validate_config,
)
from src.training.phase4_data import Phase4Data, SplitArrays, load_phase4_data

DIAGNOSTIC_EXPERIMENT_IDS = (
    "phase4_diag_d1_class_weighted",
    "phase4_diag_d2_selection_balanced_accuracy",
)

SELECTION_METRICS = (
    "validation_supported_class_macro_f1",
    "validation_supported_class_balanced_accuracy",
)

WEIGHT_METHODS = ("none", "sqrt_tempered_balanced")

UNWEIGHTED_CLASS_WEIGHTS = {"N": 1.0, "S": 1.0, "V": 1.0, "F": 1.0, "Q": 1.0}

BASELINE_RECIPE = {
    "schema_version": 1,
    "input_samples": 253,
    "model": {
        "name": "compact_cnn_v1",
        "convolution_blocks": [
            {"input_channels": 1, "output_channels": 32, "kernel_size": 7, "padding": 3, "max_pool": 2},
            {"input_channels": 32, "output_channels": 64, "kernel_size": 5, "padding": 2, "max_pool": 2},
            {"input_channels": 64, "output_channels": 128, "kernel_size": 3, "padding": 1, "max_pool": None},
        ],
        "normalization": "batch_norm_1d",
        "activation": "relu",
        "pooling": "adaptive_average_1d",
        "dropout": 0.3,
        "classifier": "linear_128_to_5",
        "trainable_parameter_count": 36357,
    },
    "training": {
        "optimizer": "AdamW",
        "learning_rate": 0.001,
        "weight_decay": 0.0001,
        "loss": "cross_entropy",
        "batch_size": 256,
        "maximum_epochs": 50,
        "early_stopping": {
            "classes": ["N", "S", "V", "F"],
            "patience": 8,
            "evaluate_epoch_zero": True,
            "tie_policy": "keep_earliest_epoch",
        },
        "seeds": [42, 43, 44, 45, 46],
        "deterministic_algorithms": True,
    },
    "metrics": {
        "absent_class_policy": "not_estimable",
        "validation_macro_classes": ["N", "S", "V", "F"],
        "test_macro_policy": "classes_with_true_support_only",
        "confusion_matrix_class_order": ["N", "S", "V", "F", "Q"],
    },
}


def balanced_class_weights(class_counts: dict[str, int]) -> dict[str, float]:
    """Balanced weights, the sklearn ``balanced`` rule, from training counts only."""
    if set(class_counts) != set(CLASS_ORDER):
        raise ValueError("Class counts must cover the approved class order exactly")
    total = sum(int(class_counts[name]) for name in CLASS_ORDER)
    if total <= 0:
        raise ValueError("Class counts must contain at least one training label")
    weights: dict[str, float] = {}
    for name in CLASS_ORDER:
        count = int(class_counts[name])
        weights[name] = float(total) / (len(CLASS_ORDER) * count) if count > 0 else 0.0
    return weights


def sqrt_tempered_balanced_weights(class_counts: dict[str, int]) -> dict[str, float]:
    """Square-root of the balanced weights, rescaled to mean 1 over the class order.

    Tempering is a monotone function of inverse frequency, so rarity ordering is
    preserved while the smallest-support class cannot dominate a batch gradient.
    """
    balanced = balanced_class_weights(class_counts)
    tempered = {name: float(np.sqrt(balanced[name])) for name in CLASS_ORDER}
    mean = float(np.mean([tempered[name] for name in CLASS_ORDER]))
    if not np.isfinite(mean) or mean <= 0.0:
        raise ValueError("Cannot normalise tempered class weights")
    return {name: tempered[name] / mean for name in CLASS_ORDER}


def derive_class_weights(method: str, class_counts: dict[str, int]) -> dict[str, float]:
    if method == "none":
        return dict(UNWEIGHTED_CLASS_WEIGHTS)
    if method == "sqrt_tempered_balanced":
        return sqrt_tempered_balanced_weights(class_counts)
    raise ValueError(f"Unsupported class weight method: {method}")


def training_label_counts(train_split: SplitArrays) -> dict[str, int]:
    counts = np.bincount(train_split.y.astype(np.int64), minlength=len(CLASS_ORDER))
    return {name: int(counts[index]) for index, name in enumerate(CLASS_ORDER)}


def load_diagnostic_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    validate_diagnostic_config(config)
    return config


def validate_diagnostic_config(config: dict[str, Any]) -> None:
    experiment_id = config.get("experiment_id")
    if experiment_id not in DIAGNOSTIC_EXPERIMENT_IDS:
        raise ValueError(f"Unknown diagnostic experiment id: {experiment_id!r}")
    training = config.get("training", {})
    # Check the frozen recipe against the baseline validator. The diagnostic config's own
    # values are copied in, so any deviation from the approved recipe is rejected here.
    merged = {
        **BASELINE_RECIPE,
        "class_order": config.get("class_order"),
        "expected_split_manifest_sha256": config.get("expected_split_manifest_sha256"),
        "expected_client_manifest_sha256": config.get("expected_client_manifest_sha256"),
        "model": config.get("model"),
        "training": {
            **BASELINE_RECIPE["training"],
            "optimizer": training.get("optimizer"),
            "learning_rate": training.get("learning_rate"),
            "weight_decay": training.get("weight_decay"),
            "loss": training.get("loss"),
            "class_weights": None,
            "batch_size": training.get("batch_size"),
            "maximum_epochs": training.get("maximum_epochs"),
            "seeds": training.get("seeds"),
            "deterministic_algorithms": training.get("deterministic_algorithms"),
            "early_stopping": {
                **BASELINE_RECIPE["training"]["early_stopping"],
                "classes": training.get("early_stopping", {}).get("classes"),
                "patience": training.get("early_stopping", {}).get("patience"),
                "evaluate_epoch_zero": training.get("early_stopping", {}).get("evaluate_epoch_zero"),
                "tie_policy": training.get("early_stopping", {}).get("tie_policy"),
                "metric": "validation_supported_class_macro_f1",
            },
        },
        "metrics": config.get("metrics"),
    }
    validate_config(merged)

    method = training.get("class_weight_method")
    if method not in WEIGHT_METHODS:
        raise ValueError(f"Unknown class_weight_method: {method!r}")
    if method == "none":
        if training.get("class_weights") is not None:
            raise ValueError("Unweighted diagnostics must declare class_weights: null")
    else:
        declared = training.get("class_weights")
        if not isinstance(declared, dict) or set(declared) != set(CLASS_ORDER):
            raise ValueError("Class-weighted diagnostics must declare weights for every class")
        for name in CLASS_ORDER:
            value = float(declared[name])
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"Class weight for {name} must be a finite positive number")

    metric = training["early_stopping"]["metric"]
    if metric not in SELECTION_METRICS:
        raise ValueError(f"Unknown checkpoint-selection metric: {metric!r}")
    if experiment_id.endswith("d2_selection_balanced_accuracy"):
        if metric != "validation_supported_class_balanced_accuracy":
            raise ValueError("D2 must select on validation balanced accuracy")
        if method != "none":
            raise ValueError("D2 must keep the unweighted loss to isolate the selection rule")
    if experiment_id.endswith("d1_class_weighted"):
        if metric != "validation_supported_class_macro_f1":
            raise ValueError("D1 must keep the baseline macro-F1 selection rule")
        if method == "none":
            raise ValueError("D1 must apply class weights")


def selection_score(metrics: dict[str, Any], metric_name: str) -> float:
    """Compute the pre-declared selection score from validation metrics only."""
    if metric_name == "validation_supported_class_macro_f1":
        score = metrics["macro_f1"]
        if score is None:
            raise ValueError("Validation macro-F1 is not estimable for the selection classes")
        return float(score)
    if metric_name == "validation_supported_class_balanced_accuracy":
        included = list(metrics["macro_classes_included"])
        if not included:
            raise ValueError("No validation class supports balanced accuracy")
        recalls = [float(metrics["per_class"][name]["recall"]) for name in included]
        return float(np.mean(recalls))
    raise ValueError(f"Unknown checkpoint-selection metric: {metric_name!r}")


def fit_diagnostic(
    config: dict[str, Any],
    train_split: SplitArrays,
    validation_split: SplitArrays,
    test_split: SplitArrays,
    device: torch.device,
    seed: int,
    checkpoint_path: Path,
    class_weights: dict[str, float],
) -> dict[str, Any]:
    training_config = config["training"]
    batch_size = int(training_config["batch_size"])
    selection_classes = list(training_config["early_stopping"]["classes"])
    selection_metric = str(training_config["early_stopping"]["metric"])
    patience = int(training_config["early_stopping"]["patience"])
    max_epochs = int(training_config["maximum_epochs"])
    _validate_selection_support(validation_split, selection_classes)

    seed_everything(seed, bool(training_config["deterministic_algorithms"]))
    model = _model(config, device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training_config["learning_rate"]),
        weight_decay=float(training_config["weight_decay"]),
    )
    weight_tensor = torch.tensor(
        [float(class_weights[name]) for name in CLASS_ORDER],
        dtype=torch.float32,
        device=device,
    )
    criterion = nn.CrossEntropyLoss(weight=weight_tensor)
    generator = torch.Generator().manual_seed(seed)
    train_loader = _loader(train_split, batch_size, device, shuffle=True, generator=generator)

    best_loss, best_metrics = evaluate_model(
        model, validation_split, batch_size, device, macro_classes=selection_classes
    )
    best_score = selection_score(best_metrics, selection_metric)
    best_epoch = 0
    best_state = _cpu_state_dict(model)
    epochs_without_improvement = 0
    history = [
        {
            "epoch": 0,
            "train_loss": None,
            "validation_loss": best_loss,
            "selection_score": best_score,
            "validation_s_metrics": best_metrics["per_class"]["S"],
        }
    ]

    for epoch in range(1, max_epochs + 1):
        model.train()
        total_loss = 0.0
        sample_count = 0
        for features, labels in train_loader:
            features = features.unsqueeze(1).to(device, non_blocking=device.type == "cuda")
            labels = labels.to(device, non_blocking=device.type == "cuda")
            optimizer.zero_grad(set_to_none=True)
            logits = model(features)
            loss = criterion(logits, labels)
            if not torch.isfinite(loss):
                raise ValueError("Training loss became non-finite")
            loss.backward()
            for parameter in model.parameters():
                if parameter.grad is not None and not torch.isfinite(parameter.grad).all():
                    raise ValueError("A model gradient became non-finite")
            optimizer.step()
            total_loss += float(loss.detach().item()) * len(labels)
            sample_count += len(labels)
        if sample_count == 0:
            raise ValueError("Training loader produced no samples")
        train_loss = total_loss / sample_count

        validation_loss, validation_metrics = evaluate_model(
            model, validation_split, batch_size, device, macro_classes=selection_classes
        )
        score = selection_score(validation_metrics, selection_metric)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "validation_loss": validation_loss,
                "selection_score": score,
                "validation_macro_f1": validation_metrics["macro_f1"],
                "validation_s_metrics": validation_metrics["per_class"]["S"],
            }
        )
        if score > best_score:
            best_score = score
            best_loss = validation_loss
            best_metrics = validation_metrics
            best_epoch = epoch
            best_state = _cpu_state_dict(model)
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
        if epochs_without_improvement >= patience:
            break

    model.load_state_dict(best_state)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(_cpu_state_dict(model), checkpoint_path)
    test_loss, test_metrics = evaluate_model(
        model, test_split, batch_size, device, macro_classes=None
    )
    return {
        "seed": seed,
        "selection_metric": selection_metric,
        "best_selection_score": best_score,
        "best_epoch": best_epoch,
        "epochs_completed": len(history) - 1,
        "best_validation_loss": best_loss,
        "best_validation_metrics": best_metrics,
        "test_loss": test_loss,
        "test_metrics": test_metrics,
        "history": history,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": _sha256_file(checkpoint_path),
    }


def _numeric_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"mean": None, "standard_deviation": None, "run_count": 0}
    return {
        "mean": float(np.mean(values)),
        "standard_deviation": float(np.std(values, ddof=1)) if len(values) > 1 else None,
        "run_count": len(values),
    }


def _evaluation_summary(results: list[dict[str, Any]], metric_key: str) -> dict[str, Any]:
    evaluations = [result[metric_key] for result in results]
    scalar_keys = [
        key for key, value in evaluations[0].items() if isinstance(value, (int, float))
    ]
    overall = {
        key: _numeric_summary(
            [float(evaluation[key]) for evaluation in evaluations if evaluation[key] is not None]
        )
        for key in scalar_keys
    }
    per_class: dict[str, Any] = {}
    for class_name in CLASS_ORDER:
        per_class[class_name] = {}
        for metric_name in evaluations[0]["per_class"][class_name].keys():
            values = [
                float(evaluation["per_class"][class_name][metric_name])
                for evaluation in evaluations
                if evaluation["per_class"][class_name][metric_name] is not None
            ]
            per_class[class_name][metric_name] = _numeric_summary(values)
    matrices = np.asarray([evaluation["confusion_matrix"] for evaluation in evaluations], dtype=np.float64)
    return {
        "overall": overall,
        "per_class": per_class,
        "confusion_matrix": {
            "class_order": [str(name) for name in evaluations[0]["class_order"]],
            "true_support": np.sum(matrices[0], axis=1).astype(int).tolist(),
            "mean": np.mean(matrices, axis=0).tolist(),
            "standard_deviation": (
                np.std(matrices, axis=0, ddof=1).tolist() if len(matrices) > 1 else None
            ),
            "run_count": len(matrices),
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, sort_keys=True)
        file.write("\n")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def run_diagnostic(
    project_root: Path,
    config_path: Path,
    output_dir: Path,
    device_name: str,
) -> dict[str, Any]:
    """Run one diagnostic experiment. Never writes into the baseline output tree."""
    config = load_diagnostic_config(config_path)
    device = torch.device(device_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable; no CPU fallback is automatic")

    data: Phase4Data = load_phase4_data(project_root, config)
    counts = training_label_counts(data.splits["train"])
    method = str(config["training"]["class_weight_method"])
    derived = derive_class_weights(method, counts)
    declared = config["training"].get("class_weights")
    if declared is not None:
        for name in CLASS_ORDER:
            if abs(float(declared[name]) - derived[name]) > 5e-7:
                raise ValueError(
                    f"Declared class weight for {name} ({declared[name]}) does not match "
                    f"the value derived from training counts ({derived[name]})"
                )

    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite diagnostic output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)

    config_bytes = config_path.read_bytes()
    (output_dir / "config.yaml").write_bytes(config_bytes)
    metadata = {
        "experiment_id": config["experiment_id"],
        "parent_experiment_id": config.get("parent_experiment_id"),
        "status": "running",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase4_config_sha256": _sha256_bytes(config_bytes),
        "split_manifest_sha256": data.split_manifest_sha256,
        "client_manifest_sha256": data.client_manifest_sha256,
        "preprocessing_report_sha256": data.preprocessing_report_sha256,
        "environment": environment_metadata(device),
        "model_parameter_count": int(config["model"]["trainable_parameter_count"]),
        "class_weight_method": method,
        "class_weight_source": "train split label counts only",
        "training_label_counts": counts,
        "derived_class_weights": derived,
        "selection_metric": config["training"]["early_stopping"]["metric"],
    }
    metadata_path = output_dir / "run_metadata.json"
    _write_json(metadata_path, metadata)

    seeds = [int(seed) for seed in config["training"]["seeds"]]
    results: list[dict[str, Any]] = []
    progress_path = output_dir / "execution_status.json"
    for index, seed in enumerate(seeds, start=1):
        run_id = f"central_seed_{seed}"
        _write_json(
            progress_path,
            {"status": "running", "current_fit_id": run_id, "completed": index - 1, "expected": len(seeds)},
        )
        started = time.perf_counter()
        run = fit_diagnostic(
            config,
            data.splits["train"],
            data.splits["validation"],
            data.splits["test"],
            device,
            seed,
            output_dir / "checkpoints" / f"{run_id}.pt",
            derived,
        )
        run["run_id"] = run_id
        run["condition"] = "centralized_diagnostic"
        run["client_id"] = None
        run["execution_seconds"] = time.perf_counter() - started
        _write_json(output_dir / f"{run_id}.json", run)
        results.append(run)

    summary = {
        "experiment_id": config["experiment_id"],
        "parent_experiment_id": config.get("parent_experiment_id"),
        "status": "complete",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "seeds": seeds,
        "seed_count": len(seeds),
        "selection_metric": config["training"]["early_stopping"]["metric"],
        "class_weight_method": method,
        "derived_class_weights": derived,
        "training_label_counts": counts,
        "split_manifest_sha256": data.split_manifest_sha256,
        "client_manifest_sha256": data.client_manifest_sha256,
        "phase4_config_sha256": metadata["phase4_config_sha256"],
        "environment": metadata["environment"],
        "runs": results,
        "aggregate": {
            "validation": _evaluation_summary(results, "best_validation_metrics"),
            "test": _evaluation_summary(results, "test_metrics"),
            "execution_seconds": _numeric_summary(
                [float(run["execution_seconds"]) for run in results]
            ),
        },
    }
    _write_json(output_dir / "summary.json", summary)
    metadata["status"] = "complete"
    metadata["completed_at_utc"] = summary["completed_at_utc"]
    _write_json(metadata_path, metadata)
    _write_json(progress_path, {"status": "complete", "completed": len(seeds), "expected": len(seeds)})
    return summary
