"""Whole-record client partitions for Phase 5 federated experiments.

Partitions are built only from the frozen Phase 3 training records. Validation and
test records are never assigned to a client, and no record may appear in two clients.

Two partition families are supported:

- ``frozen``: the approved Phase 4 client manifest (IID-like), used unchanged.
- ``record_dirichlet``: deterministic record-group Dirichlet allocation for moderate and
  severe label skew. Whole records (and frozen record groups) are assigned together, so a
  patient never spans clients.

The achieved per-client class distribution is always recorded, because whole-record
grouping means the nominal Dirichlet concentration is only a target, not a guarantee.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from src.data.phase3_pipeline import CLASS_ORDER
from src.training.phase4_data import Phase4Data


class PartitionError(ValueError):
    """Raised when a partition violates a Phase 5 integrity rule."""


@dataclass(frozen=True)
class Partition:
    family: str
    concentration: float | None
    seed: int | None
    client_records: dict[str, list[str]]


def _canonical_bytes(document: dict[str, Any]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")


def partition_sha256(document: dict[str, Any]) -> str:
    body = {key: value for key, value in document.items() if key != "manifest_sha256"}
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def record_class_counts(data: Phase4Data, record_ids: list[str]) -> dict[str, int]:
    """Class counts for a set of training records, computed from the frozen arrays."""
    train = data.splits["train"]
    record_text = train.record_ids.astype(np.int64).astype(str)
    wanted = set(record_ids)
    mask = np.isin(record_text, list(wanted))
    counts = np.bincount(train.y[mask].astype(np.int64), minlength=len(CLASS_ORDER))
    return {name: int(counts[index]) for index, name in enumerate(CLASS_ORDER)}


def training_records(data: Phase4Data) -> set[str]:
    train = data.splits["train"]
    return {str(int(value)) for value in np.unique(train.record_ids)}


def record_groups(data: Phase4Data) -> dict[str, list[str]]:
    """Frozen record groups restricted to training records."""
    train_records = training_records(data)
    groups: dict[str, list[str]] = {}
    for group_id, records in data.split_manifest["record_group_mapping"].items():
        members = [str(record) for record in records if str(record) in train_records]
        if members:
            groups[str(group_id)] = members
    return groups


def validate_partition(
    data: Phase4Data,
    client_records: dict[str, list[str]],
    client_count: int = 5,
) -> None:
    """Enforce every Phase 5 isolation rule for one partition."""
    if len(client_records) != client_count:
        raise PartitionError(
            f"Expected {client_count} clients, found {len(client_records)}"
        )
    train_records = training_records(data)
    validation_records = {str(int(v)) for v in np.unique(data.splits["validation"].record_ids)}
    test_records = {str(int(v)) for v in np.unique(data.splits["test"].record_ids)}

    seen: dict[str, str] = {}
    for client_id, records in client_records.items():
        if not records:
            raise PartitionError(f"{client_id} has no records")
        if len(records) != len(set(records)):
            raise PartitionError(f"{client_id} contains a duplicate record")
        for record in records:
            if record not in train_records:
                raise PartitionError(f"{client_id} contains non-training record {record}")
            if record in validation_records:
                raise PartitionError(f"{client_id} contains validation record {record}")
            if record in test_records:
                raise PartitionError(f"{client_id} contains test record {record}")
            if record in seen:
                raise PartitionError(
                    f"Record {record} appears in both {seen[record]} and {client_id}"
                )
            seen[record] = client_id
    if seen.keys() != train_records:
        missing = sorted(train_records - set(seen))
        raise PartitionError(
            "Partition does not cover the frozen training records; missing "
            + ", ".join(missing[:10])
        )

    for group_id, members in record_groups(data).items():
        owners = {seen[record] for record in members if record in seen}
        if len(owners) > 1:
            raise PartitionError(f"Record group {group_id} is split across clients {sorted(owners)}")


def frozen_partition(data: Phase4Data) -> Partition:
    client_records = {
        str(client["client_id"]): [str(record) for record in client["record_ids"]]
        for client in data.client_manifest["clients"]
    }
    validate_partition(data, client_records)
    return Partition(family="frozen_iid_like", concentration=None, seed=None, client_records=client_records)


def record_dirichlet_partition(
    data: Phase4Data,
    concentration: float,
    seed: int,
    client_count: int = 5,
) -> Partition:
    """Assign whole record groups to clients with a Dirichlet weight vector.

    Groups (not individual beats) are the allocation unit, so the achieved class
    distribution is reported rather than assumed. Allocation is deterministic for a
    given ``(concentration, seed)``.
    """
    if concentration <= 0:
        raise PartitionError("Dirichlet concentration must be positive")
    groups = record_groups(data)
    group_ids = sorted(groups)

    # Allocate small groups first so large groups can still balance the tail.
    weights = {
        group_id: len(groups[group_id]) for group_id in group_ids
    }
    ordered = sorted(group_ids, key=lambda g: (weights[g], g))

    rng = np.random.default_rng(seed)
    client_records: dict[str, list[str]] = {
        f"client_{index:02d}": [] for index in range(1, client_count + 1)
    }
    client_load = {client_id: 0 for client_id in client_records}

    for group_id in ordered:
        proportions = rng.dirichlet([concentration] * client_count)
        # Prefer the client with the smallest current record load, weighted by proportion,
        # so that skew is expressed without starving a client entirely.
        scores = np.array(
            [
                proportions[index] / (1.0 + client_load[f"client_{index + 1:02d}"])
                for index in range(client_count)
            ]
        )
        chosen = f"client_{int(np.argmax(scores)) + 1:02d}"
        client_records[chosen].extend(groups[group_id])
        client_load[chosen] += len(groups[group_id])

    for client_id in client_records:
        client_records[client_id] = sorted(client_records[client_id], key=int)
    validate_partition(data, client_records, client_count=client_count)
    return Partition(
        family=f"record_dirichlet_{concentration:g}",
        concentration=float(concentration),
        seed=int(seed),
        client_records=client_records,
    )


def partition_manifest(data: Phase4Data, partition: Partition) -> dict[str, Any]:
    """Full, hashable description of a partition, including achieved class support."""
    clients = []
    for client_id in sorted(partition.client_records):
        records = partition.client_records[client_id]
        counts = record_class_counts(data, records)
        clients.append(
            {
                "client_id": client_id,
                "record_ids": [int(record) for record in records],
                "record_count": len(records),
                "class_counts": counts,
                "sample_count": int(sum(counts.values())),
                "absent_classes": [name for name in CLASS_ORDER if counts[name] == 0],
            }
        )
    document = {
        "schema_version": 1,
        "phase": 5,
        "family": partition.family,
        "dirichlet_concentration": partition.concentration,
        "allocation_seed": partition.seed,
        "allocation_unit": "frozen record group; beats are never distributed individually",
        "client_count": len(partition.client_records),
        "parent_split_manifest_sha256": data.split_manifest_sha256,
        "parent_client_manifest_sha256": data.client_manifest_sha256,
        "clients": clients,
    }
    document["manifest_sha256"] = partition_sha256(document)
    return document


def verify_partition_manifest(
    data: Phase4Data,
    document: dict[str, Any],
    client_count: int = 5,
) -> None:
    """Re-verify a stored manifest against the frozen data and its own hash."""
    if document.get("parent_split_manifest_sha256") != data.split_manifest_sha256:
        raise PartitionError("Partition manifest references a different split manifest")
    expected = partition_sha256(document)
    if document.get("manifest_sha256") != expected:
        raise PartitionError(
            f"Partition manifest hash mismatch: stored {document.get('manifest_sha256')} "
            f"!= computed {expected}"
        )
    client_records = {
        str(client["client_id"]): [str(record) for record in client["record_ids"]]
        for client in document["clients"]
    }
    validate_partition(data, client_records, client_count=client_count)
