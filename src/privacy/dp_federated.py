"""Phase 6 privacy-preserving federated training: P1 (DP), P2 (HE), P3 (HE+DP), P1-ctl.

Runs the frozen FedAvg training procedure unchanged, inserting the approved privacy
transformation at the point fixed in ``docs/PHASE_6_PRIVACY_MATHEMATICS.md`` §8:

    clip → add Gaussian noise → (encrypt) → aggregate → (decrypt)

Design rules honoured here:

- The model, optimizer, loss, batch size, epochs, seeds, partition and checkpoint-selection
  rule are the frozen Phase 5 recipe. Nothing is retuned.
- The DP payload is the 36,357 trainable parameters. BatchNorm buffers and
  ``num_batches_tracked`` are excluded and aggregated exactly as Phase 5 (decision D5, a
  disclosed limitation).
- Aggregation weights are the frozen public sample counts, so the released aggregate is a
  fixed linear functional and the sensitivity of ``PHASE_6_PRIVACY_MATHEMATICS.md`` holds.
- Test data is read exactly once per seed, after the selected round is fixed.
- P1-ctl clips but adds no noise, and therefore provides no privacy.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch

from src.data.phase3_pipeline import CLASS_ORDER
from src.federated.fedavg import (
    FederatedError,
    select_participants,
    weighted_state_dict,
)
from src.privacy.calibration import train_local_observed, trainable_parameter_keys
from src.privacy.clipping import (
    PrivacyError,
    clip_update,
    frozen_weights,
    per_client_sensitivity,
)
from src.privacy.dp_mechanism import (
    RandomnessMode,
    add_gaussian_noise,
    compute_epsilon,
    make_generator,
    validate_accountant,
)
from src.privacy.he_ckks import (
    HEContext,
    HEConfig,
    ciphertext_bytes,
    ciphertext_count,
    homomorphic_weighted_sum,
    relative_l2_error,
)
from src.training.phase4 import (
    _cpu_state_dict,
    _model,
    _sha256_file,
    environment_metadata,
    evaluate_model,
    seed_everything,
)
from src.training.phase4_data import Phase4Data, SplitArrays

PRIVACY_MODES = ("none", "dp", "he", "he_dp")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, sort_keys=True)
        file.write("\n")


def _flatten_parameters(
    state: dict[str, torch.Tensor], keys: list[str]
) -> torch.Tensor:
    return torch.cat([state[key].detach().to(torch.float32).reshape(-1) for key in keys])


def _unflatten_parameters(
    flat: torch.Tensor, keys: list[str], reference: dict[str, torch.Tensor]
) -> dict[str, torch.Tensor]:
    result: dict[str, torch.Tensor] = {}
    offset = 0
    for key in keys:
        count = reference[key].numel()
        result[key] = flat[offset:offset + count].reshape(reference[key].shape).clone()
        offset += count
    if offset != flat.numel():
        raise PrivacyError("Flattened parameter vector length does not match the model")
    return result


def run_privacy_federated(
    project_root: Path,
    config: dict[str, Any],
    config_path: Path,
    data: Phase4Data,
    client_splits: dict[str, SplitArrays],
    output_dir: Path,
    device_name: str,
    seed: int,
) -> dict[str, Any]:
    """Run one Phase 6 condition for one seed. Writes round-level artefacts."""
    privacy = config["privacy"]
    mode = str(privacy["mode"])
    if mode not in PRIVACY_MODES:
        raise PrivacyError(f"Unsupported privacy mode: {mode!r}")

    federated = config["federated"]
    training = config["training"]
    rounds = int(federated["rounds"])
    local_epochs = int(federated["local_epochs"])
    fraction = float(federated["participation_fraction"])

    use_dp = mode in ("dp", "he_dp")
    use_he = mode in ("he", "he_dp")
    clip_only = bool(privacy.get("clip_only", False))
    add_noise = bool(privacy.get("add_noise", use_dp))
    clip_norm = privacy.get("clip_norm")

    do_clip = clip_only or use_dp
    if do_clip and clip_norm is None:
        raise PrivacyError("Clipping requires an approved clip_norm")
    if not do_clip and clip_norm is not None:
        raise PrivacyError("A clip_norm was supplied but clipping is not enabled")
    if mode == "none" and not clip_only:
        raise PrivacyError("Use mode 'none' only for the clip-only control")
    if mode != "none" and clip_only:
        raise PrivacyError("clip_only is only valid for the clip-only control condition")
    if use_dp and not add_noise:
        raise PrivacyError("DP conditions must add noise; use mode 'none' for clip-only")
    if not use_dp and add_noise:
        raise PrivacyError("Noise was requested without a DP mode")

    if add_noise:
        noise_multiplier = privacy.get("noise_multiplier")
        if noise_multiplier is None:
            raise PrivacyError("A noise multiplier is required when noise is enabled")
        delta = float(privacy["delta"])
    else:
        noise_multiplier = None
        delta = None

    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    device = torch.device(device_name)

    client_ids = sorted(client_splits)
    for client_id, split in client_splits.items():
        if len(split.y) == 0:
            raise FederatedError(f"{client_id} has an empty training split")

    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite privacy output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    seed_everything(seed, bool(training["deterministic_algorithms"]))
    model = _model(config, device)
    global_state = _cpu_state_dict(model)
    keys = trainable_parameter_keys(global_state, model)
    parameter_count = int(sum(global_state[key].numel() for key in keys))

    # Frozen public weights (definition 4.1): fixed constants, not realised counts.
    counts = {client_id: len(client_splits[client_id].y) for client_id in client_ids}
    weights = frozen_weights(counts)
    max_weight = max(weights.values())

    he_context = HEContext(HEConfig()) if use_he else None
    expected_ciphertexts = ciphertext_count(parameter_count) if use_he else None
    plaintext_bytes = parameter_count * 4

    if add_noise:
        accountant_gate = validate_accountant()
    else:
        accountant_gate = None

    selection_classes = list(training["early_stopping"]["classes"])
    rounds_log: list[dict[str, Any]] = []
    best: dict[str, Any] = {
        "score": None, "round": None, "state": None,
        "validation_metrics": None, "validation_loss": None,
    }

    _write_json(output_dir / "run_metadata.json", {
        "seed": seed,
        "condition_mode": mode,
        "add_noise": add_noise,
        "noise_multiplier": noise_multiplier,
        "delta": delta,
        "clip_norm": clip_norm,
        "parameter_count": parameter_count,
        "excluded_unprotected_components": [
            "BatchNorm running_mean/running_var (448 floats)",
            "num_batches_tracked (3 ints)",
        ],
        "randomness_mode": RandomnessMode.RESEARCH if add_noise else "not_applicable",
        "privacy_provided": bool(add_noise),
        "simulation_only": True,
        "frozen_weights": weights,
        "config_sha256": __import__("hashlib").sha256(config_path.read_bytes()).hexdigest(),
        "split_manifest_sha256": data.split_manifest_sha256,
        "client_manifest_sha256": data.client_manifest_sha256,
        "he_config": he_context.config.as_dict() if he_context else None,
        "accountant_gate": accountant_gate,
        "environment": environment_metadata(device),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
    })

    invocation_started = time.perf_counter()

    for round_index in range(rounds + 1):
        round_started = time.perf_counter()
        if round_index == 0:
            validation_loss, validation_metrics = evaluate_model(
                model, data.splits["validation"], int(training["batch_size"]), device,
                macro_classes=selection_classes,
            )
            round_record = {
                "round": 0,
                "participants": [],
                "validation_loss": validation_loss,
                "validation_macro_f1": validation_metrics["macro_f1"],
                "seconds": time.perf_counter() - round_started,
            }
        else:
            model.load_state_dict({key: value.to(device) for key, value in global_state.items()})
            participants = select_participants(client_ids, round_index, fraction, seed)
            local_states: list[tuple[dict[str, torch.Tensor], int]] = []
            client_stats: dict[str, Any] = {}
            encode_started = time.perf_counter()
            ciphertext_payloads: dict[str, Any] = {}
            clip_seconds = noise_seconds = encrypt_seconds = 0.0

            for client_id in participants:
                result = train_local_observed(
                    global_state, config, client_splits[client_id], local_epochs, device,
                    seed=seed * 1000 + round_index * 10 + client_ids.index(client_id),
                )
                local_state = result["state"]
                local_states.append((local_state, result["samples"]))

                stats: dict[str, Any] = {}
                if do_clip:
                    flat = _flatten_parameters(local_state, keys)
                    baseline = _flatten_parameters(global_state, keys)
                    update = flat - baseline
                    clip_started = time.perf_counter()
                    clipped = clip_update(update, float(clip_norm))
                    clip_seconds += time.perf_counter() - clip_started
                    stats["update_norm_before_clip"] = clipped.norm_before
                    stats["update_norm_after_clip"] = clipped.norm_after
                    stats["clipped"] = clipped.clipped
                    payload = clipped.tensor
                    if add_noise:
                        noise_started = time.perf_counter()
                        payload = add_gaussian_noise(
                            payload,
                            float(noise_multiplier),
                            float(clip_norm),
                            make_generator(seed, round_index, client_ids.index(client_id)),
                        )
                        noise_seconds += time.perf_counter() - noise_started
                    # The payload is an update, not a parameter value: reconstruct
                    # w_local' = w_global + transformed_delta.
                    private_state = dict(local_state)
                    transformed_delta = _unflatten_parameters(payload, keys, global_state)
                    for key in keys:
                        private_state[key] = (
                            global_state[key].to(torch.float64)
                            + transformed_delta[key].to(torch.float64)
                        ).to(local_state[key].dtype)
                    local_states[-1] = (private_state, result["samples"])
                    # The HE payload is the transformed *update* here, not the parameters.
                    transformed = payload
                else:
                    transformed = _flatten_parameters(local_state, keys)

                if use_he:
                    encrypt_started = time.perf_counter()
                    ciphertext_payloads[client_id] = he_context.encrypt_chunks(transformed)
                    encrypt_seconds += time.perf_counter() - encrypt_started
                    if len(ciphertext_payloads[client_id]) != expected_ciphertexts:
                        raise PrivacyError(
                            f"Expected {expected_ciphertexts} ciphertexts, "
                            f"got {len(ciphertext_payloads[client_id])}"
                        )
                client_stats[client_id] = stats

            aggregate_seconds = decrypt_seconds = 0.0
            approximation_error = None
            if use_he:
                aggregate_started = time.perf_counter()
                aggregated_ciphertexts = homomorphic_weighted_sum(
                    ciphertext_payloads,
                    {client_id: weights[client_id] for client_id in participants},
                )
                aggregate_seconds = time.perf_counter() - aggregate_started
                decrypt_started = time.perf_counter()
                decrypted = he_context.decrypt_chunks(aggregated_ciphertexts, parameter_count)
                decrypt_seconds = time.perf_counter() - decrypt_started

                # The exact reference must match what was encrypted: the delta (clip -> noise)
                # for DP+HE, or the absolute parameters for HE-only.
                exact = torch.zeros(parameter_count, dtype=torch.float32)
                for client_id in participants:
                    index = client_ids.index(client_id)
                    state = local_states[index][0]
                    flat = _flatten_parameters(state, keys)
                    if do_clip:
                        flat = flat - _flatten_parameters(global_state, keys)
                    exact += flat * weights[client_id]
                approximation_error = relative_l2_error(decrypted, exact)

                delta_state = _unflatten_parameters(decrypted, keys, global_state)
                new_global = {}
                for name, reference in global_state.items():
                    if name in keys:
                        if do_clip:
                            # The HE payload is the transformed *update* (clip -> noise), so the
                            # new parameters are global + aggregate of deltas.
                            new_global[name] = reference + delta_state[name]
                        else:
                            # HE-only: the payload is the aggregate of *absolute* client
                            # parameters (sum p_k = 1), so it is the new value directly.
                            new_global[name] = delta_state[name]
                    else:
                        new_global[name] = reference.clone()
                # Buffers must still be aggregated across clients (unprotected, D5).
                buffer_state = weighted_state_dict(
                    [(state, counts[client_id]) for (state, _), client_id
                     in zip(local_states, participants)]
                )
                for name in global_state:
                    if name not in keys:
                        new_global[name] = buffer_state[name]
                global_state = new_global
            else:
                global_state = weighted_state_dict(
                    [(state, counts[client_id]) for (state, _), client_id
                     in zip(local_states, participants)]
                )

            encode_seconds = time.perf_counter() - encode_started
            model.load_state_dict({key: value.to(device) for key, value in global_state.items()})
            validation_loss, validation_metrics = evaluate_model(
                model, data.splits["validation"], int(training["batch_size"]), device,
                macro_classes=selection_classes,
            )

            # Catastrophic-instability guard (D-2 condition). Records the evidence and halts
            # the condition rather than continuing to burn compute on a diverged model.
            stability = config.get("stability") or {}
            if stability:
                limit = float(stability.get("max_validation_loss", float("inf")))
                non_finite = not np.isfinite(validation_loss)
                if non_finite or validation_loss > limit:
                    round_record = {
                        "round": round_index,
                        "participants": participants,
                        "client_stats": client_stats,
                        "validation_loss": validation_loss,
                        "validation_macro_f1": validation_metrics["macro_f1"],
                        "seconds": time.perf_counter() - round_started,
                        "clip_seconds": clip_seconds,
                        "noise_seconds": noise_seconds,
                        "instability": {
                            "triggered": True,
                            "reason": "non_finite_loss" if non_finite else "validation_loss_exceeded_limit",
                            "validation_loss": None if non_finite else float(validation_loss),
                            "limit": limit,
                        },
                    }
                    rounds_log.append(round_record)
                    _write_json(output_dir / "rounds.json", {
                        "seed": seed, "mode": mode, "rounds": rounds_log,
                        "stopped_early": True,
                    })
                    summary = {
                        "seed": seed,
                        "condition_mode": mode,
                        "status": "stopped_catastrophic_instability",
                        "stopped_at_round": round_index,
                        "stopping_evidence": round_record["instability"],
                        "completed_rounds": len(rounds_log),
                    }
                    _write_json(output_dir / "run_summary.json", summary)
                    print(
                        f"STOPPED at round {round_index}: "
                        f"{round_record['instability']['reason']} "
                        f"(validation_loss={validation_loss})"
                    )
                    return summary

            round_record = {
                "round": round_index,
                "participants": participants,
                "client_stats": client_stats,
                "validation_loss": validation_loss,
                "validation_macro_f1": validation_metrics["macro_f1"],
                "seconds": time.perf_counter() - round_started,
                "clip_seconds": clip_seconds,
                "noise_seconds": noise_seconds,
                "encrypt_seconds": encrypt_seconds,
                "homomorphic_aggregate_seconds": aggregate_seconds,
                "decrypt_seconds": decrypt_seconds,
                "approximation_relative_error": approximation_error,
            }
            if use_he:
                round_record["ciphertexts_per_client"] = expected_ciphertexts
                round_record["ciphertext_bytes_per_client"] = ciphertext_bytes(
                    next(iter(ciphertext_payloads.values()))
                )
                round_record["plaintext_bytes_per_client"] = plaintext_bytes
            print(
                f"round {round_index:>3} val_macro_f1 "
                f"{validation_metrics['macro_f1'] if validation_metrics['macro_f1'] is None else round(validation_metrics['macro_f1'], 4)} "
                f"val_loss {round(validation_loss, 4)}"
            )

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
        _write_json(output_dir / "rounds.json", {
            "seed": seed, "mode": mode, "rounds": rounds_log,
        })

    selected_round = best["round"]
    model.load_state_dict({key: value.to(device) for key, value in best["state"].items()})
    checkpoint_path = output_dir / "checkpoints" / f"selected_seed_{seed}.pt"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(_cpu_state_dict(model), checkpoint_path)
    test_loss, test_metrics = evaluate_model(
        model, data.splits["test"], int(training["batch_size"]), device, macro_classes=None
    )

    sensitivity = per_client_sensitivity(float(clip_norm)) if do_clip else None
    accountant = None
    if add_noise:
        accountant = compute_epsilon(
            float(noise_multiplier), rounds, float(delta), float(sensitivity)
        )

    summary = {
        "seed": seed,
        "condition_mode": mode,
        "add_noise": add_noise,
        "selected_round": selected_round,
        "round_zero_selected": selected_round == 0,
        "selection_metric": training["early_stopping"]["metric"],
        "best_validation_macro_f1": best["score"],
        "test_loss": test_loss,
        "test_metrics": test_metrics,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": _sha256_file(checkpoint_path),
        "privacy": {
            "privacy_provided": bool(add_noise),
            "privacy_unit": "client (institution slot)",
            "adjacency": "replace-one, equal cardinality, other clients fixed",
            "clip_norm": clip_norm,
            "sensitivity_l2": sensitivity,
            "noise_multiplier": noise_multiplier,
            "accountant": accountant.as_dict() if accountant else None,
            "epsilon_undefined_reason": (
                None if add_noise else "No noise mechanism: this condition provides no DP guarantee"
            ),
            "unprotected_components": [
                "BatchNorm running_mean/running_var (448 floats)",
                "num_batches_tracked (3 ints)",
            ],
            "randomness_mode": RandomnessMode.RESEARCH if add_noise else "not_applicable",
        },
        "he": {
            "enabled": use_he,
            "ciphertexts_per_client": expected_ciphertexts,
            "ciphertext_bytes_per_client": (
                ciphertext_bytes(next(iter(ciphertext_payloads.values()))) if use_he else None
            ),
            "plaintext_bytes_per_client": plaintext_bytes if use_he else None,
            "expansion_factor": (
                ciphertext_bytes(next(iter(ciphertext_payloads.values()))) / plaintext_bytes
                if use_he else None
            ),
            "mean_approximation_relative_error": (
                float(np.mean([
                    record["approximation_relative_error"]
                    for record in rounds_log
                    if record.get("approximation_relative_error") is not None
                ])) if use_he else None
            ),
            "max_approximation_relative_error": (
                float(np.max([
                    record["approximation_relative_error"]
                    for record in rounds_log
                    if record.get("approximation_relative_error") is not None
                ])) if use_he else None
            ),
        },
        "cost": {
            "total_seconds": sum(float(record["seconds"]) for record in rounds_log),
            "clip_seconds": sum(float(record.get("clip_seconds", 0.0)) for record in rounds_log),
            "noise_seconds": sum(float(record.get("noise_seconds", 0.0)) for record in rounds_log),
            "encrypt_seconds": sum(float(record.get("encrypt_seconds", 0.0)) for record in rounds_log),
            "homomorphic_aggregate_seconds": sum(
                float(record.get("homomorphic_aggregate_seconds", 0.0)) for record in rounds_log
            ),
            "decrypt_seconds": sum(float(record.get("decrypt_seconds", 0.0)) for record in rounds_log),
            "invocation_seconds": time.perf_counter() - invocation_started,
        },
    }
    _write_json(output_dir / "run_summary.json", summary)
    return summary
