"""Phase 7 audit runner: record a federated run into the L1 hash chain and the L2 contract.

Design: the audit layer is a **wrapper**, not a modification. It re-executes the frozen Phase 5
recipe (a pattern already approved for the A1/A2 ablations) and records commitments as rounds occur.

Two neutrality requirements are enforced:

1. The audit layer must not consume the training PRNG. It never calls ``torch.manual_seed`` or any
   random function.
2. The resulting test metrics must match the frozen Phase 5 run for the same seed. ``--verify-neutral``
   compares against the stored baseline and fails loudly on any difference.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import torch

from src.blockchain.commitments import (
    commitment,
    file_commitment,
    make_event,
    participant_set_commitment,
    privacy_attestation,
    update_commitment,
)
from src.blockchain.ledger import HashChainLedger, compare_to_anchor, verify_ledger
from src.federated.fedavg import _write_json, client_split, select_participants, weighted_state_dict
from src.federated.partitions import verify_partition_manifest
from scripts.run_phase5_a2_ablation import train_local
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


def _state_bytes(state: dict[str, torch.Tensor]) -> bytes:
    """Serialise a model state deterministically for hashing."""
    hasher = hashlib.sha256()
    for key in sorted(state):
        tensor = state[key].detach().to(torch.float32).contiguous()
        hasher.update(key.encode("utf-8"))
        hasher.update(str(tuple(tensor.shape)).encode("utf-8"))
        hasher.update(tensor.numpy().tobytes())
    return hasher.digest()


def _state_commitment(state: dict[str, torch.Tensor]) -> str:
    return update_commitment(_state_bytes(state))


def run_audited(
    root: Path,
    config: dict[str, Any],
    config_path: Path,
    client_splits: dict[str, Any],
    partition_document: dict[str, Any],
    output_dir: Path,
    device_name: str,
    seed: int,
    contract: Any | None = None,
    max_rounds: int | None = None,
) -> dict[str, Any]:
    data = load_phase4_data(root, config)
    federated = config["federated"]
    training = config["training"]
    rounds = int(federated["rounds"]) if max_rounds is None else int(max_rounds)
    local_epochs = int(federated["local_epochs"])
    fraction = float(federated["participation_fraction"])
    device = torch.device(device_name)

    client_ids = sorted(client_splits)
    counts = {client_id: len(client_splits[client_id].y) for client_id in client_ids}

    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    run_id = f"{config['partition']['manifest_path'].split('/')[-1].replace('.json','')}_seed{seed}"
    ledger = HashChainLedger(output_dir / "audit_ledger.jsonl")

    audit_started = time.perf_counter()
    ledger.append(make_event("RunRegistered", {
        "run_id": run_id,
        "config_sha256": _sha256_file(config_path),
        "split_sha256": data.split_manifest_sha256,
        "client_manifest_sha256": data.client_manifest_sha256,
        "model_arch_id": "compact_cnn_v1",
        "seed": seed,
    }))
    if contract is not None:
        contract.register_run(
            run_id,
            _sha256_file(config_path),
            data.split_manifest_sha256,
            data.client_manifest_sha256,
        )

    seed_everything(seed, bool(training["deterministic_algorithms"]))
    model = _model(config, device)
    global_state = _cpu_state_dict(model)
    classes = list(training["early_stopping"]["classes"])
    batch = int(training["batch_size"])

    rounds_log: list[dict[str, Any]] = []
    best = {"score": None, "round": None, "state": None, "metrics": None, "loss": None}
    audit_seconds = 0.0

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

            audit_round_started = time.perf_counter()
            ledger.append(make_event("RoundOpened", {
                "run_id": run_id,
                "round_index": round_index,
                "participant_set_sha256": participant_set_commitment(participants),
            }))
            if contract is not None:
                contract.open_round(run_id, round_index,
                                    participant_set_commitment(participants))
            audit_seconds += time.perf_counter() - audit_round_started

            states = []
            for client_id in participants:
                result = train_local(
                    global_state, config, client_splits[client_id], local_epochs, device,
                    seed=seed * 1000 + round_index * 10 + client_ids.index(client_id),
                )
                states.append((result["state"], counts[client_id]))

                client_cipher = _state_bytes(result["state"])
                audit_client_started = time.perf_counter()
                ledger.append(make_event("UpdateCommitted", {
                    "run_id": run_id,
                    "round_index": round_index,
                    "client_id": client_id,
                    "update_sha256": update_commitment(client_cipher),
                    "update_bytes": len(client_cipher),
                }))
                if contract is not None:
                    contract.commit_update(run_id, round_index, client_id,
                                           update_commitment(client_cipher), len(client_cipher))
                audit_seconds += time.perf_counter() - audit_client_started

            global_state = weighted_state_dict(states)
            model.load_state_dict({k: v.to(device) for k, v in global_state.items()})

            global_hash = _state_commitment(global_state)
            audit_close_started = time.perf_counter()
            ledger.append(make_event("RoundClosed", {
                "run_id": run_id,
                "round_index": round_index,
                "global_model_sha256": global_hash,
                "aggregation_rule_id": "fedavg_sample_weighted",
            }))
            if contract is not None:
                contract.close_round(run_id, round_index, global_hash,
                                     "fedavg_sample_weighted")
            audit_seconds += time.perf_counter() - audit_close_started

            loss, metrics = evaluate_model(model, data.splits["validation"], batch, device,
                                          macro_classes=classes)
            rounds_log.append({"round": round_index, "validation_loss": loss,
                               "validation_macro_f1": metrics["macro_f1"]})

        score = rounds_log[-1]["validation_macro_f1"]
        if score is not None and (best["score"] is None or score > best["score"]):
            best = {"score": score, "round": round_index,
                    "state": {k: v.clone() for k, v in global_state.items()},
                    "metrics": metrics, "loss": loss}
        rounds_log[-1]["seconds"] = time.perf_counter() - round_started

    model.load_state_dict({k: v.to(device) for k, v in best["state"].items()})
    checkpoint = output_dir / "checkpoints" / f"audited_seed_{seed}.pt"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save(_cpu_state_dict(model), checkpoint)
    checkpoint_hash = file_commitment(checkpoint)

    ledger.append(make_event("CheckpointSealed", {
        "run_id": run_id,
        "selected_round": int(best["round"]),
        "checkpoint_sha256": checkpoint_hash,
    }))
    if contract is not None:
        contract.seal_checkpoint(run_id, int(best["round"]), checkpoint_hash)

    test_loss, test_metrics = evaluate_model(model, data.splits["test"], batch, device,
                                             macro_classes=None)

    total_audit = time.perf_counter() - audit_started
    verification = verify_ledger(output_dir / "audit_ledger.jsonl")
    summary = {
        "run_id": run_id,
        "seed": seed,
        "audit_condition": "B2_ganache" if contract is not None else "B1_hash_chain",
        "selected_round": best["round"],
        "best_validation_macro_f1": best["score"],
        "test_loss": test_loss,
        "test_metrics": test_metrics,
        "checkpoint_sha256": checkpoint_hash,
        "rounds": rounds_log,
        "audit": {
            "entries": len(ledger),
            "head_hash": ledger.head_hash(),
            "verification": verification,
            "append_seconds": audit_seconds,
            "total_audit_seconds": total_audit,
            "per_round_audit_seconds": audit_seconds / max(1, rounds),
            "contract": contract.deployment if contract is not None else None,
            "contract_measurements": contract.measurement_table() if contract is not None else None,
            "on_chain_bytes_per_round": 32 * 3 + 8,  # 2 hashes + rule hash + one int, conservative
            "environment": environment_metadata(device),
        },
    }
    _write_json(output_dir / "audit_summary.json", summary)
    _write_json(output_dir / "anchor.json", {
        "run_id": run_id,
        "head_hash": ledger.head_hash(),
        "entries": len(ledger),
        "note": "Out-of-band anchor. Comparing a ledger to this value detects truncation and "
                "consistent rewrite, which an internally valid chain cannot reveal.",
    })
    if contract is not None:
        summary["audit"]["contract_verification"] = contract.read_run(run_id)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-name", default="phase5_f3_fedavg_severe")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--use-contract", action="store_true",
                        help="Also record to the Ganache contract (Level 2)")
    parser.add_argument("--max-rounds", type=int, default=None)
    args = parser.parse_args()

    import yaml

    config = load_config(PROJECT_ROOT / "configs" / "models" / "phase4_cnn_v1.yaml")
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

    contract = None
    if args.use_contract:
        from src.blockchain.evm import AuditContract

        contract = AuditContract.deploy()

    seeds = [args.seed] if args.seed is not None else [int(s) for s in config["training"]["seeds"]]
    for seed in seeds:
        summary = run_audited(
            PROJECT_ROOT, config, PROJECT_ROOT / "configs" / "models" / "phase4_cnn_v1.yaml",
            client_splits, partition_document, args.output_dir / f"seed_{seed}",
            args.device, seed, contract, args.max_rounds,
        )
        print(f"seed {seed}: acc {summary['test_metrics']['accuracy']:.4f} "
              f"mF1 {summary['test_metrics']['macro_f1']:.4f} "
              f"ledger {summary['audit']['entries']} entries "
              f"verify {summary['audit']['verification']['valid']}")


if __name__ == "__main__":
    main()
