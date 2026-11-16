"""FedAvg (McMahan et al., 2017) and FedProx (Li et al., 2020) over the frozen Phase 4 model.

Design choices fixed by ``docs/PHASE_5_IMPLEMENTATION_PLAN.md`` and the approved protocol:

- The model, optimizer, loss, batch size and checkpoint-selection rule are the frozen
  ``compact_cnn_v1`` Phase 4 recipe; nothing is retuned here.
- Aggregation weights are client training-sample counts.
- BatchNorm running statistics are aggregated weighted by sample count and
  ``num_batches_tracked`` is summed; this is stated explicitly because federated
  normalisation is otherwise ambiguous.
- Optimizer state is reset at the start of every round (standard FedAvg).
- Test data is read exactly once per run, after the selected round is fixed.
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from src.data.phase3_pipeline import CLASS_ORDER
from src.training.phase4 import (
    _cpu_state_dict,
    _dataset,
    _model,
    _sha256_file,
    environment_metadata,
    evaluate_model,
    seed_everything,
)
from src.training.phase4_data import Phase4Data, SplitArrays

INTEGER_BUFFERS = {"num_batches_tracked"}


class FederatedError(ValueError):
    """Raised when a federated run violates a Phase 5 rule."""


def weighted_state_dict(
    client_states: list[tuple[dict[str, torch.Tensor], int]],
) -> dict[str, torch.Tensor]:
    """Sample-count weighted average of client state dicts, in float64.

    ``client_states`` is a list of ``(state_dict, sample_count)`` pairs. Integer buffers
    are excluded from averaging; ``num_batches_tracked`` is summed instead.
    """
    if not client_states:
        raise FederatedError("Cannot aggregate an empty client set")
    total = sum(int(count) for _, count in client_states)
    if total <= 0:
        raise FederatedError("Aggregation weights must sum to a positive value")

    keys = client_states[0][0].keys()
    for state, _ in client_states:
        if state.keys() != keys:
            raise FederatedError("Client state dicts have inconsistent keys")

    aggregated: dict[str, torch.Tensor] = {}
    for key in keys:
        reference = client_states[0][0][key]
        if key.split(".")[-1] in INTEGER_BUFFERS:
            aggregated[key] = torch.stack(
                [state[key].to(torch.int64) for state, _ in client_states]
            ).sum(dim=0).to(reference.dtype)
            continue
        if not torch.is_floating_point(reference):
            aggregated[key] = reference.clone()
            continue
        accumulator = torch.zeros(reference.shape, dtype=torch.float64)
        for state, count in client_states:
            tensor = state[key].to(torch.float64)
            if tensor.shape != reference.shape:
                raise FederatedError(f"Aggregation shape mismatch for {key}")
            accumulator += tensor * (float(count) / float(total))
        aggregated[key] = accumulator.to(reference.dtype)
    return aggregated


def aggregate_models(models: list[nn.Module], sample_counts: list[int]) -> dict[str, torch.Tensor]:
    states = [(_cpu_state_dict(model), count) for model, count in zip(models, sample_counts)]
    return weighted_state_dict(states)


def _local_loader(split: SplitArrays, batch_size: int, seed: int) -> DataLoader:
    generator = torch.Generator().manual_seed(seed)
    return DataLoader(
        _dataset(split),
        batch_size=batch_size,
        shuffle=True,
        generator=generator,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )


def train_local(
    global_state: dict[str, torch.Tensor],
    config: dict[str, Any],
    train_split: SplitArrays,
    local_epochs: int,
    device: torch.device,
    seed: int,
    proximal_mu: float = 0.0,
) -> dict[str, Any]:
    """Train one client from the global state for a fixed number of local epochs."""
    training = config["training"]
    batch_size = int(training["batch_size"])
    model = _model(config, device)
    model.load_state_dict({key: value.to(device) for key, value in global_state.items()})
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training["learning_rate"]),
        weight_decay=float(training["weight_decay"]),
    )
    criterion = nn.CrossEntropyLoss()
    reference = (
        {key: value.detach().to(device) for key, value in global_state.items()}
        if proximal_mu > 0
        else None
    )
    loader = _local_loader(train_split, batch_size, seed)

    model.train()
    total_loss = 0.0
    sample_count = 0
    for _ in range(local_epochs):
        for features, labels in loader:
            features = features.unsqueeze(1).to(device, non_blocking=device.type == "cuda")
            labels = labels.to(device, non_blocking=device.type == "cuda")
            optimizer.zero_grad(set_to_none=True)
            logits = model(features)
            loss = criterion(logits, labels)
            if reference is not None:
                prox = torch.zeros((), device=device)
                for name, parameter in model.named_parameters():
                    prox = prox + torch.sum((parameter - reference[name]) ** 2)
                loss = loss + 0.5 * float(proximal_mu) * prox
            if not torch.isfinite(loss):
                raise FederatedError("Local training loss became non-finite")
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach().item()) * len(labels)
            sample_count += len(labels)
    if sample_count == 0:
        raise FederatedError("Client training split produced no samples")
    return {"state": _cpu_state_dict(model), "loss": total_loss / sample_count, "samples": sample_count}


def _round_generator(seed: int, round_index: int) -> torch.Generator:
    generator = torch.Generator()
    generator.manual_seed((int(seed) * 1_000_003 + int(round_index)) % (2**31 - 1))
    return generator


def select_participants(
    client_ids: list[str],
    round_index: int,
    fraction: float,
    seed: int,
) -> list[str]:
    """Deterministic participation for a given (seed, round)."""
    if fraction >= 1.0:
        return list(client_ids)
    count = max(1, int(round(len(client_ids) * fraction)))
    generator = _round_generator(seed, round_index)
    order = torch.randperm(len(client_ids), generator=generator).tolist()
    return sorted(client_ids[index] for index in order[:count])


def _balanced_accuracy(metrics: dict[str, Any]) -> float | None:
    """Unweighted mean of per-class recall over the included selection classes."""
    included = list(metrics.get("macro_classes_included", []))
    if not included:
        return None
    recalls = [metrics["per_class"][name]["recall"] for name in included]
    if any(value is None for value in recalls):
        return None
    return float(sum(recalls) / len(recalls))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, sort_keys=True)
        file.write("\n")


def run_federated(
    project_root: Path,
    config: dict[str, Any],
    config_path: Path,
    data: Phase4Data,
    client_splits: dict[str, SplitArrays],
    output_dir: Path,
    device_name: str,
    seed: int,
    resume: bool = False,
) -> dict[str, Any]:
    """Run one federated experiment for one seed. Writes round-level artefacts."""
    federated = config["federated"]
    training = config["training"]
    rounds = int(federated["rounds"])
    local_epochs = int(federated["local_epochs"])
    fraction = float(federated["participation_fraction"])
    method = str(federated["method"])
    proximal_mu = float(federated.get("proximal_mu") or 0.0)
    if method == "fedprox" and proximal_mu <= 0:
        raise FederatedError("FedProx requires a positive proximal_mu")
    if method == "fedavg" and proximal_mu != 0.0:
        raise FederatedError("FedAvg must not set proximal_mu")

    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    device = torch.device(device_name)

    client_ids = sorted(client_splits)
    for client_id, split in client_splits.items():
        if len(split.y) == 0:
            raise FederatedError(f"{client_id} has an empty training split")

    output_dir = output_dir.resolve()
    state_path = output_dir / "rounds_state.json"
    last_state_path = output_dir / "checkpoints" / "latest_global_state.pt"
    if resume:
        if not state_path.is_file():
            raise FileNotFoundError(f"Cannot resume; no round state at {state_path}")
        with state_path.open(encoding="utf-8") as file:
            state = json.load(file)
        if state.get("seed") != seed or state.get("method") != method:
            raise FederatedError("Cannot resume: seed or method differs")
        start_round = int(state["next_round"])
    else:
        if output_dir.exists() and any(output_dir.iterdir()):
            raise FileExistsError(f"Refusing to overwrite federated output: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)
        start_round = 0
        state = {
            "seed": seed,
            "method": method,
            "next_round": 0,
            "rounds": [],
            "selection_metric": training["early_stopping"]["metric"],
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
        }

    seed_everything(seed, bool(training["deterministic_algorithms"]))
    model = _model(config, device)
    global_state = _cpu_state_dict(model)

    rounds_log = state["rounds"]
    selection_classes = list(training["early_stopping"]["classes"])
    best = {
        "score": None,
        "round": None,
        "state": None,
        "validation_metrics": None,
        "validation_loss": None,
    }

    # On resume the in-memory best state is gone; recover the selected round from the log
    # and rebuild the checkpoint from the last persisted global state.
    if resume:
        completed = [record for record in rounds_log if record.get("validation_macro_f1") is not None]
        if completed and completed[-1]["round"] <= rounds:
            chosen = max(completed, key=lambda record: (record["validation_macro_f1"], -record["round"]))
            if chosen["round"] > 0 and last_state_path.is_file():
                # The persisted state is the latest round, not necessarily the best one;
                # restrict resume to the common case where the latest round is the best.
                latest = completed[-1]["round"]
                if chosen["round"] == latest:
                    best = {
                        "score": float(chosen["validation_macro_f1"]),
                        "round": int(chosen["round"]),
                        "state": torch.load(last_state_path, map_location="cpu"),
                        "validation_metrics": None,
                        "validation_loss": chosen["validation_loss"],
                    }

    metadata_path = output_dir / "run_metadata.json"
    if not resume:
        _write_json(
            metadata_path,
            {
                "seed": seed,
                "method": method,
                "rounds": rounds,
                "local_epochs": local_epochs,
                "participation_fraction": fraction,
                "proximal_mu": proximal_mu,
                "aggregation": "sample_count_weighted_state_dict",
                "batchnorm_handling": "running_statistics_weighted_by_sample_count",
                "optimizer_state_policy": "reset_each_round",
                "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
                "split_manifest_sha256": data.split_manifest_sha256,
                "client_manifest_sha256": data.client_manifest_sha256,
                "environment": environment_metadata(device),
            },
        )

    invocation_started = time.perf_counter()

    for round_index in range(start_round, rounds + 1):
        participants = select_participants(client_ids, round_index, fraction, seed)
        round_started = time.perf_counter()

        if round_index == 0:
            validation_loss, validation_metrics = evaluate_model(
                model, data.splits["validation"], int(training["batch_size"]), device,
                macro_classes=selection_classes,
            )
            round_record = {
                "round": 0,
                "participants": [],
                "local_losses": {},
                "validation_loss": validation_loss,
                "validation_macro_f1": validation_metrics["macro_f1"],
                "seconds": time.perf_counter() - round_started,
                "bytes_down": 0,
                "bytes_up": 0,
                "samples_processed": 0,
            }
        else:
            model.load_state_dict({key: value.to(device) for key, value in global_state.items()})
            local_states = []
            local_losses = {}
            client_metrics = {}
            client_weights = {}
            samples = 0
            for client_id in participants:
                result = train_local(
                    global_state,
                    config,
                    client_splits[client_id],
                    local_epochs,
                    device,
                    seed=seed * 1000 + round_index * 10 + client_ids.index(client_id),
                    proximal_mu=proximal_mu,
                )
                local_states.append((result["state"], result["samples"]))
                local_losses[client_id] = result["loss"]
                samples += result["samples"]

                # Client-level evaluation on the client's own training partition, plus the
                # shared validation partition. Training-partition metrics are descriptive
                # (in-sample); validation metrics are what the protocol already permits.
                local_model = _model(config, device)
                local_model.load_state_dict(
                    {key: value.to(device) for key, value in result["state"].items()}
                )
                _, train_metrics = evaluate_model(
                    local_model, client_splits[client_id], int(training["batch_size"]), device,
                    macro_classes=selection_classes,
                )
                _, local_val_metrics = evaluate_model(
                    local_model, data.splits["validation"], int(training["batch_size"]), device,
                    macro_classes=selection_classes,
                )
                client_metrics[client_id] = {
                    "local_train_accuracy": train_metrics["accuracy"],
                    "local_train_macro_f1": train_metrics["macro_f1"],
                    "validation_macro_f1": local_val_metrics["macro_f1"],
                    "per_class": {
                        name: dict(local_val_metrics["per_class"][name]) for name in CLASS_ORDER
                    },
                }
            for index, client_id in enumerate(participants):
                client_weights[client_id] = float(local_states[index][1]) / float(samples)
            global_state = weighted_state_dict(local_states)
            model.load_state_dict({key: value.to(device) for key, value in global_state.items()})
            validation_loss, validation_metrics = evaluate_model(
                model, data.splits["validation"], int(training["batch_size"]), device,
                macro_classes=selection_classes,
            )
            parameter_bytes = sum(
                tensor.numel() * tensor.element_size() for tensor in global_state.values()
            )
            round_record = {
                "round": round_index,
                "participants": participants,
                "local_losses": local_losses,
                "aggregation_weights": client_weights,
                "client_metrics": client_metrics,
                "validation_loss": validation_loss,
                "validation_macro_f1": validation_metrics["macro_f1"],
                "validation_balanced_accuracy": _balanced_accuracy(validation_metrics),
                "validation_per_class": {
                    name: dict(validation_metrics["per_class"][name]) for name in CLASS_ORDER
                },
                "aggregation_weights_sum": sum(client_weights.values()),
                "seconds": time.perf_counter() - round_started,
                "bytes_down": parameter_bytes * len(participants),
                "bytes_up": parameter_bytes * len(participants),
                "model_parameter_bytes": parameter_bytes,
                "samples_processed": samples,
            }

        score = round_record["validation_macro_f1"]
        if score is not None and (best["score"] is None or score > best["score"]):
            best = {
                "score": float(score),
                "round": round_index,
                "state": {key: value.clone() for key, value in global_state.items()},
                "validation_metrics": validation_metrics,
                "validation_loss": validation_loss,
            }

        rounds_log.append(round_record)
        state["next_round"] = round_index + 1
        last_state_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(global_state, last_state_path)
        _write_json(
            output_dir / "rounds.json",
            {"seed": seed, "method": method, "rounds": rounds_log},
        )
        _write_json(state_path, state)
        print(
            f"round {round_index:>3} participants {len(participants)} "
            f"val_macro_f1 {score if score is None else round(score, 4)} "
            f"val_loss {round(validation_loss, 4)}"
        )

    selected_round = best["round"]
    model.load_state_dict({key: value.to(device) for key, value in best["state"].items()})
    checkpoint_path = output_dir / "checkpoints" / f"selected_seed_{seed}.pt"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(_cpu_state_dict(model), checkpoint_path)
    test_loss, test_metrics = evaluate_model(
        model, data.splits["test"], int(training["batch_size"]), device, macro_classes=None
    )

    total_seconds = sum(float(record["seconds"]) for record in rounds_log)
    summary = {
        "seed": seed,
        "method": method,
        "selected_round": selected_round,
        "round_zero_selected": selected_round == 0,
        "selection_metric": training["early_stopping"]["metric"],
        "best_validation_macro_f1": best["score"],
        "best_validation_metrics": best["validation_metrics"],
        "test_loss": test_loss,
        "test_metrics": test_metrics,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": _sha256_file(checkpoint_path),
        "rounds_executed": len(rounds_log),
        "total_seconds": total_seconds,
        "total_bytes": sum(int(r["bytes_up"]) + int(r["bytes_down"]) for r in rounds_log),
        "total_samples_processed": sum(int(r["samples_processed"]) for r in rounds_log),
        "invocation_seconds": time.perf_counter() - invocation_started,
    }
    if selected_round == 0:
        summary["round_zero_note"] = (
            "Validation selected round 0: no later round improved validation macro-F1. "
            "Reported as-is per protocol; not substituted."
        )
    _write_json(output_dir / "run_summary.json", summary)
    return summary


def client_split(data: Phase4Data, record_ids: list[str]) -> SplitArrays:
    """Training windows belonging to a set of records (never validation or test)."""
    train = data.splits["train"]
    record_text = train.record_ids.astype(np.int64).astype(str)
    mask = np.isin(record_text, [str(record) for record in record_ids])
    if not mask.any():
        raise FederatedError("Client has no training windows")
    return SplitArrays(
        x=np.ascontiguousarray(train.x[mask]),
        y=np.ascontiguousarray(train.y[mask]),
        record_ids=train.record_ids[mask],
        sample_positions=train.sample_positions[mask],
    )
