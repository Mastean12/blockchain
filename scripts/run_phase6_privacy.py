"""Run a Phase 6 privacy condition (P1-ctl, P1-a..d, P2, P3-a/b) on the frozen F3 partition."""

import argparse
import json
from pathlib import Path

import yaml

from src.federated.fedavg import client_split
from src.federated.partitions import verify_partition_manifest
from src.privacy.dp_federated import run_privacy_federated
from src.privacy.dp_mechanism import validate_accountant
from src.training.phase4 import load_config
from src.training.phase4_data import load_phase4_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "configs" / "privacy"

APPROVED_CLIP_NORM = 3.44
APPROVED_SIGMA = (0.5, 1.0, 2.0, 4.0)
APPROVED_DELTA = 1e-5
# Diagnostic frontier exploration authorised separately (D-2). These sigma values are NOT
# part of the approved experimental matrix and may only be used by configs carrying
# ``diagnostic: true``.
DIAGNOSTIC_SIGMA = (0.01, 0.05)
DIAGNOSTIC_SEED = 42
DIAGNOSTIC_MAX_ROUNDS = 8


def load_privacy_config(path: Path) -> dict:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    validate_privacy_config(document)
    return document


def validate_privacy_config(config: dict) -> None:
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported Phase 6 config schema")
    if config.get("phase") != 6:
        raise ValueError("Phase 6 config must declare phase 6")
    privacy = config.get("privacy")
    if not isinstance(privacy, dict):
        raise ValueError("Phase 6 config requires a privacy section")

    approval = privacy.get("approval") or {}
    if approval.get("status") != "approved":
        raise ValueError("Privacy config lacks a research-lead approval record")

    mode = privacy.get("mode")
    if mode not in {"none", "dp", "he", "he_dp"}:
        raise ValueError(f"Unsupported privacy mode: {mode!r}")

    clip_norm = privacy.get("clip_norm")
    if clip_norm is not None:
        if float(clip_norm) != APPROVED_CLIP_NORM:
            raise ValueError(f"Approved clip norm is {APPROVED_CLIP_NORM}")
    sigma = privacy.get("noise_multiplier")
    diagnostic = bool(config.get("diagnostic", False))
    if sigma is not None:
        allowed = APPROVED_SIGMA + (DIAGNOSTIC_SIGMA if diagnostic else ())
        if float(sigma) not in allowed:
            raise ValueError(
                f"Noise multiplier {sigma} is not approved for "
                f"{'diagnostic' if diagnostic else 'approved'} configs; allowed {allowed}"
            )
    if privacy.get("add_noise") and privacy.get("delta") is not None:
        if float(privacy["delta"]) != APPROVED_DELTA:
            raise ValueError(f"Approved delta is {APPROVED_DELTA}")

    # The training recipe must be the frozen Phase 4/5 recipe, unchanged.
    baseline = load_config(PROJECT_ROOT / "configs" / "models" / "phase4_cnn_v1.yaml")
    for key in ("model", "input_samples", "class_order", "metrics"):
        if config.get(key) != baseline.get(key):
            raise ValueError(f"Phase 6 config changes the frozen {key} section")
    for key in ("optimizer", "learning_rate", "weight_decay", "loss", "class_weights", "batch_size"):
        if config["training"].get(key) != baseline["training"].get(key):
            raise ValueError(f"Phase 6 config changes the frozen training.{key}")
    approved_seeds = baseline["training"].get("seeds")
    declared_seeds = config["training"].get("seeds")
    if diagnostic:
        # Diagnostic configs may run a single approved seed, never an unapproved one.
        if not declared_seeds or any(int(seed) not in approved_seeds for seed in declared_seeds):
            raise ValueError(f"Diagnostic seeds must be drawn from {approved_seeds}")
    elif declared_seeds != approved_seeds:
        raise ValueError("Phase 6 config must use the approved seeds 42-46")
    if config["training"]["early_stopping"] != baseline["training"]["early_stopping"]:
        raise ValueError("Phase 6 config must use the approved checkpoint-selection rule")

    federated = config.get("federated") or {}
    if diagnostic:
        # Diagnostic conditions are restricted further, not relaxed: one seed, short budget.
        if config["training"].get("seeds") != [DIAGNOSTIC_SEED]:
            raise ValueError(f"Diagnostic configs must use seed {DIAGNOSTIC_SEED} only")
        if int(federated.get("rounds", 0)) > DIAGNOSTIC_MAX_ROUNDS:
            raise ValueError(f"Diagnostic configs may run at most {DIAGNOSTIC_MAX_ROUNDS} rounds")
        if federated.get("local_epochs") != 2:
            raise ValueError("Diagnostic configs keep the approved 2 local epochs")
    else:
        if federated.get("rounds") != 50 or federated.get("local_epochs") != 2:
            raise ValueError("Phase 6 uses the approved 50 rounds and 2 local epochs")
    if float(federated.get("participation_fraction", 0.0)) != 1.0:
        raise ValueError("Approved participation is all five clients in every round")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--seed", type=int, default=None, help="Run a single seed instead of all")
    parser.add_argument(
        "--validate-accountant-only",
        action="store_true",
        help="Run the toy accountant gate and exit without training",
    )
    args = parser.parse_args()

    if args.validate_accountant_only:
        report = validate_accountant()
        print(json.dumps(report, indent=2))
        return

    project_root = args.project_root.resolve()
    config_path = (args.config or CONFIG_DIR / f"{args.experiment}.yaml").resolve()
    config = load_privacy_config(config_path)
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
        summary = run_privacy_federated(
            project_root=project_root,
            config=config,
            config_path=config_path,
            data=data,
            client_splits=client_splits,
            output_dir=output_dir / f"seed_{seed}",
            device_name=args.device,
            seed=seed,
        )
        epsilon = summary["privacy"]["accountant"]
        print(
            f"seed {seed}: selected_round {summary['selected_round']} "
            f"test_acc {summary['test_metrics']['accuracy']:.4f} "
            f"test_macro_f1 {summary['test_metrics']['macro_f1']} "
            f"eps {'n/a' if epsilon is None else round(epsilon['epsilon'], 3)}"
        )


if __name__ == "__main__":
    main()
