"""G5 explanatory ablation A2: uniform vs sample-count-weighted FedAvg on the F3 partition.

**Pre-registered hypotheses (fixed before any run):**

H_A2 (mechanism): the F3 severe partition produced higher test accuracy and macro-F1 than the
IID-like F1 partition (0.8523/0.3752 vs 0.7861/0.3040) **not** because heterogeneity helps, but
because the F3 partition's sample-count weights are highly dispersed (max 0.371, min 0.087,
ratio 4.26x against 1.26x on F1). A single client holding 37 % of the aggregate pulls the global
model towards its own data distribution, making weighted FedAvg behave more like centralized
training on a subset. If this is the mechanism, replacing sample-count weights with **uniform
weights** on the same F3 partition should reduce accuracy and macro-F1 towards the F1 level,
without changing the data, the model, the seeds, or the number of clients.

**Pre-registered decision rule:**
- If uniform-weight F3 macro-F1 falls by more than half the F1→F3 gap (gap = 0.3752 - 0.3040 =
  0.0712, half = 0.0356), H_A2 is **supported**: weight dispersion is a material driver.
- If it falls by less than that, H_A2 is **not supported** and the partition's label distribution
  or another factor must be considered.

**Pre-registered success guards:** if the ablation run does not reproduce the frozen weighted-F3
mean within 2 standard errors when run with weighted aggregation under the same code path, the
ablation is void and must be re-run.

Everything else is the frozen Phase 5 recipe: same model, 50 rounds, 2 local epochs, all five
clients, BatchNorm weighted by sample count, optimizer state reset, unweighted cross-entropy,
same checkpoint-selection rule, seeds 42-46. The frozen `fedavg.py` is not modified.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

from src.federated.fedavg import (
    FederatedError,
    _local_loader,
    _write_json,
    select_participants,
    weighted_state_dict,
)
from src.federated.partitions import verify_partition_manifest
from src.training.phase4 import (
    _cpu_state_dict,
    _model,
    _sha256_file,
    environment_metadata,
    evaluate_model,
    load_config,
    seed_everything,
)
from src.training.phase4_data import load_phase4_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def train_local(
    global_state: dict[str, torch.Tensor],
    config: dict[str, Any],
    train_split,
    local_epochs: int,
    device: torch.device,
    seed: int,
) -> dict[str, Any]:
    """Frozen Phase 5 local training (FedAvg, no proximal term)."""
    training = config["training"]
    model = _model(config, device)
    model.load_state_dict({k: v.to(device) for k, v in global_state.items()})
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training["learning_rate"]),
        weight_decay=float(training["weight_decay"]),
    )
    criterion = torch.nn.CrossEntropyLoss()
    loader = _local_loader(train_split, int(training["batch_size"]), seed)

    model.train()
    total, count = 0.0, 0
    for _ in range(local_epochs):
        for features, labels in loader:
            features = features.unsqueeze(1).to(device, non_blocking=device.type == "cuda")
            labels = labels.to(device, non_blocking=labels.device.type == "cuda")
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(features), labels)
            if not torch.isfinite(loss):
                raise FederatedError("Local training loss became non-finite")
            loss.backward()
            optimizer.step()
            total += float(loss.detach()) * len(labels)
            count += len(labels)
    if count == 0:
        raise FederatedError("Client training split produced no samples")
    return {"state": _cpu_state_dict(model), "loss": total / count, "samples": count}


def run_seed(
    root: Path,
    config: dict[str, Any],
    client_splits: dict[str, Any],
    output_dir: Path,
    device_name: str,
    seed: int,
    weighting: str,
) -> dict[str, Any]:
    data = load_phase4_data(root, config)
    federated = config["federated"]
    training = config["training"]
    rounds = int(federated["rounds"])
    local_epochs = int(federated["local_epochs"])
    fraction = float(federated["participation_fraction"])
    device = torch.device(device_name)

    client_ids = sorted(client_splits)
    counts = {c: len(client_splits[c].y) for c in client_ids}

    if weighting == "uniform":
        # Every participating client contributes equally, regardless of size.
        effective = {c: 1 for c in client_ids}
    elif weighting == "sample_count":
        effective = counts
    else:
        raise ValueError(f"Unknown weighting: {weighting}")

    weights = {c: effective[c] / sum(effective.values()) for c in client_ids}

    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    seed_everything(seed, bool(training["deterministic_algorithms"]))
    model = _model(config, device)
    global_state = _cpu_state_dict(model)
    classes = list(training["early_stopping"]["classes"])
    batch = int(training["batch_size"])

    rounds_log: list[dict[str, Any]] = []
    best = {"score": None, "round": None, "state": None, "metrics": None, "loss": None}
    started = time.perf_counter()

    for round_index in range(rounds + 1):
        if round_index == 0:
            loss, metrics = evaluate_model(model, data.splits["validation"], batch, device,
                                          macro_classes=classes)
            rounds_log.append({"round": 0, "validation_loss": loss,
                               "validation_macro_f1": metrics["macro_f1"]})
        else:
            model.load_state_dict({k: v.to(device) for k, v in global_state.items()})
            participants = select_participants(client_ids, round_index, fraction, seed)
            states = []
            for client_id in participants:
                result = train_local(
                    global_state, config, client_splits[client_id], local_epochs, device,
                    seed=seed * 1000 + round_index * 10 + client_ids.index(client_id),
                )
                states.append((result["state"], effective[client_id]))
            global_state = weighted_state_dict(states)
            model.load_state_dict({k: v.to(device) for k, v in global_state.items()})
            loss, metrics = evaluate_model(model, data.splits["validation"], batch, device,
                                          macro_classes=classes)
            rounds_log.append({"round": round_index, "validation_loss": loss,
                               "validation_macro_f1": metrics["macro_f1"]})
            print(f"  round {round_index:>3} val_mF1 {metrics['macro_f1']:.4f} loss {loss:.4f}")

        score = rounds_log[-1]["validation_macro_f1"]
        if score is not None and (best["score"] is None or score > best["score"]):
            best = {"score": score, "round": round_index,
                    "state": {k: v.clone() for k, v in global_state.items()},
                    "metrics": metrics, "loss": loss}

    model.load_state_dict({k: v.to(device) for k, v in best["state"].items()})
    checkpoint = output_dir / "checkpoints" / f"a2_seed_{seed}.pt"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save(_cpu_state_dict(model), checkpoint)
    test_loss, test_metrics = evaluate_model(model, data.splits["test"], batch, device,
                                             macro_classes=None)

    return {
        "run_id": f"a2_{weighting}_seed_{seed}",
        "ablation": "a2_aggregation_weighting",
        "weighting": weighting,
        "seed": seed,
        "selected_round": best["round"],
        "best_validation_macro_f1": best["score"],
        "test_loss": test_loss,
        "test_metrics": test_metrics,
        "aggregation_weights": weights,
        "weight_max": max(weights.values()),
        "weight_ratio": max(weights.values()) / min(weights.values()),
        "client_sample_counts": counts,
        "rounds": rounds_log,
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": _sha256_file(checkpoint),
        "execution_seconds": time.perf_counter() - started,
        "environment": environment_metadata(device),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config-name", default="phase5_f3_fedavg_severe")
    parser.add_argument("--weighting", choices=("uniform", "sample_count"), default="uniform")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    from src.federated.fedavg import client_split
    from src.federated.partitions import verify_partition_manifest

    config = load_config(PROJECT_ROOT / "configs" / "models" / "phase4_cnn_v1.yaml")
    # Use the frozen Phase 5 federated settings so only weighting differs.
    import yaml
    federated_config = yaml.safe_load(
        (PROJECT_ROOT / "configs" / "federated" / f"{args.config_name}.yaml").read_text(encoding="utf-8")
    )
    config = {**config, "federated": federated_config["federated"],
              "partition": federated_config["partition"]}

    data = load_phase4_data(PROJECT_ROOT, config)
    partition_document = json.loads(
        (PROJECT_ROOT / config["partition"]["manifest_path"]).read_text(encoding="utf-8")
    )
    verify_partition_manifest(data, partition_document)
    client_splits = {
        str(c["client_id"]): client_split(data, [str(r) for r in c["record_ids"]])
        for c in partition_document["clients"]
    }

    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    seeds = [args.seed] if args.seed is not None else [int(s) for s in config["training"]["seeds"]]
    for seed in seeds:
        print(f"[{args.weighting}] seed {seed}")
        path = output_dir / f"a2_{args.weighting}_seed_{seed}.json"
        if path.exists():
            print("  exists, skipping")
            continue
        _write_json(path, run_seed(PROJECT_ROOT, config, client_splits, output_dir / f"seed_{seed}",
                                   args.device, seed, args.weighting))


if __name__ == "__main__":
    main()
