"""Phase 9 integration layer.

**Composes already-validated components.** It does not introduce new mechanisms.

Eligibility (master spec §37, "integrate only components that passed individual tests"):

- dataset/split (G3), FedAvg (G5), HE (G6), ledger (G7) — included;
- **robust aggregation — EXCLUDED** because G8 did not pass;
- DP — excluded by default (recommendation 9-DP-a; the mechanism passed its gate but its scientific
  result was negative).

Design rule: this module calls the existing implementations rather than reimplementing anything, so
an integration result can never diverge from the unit-tested component behaviour.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch

from src.blockchain.commitments import file_commitment, make_event, participant_set_commitment
from src.blockchain.ledger import HashChainLedger, verify_ledger
from src.federated.fedavg import client_split, select_participants, weighted_state_dict
from src.federated.partitions import verify_partition_manifest
from src.privacy.he_ckks import (
    HEConfig,
    HEContext,
    ciphertext_bytes,
    ciphertext_count,
    homomorphic_weighted_sum,
    relative_l2_error,
)
from src.training.phase4 import (
    _cpu_state_dict,
    _model,
    _sha256_file,
    evaluate_model,
    load_config,
    seed_everything,
)
from src.training.phase4_data import load_phase4_data
from scripts.run_phase5_a2_ablation import train_local

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INTEGRATION_MODES = ("centralized", "local_only", "federated", "federated_he")

# G8 failed, so no robust rule may be integrated. Declared explicitly so a future caller cannot
# enable one by accident.
EXCLUDED_FROM_INTEGRATION = {
    "robust_aggregation": "G8 NOT PASSED - master spec section 37 forbids integrating a failed component",
    "dp": "recommendation 9-DP-a: mechanism validated but scientific result negative",
}


class IntegrationError(RuntimeError):
    """Raised when an integration run would violate the eligibility rules."""


@dataclass
class IntegrationResult:
    """Outcome of one integration run."""

    mode: str
    seed: int
    rounds: int
    device: str
    test_metrics: dict[str, Any] | None = None
    validation_history: list[dict[str, Any]] = field(default_factory=list)
    ledger_entries: int = 0
    ledger_head: str | None = None
    ledger_valid: bool = False
    he_included: bool = False
    he_max_relative_error: float | None = None
    he_ciphertext_bytes_per_client: int | None = None
    elapsed_seconds: float = 0.0
    environment: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "seed": self.seed,
            "rounds": self.rounds,
            "device": self.device,
            "test_metrics": self.test_metrics,
            "validation_history": self.validation_history,
            "ledger_entries": self.ledger_entries,
            "ledger_head": self.ledger_head,
            "ledger_valid": self.ledger_valid,
            "he_included": self.he_included,
            "he_max_relative_error": self.he_max_relative_error,
            "he_ciphertext_bytes_per_client": self.he_ciphertext_bytes_per_client,
            "elapsed_seconds": self.elapsed_seconds,
            "environment": self.environment,
        }


def assert_integration_allowed(component: str) -> None:
    """Refuse to integrate a component whose gate did not pass."""
    if component in EXCLUDED_FROM_INTEGRATION:
        raise IntegrationError(
            f"{component} cannot be integrated: {EXCLUDED_FROM_INTEGRATION[component]}"
        )


def _environment() -> dict[str, Any]:
    info: dict[str, Any] = {
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
    }
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        info["device"] = props.name
        info["vram_gb"] = round(props.total_memory / 1024**3, 2)
    return info


def _load_f3(project_root: Path) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any]]:
    """Load the frozen config, data, partition and per-client splits."""
    config = load_config(project_root / "configs" / "models" / "phase4_cnn_v1.yaml")
    federated_config = json.loads(
        (project_root / "configs" / "federated" / "phase5_f3_fedavg_severe.yaml")
        .read_text(encoding="utf-8")
        .replace("", "") or "{}"
    ) if False else None

    import yaml

    fed = yaml.safe_load(
        (project_root / "configs" / "federated" / "phase5_f3_fedavg_severe.yaml").read_text(encoding="utf-8")
    )
    config = {**config, "federated": fed["federated"], "partition": fed["partition"]}

    data = load_phase4_data(project_root, config)
    partition = json.loads(
        (project_root / config["partition"]["manifest_path"]).read_text(encoding="utf-8")
    )
    verify_partition_manifest(data, partition)
    splits = {
        str(c["client_id"]): client_split(data, [str(r) for r in c["record_ids"]])
        for c in partition["clients"]
    }
    return config, data, partition, splits


def run_integrated(
    project_root: Path,
    mode: str,
    seed: int = 61,
    rounds: int = 2,
    device_name: str = "cuda",
    max_samples: int | None = None,
    ledger_path: Path | None = None,
) -> IntegrationResult:
    """Run one short integration pass.

    ``mode`` is one of ``centralized``, ``local_only``, ``federated``, ``federated_he``.
    ``rounds`` is deliberately small: this is a smoke test, not an experiment.
    """
    if mode not in INTEGRATION_MODES:
        raise IntegrationError(f"Unknown integration mode {mode!r}")

    started = time.perf_counter()
    config, data, partition, splits = _load_f3(project_root)
    training = config["training"]
    device = torch.device(device_name if torch.cuda.is_available() else "cpu")
    classes = list(training["early_stopping"]["classes"])
    batch = int(training["batch_size"])
    client_ids = sorted(splits)

    result = IntegrationResult(mode=mode, seed=seed, rounds=rounds,
                               device=str(device), environment=_environment())

    seed_everything(seed, bool(training["deterministic_algorithms"]))

    # ------------------------------------------------------------------ centralized / local_only
    if mode in ("centralized", "local_only"):
        model = _model(config, device)
        splits_to_eval = []
        if mode == "centralized":
            splits_to_eval = [("train", data.splits["train"])]
        else:
            splits_to_eval = [(cid, splits[cid]) for cid in client_ids]

        for label, split in splits_to_eval:
            local_cfg = json.loads(json.dumps(config))
            gs = _cpu_state_dict(model)
            for _ in range(rounds):
                out = train_local(gs, local_cfg, split, 1, device, seed=seed)
                gs = out["state"]
            model.load_state_dict({k: v.to(device) for k, v in gs.items()})
            _, vm = evaluate_model(model, data.splits["validation"], batch, device,
                                   macro_classes=classes)
            result.validation_history.append({
                "stage": label, "validation_macro_f1": vm["macro_f1"],
                "validation_accuracy": vm["accuracy"],
            })

        _, tm = evaluate_model(model, data.splits["test"], batch, device, macro_classes=None)
        result.test_metrics = {
            "accuracy": tm["accuracy"], "macro_f1": tm["macro_f1"],
            "per_class": {k: {"recall": v["recall"], "support": v["support"]}
                          for k, v in tm["per_class"].items()},
        }
        result.elapsed_seconds = time.perf_counter() - started
        return result

    # ------------------------------------------------------------------ federated (optionally HE)
    use_he = mode == "federated_he"
    he_context = HEContext(HEConfig()) if use_he else None
    model = _model(config, device)
    global_state = _cpu_state_dict(model)
    counts = {cid: len(splits[cid].y) for cid in client_ids}

    ledger = None
    if ledger_path is not None:
        ledger = HashChainLedger(ledger_path)

    run_id = f"integration_{mode}_seed{seed}"
    if ledger is not None:
        ledger.append(make_event("RunRegistered", {
            "run_id": run_id,
            "config_sha256": _sha256_file(project_root / "configs" / "models" / "phase4_cnn_v1.yaml"),
            "split_sha256": data.split_manifest_sha256,
            "client_manifest_sha256": data.client_manifest_sha256,
            "model_arch_id": "compact_cnn_v1",
            "seed": seed,
        }))

    parameter_keys = [k for k in global_state if torch.is_floating_point(global_state[k])]

    for round_index in range(1, rounds + 1):
        model.load_state_dict({k: v.to(device) for k, v in global_state.items()})
        participants = select_participants(client_ids, round_index, 1.0, seed)

        if ledger is not None:
            ledger.append(make_event("RoundOpened", {
                "run_id": run_id,
                "round_index": round_index,
                "participant_set_sha256": participant_set_commitment(participants),
            }))

        states = []
        ciphertexts = {}
        for cid in participants:
            out = train_local(global_state, config, splits[cid], 1, device,
                              seed=seed * 1000 + round_index * 10 + client_ids.index(cid))
            states.append((out["state"], counts[cid]))

            if ledger is not None:
                flat = torch.cat([out["state"][k].reshape(-1) for k in parameter_keys])
                ledger.append(make_event("UpdateCommitted", {
                    "run_id": run_id,
                    "round_index": round_index,
                    "client_id": cid,
                    "update_sha256": __import__("hashlib").sha256(
                        flat.numpy().tobytes()
                    ).hexdigest(),
                    "update_bytes": int(flat.numel() * 4),
                }))

            if use_he:
                flat = torch.cat([out["state"][k].reshape(-1).to(torch.float32)
                                  for k in parameter_keys])
                ciphertexts[cid] = he_context.encrypt_chunks(flat)

        if use_he:
            weights = {cid: counts[cid] / sum(counts.values()) for cid in participants}
            aggregated_ct = homomorphic_weighted_sum(ciphertexts, weights)
            n_params = sum(global_state[k].numel() for k in parameter_keys)
            decrypted = he_context.decrypt_chunks(aggregated_ct, n_params)

            # Exact reference in the same flat layout as the ciphertext payload.
            # `states` holds (state_dict, sample_count) tuples, so unpack first.
            exact = torch.cat([
                sum(state[k].to(torch.float64) * weights[cid]
                    for (state, _), cid in zip(states, participants)).reshape(-1).to(torch.float32)
                for k in parameter_keys
            ])
            err = relative_l2_error(decrypted, exact)
            result.he_max_relative_error = (
                err if result.he_max_relative_error is None
                else max(result.he_max_relative_error, err)
            )
            result.he_ciphertext_bytes_per_client = ciphertext_bytes(
                next(iter(ciphertexts.values()))
            )
            result.he_included = True

            new_state = {}
            offset = 0
            for k in global_state:
                if not torch.is_floating_point(global_state[k]):
                    new_state[k] = global_state[k].clone()
                    continue
                size = global_state[k].numel()
                piece = decrypted[offset:offset + size].reshape(global_state[k].shape)
                new_state[k] = piece.to(global_state[k].dtype)
                offset += size
            global_state = new_state
        else:
            global_state = weighted_state_dict(states)

        model.load_state_dict({k: v.to(device) for k, v in global_state.items()})
        _, vm = evaluate_model(model, data.splits["validation"], batch, device,
                               macro_classes=classes)
        result.validation_history.append({
            "round": round_index,
            "validation_macro_f1": vm["macro_f1"],
            "validation_accuracy": vm["accuracy"],
        })

        if ledger is not None:
            ledger.append(make_event("RoundClosed", {
                "run_id": run_id,
                "round_index": round_index,
                "global_model_sha256": __import__("hashlib").sha256(
                    torch.cat([global_state[k].reshape(-1).to(torch.float32)
                               for k in parameter_keys]).numpy().tobytes()
                ).hexdigest(),
                "aggregation_rule_id": "fedavg_sample_weighted",
            }))

    _, tm = evaluate_model(model, data.splits["test"], batch, device, macro_classes=None)
    result.test_metrics = {
        "accuracy": tm["accuracy"], "macro_f1": tm["macro_f1"],
        "per_class": {k: {"recall": v["recall"], "support": v["support"]}
                      for k, v in tm["per_class"].items()},
    }

    if ledger is not None:
        result.ledger_entries = len(ledger)
        result.ledger_head = ledger.head_hash()
        check_path = ledger.path
        result.ledger_valid = bool(verify_ledger(check_path)["valid"])

    result.elapsed_seconds = time.perf_counter() - started
    return result
