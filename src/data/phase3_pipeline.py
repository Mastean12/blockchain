"""Deterministic Phase 3 splitting and annotation-centered segmentation helpers."""

import hashlib
import json
import math
import random
from collections.abc import Iterable, Mapping

import numpy as np


CLASS_ORDER = ("N", "S", "V", "F", "Q")
SPLIT_ORDER = ("train", "validation", "test")
SPLIT_PROPORTIONS = {"train": 0.70, "validation": 0.15, "test": 0.15}
WINDOW_BEFORE_SECONDS = 0.25
WINDOW_AFTER_SECONDS = 0.45


def canonical_json_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def add_manifest_hash(payload: dict[str, object]) -> dict[str, object]:
    result = dict(payload)
    result["manifest_sha256"] = canonical_json_sha256(result)
    return result


def verify_manifest_hash(document: Mapping[str, object]) -> str:
    claimed_hash = document.get("manifest_sha256")
    if not isinstance(claimed_hash, str):
        raise ValueError("Manifest is missing manifest_sha256")
    payload = {key: value for key, value in document.items() if key != "manifest_sha256"}
    actual_hash = canonical_json_sha256(payload)
    if actual_hash != claimed_hash:
        raise ValueError("Manifest SHA-256 does not match its contents")
    return actual_hash


def group_record_ids(record_ids: Iterable[str]) -> dict[str, list[str]]:
    normalized = [str(record_id) for record_id in record_ids]
    if len(normalized) != len(set(normalized)):
        raise ValueError("Record IDs must be unique")
    present = set(normalized)
    if ("201" in present) != ("202" in present):
        raise ValueError("Records 201 and 202 must either both be present or both be absent")

    groups: dict[str, list[str]] = {}
    for record_id in sorted(normalized, key=int):
        group_id = "subject:201-202" if record_id in {"201", "202"} else f"record:{record_id}"
        groups.setdefault(group_id, []).append(record_id)
    return groups


def _allocate_group_counts(group_count: int) -> dict[str, int]:
    if group_count < len(SPLIT_ORDER):
        raise ValueError("At least one record group is required in each split")

    exact = {
        split_name: group_count * proportion
        for split_name, proportion in SPLIT_PROPORTIONS.items()
    }
    counts = {split_name: math.floor(exact[split_name]) for split_name in SPLIT_ORDER}
    remaining = group_count - sum(counts.values())
    tie_priority = {"test": 0, "validation": 1, "train": 2}
    remainder_order = sorted(
        SPLIT_ORDER,
        key=lambda split_name: (
            -(exact[split_name] - counts[split_name]),
            tie_priority[split_name],
        ),
    )
    for split_name in remainder_order[:remaining]:
        counts[split_name] += 1
    return counts


def split_record_groups(
    groups: Mapping[str, list[str]],
    seed: int,
) -> dict[str, list[str]]:
    group_ids = sorted(
        groups,
        key=lambda group_id: min(int(record_id) for record_id in groups[group_id]),
    )
    if len(group_ids) != len(groups):
        raise ValueError("Group IDs must be unique")

    shuffled = list(group_ids)
    random.Random(seed).shuffle(shuffled)
    sizes = _allocate_group_counts(len(shuffled))
    result: dict[str, list[str]] = {}
    cursor = 0
    for split_name in SPLIT_ORDER:
        next_cursor = cursor + sizes[split_name]
        result[split_name] = shuffled[cursor:next_cursor]
        cursor = next_cursor
    return result


def validate_split_partition(
    split_records: Mapping[str, Iterable[str]],
    expected_record_ids: Iterable[str],
    groups: Mapping[str, list[str]],
) -> dict[str, str]:
    if set(split_records) != set(SPLIT_ORDER):
        raise ValueError(f"Split names must be exactly {SPLIT_ORDER}")
    expected = {str(record_id) for record_id in expected_record_ids}
    record_to_split: dict[str, str] = {}
    for split_name in SPLIT_ORDER:
        records = [str(record_id) for record_id in split_records[split_name]]
        if len(records) != len(set(records)):
            raise ValueError(f"Duplicate record within {split_name} split")
        for record_id in records:
            if record_id in record_to_split:
                raise ValueError(f"Record {record_id} appears in multiple splits")
            record_to_split[record_id] = split_name
    if set(record_to_split) != expected:
        missing = sorted(expected - set(record_to_split), key=int)
        unexpected = sorted(set(record_to_split) - expected, key=int)
        raise ValueError(f"Split records mismatch; missing={missing}, unexpected={unexpected}")
    if ("201" in record_to_split) != ("202" in record_to_split):
        raise ValueError("Records 201 and 202 must either both be present or both be absent")
    if "201" in record_to_split and record_to_split["201"] != record_to_split["202"]:
        raise ValueError("Records 201 and 202 are assigned to different splits")
    for group_id, record_ids in groups.items():
        assigned_splits = {record_to_split.get(record_id) for record_id in record_ids}
        if None in assigned_splits or len(assigned_splits) != 1:
            raise ValueError(f"Record group {group_id} is split across partitions")
    return record_to_split


def assign_training_clients(
    training_group_ids: Iterable[str],
    groups: Mapping[str, list[str]],
    group_class_counts: Mapping[str, Mapping[str, int]],
    client_count: int = 5,
) -> list[dict[str, object]]:
    selected_groups = list(training_group_ids)
    if len(selected_groups) != len(set(selected_groups)):
        raise ValueError("Training group IDs must be unique")
    if client_count < 1:
        raise ValueError("At least one client is required")
    if len(selected_groups) < client_count:
        raise ValueError("There must be at least one training group per client")
    if set(selected_groups) - set(groups) or set(selected_groups) - set(group_class_counts):
        raise ValueError("Every training group must have record and class-count data")

    total_by_class = {
        class_name: sum(group_class_counts[group_id].get(class_name, 0) for group_id in selected_groups)
        for class_name in CLASS_ORDER
    }
    target_by_class = {
        class_name: total_by_class[class_name] / client_count
        for class_name in CLASS_ORDER
    }
    target_records = sum(len(groups[group_id]) for group_id in selected_groups) / client_count

    def group_priority(group_id: str) -> tuple[float, int, int]:
        counts = group_class_counts[group_id]
        rarity = sum(
            counts.get(class_name, 0) / total_by_class[class_name]
            for class_name in CLASS_ORDER
            if total_by_class[class_name] > 0
        )
        total_beats = sum(counts.get(class_name, 0) for class_name in CLASS_ORDER)
        first_record = min(int(record_id) for record_id in groups[group_id])
        return -rarity, -total_beats, first_record

    ordered_groups = sorted(selected_groups, key=group_priority)
    client_groups: list[list[str]] = [[] for _ in range(client_count)]
    client_counts = [{class_name: 0 for class_name in CLASS_ORDER} for _ in range(client_count)]
    client_record_counts = [0 for _ in range(client_count)]

    def assign_group(group_id: str, client_index: int) -> None:
        client_groups[client_index].append(group_id)
        client_record_counts[client_index] += len(groups[group_id])
        for class_name in CLASS_ORDER:
            client_counts[client_index][class_name] += group_class_counts[group_id].get(
                class_name, 0
            )

    for group_id in ordered_groups:
        group_counts = group_class_counts[group_id]
        group_record_count = len(groups[group_id])
        least_group_count = min(len(assigned) for assigned in client_groups)
        candidate_clients = [
            index for index, assigned in enumerate(client_groups)
            if len(assigned) == least_group_count
        ]
        choices = []
        for client_index in candidate_clients:
            class_error = sum(
                (
                    (
                        client_counts[client_index][class_name]
                        + group_counts.get(class_name, 0)
                        - target_by_class[class_name]
                    )
                    / max(target_by_class[class_name], 1.0)
                ) ** 2
                for class_name in CLASS_ORDER
                if total_by_class[class_name] > 0
            )
            projected_records = client_record_counts[client_index] + group_record_count
            record_error = ((projected_records - target_records) / max(target_records, 1.0)) ** 2
            choices.append((class_error + 0.25 * record_error, client_index))
        chosen_client = min(choices)[1]
        assign_group(group_id, chosen_client)

    clients = []
    for client_index, assigned_groups in enumerate(client_groups, start=1):
        records = sorted(
            (record_id for group_id in assigned_groups for record_id in groups[group_id]),
            key=int,
        )
        counts = client_counts[client_index - 1]
        clients.append({
            "client_id": f"client_{client_index:02d}",
            "group_ids": sorted(assigned_groups),
            "record_ids": records,
            "record_count": len(records),
            "class_counts": counts,
            "absent_classes": [name for name in CLASS_ORDER if counts[name] == 0],
        })
    return clients


def window_offsets(sampling_frequency_hz: float) -> tuple[int, int, int]:
    if not math.isfinite(sampling_frequency_hz) or sampling_frequency_hz <= 0:
        raise ValueError("Sampling frequency must be finite and positive")
    before = int(round(WINDOW_BEFORE_SECONDS * sampling_frequency_hz))
    after = int(round(WINDOW_AFTER_SECONDS * sampling_frequency_hz))
    return before, after, before + after + 1


def extract_annotated_windows(
    signal: np.ndarray,
    sample_positions: Iterable[int],
    symbols: Iterable[str],
    symbol_to_class: Mapping[str, str],
    class_order: Iterable[str],
    sampling_frequency_hz: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    signal_values = np.asarray(signal, dtype=np.float32).reshape(-1)
    positions = np.asarray(list(sample_positions), dtype=np.int64)
    annotation_symbols = np.asarray(list(symbols), dtype="U1")
    order = tuple(class_order)
    class_indices = {class_name: index for index, class_name in enumerate(order)}
    if len(positions) != len(annotation_symbols):
        raise ValueError("Annotation sample and symbol counts differ")
    if not np.isfinite(signal_values).all():
        raise ValueError("Signal contains non-finite values")

    before, after, window_size = window_offsets(sampling_frequency_hz)
    windows: list[np.ndarray] = []
    labels: list[int] = []
    retained_positions: list[int] = []
    retained_symbols: list[str] = []
    boundary_excluded = {class_name: 0 for class_name in order}

    for sample_position, symbol in zip(positions, annotation_symbols):
        class_name = symbol_to_class.get(str(symbol))
        if class_name is None:
            continue
        if class_name not in class_indices:
            raise ValueError(f"Mapped class {class_name!r} is not in the approved class order")
        start = int(sample_position) - before
        stop = int(sample_position) + after + 1
        if start < 0 or stop > len(signal_values):
            boundary_excluded[class_name] += 1
            continue
        window = signal_values[start:stop]
        if len(window) != window_size:
            raise ValueError("Extracted ECG window has an unexpected length")
        windows.append(window)
        labels.append(class_indices[class_name])
        retained_positions.append(int(sample_position))
        retained_symbols.append(str(symbol))

    if not windows:
        raise ValueError("No mapped, in-bounds annotated windows were extracted")
    return (
        np.stack(windows).astype(np.float32, copy=False),
        np.asarray(labels, dtype=np.int8),
        np.asarray(retained_positions, dtype=np.int32),
        np.asarray(retained_symbols, dtype="U1"),
        boundary_excluded,
    )


def fit_standardization(training_windows: np.ndarray) -> tuple[float, float]:
    values = np.asarray(training_windows, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] == 0 or values.shape[1] == 0:
        raise ValueError("Training windows must be a non-empty 2D array")
    if not np.isfinite(values).all():
        raise ValueError("Training windows contain non-finite values")
    mean = float(values.mean())
    standard_deviation = float(values.std())
    if not math.isfinite(standard_deviation) or standard_deviation <= 0:
        raise ValueError("Training-window standard deviation must be finite and positive")
    return mean, standard_deviation


def standardize_windows(
    windows: np.ndarray,
    mean: float,
    standard_deviation: float,
) -> np.ndarray:
    if not math.isfinite(mean) or not math.isfinite(standard_deviation) or standard_deviation <= 0:
        raise ValueError("Standardization parameters must be finite with positive scale")
    standardized = (np.asarray(windows, dtype=np.float32) - np.float32(mean)) / np.float32(
        standard_deviation
    )
    if not np.isfinite(standardized).all():
        raise ValueError("Standardized windows contain non-finite values")
    return standardized.astype(np.float32, copy=False)
