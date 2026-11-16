"""G4 architecture ablation runner: tests whether max+mean pooling recovers validation S.

Pre-registered before running (recorded in docs/PHASE_4_G4_RESOLUTION.md):
- same frozen split, preprocessing, optimizer, loss, batch size, epochs, patience, seeds;
- same checkpoint-selection rule (validation supported-class macro-F1, earliest on tie);
- only the model head changes;
- success criterion: validation S recall > 0 at the selected checkpoint for at least 3 of 5
  seeds. A single seed is treated as noise, not a result.
- test data is read once per seed after selection, never during training.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

from src.data.phase3_pipeline import CLASS_ORDER
from src.federated.fedavg import _local_loader
from src.models.cnn1d_shape import CompactECGCNNShapePreserving
from src.training.phase4 import (
    _cpu_state_dict,
    _sha256_file,
    write_json,
    environment_metadata,
    evaluate_model,
    load_config,
    seed_everything,
)
from src.training.phase4_data import load_phase4_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_one_seed(root: Path, config: dict, seed: int, output_dir: Path, device_name: str) -> dict:
    training = config["training"]
    device = torch.device(device_name)
    seed_everything(seed, bool(training["deterministic_algorithms"]))

    data = load_phase4_data(root, config)
    model = CompactECGCNNShapePreserving(
        input_samples=int(config["input_samples"]),
        class_count=len(config["class_order"]),
        dropout=float(config["model"]["dropout"]),
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training["learning_rate"]),
        weight_decay=float(training["weight_decay"]),
    )
    criterion = torch.nn.CrossEntropyLoss()
    loader = _local_loader(data.splits["train"], int(training["batch_size"]), seed)
    classes = list(training["early_stopping"]["classes"])
    patience = int(training["early_stopping"]["patience"])
    batch = int(training["batch_size"])

    history: list[dict] = []
    best = {"score": None, "epoch": None, "state": None, "metrics": None, "loss": None}
    stale = 0
    started = time.perf_counter()

    for epoch in range(int(training["maximum_epochs"]) + 1):
        if epoch == 0:
            val_loss, val_metrics = evaluate_model(
                model, data.splits["validation"], batch, device, macro_classes=classes
            )
            history.append({
                "epoch": 0, "train_loss": None,
                "validation_loss": val_loss, "validation_macro_f1": val_metrics["macro_f1"],
                "validation_s_recall": val_metrics["per_class"]["S"]["recall"],
            })
        else:
            model.train()
            total, count = 0.0, 0
            for features, labels in loader:
                features = features.unsqueeze(1).to(device, non_blocking=True)
                labels = labels.to(device, non_blocking=True)
                optimizer.zero_grad(set_to_none=True)
                loss = criterion(model(features), labels)
                if not torch.isfinite(loss):
                    raise RuntimeError("A1 training loss became non-finite")
                loss.backward()
                optimizer.step()
                total += float(loss.detach()) * len(labels)
                count += len(labels)
            val_loss, val_metrics = evaluate_model(
                model, data.splits["validation"], batch, device, macro_classes=classes
            )
            history.append({
                "epoch": epoch, "train_loss": total / count,
                "validation_loss": val_loss, "validation_macro_f1": val_metrics["macro_f1"],
                "validation_s_recall": val_metrics["per_class"]["S"]["recall"],
            })
            print(f"  epoch {epoch:>2} train {total / count:.4f} val_loss {val_loss:.4f} "
                  f"val_mF1 {val_metrics['macro_f1']:.4f} "
                  f"val_S_recall {val_metrics['per_class']['S']['recall']:.4f}")

        score = history[-1]["validation_macro_f1"]
        if score is not None and (best["score"] is None or score > best["score"]):
            best = {
                "score": score, "epoch": epoch,
                "state": _cpu_state_dict(model),
                "metrics": val_metrics, "loss": val_loss,
            }
            stale = 0
        else:
            stale += 1
            if epoch > 0 and stale >= patience:
                print(f"  early stop at epoch {epoch} (patience {patience})")
                break

    model.load_state_dict({k: v.to(device) for k, v in best["state"].items()})
    checkpoint = output_dir / "checkpoints" / f"a1_seed_{seed}.pt"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save(_cpu_state_dict(model), checkpoint)

    test_loss, test_metrics = evaluate_model(
        model, data.splits["test"], batch, device, macro_classes=None
    )
    return {
        "run_id": f"a1_seed_{seed}",
        "condition": "a1_max_mean_pooling",
        "seed": seed,
        "epochs_completed": len(history) - 1,
        "best_epoch": best["epoch"],
        "best_validation_macro_f1": best["score"],
        "best_validation_metrics": best["metrics"],
        "best_validation_loss": best["loss"],
        "history": history,
        "test_loss": test_loss,
        "test_metrics": test_metrics,
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": _sha256_file(checkpoint),
        "execution_seconds": time.perf_counter() - started,
        "environment": environment_metadata(device),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    config = load_config(PROJECT_ROOT / "configs" / "models" / "phase4_cnn_v1.yaml")
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    seeds = [args.seed] if args.seed is not None else [int(s) for s in config["training"]["seeds"]]
    for seed in seeds:
        path = output_dir / f"a1_seed_{seed}.json"
        if path.exists():
            print(f"seed {seed}: exists, skipping")
            continue
        print(f"seed {seed}")
        write_json(path, run_one_seed(PROJECT_ROOT, config, seed, output_dir, args.device))


if __name__ == "__main__":
    main()
