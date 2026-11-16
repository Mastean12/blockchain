"""Verified loading of the frozen Phase 3 arrays and client assignments."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from src.data.phase3_pipeline import CLASS_ORDER, SPLIT_ORDER, verify_manifest_hash


@dataclass(frozen=True)
class SplitArrays:
    x: np.ndarray
    y: np.ndarray
    record_ids: np.ndarray
    sample_positions: np.ndarray


@dataclass(frozen=True)
class Phase4Data:
    splits: dict[str, SplitArrays]
    split_manifest: dict[str, Any]
    client_manifest: dict[str, Any]
    split_manifest_sha256: str
    client_manifest_sha256: str
    preprocessing_report_sha256: str


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        document = json.load(file)
    if not isinstance(document, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return document


def load_phase4_data(project_root: Path, config: dict[str, Any]) -> Phase4Data:
    data_config = config["data"]
    split_path = project_root / data_config["split_manifest"]
    client_path = project_root / data_config["client_manifest"]
    report_path = project_root / data_config["preprocessing_report"]
    processed_dir = project_root / data_config["processed_directory"]

    split_manifest = _read_json(split_path)
    split_hash = verify_manifest_hash(split_manifest)
    if split_hash != config["expected_split_manifest_sha256"]:
        raise ValueError("Frozen split manifest hash differs from the Phase 4 config")
    if split_manifest["class_order"] != list(CLASS_ORDER):
        raise ValueError("Split manifest class order differs from the Phase 4 class order")

    client_manifest = _read_json(client_path)
    client_hash = verify_manifest_hash(client_manifest)
    if client_hash != config["expected_client_manifest_sha256"]:
        raise ValueError("Frozen client manifest hash differs from the Phase 4 config")
    if client_manifest["parent_split_manifest_sha256"] != split_hash:
        raise ValueError("Client manifest references a different split manifest")

    preprocessing_report = _read_json(report_path)
    preprocessing_hash = verify_manifest_hash(preprocessing_report)
    if preprocessing_report["split_manifest_sha256"] != split_hash:
        raise ValueError("Preprocessing report references a different split manifest")

    artifact_hashes = preprocessing_report["processed_artifact_sha256"]
    splits: dict[str, SplitArrays] = {}
    source_record_sets: dict[str, set[str]] = {}
    seen_record_positions: set[tuple[str, int]] = set()
    index_to_class = {index: name for index, name in enumerate(CLASS_ORDER)}

    for split_name in SPLIT_ORDER:
        expected_records = set(split_manifest["splits"][split_name]["record_ids"])
        arrays: dict[str, np.ndarray] = {}
        for array_name in ("x", "y", "record_ids", "sample_positions", "symbols"):
            file_name = f"{split_name}_{array_name}.npy"
            path = processed_dir / file_name
            expected_hash = artifact_hashes.get(file_name)
            if expected_hash is None or _sha256_file(path) != expected_hash:
                raise ValueError(f"Processed artifact checksum mismatch for {file_name}")
            arrays[array_name] = np.load(path, allow_pickle=False)

        x = arrays["x"]
        y = arrays["y"]
        record_ids = arrays["record_ids"]
        positions = arrays["sample_positions"]
        symbols = arrays["symbols"]
        if x.ndim != 2 or x.shape[1] != int(config["input_samples"]):
            raise ValueError(f"{split_name} windows have unexpected shape {x.shape}")
        if not np.isfinite(x).all():
            raise ValueError(f"{split_name} windows contain non-finite values")
        if y.ndim != 1 or record_ids.ndim != 1 or positions.ndim != 1 or symbols.ndim != 1:
            raise ValueError(f"{split_name} label and provenance arrays must be one-dimensional")
        if not (len(x) == len(y) == len(record_ids) == len(positions) == len(symbols)):
            raise ValueError(f"{split_name} arrays have inconsistent row counts")
        if not np.issubdtype(y.dtype, np.integer):
            raise ValueError(f"{split_name} labels must be integer class indices")
        if len(y) == 0 or int(y.min()) < 0 or int(y.max()) >= len(CLASS_ORDER):
            raise ValueError(f"{split_name} labels are empty or outside the approved class range")

        actual_records = {str(int(record_id)) for record_id in np.unique(record_ids)}
        if actual_records != expected_records:
            raise ValueError(f"{split_name} array records do not match the frozen manifest")
        source_record_sets[split_name] = actual_records

        record_text = record_ids.astype(np.int64).astype(str)
        pairs = set(zip(record_text.tolist(), positions.astype(np.int64).tolist()))
        if len(pairs) != len(record_text):
            raise ValueError(f"{split_name} contains duplicate record/annotation positions")
        if seen_record_positions.intersection(pairs):
            raise ValueError("A source beat appears in more than one partition")
        seen_record_positions.update(pairs)

        counts = {
            class_name: int(np.count_nonzero(y == index))
            for index, class_name in index_to_class.items()
        }
        expected_counts = preprocessing_report["split_details"][split_name]["class_counts"]
        if counts != expected_counts:
            raise ValueError(f"{split_name} labels do not reconcile with the preprocessing report")
        splits[split_name] = SplitArrays(x=x, y=y, record_ids=record_ids, sample_positions=positions)

    if source_record_sets["train"] & source_record_sets["validation"]:
        raise ValueError("Train and validation contain a shared record")
    if source_record_sets["train"] & source_record_sets["test"]:
        raise ValueError("Train and test contain a shared record")
    if source_record_sets["validation"] & source_record_sets["test"]:
        raise ValueError("Validation and test contain a shared record")

    training_records = source_record_sets["train"]
    assigned_client_records: list[str] = []
    record_to_client: dict[str, str] = {}
    for client in client_manifest["clients"]:
        client_records = [str(record_id) for record_id in client["record_ids"]]
        if set(client_records) - training_records:
            raise ValueError(f"{client['client_id']} includes a non-training record")
        if len(client_records) != len(set(client_records)):
            raise ValueError(f"{client['client_id']} contains a duplicate record")
        assigned_client_records.extend(client_records)
        record_to_client.update({record_id: str(client["client_id"]) for record_id in client_records})
    if set(assigned_client_records) != training_records:
        raise ValueError("Client manifests do not exactly cover the frozen training records")
    if len(assigned_client_records) != len(set(assigned_client_records)):
        raise ValueError("A training record appears in multiple clients")
    for group_id, group_records in split_manifest["record_group_mapping"].items():
        training_group_records = [
            str(record_id) for record_id in group_records if str(record_id) in training_records
        ]
        if training_group_records and len(
            {record_to_client[record_id] for record_id in training_group_records}
        ) != 1:
            raise ValueError(f"Training record group {group_id} is split across clients")

    return Phase4Data(
        splits=splits,
        split_manifest=split_manifest,
        client_manifest=client_manifest,
        split_manifest_sha256=split_hash,
        client_manifest_sha256=client_hash,
        preprocessing_report_sha256=preprocessing_hash,
    )
