"""Phase 6 calibration: measure client-update norms with NO noise and NO clipping.

This module exists solely to determine the L2 clipping constant ``C`` under the
pre-registered rule in ``docs/PHASE_6_EXPERIMENT_MATRIX.md`` §4.1. It performs no
privacy mechanism and provides no privacy protection. It reuses the frozen Phase 5
training loop unchanged and only observes the update norms that the loop already
computes internally.

Design constraints:

- The training procedure, model, optimizer, data, partition and seeds are the frozen
  Phase 5 values. Nothing is retuned.
- Only trainable parameters contribute to the measured norm, matching the DP vector
  (36,357 values). BatchNorm buffers and ``num_batches_tracked`` are excluded, per
  decision D5.
- Test data is never read.
"""

from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch

from src.federated.fedavg import (
    _local_loader,
    _write_json,
    select_participants,
    weighted_state_dict,
)
from src.training.phase4 import (
    _cpu_state_dict,
    _model,
    environment_metadata,
    evaluate_model,
    seed_everything,
)
from src.training.phase4_data import Phase4Data, SplitArrays


def trainable_parameter_keys(state: dict[str, torch.Tensor], model: torch.nn.Module) -> list[str]:
    """State-dict keys that are trainable parameters, in a stable order.

    ``state_dict`` and ``named_parameters`` share names, so the parameter set is exactly
    the names reported by ``named_parameters``. Buffers (running statistics,
    ``num_batches_tracked``) are excluded.
    """
    parameter_names = {name for name, _ in model.named_parameters()}
    keys = [key for key in state if key in parameter_names]
    if len(keys) != len(parameter_names):
        raise RuntimeError("State dict does not contain every trainable parameter")
    return keys


def update_norm(
    local_state: dict[str, torch.Tensor],
    global_state: dict[str, torch.Tensor],
    keys: list[str],
) -> float:
    """L2 norm of ``local - global`` over the trainable parameters only."""
    total = 0.0
    for key in keys:
        delta = local_state[key].to(torch.float64) - global_state[key].to(torch.float64)
        total += float(torch.sum(delta * delta))
    return math.sqrt(total)


def train_local_observed(
    global_state: dict[str, torch.Tensor],
    config: dict[str, Any],
    train_split: SplitArrays,
    local_epochs: int,
    device: torch.device,
    seed: int,
) -> dict[str, Any]:
    """One client's local training, identical to Phase 5 ``train_local`` for FedAvg.

    Reimplemented here rather than imported so that the calibration pass cannot alter the
    frozen function, and so the pre/post-update states are both available for measurement.
    The arithmetic is the same: AdamW, unweighted cross-entropy, same loader, same epochs.
    """
    training = config["training"]
    batch_size = int(training["batch_size"])
    model = _model(config, device)
    model.load_state_dict({key: value.to(device) for key, value in global_state.items()})
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training["learning_rate"]),
        weight_decay=float(training["weight_decay"]),
    )
    criterion = torch.nn.CrossEntropyLoss()
    loader = _local_loader(train_split, batch_size, seed)

    model.train()
    sample_count = 0
    total_loss = 0.0
    for _ in range(local_epochs):
        for features, labels in loader:
            features = features.unsqueeze(1).to(device, non_blocking=device.type == "cuda")
            labels = labels.to(device, non_blocking=device.type == "cuda")
            optimizer.zero_grad(set_to_none=True)
            logits = model(features)
            loss = criterion(logits, labels)
            if not torch.isfinite(loss):
                raise RuntimeError("Calibration local training produced a non-finite loss")
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach().item()) * len(labels)
            sample_count += len(labels)
    if sample_count == 0:
        raise RuntimeError("Client training split produced no samples")
    return {
        "state": _cpu_state_dict(model),
        "loss": total_loss / sample_count,
        "samples": sample_count,
    }


def run_calibration(
    project_root: Path,
    config: dict[str, Any],
    config_path: Path,
    data: Phase4Data,
    client_splits: dict[str, SplitArrays],
    output_dir: Path,
    device_name: str,
    seed: int,
    max_rounds: int | None = None,
) -> dict[str, Any]:
    """Run FedAvg for one seed and record per-client, per-round update norms."""
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    device = torch.device(device_name)

    federated = config["federated"]
    training = config["training"]
    rounds = int(federated["rounds"]) if max_rounds is None else int(max_rounds)
    local_epochs = int(federated["local_epochs"])
    fraction = float(federated["participation_fraction"])

    client_ids = sorted(client_splits)
    for client_id, split in client_splits.items():
        if len(split.y) == 0:
            raise RuntimeError(f"{client_id} has an empty training split")

    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite calibration output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    seed_everything(seed, bool(training["deterministic_algorithms"]))
    model = _model(config, device)
    global_state = _cpu_state_dict(model)
    keys = trainable_parameter_keys(global_state, model)

    # Frozen public aggregation weights (definition 4.1 of PHASE_6_PRIVACY_MATHEMATICS.md).
    frozen_counts = {client_id: len(client_splits[client_id].y) for client_id in client_ids}
    frozen_total = sum(frozen_counts.values())
    weights = {client_id: frozen_counts[client_id] / frozen_total for client_id in client_ids}

    selection_classes = list(training["early_stopping"]["classes"])
    records: list[dict[str, Any]] = []
    started = time.perf_counter()

    for round_index in range(rounds + 1):
        round_started = time.perf_counter()
        if round_index == 0:
            validation_loss, validation_metrics = evaluate_model(
                model, data.splits["validation"], int(training["batch_size"]), device,
                macro_classes=selection_classes,
            )
            records.append({
                "round": 0,
                "participants": [],
                "client_norms": {},
                "aggregate_norm": None,
                "validation_loss": validation_loss,
                "validation_macro_f1": validation_metrics["macro_f1"],
                "seconds": time.perf_counter() - round_started,
            })
            print(f"round   0 val_macro_f1 {validation_metrics['macro_f1']:.4f}")
            continue

        model.load_state_dict({key: value.to(device) for key, value in global_state.items()})
        participants = select_participants(client_ids, round_index, fraction, seed)
        local_states: list[tuple[dict[str, torch.Tensor], int]] = []
        client_norms: dict[str, float] = {}
        for client_id in participants:
            result = train_local_observed(
                global_state, config, client_splits[client_id], local_epochs, device,
                seed=seed * 1000 + round_index * 10 + client_ids.index(client_id),
            )
            local_states.append((result["state"], result["samples"]))
            client_norms[client_id] = update_norm(result["state"], global_state, keys)

        # Frozen weights, not the realised sample counts: identical arithmetic because
        # equal-cardinality replacement leaves the realised counts unchanged, but the
        # release is then a fixed linear functional with a valid sensitivity.
        global_state_new = weighted_state_dict(
            [(state, frozen_counts[client_id]) for (state, _), client_id
             in zip(local_states, participants)]
        )
        aggregate_delta = {
            key: global_state_new[key].to(torch.float64)
            - global_state[key].to(torch.float64)
            for key in keys
        }
        aggregate_norm = math.sqrt(
            sum(float(torch.sum(tensor * tensor)) for tensor in aggregate_delta.values())
        )
        global_state = global_state_new
        model.load_state_dict({key: value.to(device) for key, value in global_state.items()})
        validation_loss, validation_metrics = evaluate_model(
            model, data.splits["validation"], int(training["batch_size"]), device,
            macro_classes=selection_classes,
        )
        records.append({
            "round": round_index,
            "participants": list(client_norms),
            "client_norms": client_norms,
            "aggregate_norm": aggregate_norm,
            "validation_loss": validation_loss,
            "validation_macro_f1": validation_metrics["macro_f1"],
            "seconds": time.perf_counter() - round_started,
        })
        print(
            f"round {round_index:>3} val_macro_f1 {validation_metrics['macro_f1']:.4f} "
            f"norm(mean) {np.mean(list(client_norms.values())):.4f}"
        )

    all_norms = [
        norm for record in records for norm in record["client_norms"].values()
    ]
    summary = {
        "seed": seed,
        "rounds": rounds,
        "local_epochs": local_epochs,
        "trainable_parameter_count": len(keys),
        "client_sample_counts": frozen_counts,
        "frozen_weights": weights,
        "max_frozen_weight": max(weights.values()),
        "environment": environment_metadata(device),
        "config_sha256": __import__("hashlib").sha256(config_path.read_bytes()).hexdigest(),
        "split_manifest_sha256": data.split_manifest_sha256,
        "client_manifest_sha256": data.client_manifest_sha256,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_client_round_observations": len(all_norms),
        "norm_min": float(np.min(all_norms)),
        "norm_max": float(np.max(all_norms)),
        "norm_median": float(np.median(all_norms)),
        "norm_mean": float(np.mean(all_norms)),
        "norm_std": float(np.std(all_norms, ddof=1)),
        "invocation_seconds": time.perf_counter() - started,
    }
    _write_json(output_dir / "norms.json", {"seed": seed, "records": records, "summary": summary})
    _write_json(output_dir / "run_metadata.json", {
        "seed": seed,
        "purpose": "phase6_clip_calibration_no_noise_no_clipping",
        "provides_privacy": False,
        "environment": summary["environment"],
        "config_sha256": summary["config_sha256"],
    })
    return summary
