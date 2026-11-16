"""Run a Phase 5 federated experiment (FedAvg or FedProx) on a frozen partition."""

import argparse
import json
from pathlib import Path

import yaml

from src.federated.fedavg import client_split, run_federated
from src.federated.partitions import verify_partition_manifest
from src.training.phase4 import load_config
from src.training.phase4_data import load_phase4_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "configs" / "federated"

APPROVED_VALUES = {"rounds", "local_epochs", "participation_fraction", "proximal_mu"}

APPROVED_DECISIONS = {
    "rounds": 50,
    "local_epochs": 2,
    "participation_fraction": 1.0,
    "fedprox_proximal_mu": 0.01,
}


def load_federated_config(path: Path) -> dict:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    validate_federated_config(document)
    return document


def validate_federated_config(config: dict) -> None:
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported Phase 5 config schema")
    federated = config.get("federated")
    if not isinstance(federated, dict):
        raise ValueError("Phase 5 config requires a federated section")

    pending = []
    for key in APPROVED_VALUES:
        value = federated.get(key)
        if value == "pending_approval":
            pending.append(key)
    if pending:
        raise ValueError(
            "Federated hyperparameters are not yet approved: " + ", ".join(sorted(pending))
            + ". Record research-lead approval in the config before running."
        )

    approval = federated.get("approval") or {}
    if approval.get("status") != "approved":
        raise ValueError("Federated config lacks a research-lead approval record")
    if int(federated["rounds"]) != APPROVED_DECISIONS["rounds"]:
        raise ValueError(f"Approved round budget is {APPROVED_DECISIONS['rounds']}")
    if int(federated["local_epochs"]) != APPROVED_DECISIONS["local_epochs"]:
        raise ValueError(f"Approved local epoch count is {APPROVED_DECISIONS['local_epochs']}")
    if float(federated["participation_fraction"]) != APPROVED_DECISIONS["participation_fraction"]:
        raise ValueError("Approved participation is all five clients in every round")
    if federated.get("batchnorm_handling") != "running_statistics_weighted_by_sample_count":
        raise ValueError("Approved BatchNorm handling is sample-count-weighted aggregation")
    if federated.get("optimizer_state_policy") != "reset_each_round":
        raise ValueError("Approved optimizer policy is state reset at the beginning of each round")

    method = federated.get("method")
    if method not in {"fedavg", "fedprox"}:
        raise ValueError(f"Unsupported federated method: {method!r}")
    rounds = int(federated["rounds"])
    local_epochs = int(federated["local_epochs"])
    if rounds < 1 or local_epochs < 1:
        raise ValueError("rounds and local_epochs must be positive integers")
    fraction = float(federated["participation_fraction"])
    if not 0.0 < fraction <= 1.0:
        raise ValueError("participation_fraction must be in (0, 1]")
    mu = federated.get("proximal_mu")
    if method == "fedprox" and (mu is None or float(mu) <= 0):
        raise ValueError("FedProx requires a positive proximal_mu")
    if method == "fedprox" and float(mu) != APPROVED_DECISIONS["fedprox_proximal_mu"]:
        raise ValueError(
            f"Approved FedProx proximal_mu is {APPROVED_DECISIONS['fedprox_proximal_mu']}"
        )
    if method == "fedavg" and mu not in (None, 0):
        raise ValueError("FedAvg must leave proximal_mu empty")

    # The frozen training recipe must not be altered by a federated config.
    baseline = load_config(PROJECT_ROOT / "configs" / "models" / "phase4_cnn_v1.yaml")
    for key in ("model", "input_samples", "class_order", "metrics"):
        if config.get(key) != baseline.get(key):
            raise ValueError(f"Federated config changes the frozen {key} section")
    for key in ("optimizer", "learning_rate", "weight_decay", "loss", "class_weights", "batch_size"):
        if config["training"].get(key) != baseline["training"].get(key):
            raise ValueError(f"Federated config changes the frozen training.{key}")
    if config["training"].get("seeds") != baseline["training"].get("seeds"):
        raise ValueError("Federated config must use the approved seeds 42-46")
    if config["training"]["early_stopping"] != baseline["training"]["early_stopping"]:
        raise ValueError("Federated config must use the approved checkpoint-selection rule")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--seed", type=int, default=None, help="Run a single seed instead of all")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    config_path = (args.config or CONFIG_DIR / f"{args.experiment}.yaml").resolve()
    config = load_federated_config(config_path)
    data = load_phase4_data(project_root, config)

    partition_path = project_root / config["partition"]["manifest_path"]
    partition_document = json.loads(partition_path.read_text(encoding="utf-8"))
    verify_partition_manifest(data, partition_document)
    if partition_document["manifest_sha256"] != config["partition"]["manifest_sha256"]:
        raise ValueError("Partition manifest hash differs from the frozen config")

    client_splits = {
        str(client["client_id"]): client_split(data, [str(r) for r in client["record_ids"]])
        for client in partition_document["clients"]
    }

    seeds = [args.seed] if args.seed is not None else [int(s) for s in config["training"]["seeds"]]
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir

    for seed in seeds:
        summary = run_federated(
            project_root=project_root,
            config=config,
            config_path=config_path,
            data=data,
            client_splits=client_splits,
            output_dir=output_dir / f"seed_{seed}",
            device_name=args.device,
            seed=seed,
            resume=args.resume,
        )
        print(
            f"seed {seed}: selected_round {summary['selected_round']} "
            f"test_acc {summary['test_metrics']['accuracy']:.4f} "
            f"test_macro_f1 {summary['test_metrics']['macro_f1']}"
        )


if __name__ == "__main__":
    main()
