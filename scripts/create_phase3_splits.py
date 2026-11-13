"""Create the frozen Phase 3 record split and training-only client manifests."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from src.data.aami_mapping import load_mapping
from src.data.phase3_pipeline import (
    CLASS_ORDER,
    SPLIT_ORDER,
    SPLIT_PROPORTIONS,
    add_manifest_hash,
    assign_training_clients,
    group_record_ids,
    split_record_groups,
    validate_split_partition,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DOCS = PROJECT_ROOT / "docs" / "data_and_labels"
MAPPING_PATH = PROJECT_ROOT / "configs" / "data" / "aami5_mapping_v1.yaml"
AUDIT_SUMMARY_PATH = DATA_DOCS / "MITBIH_AUDIT_SUMMARY.json"
PER_RECORD_PATH = DATA_DOCS / "MITBIH_PER_RECORD_AAMI_COUNTS.csv"
CHECKSUM_PATH = DATA_DOCS / "MITBIH_v1.0.0_SHA256SUMS.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "splits"
SPLIT_SEED = 42
CLIENT_COUNT = 5


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(path: Path, payload: dict[str, object]) -> dict[str, object]:
    manifest = add_manifest_hash(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(manifest, file, indent=2, sort_keys=True)
        file.write("\n")
    return manifest


def create_manifests(output_dir: Path) -> dict[str, object]:
    mapping = load_mapping(MAPPING_PATH)
    if mapping.status != "research_lead_approved":
        raise ValueError(f"Mapping is not approved: {mapping.status}")
    if mapping.class_order != CLASS_ORDER:
        raise ValueError("Approved mapping class order differs from the Phase 3 pipeline")

    with AUDIT_SUMMARY_PATH.open(encoding="utf-8") as file:
        audit_summary = json.load(file)
    if audit_summary["mapping_status"] != mapping.status:
        raise ValueError("Audit summary and mapping approval statuses differ")
    if audit_summary["approval_status"] != mapping.status:
        raise ValueError("Audit summary does not record the mapping approval")
    approved_record_ids = set(audit_summary["approved_protocol_record_ids"])
    configured_record_ids = set(audit_summary["record_ids"]) - set(mapping.record_exclusions)
    if approved_record_ids != configured_record_ids:
        raise ValueError("Approved record list does not match configured record exclusions")

    record_class_counts: dict[str, dict[str, int]] = {}
    with PER_RECORD_PATH.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            record_id = row["record"]
            included = row["included_in_approved_protocol"].lower() == "true"
            if included != (record_id in approved_record_ids):
                raise ValueError(f"Record inclusion flag is inconsistent for {record_id}")
            record_class_counts[record_id] = {
                class_name: int(row[f"mapped_{class_name}_count"])
                for class_name in CLASS_ORDER
            }
    if set(record_class_counts) != set(audit_summary["record_ids"]):
        raise ValueError("Per-record audit is incomplete or contains unexpected records")

    eligible_ids = sorted(approved_record_ids, key=int)
    groups = group_record_ids(eligible_ids)
    group_splits = split_record_groups(groups, SPLIT_SEED)
    group_class_counts = {
        group_id: {
            class_name: sum(record_class_counts[record_id][class_name] for record_id in record_ids)
            for class_name in CLASS_ORDER
        }
        for group_id, record_ids in groups.items()
    }

    split_records = {
        split_name: sorted(
            (record_id for group_id in group_ids for record_id in groups[group_id]),
            key=int,
        )
        for split_name, group_ids in group_splits.items()
    }
    record_assignments = validate_split_partition(split_records, approved_record_ids, groups)

    split_details = {}
    for split_name in SPLIT_ORDER:
        record_ids = split_records[split_name]
        class_counts = {
            class_name: sum(record_class_counts[record_id][class_name] for record_id in record_ids)
            for class_name in CLASS_ORDER
        }
        split_details[split_name] = {
            "group_ids": sorted(
                group_splits[split_name],
                key=lambda group_id: min(int(record_id) for record_id in groups[group_id]),
            ),
            "record_ids": record_ids,
            "group_count": len(group_splits[split_name]),
            "record_count": len(record_ids),
            "class_counts": class_counts,
            "absent_classes": [name for name in CLASS_ORDER if class_counts[name] == 0],
        }

    clients = assign_training_clients(
        group_splits["train"],
        groups,
        group_class_counts,
        client_count=CLIENT_COUNT,
    )
    assigned_client_records = [
        record_id for client in clients for record_id in client["record_ids"]
    ]
    if set(assigned_client_records) != set(split_records["train"]):
        raise ValueError("Client records do not exactly cover the training records")
    if len(assigned_client_records) != len(set(assigned_client_records)):
        raise ValueError("A training record appears in more than one client")

    excluded_records = {
        record_id: mapping.record_exclusions[record_id]["reason"]
        for record_id in sorted(mapping.record_exclusions, key=int)
    }
    split_payload: dict[str, object] = {
        "schema_version": 1,
        "phase3_split_code_version": "1.0.0",
        "dataset": audit_summary["dataset"],
        "dataset_version": audit_summary["dataset_version"],
        "raw_archive_sha256": audit_summary["archive_sha256"],
        "checksum_manifest_sha256": sha256_file(CHECKSUM_PATH),
        "mapping_version": mapping.version,
        "mapping_config_sha256": sha256_file(MAPPING_PATH),
        "mapping_status": mapping.status,
        "class_order": list(CLASS_ORDER),
        "split_seed": SPLIT_SEED,
        "target_group_proportions": SPLIT_PROPORTIONS,
        "split_algorithm": (
            "Seeded shuffle of record groups, then largest-remainder allocation "
            "to 70/15/15 group proportions; no metric-based retries."
        ),
        "grouping_rule": (
            "Records 201 and 202 form one group; every other eligible record is a separate group. "
            "No patient identity is inferred for other records."
        ),
        "record_group_mapping": groups,
        "excluded_records": excluded_records,
        "split_group_counts": {
            split_name: split_details[split_name]["group_count"]
            for split_name in SPLIT_ORDER
        },
        "split_record_counts": {
            split_name: split_details[split_name]["record_count"]
            for split_name in SPLIT_ORDER
        },
        "splits": split_details,
        "record_assignments": record_assignments,
    }
    split_manifest = write_manifest(output_dir / "phase3_split_manifest.json", split_payload)

    client_payload: dict[str, object] = {
        "schema_version": 1,
        "client_manifest_code_version": "1.0.0",
        "parent_split_manifest_sha256": split_manifest["manifest_sha256"],
        "assignment_policy": (
            "Five clients receive training record groups only, using deterministic greedy "
            "balancing of mapped class counts and record load."
        ),
        "clients": clients,
    }
    client_manifest = write_manifest(output_dir / "client_manifests.json", client_payload)
    return {
        "split_manifest_sha256": split_manifest["manifest_sha256"],
        "client_manifest_sha256": client_manifest["manifest_sha256"],
        "split_group_counts": split_payload["split_group_counts"],
        "split_record_counts": split_payload["split_record_counts"],
        "split_class_counts": {
            split_name: split_details[split_name]["class_counts"]
            for split_name in SPLIT_ORDER
        },
        "split_absent_classes": {
            split_name: split_details[split_name]["absent_classes"]
            for split_name in SPLIT_ORDER
        },
        "client_count": len(clients),
        "client_record_counts": {
            client["client_id"]: client["record_count"] for client in clients
        },
        "outputs": [
            str((output_dir / "phase3_split_manifest.json").relative_to(PROJECT_ROOT)),
            str((output_dir / "client_manifests.json").relative_to(PROJECT_ROOT)),
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    print(json.dumps(create_manifests(args.output_dir), indent=2))


if __name__ == "__main__":
    main()
