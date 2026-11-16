"""Phase 4 majority, centralized, and local-only baseline execution."""

import hashlib
import json
import os
import platform
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import sklearn
import torch
import yaml
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from src.data.phase3_pipeline import CLASS_ORDER
from src.evaluation.phase4_metrics import classification_metrics
from src.models.cnn1d import CompactECGCNN, trainable_parameter_count
from src.training.phase4_data import Phase4Data, SplitArrays, load_phase4_data


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported Phase 4 config schema")
    if config.get("class_order") != list(CLASS_ORDER):
        raise ValueError("Phase 4 class order differs from the approved mapping")
    if int(config.get("input_samples", 0)) != 253:
        raise ValueError("Phase 4 requires 253-sample windows")
    if config["model"]["name"] != "compact_cnn_v1":
        raise ValueError("Unsupported Phase 4 model")
    if int(config["model"]["trainable_parameter_count"]) != 36357:
        raise ValueError("Configured CNN parameter count does not match compact_cnn_v1")
    expected_blocks = [
        {
            "input_channels": 1,
            "output_channels": 32,
            "kernel_size": 7,
            "padding": 3,
            "max_pool": 2,
        },
        {
            "input_channels": 32,
            "output_channels": 64,
            "kernel_size": 5,
            "padding": 2,
            "max_pool": 2,
        },
        {
            "input_channels": 64,
            "output_channels": 128,
            "kernel_size": 3,
            "padding": 1,
            "max_pool": None,
        },
    ]
    if config["model"]["convolution_blocks"] != expected_blocks:
        raise ValueError("Configured convolution blocks differ from compact_cnn_v1")
    if float(config["model"]["dropout"]) != 0.3:
        raise ValueError("Phase 4 dropout differs from the approved compact_cnn_v1 recipe")
    training = config["training"]
    if training["optimizer"] != "AdamW" or training["loss"] != "cross_entropy":
        raise ValueError("Phase 4 optimizer or loss differs from the approved recipe")
    if training["class_weights"] is not None:
        raise ValueError("The approved Phase 4 baseline uses unweighted cross-entropy")
    if int(training["batch_size"]) != 256 or int(training["maximum_epochs"]) != 50:
        raise ValueError("Phase 4 batch size or epoch budget differs from the approved recipe")
    if float(training["learning_rate"]) != 0.001 or float(training["weight_decay"]) != 0.0001:
        raise ValueError("Phase 4 AdamW parameters differ from the approved recipe")
    if training["early_stopping"]["classes"] != ["N", "S", "V", "F"]:
        raise ValueError("Validation selection must use supported classes N/S/V/F")
    if int(training["early_stopping"]["patience"]) != 8:
        raise ValueError("Phase 4 early-stopping patience differs from the approved recipe")
    seeds = training["seeds"]
    if not seeds or len(seeds) != len(set(seeds)) or any(int(seed) < 0 for seed in seeds):
        raise ValueError("Phase 4 seeds must be unique non-negative integers")
    if [int(seed) for seed in seeds] != [42, 43, 44, 45, 46]:
        raise ValueError("Phase 4 full runs must use the approved seeds 42–46")
    if config["metrics"]["validation_macro_classes"] != ["N", "S", "V", "F"]:
        raise ValueError("Validation selection classes must be N/S/V/F")
    if config["training"]["early_stopping"]["metric"] != "validation_supported_class_macro_f1":
        raise ValueError("Phase 4 checkpoint metric differs from the approved rule")
    if (
        not config["training"]["early_stopping"]["evaluate_epoch_zero"]
        or config["training"]["early_stopping"]["tie_policy"] != "keep_earliest_epoch"
        or not training["deterministic_algorithms"]
    ):
        raise ValueError("Phase 4 checkpoint or deterministic training policy changed")
    if config["metrics"]["absent_class_policy"] != "not_estimable":
        raise ValueError("Undefined class metrics must remain not estimable")
    if config["metrics"]["test_macro_policy"] != "classes_with_true_support_only":
        raise ValueError("Test metric support policy changed")


def seed_everything(seed: int, deterministic_algorithms: bool = True) -> None:
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(deterministic_algorithms)


def _dataset(split: SplitArrays) -> TensorDataset:
    features = torch.from_numpy(np.ascontiguousarray(split.x, dtype=np.float32))
    labels = torch.from_numpy(np.ascontiguousarray(split.y, dtype=np.int64))
    return TensorDataset(features, labels)


def _loader(
    split: SplitArrays,
    batch_size: int,
    device: torch.device,
    shuffle: bool,
    generator: torch.Generator | None = None,
) -> DataLoader:
    return DataLoader(
        _dataset(split),
        batch_size=batch_size,
        shuffle=shuffle,
        generator=generator,
        num_workers=0,
        pin_memory=device.type == "cuda",
    )


def _train_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
) -> float:
    model.train()
    total_loss = 0.0
    sample_count = 0
    for features, labels in loader:
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
    return total_loss / sample_count


def evaluate_model(
    model: nn.Module,
    split: SplitArrays,
    batch_size: int,
    device: torch.device,
    macro_classes: list[str] | None = None,
) -> tuple[float, dict[str, object]]:
    model.eval()
    criterion = nn.CrossEntropyLoss()
    loader = _loader(split, batch_size, device, shuffle=False)
    labels_all: list[np.ndarray] = []
    scores_all: list[np.ndarray] = []
    total_loss = 0.0
    sample_count = 0
    with torch.inference_mode():
        for features, labels in loader:
            features = features.unsqueeze(1).to(device, non_blocking=device.type == "cuda")
            labels_device = labels.to(device, non_blocking=device.type == "cuda")
            logits = model(features)
            loss = criterion(logits, labels_device)
            if not torch.isfinite(loss):
                raise ValueError("Evaluation loss became non-finite")
            probabilities = torch.softmax(logits, dim=1)
            total_loss += float(loss.item()) * len(labels)
            sample_count += len(labels)
            labels_all.append(labels.numpy())
            scores_all.append(probabilities.cpu().numpy())
    if sample_count == 0:
        raise ValueError("Evaluation split contains no samples")
    labels_np = np.concatenate(labels_all)
    scores_np = np.concatenate(scores_all)
    metrics = classification_metrics(
        labels_np,
        scores_np,
        class_order=CLASS_ORDER,
        macro_classes=macro_classes,
    )
    return total_loss / sample_count, metrics


def _cpu_state_dict(model: nn.Module) -> dict[str, torch.Tensor]:
    return {name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _model(config: dict[str, Any], device: torch.device) -> CompactECGCNN:
    model = CompactECGCNN(
        input_samples=int(config["input_samples"]),
        class_count=len(CLASS_ORDER),
        dropout=float(config["model"]["dropout"]),
    ).to(device)
    actual_parameters = trainable_parameter_count(model)
    expected_parameters = int(config["model"]["trainable_parameter_count"])
    if actual_parameters != expected_parameters:
        raise ValueError(
            f"Model has {actual_parameters} trainable parameters; expected {expected_parameters}"
        )
    return model


def _validate_selection_support(split: SplitArrays, classes: list[str]) -> None:
    counts = np.bincount(split.y.astype(np.int64), minlength=len(CLASS_ORDER))
    missing = [name for name in classes if counts[CLASS_ORDER.index(name)] == 0]
    if missing:
        raise ValueError(
            "Checkpoint-selection classes are absent from validation: "
            + ", ".join(missing)
        )


def fit_and_evaluate(
    config: dict[str, Any],
    train_split: SplitArrays,
    validation_split: SplitArrays,
    test_split: SplitArrays,
    device: torch.device,
    seed: int,
    checkpoint_path: Path,
) -> dict[str, Any]:
    training_config = config["training"]
    batch_size = int(training_config["batch_size"])
    selection_classes = list(training_config["early_stopping"]["classes"])
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
    criterion = nn.CrossEntropyLoss()
    generator = torch.Generator().manual_seed(seed)
    train_loader = _loader(train_split, batch_size, device, shuffle=True, generator=generator)

    best_loss, best_metrics = evaluate_model(
        model, validation_split, batch_size, device, macro_classes=selection_classes
    )
    best_score = float(best_metrics["macro_f1"])
    best_epoch = 0
    best_state = _cpu_state_dict(model)
    epochs_without_improvement = 0
    history = [{
        "epoch": 0,
        "train_loss": None,
        "validation_loss": best_loss,
        "validation_macro_f1": best_score,
    }]

    for epoch in range(1, max_epochs + 1):
        train_loss = _train_epoch(model, train_loader, optimizer, criterion, device)
        validation_loss, validation_metrics = evaluate_model(
            model, validation_split, batch_size, device, macro_classes=selection_classes
        )
        validation_score = float(validation_metrics["macro_f1"])
        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "validation_loss": validation_loss,
            "validation_macro_f1": validation_score,
        })
        if validation_score > best_score:
            best_score = validation_score
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
    train_counts = np.bincount(train_split.y.astype(np.int64), minlength=len(CLASS_ORDER))
    return {
        "seed": seed,
        "training_window_class_counts": {
            class_name: int(train_counts[index])
            for index, class_name in enumerate(CLASS_ORDER)
        },
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


def majority_baseline(data: Phase4Data, config: dict[str, Any]) -> dict[str, Any]:
    train = data.splits["train"]
    class_counts = np.bincount(train.y.astype(np.int64), minlength=len(CLASS_ORDER))
    majority_index = int(class_counts.argmax())
    result: dict[str, Any] = {
        "baseline": "training_majority_class",
        "predicted_class": CLASS_ORDER[majority_index],
        "training_class_counts": {
            name: int(class_counts[index]) for index, name in enumerate(CLASS_ORDER)
        },
        "split_manifest_sha256": data.split_manifest_sha256,
        "evaluations": {},
    }
    for split_name in ("validation", "test"):
        split = data.splits[split_name]
        scores = np.zeros((len(split.y), len(CLASS_ORDER)), dtype=np.float64)
        scores[:, majority_index] = 1.0
        macro_classes = (
            list(config["training"]["early_stopping"]["classes"])
            if split_name == "validation"
            else None
        )
        result["evaluations"][split_name] = classification_metrics(
            split.y.astype(np.int64),
            scores,
            class_order=CLASS_ORDER,
            macro_classes=macro_classes,
        )
    return result


def environment_metadata(device: torch.device) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "numpy_version": np.__version__,
        "scikit_learn_version": sklearn.__version__,
        "pyyaml_version": yaml.__version__,
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "device": str(device),
        "cuda_available": torch.cuda.is_available(),
    }
    if device.type == "cuda":
        metadata["cuda_device_name"] = torch.cuda.get_device_name(device)
        metadata["cuda_device_capability"] = list(torch.cuda.get_device_capability(device))
    return metadata


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, indent=2, sort_keys=True, default=_json_default, allow_nan=False)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary_path, path)


def _subset_records(split: SplitArrays, record_ids: list[str]) -> SplitArrays:
    selected = np.isin(split.record_ids.astype(np.int64).astype(str), record_ids)
    if not selected.any():
        raise ValueError(f"No training windows were found for records {record_ids}")
    return SplitArrays(
        x=split.x[selected],
        y=split.y[selected],
        record_ids=split.record_ids[selected],
        sample_positions=split.sample_positions[selected],
    )


def _numeric_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"mean": None, "standard_deviation": None, "run_count": 0}
    return {
        "mean": float(np.mean(values)),
        "standard_deviation": float(np.std(values, ddof=1)) if len(values) > 1 else None,
        "run_count": len(values),
    }


def _evaluation_summary(
    results: list[dict[str, Any]], metric_key: str
) -> dict[str, Any]:
    evaluations = [result[metric_key] for result in results]
    scalar_keys = [
        key
        for key, value in evaluations[0].items()
        if isinstance(value, (int, float))
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
        metric_names = evaluations[0]["per_class"][class_name].keys()
        for metric_name in metric_names:
            values = [
                float(evaluation["per_class"][class_name][metric_name])
                for evaluation in evaluations
                if evaluation["per_class"][class_name][metric_name] is not None
            ]
            per_class[class_name][metric_name] = _numeric_summary(values)

    matrices = np.asarray(
        [evaluation["confusion_matrix"] for evaluation in evaluations], dtype=np.float64
    )
    confusion_summary = {
        "class_order": list(CLASS_ORDER),
        "true_support": np.sum(matrices[0], axis=1).astype(int).tolist(),
        "mean": np.mean(matrices, axis=0).tolist(),
        "standard_deviation": (
            np.std(matrices, axis=0, ddof=1).tolist()
            if len(matrices) > 1
            else None
        ),
        "run_count": len(matrices),
    }
    return {
        "overall": overall,
        "per_class": per_class,
        "confusion_matrix": confusion_summary,
    }


def _load_completed_fit(
    run_path: Path,
    checkpoint_path: Path,
    run_id: str,
    condition: str,
    client_id: str | None,
    seed: int,
) -> dict[str, Any] | None:
    if not run_path.exists():
        if checkpoint_path.exists():
            raise ValueError(
                f"Found a checkpoint without its completed run report: {checkpoint_path}"
            )
        return None

    with run_path.open(encoding="utf-8") as file:
        result = json.load(file)
    if (
        result.get("run_id") != run_id
        or result.get("condition") != condition
        or result.get("client_id") != client_id
        or result.get("seed") != seed
    ):
        raise ValueError(f"Existing Phase 4 result does not match expected run {run_id}")
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"Completed run {run_id} has no checkpoint: {checkpoint_path}")
    if _sha256_file(checkpoint_path) != result.get("checkpoint_sha256"):
        raise ValueError(f"Checkpoint hash mismatch for completed run {run_id}")
    if result.get("checkpoint") != str(checkpoint_path):
        raise ValueError(f"Checkpoint path mismatch for completed run {run_id}")
    if not isinstance(result.get("execution_seconds"), (int, float)):
        raise ValueError(f"Completed run {run_id} has no valid execution time")
    return result


def run_phase4(
    project_root: Path,
    config_path: Path,
    output_dir: Path,
    device_name: str,
    smoke_test: bool = False,
    resume: bool = False,
) -> dict[str, Any]:
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    if resume and smoke_test:
        raise ValueError("The Phase 4 smoke test does not support resuming")
    config = load_config(config_path)
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable; no CPU fallback is automatic")
    device = torch.device(device_name)
    if device.type == "cuda" and device.index is not None and device.index >= torch.cuda.device_count():
        raise ValueError(f"CUDA device index {device.index} is not available")

    data = load_phase4_data(project_root, config)
    config_bytes = config_path.read_bytes()
    output_dir = output_dir.resolve()
    expected_metadata = {
        "phase4_config_sha256": _sha256_file(config_path),
        "split_manifest_sha256": data.split_manifest_sha256,
        "client_manifest_sha256": data.client_manifest_sha256,
        "preprocessing_report_sha256": data.preprocessing_report_sha256,
        "environment": environment_metadata(device),
        "model_parameter_count": int(config["model"]["trainable_parameter_count"]),
    }
    metadata_path = output_dir / "run_metadata.json"
    if resume:
        if not output_dir.is_dir():
            raise FileNotFoundError(f"Cannot resume; Phase 4 output directory not found: {output_dir}")
        if not metadata_path.is_file():
            raise FileNotFoundError(f"Cannot resume; run metadata not found: {metadata_path}")
        with metadata_path.open(encoding="utf-8") as file:
            metadata = json.load(file)
        for key, value in expected_metadata.items():
            if metadata.get(key) != value:
                raise ValueError(f"Cannot resume: {key} differs from the original run")
        config_copy = output_dir / "config.yaml"
        if not config_copy.is_file() or _sha256_file(config_copy) != expected_metadata["phase4_config_sha256"]:
            raise ValueError("Cannot resume: saved Phase 4 config is missing or has changed")
        metadata["resume_count"] = int(metadata.get("resume_count", 0)) + 1
        metadata["last_resumed_at_utc"] = datetime.now(timezone.utc).isoformat()
    else:
        if output_dir.exists():
            raise FileExistsError(f"Refusing to overwrite Phase 4 output directory: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=False)
        (output_dir / "config.yaml").write_bytes(config_bytes)
        metadata = {
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "resume_count": 0,
            **expected_metadata,
        }
    metadata["status"] = "smoke_test" if smoke_test else "running"
    write_json(output_dir / "run_metadata.json", metadata)

    majority = majority_baseline(data, config)
    write_json(output_dir / "majority_baseline.json", majority)
    if smoke_test:
        seed = int(config["training"]["seeds"][0])
        seed_everything(seed, bool(config["training"]["deterministic_algorithms"]))
        model = _model(config, device)
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=float(config["training"]["learning_rate"]),
            weight_decay=float(config["training"]["weight_decay"]),
        )
        first_features = torch.from_numpy(
            np.ascontiguousarray(data.splits["train"].x[:256], dtype=np.float32)
        ).unsqueeze(1).to(device)
        first_labels = torch.from_numpy(
            np.ascontiguousarray(data.splits["train"].y[:256], dtype=np.int64)
        ).to(device)
        model.train()
        optimizer.zero_grad(set_to_none=True)
        logits = model(first_features)
        loss = nn.CrossEntropyLoss()(logits, first_labels)
        if logits.shape != (len(first_labels), len(CLASS_ORDER)) or not torch.isfinite(loss):
            raise ValueError("CNN smoke test produced invalid logits or loss")
        loss.backward()
        if any(
            parameter.grad is not None and not torch.isfinite(parameter.grad).all()
            for parameter in model.parameters()
        ):
            raise ValueError("CNN smoke test produced non-finite gradients")
        optimizer.step()
        result = {
            **metadata,
            "status": "smoke_test_passed",
            "sample_count": len(first_labels),
            "logit_shape": list(logits.shape),
            "training_loss": float(loss.detach().item()),
            "cnn_validation_used_for_selection": False,
            "cnn_test_used_for_evaluation": False,
            "majority_baseline_test_evaluated": True,
        }
        write_json(output_dir / "smoke_test.json", result)
        return result

    validation = data.splits["validation"]
    test = data.splits["test"]
    train = data.splits["train"]
    seeds = [int(seed) for seed in config["training"]["seeds"]]
    fit_specs = []
    for seed in seeds:
        fit_specs.append(
            {
                "run_id": f"central_seed_{seed}",
                "condition": "centralized",
                "client_id": None,
                "seed": seed,
                "train_split": train,
                "training_record_ids": None,
            }
        )

    for client in data.client_manifest["clients"]:
        client_id = str(client["client_id"])
        client_train = _subset_records(train, list(client["record_ids"]))
        for seed in seeds:
            fit_specs.append(
                {
                    "run_id": f"{client_id}_seed_{seed}",
                    "condition": "local_only",
                    "client_id": client_id,
                    "seed": seed,
                    "train_split": client_train,
                    "training_record_ids": list(client["record_ids"]),
                }
            )

    progress_path = output_dir / "execution_status.json"
    completed_fit_ids = []
    orphaned_checkpoints = []
    results_by_id: dict[str, dict[str, Any]] = {}
    for spec in fit_specs:
        run_path = output_dir / f"{spec['run_id']}.json"
        checkpoint_path = output_dir / "checkpoints" / f"{spec['run_id']}.pt"
        if resume and not run_path.exists() and checkpoint_path.exists():
            archive_dir = output_dir / "checkpoints" / "unverified"
            archive_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            archived_path = archive_dir / f"{spec['run_id']}_{timestamp}.pt"
            checkpoint_path.rename(archived_path)
            orphaned_checkpoints.append(
                {"run_id": spec["run_id"], "path": str(archived_path)}
            )
        completed = _load_completed_fit(
            run_path,
            checkpoint_path,
            spec["run_id"],
            spec["condition"],
            spec["client_id"],
            spec["seed"],
        )
        if completed is not None:
            results_by_id[spec["run_id"]] = completed
            completed_fit_ids.append(spec["run_id"])

    progress = {
        "status": "running",
        "expected_fit_count": len(fit_specs),
        "completed_fit_count": len(completed_fit_ids),
        "completed_fit_ids": completed_fit_ids,
        "orphaned_checkpoints": orphaned_checkpoints,
        "current_fit_id": None,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(progress_path, progress)

    invocation_started = time.perf_counter()
    for spec in fit_specs:
        run_id = spec["run_id"]
        if run_id in results_by_id:
            continue
        progress["current_fit_id"] = run_id
        progress["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(progress_path, progress)
        fit_started = time.perf_counter()
        try:
            run = fit_and_evaluate(
                config,
                spec["train_split"],
                validation,
                test,
                device,
                spec["seed"],
                output_dir / "checkpoints" / f"{run_id}.pt",
            )
        except Exception as error:
            progress["status"] = "failed"
            progress["failed_fit_id"] = run_id
            progress["error"] = {"type": type(error).__name__, "message": str(error)}
            progress["current_fit_id"] = None
            progress["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            write_json(progress_path, progress)
            metadata["status"] = "failed"
            metadata["failed_fit_id"] = run_id
            metadata["last_error"] = progress["error"]
            write_json(metadata_path, metadata)
            raise
        run["run_id"] = run_id
        run["condition"] = spec["condition"]
        run["client_id"] = spec["client_id"]
        if spec["training_record_ids"] is not None:
            run["training_record_ids"] = spec["training_record_ids"]
        run["execution_seconds"] = time.perf_counter() - fit_started
        run_path = output_dir / f"{run_id}.json"
        write_json(run_path, run)
        results_by_id[run_id] = run
        completed_fit_ids.append(run_id)
        progress["completed_fit_count"] = len(completed_fit_ids)
        progress["completed_fit_ids"] = completed_fit_ids
        progress["current_fit_id"] = None
        progress["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(progress_path, progress)

    results = [results_by_id[spec["run_id"]] for spec in fit_specs]
    central_results = [run for run in results if run["condition"] == "centralized"]
    client_results = {
        str(client["client_id"]): [
            run for run in results
            if run["condition"] == "local_only"
            and run["client_id"] == str(client["client_id"])
        ]
        for client in data.client_manifest["clients"]
    }
    summaries = {
        "centralized": {
            "test": _evaluation_summary(central_results, "test_metrics"),
            "validation": _evaluation_summary(central_results, "best_validation_metrics"),
            "execution_seconds": _numeric_summary(
                [float(run["execution_seconds"]) for run in central_results]
            ),
        },
        "local_only": {
            client_id: {
                "test": _evaluation_summary(runs, "test_metrics"),
                "validation": _evaluation_summary(runs, "best_validation_metrics"),
                "execution_seconds": _numeric_summary(
                    [float(run["execution_seconds"]) for run in runs]
                ),
            }
            for client_id, runs in client_results.items()
        },
    }
    invocation_seconds = time.perf_counter() - invocation_started
    progress["status"] = "complete"
    progress["completed_fit_count"] = len(results)
    progress["current_fit_id"] = None
    progress["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(progress_path, progress)
    metadata["status"] = "complete"
    metadata["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["last_invocation_execution_seconds"] = invocation_seconds
    write_json(metadata_path, metadata)
    complete = {
        **metadata,
        "seed_count": len(seeds),
        "seeds": seeds,
        "majority_baseline": majority,
        "centralized_runs": central_results,
        "local_only_runs": client_results,
        "aggregate_test_metrics": summaries,
        "execution_seconds": {
            "last_invocation": invocation_seconds,
            "sum_of_fit_times": sum(float(run["execution_seconds"]) for run in results),
        },
    }
    write_json(output_dir / "summary.json", complete)
    return complete
