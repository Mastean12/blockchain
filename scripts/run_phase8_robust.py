"""Phase 8 runner: robust aggregation under clean and attack conditions.

Executes one (rule x condition x malicious-count) cell over a seed set, recording everything §21
requires: clean macro-F1, minority-class recall, attack degradation, detection rate, honest
false-positive rate, per-round validity, contribution/rejection counts, timing and seed variability.

Design constraints honoured:

- The frozen Phase 5 training recipe is reused unchanged (same pattern as the A1/A2 ablations).
- Development seeds (47, 48) may inform thresholds. Fresh seeds (49-53) must not be run until the
  thresholds are frozen; the runner warns loudly if a fresh seed is used before freezing.
- Admissibility is enforced: Krum at f = 2 raises rather than producing a misleading number.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

from src.aggregation.attacks import adversarial_updates, is_attack_condition, select_malicious
from src.aggregation.defence import (
    RejectionPolicy,
    apply_rejection_policy,
    summarise_accounting,
)
from src.aggregation.rules import check_admissible, get_rule
from src.data.phase3_pipeline import CLASS_ORDER
from src.federated.fedavg import _write_json, client_split, select_participants
from src.federated.partitions import verify_partition_manifest
from scripts.run_phase5_a2_ablation import train_local
from src.training.phase4 import (
    _cpu_state_dict,
    _model,
    evaluate_model,
    load_config,
    seed_everything,
)
from src.training.phase4_data import load_phase4_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "configs" / "aggregation"

DEVELOPMENT_SEEDS = (47, 48)
FRESH_SEEDS = (49, 50, 51, 52, 53)
# Amended protocol (see PHASE_8_PROTOCOL_AMENDMENT_PROPOSAL.md). These sets are disjoint from the
# original seeds, so an amended result can never be confused with an original confirmatory result.
AMENDED_DEVELOPMENT_SEEDS = (54, 55)
AMENDED_CONFIRMATORY_SEEDS = (56, 57, 58, 59, 60)
# Set to True only by the research lead, after thresholds are frozen on development seeds.
# Set 16 November 2026 following PHASE_8_THRESHOLD_VALIDATION.md: the frozen thresholds were
# exercised across 29 cells and 58 development-seed runs and found to discriminate correctly.
# No threshold value was altered after observing those results.
THRESHOLDS_FROZEN = True
# Set 17 November 2026 after approving amendment proposal A8-2 (intervention 3B). Gates the amended
# confirmatory seeds only; it does not affect the original fresh-seed gate above.
AMENDED_THRESHOLDS_FROZEN = True


class Phase8Error(RuntimeError):
    """Raised when a Phase 8 run would violate the approved protocol."""


def load_phase8_config(path: Path) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise Phase8Error(f"Expected a YAML mapping in {path}")
    if document.get("phase") != 8:
        raise Phase8Error("Phase 8 config must declare phase 8")
    aggregation = document.get("aggregation") or {}
    if not aggregation.get("rule"):
        raise Phase8Error("Config must name an aggregation rule")
    get_rule(aggregation["rule"])  # validates name and exclusion list
    phase8 = document.get("phase8") or {}
    if (phase8.get("approval") or {}).get("status") != "approved":
        raise Phase8Error("Phase 8 config lacks an approval record")

    seeds = [int(s) for s in document["training"]["seeds"]]
    role = phase8.get("seed_role")
    if role == "development":
        if any(seed not in DEVELOPMENT_SEEDS for seed in seeds):
            raise Phase8Error(f"Development configs may only use seeds {DEVELOPMENT_SEEDS}")
    elif role == "fresh":
        if not THRESHOLDS_FROZEN:
            raise Phase8Error(
                "Fresh-seed config refused: thresholds are not frozen. "
                "Freeze them on development seeds and set THRESHOLDS_FROZEN after approval."
            )
        if any(seed not in FRESH_SEEDS for seed in seeds):
            raise Phase8Error(f"Fresh configs may only use seeds {FRESH_SEEDS}")
    elif role == "amended_development":
        if any(seed not in AMENDED_DEVELOPMENT_SEEDS for seed in seeds):
            raise Phase8Error(
                f"Amended development configs may only use seeds {AMENDED_DEVELOPMENT_SEEDS}"
            )
    elif role == "amended_confirmatory":
        if not AMENDED_THRESHOLDS_FROZEN:
            raise Phase8Error(
                "Amended confirmatory config refused: amended thresholds are not frozen."
            )
        if any(seed not in AMENDED_CONFIRMATORY_SEEDS for seed in seeds):
            raise Phase8Error(
                f"Amended confirmatory configs may only use seeds {AMENDED_CONFIRMATORY_SEEDS}"
            )
        # A confirmatory config must never carry an original or development seed.
        forbidden = set(DEVELOPMENT_SEEDS) | set(FRESH_SEEDS) | set(AMENDED_DEVELOPMENT_SEEDS)
        if set(seeds) & forbidden:
            raise Phase8Error(
                "Amended confirmatory seeds must be disjoint from every original seed set"
            )
    else:
        raise Phase8Error(
            "Config must declare phase8.seed_role as development, fresh, "
            "amended_development or amended_confirmatory"
        )
    return document


def run_cell(
    root: Path,
    config: dict[str, Any],
    config_path: Path,
    client_splits: dict[str, Any],
    output_dir: Path,
    device_name: str,
    seed: int,
) -> dict[str, Any]:
    aggregation = config["aggregation"]
    rule_name = aggregation["rule"]
    condition = aggregation["condition"]
    byzantine = int(aggregation["byzantine_clients"])
    scale = float(aggregation.get("scale", 5.0))
    check_admissible(rule_name, byzantine)

    rule = get_rule(rule_name)
    data = load_phase4_data(root, config)
    federated = config["federated"]
    training = config["training"]
    rounds = int(federated["rounds"])
    local_epochs = int(federated["local_epochs"])
    fraction = float(federated["participation_fraction"])
    device = torch.device(device_name)

    client_ids = sorted(client_splits)
    counts = {client_id: len(client_splits[client_id].y) for client_id in client_ids}
    malicious = select_malicious(client_ids, byzantine)
    policy = RejectionPolicy(
        max_norm_ratio=float(
            (aggregation.get("rejection_policy") or {}).get("max_norm_ratio", 3.0)
        )
    )

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
    accounting_records = []
    best = {"score": None, "round": None, "state": None}
    diverged_at: int | None = None

    for round_index in range(rounds + 1):
        round_started = time.perf_counter()
        if round_index == 0:
            loss, metrics = evaluate_model(model, data.splits["validation"], batch, device,
                                          macro_classes=classes)
            rounds_log.append({"round": 0, "validation_loss": loss,
                               "validation_macro_f1": metrics["macro_f1"]})
        else:
            model.load_state_dict({k: v.to(device) for k, v in global_state.items()})
            participants = select_participants(client_ids, round_index, fraction, seed)

            updates: dict[str, torch.Tensor] = {}
            # O3 (Tier 1): `global_state` is immutable for the whole client loop — it is only
            # reassigned after every client has trained — so its float64 flattening is computed
            # once here instead of once per client. Same values, one third of the work.
            _baseline_flat = torch.cat([
                global_state[key].to(torch.float64).reshape(-1)
                for key in global_state
                if torch.is_floating_point(global_state[key])
            ])
            for client_id in participants:
                result = train_local(
                    global_state, config, client_splits[client_id], local_epochs, device,
                    seed=seed * 1000 + round_index * 10 + client_ids.index(client_id),
                )
                local = result["state"]
                delta = torch.cat([
                    local[key].to(torch.float64).reshape(-1)
                    for key in local
                    if torch.is_floating_point(local[key])
                ]) - _baseline_flat
                updates[client_id] = delta

            updates = adversarial_updates(updates, malicious, condition, scale=scale, seed=seed)

            # The rejection policy runs *in parallel* to measure detection and false positives.
            # It must not remove clients before aggregation: a robust rule needs the full client
            # set to apply its own filter, and Krum at n=4 is inadmissible.
            _, accounting = apply_rejection_policy(updates, policy, round_index)
            accounting_records.append(accounting)

            ordered = sorted(updates)
            aggregated = rule.callable(
                [updates[client_id] for client_id in ordered],
                [float(counts[client_id]) for client_id in ordered],
            )

            # Apply the aggregated delta to the global floating tensors; buffers stay as Phase 5.
            new_state = dict(global_state)
            offset = 0
            for key in global_state:
                if not torch.is_floating_point(global_state[key]):
                    continue
                size = global_state[key].numel()
                piece = aggregated[offset:offset + size].reshape(global_state[key].shape)
                new_state[key] = (
                    global_state[key].to(torch.float64) + piece.to(torch.float64)
                ).to(global_state[key].dtype)
                offset += size
            global_state = new_state
            model.load_state_dict({k: v.to(device) for k, v in global_state.items()})

            # Divergence guard. An attack may legitimately destroy the model; that is a finding,
            # so it is recorded and the run stops rather than raising and losing the evidence.
            # Two paths are needed: the weights may be non-finite, or the weights may be finite
            # while the validation loss overflows. The frozen evaluator raises on the latter, so
            # it is caught here and converted into a recorded outcome.
            diverged = not all(torch.isfinite(v).all() for v in global_state.values())
            loss = None
            metrics = None
            if not diverged:
                try:
                    loss, metrics = evaluate_model(model, data.splits["validation"], batch,
                                                   device, macro_classes=classes)
                except ValueError:
                    diverged = True

            if diverged:
                rounds_log.append({
                    "round": round_index,
                    "validation_loss": None,
                    "validation_macro_f1": None,
                    "rejected": accounting.rejected,
                    "accepted": accounting.accepted,
                    "median_norm": accounting.median_norm,
                    "seconds": time.perf_counter() - round_started,
                    "diverged": True,
                })
                diverged_at = round_index
                break

            rounds_log.append({
                "round": round_index,
                "validation_loss": loss,
                "validation_macro_f1": metrics["macro_f1"],
                "rejected": accounting.rejected,
                "accepted": accounting.accepted,
                "median_norm": accounting.median_norm,
                "seconds": time.perf_counter() - round_started,
            })

        score = rounds_log[-1]["validation_macro_f1"]
        if score is not None and (best["score"] is None or score > best["score"]):
            best = {"score": score, "round": round_index,
                    "state": {k: v.clone() for k, v in global_state.items()}}

    if best["state"] is None:
        # Diverged before any usable round: report the failure explicitly rather than
        # fabricating a checkpoint.
        accounting_summary = summarise_accounting(accounting_records, malicious)
        return {
            "experiment_id": config["experiment_id"],
            "rule": rule_name,
            "condition": condition,
            "is_attack": is_attack_condition(condition),
            "byzantine_clients": byzantine,
            "malicious_clients": malicious,
            "seed": seed,
            "status": "diverged_no_usable_checkpoint",
            "diverged_at_round": diverged_at,
            "selected_round": None,
            "best_validation_macro_f1": None,
            "test_loss": None,
            "test_metrics": None,
            "minority_class_recall": None,
            "rounds": [{k: v for k, v in record.items() if k != "accepted"}
                       for record in rounds_log],
            "accounting": {
                "detection_rate": accounting_summary["detection_rate"],
                "false_positive_rate": accounting_summary["false_positive_rate"],
                "malicious_client_rounds": accounting_summary["malicious_client_rounds"],
                "honest_client_rounds": accounting_summary["honest_client_rounds"],
                "per_round_rejections": [
                    {"round": rec.round_index, "rejected": rec.rejected}
                    for rec in accounting_records
                ],
            },
            "cost": {
                "total_seconds": sum(float(r.get("seconds", 0.0)) for r in rounds_log),
                "mean_round_seconds": float(np.mean([r.get("seconds", 0.0)
                                                     for r in rounds_log if r.get("seconds")]))
                if any(r.get("seconds") for r in rounds_log) else 0.0,
            },
        }

    model.load_state_dict({k: v.to(device) for k, v in best["state"].items()})
    test_loss, test_metrics = evaluate_model(model, data.splits["test"], batch, device,
                                             macro_classes=None)
    accounting_summary = summarise_accounting(accounting_records, malicious)

    return {
        "experiment_id": config["experiment_id"],
        "rule": rule_name,
        "condition": condition,
        "is_attack": is_attack_condition(condition),
        "byzantine_clients": byzantine,
        "malicious_clients": malicious,
        "seed": seed,
        "status": "completed",
        "diverged_at_round": diverged_at,
        "selected_round": best["round"],
        "best_validation_macro_f1": best["score"],
        "test_loss": test_loss,
        "test_metrics": test_metrics,
        "minority_class_recall": {
            "V": test_metrics["per_class"]["V"]["recall"],
            "S": test_metrics["per_class"]["S"]["recall"],
            "S_note": "S recall is 0.000 in every condition including clean; not diagnostic",
        },
        "rounds": [{k: v for k, v in record.items() if k != "accepted"}
                   for record in rounds_log],
        "accounting": {
            "detection_rate": accounting_summary["detection_rate"],
            "false_positive_rate": accounting_summary["false_positive_rate"],
            "malicious_client_rounds": accounting_summary["malicious_client_rounds"],
            "honest_client_rounds": accounting_summary["honest_client_rounds"],
            "per_round_rejections": [
                {"round": rec.round_index, "rejected": rec.rejected}
                for rec in accounting_records
            ],
        },
        "cost": {
            "total_seconds": sum(float(r.get("seconds", 0.0)) for r in rounds_log),
            "mean_round_seconds": float(np.mean([r.get("seconds", 0.0)
                                                 for r in rounds_log if r.get("seconds")])),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = load_phase8_config(config_path)

    data = load_phase4_data(PROJECT_ROOT, config)
    partition_document = json.loads(
        (PROJECT_ROOT / config["partition"]["manifest_path"]).read_text(encoding="utf-8")
    )
    verify_partition_manifest(data, partition_document)
    client_splits = {
        str(c["client_id"]): client_split(data, [str(r) for r in c["record_ids"]])
        for c in partition_document["clients"]
    }

    seeds = [args.seed] if args.seed is not None else [int(s) for s in config["training"]["seeds"]]
    output_dir = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    for seed in seeds:
        summary = run_cell(PROJECT_ROOT, config, config_path, client_splits,
                           output_dir / f"seed_{seed}", args.device, seed)
        _write_json(output_dir / f"seed_{seed}" / "phase8_summary.json", summary)
        print(f"seed {seed} {summary['rule']}/{summary['condition']}/f{summary['byzantine_clients']}"
              f" acc {summary['test_metrics']['accuracy']:.4f}"
              f" mF1 {summary['test_metrics']['macro_f1']:.4f}"
              f" rejected {len(summary['accounting']['per_round_rejections'][-1]['rejected']) if summary['accounting']['per_round_rejections'] else 0}")


if __name__ == "__main__":
    main()
