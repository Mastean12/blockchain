"""Phase 5 tests: aggregation correctness, client isolation and data integrity."""

from pathlib import Path

import numpy as np
import pytest
import torch

from src.data.phase3_pipeline import CLASS_ORDER
from src.federated.fedavg import (
    FederatedError,
    aggregate_models,
    select_participants,
    weighted_state_dict,
)
from src.federated.partitions import (
    PartitionError,
    frozen_partition,
    partition_manifest,
    partition_sha256,
    record_dirichlet_partition,
    training_records,
    validate_partition,
    verify_partition_manifest,
)
from src.training.phase4_data import load_phase4_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "models" / "phase4_cnn_v1.yaml"


@pytest.fixture(scope="module")
def data():
    from src.training.phase4 import load_config

    return load_phase4_data(PROJECT_ROOT, load_config(CONFIG_PATH))


# ---------------------------------------------------------------- aggregation
def test_weighted_state_dict_matches_closed_form() -> None:
    a = {"w": torch.tensor([1.0, 2.0]), "b": torch.tensor([0.0])}
    b = {"w": torch.tensor([3.0, 4.0]), "b": torch.tensor([10.0])}
    result = weighted_state_dict([(a, 1), (b, 3)])
    expected_w = (a["w"] * 0.25 + b["w"] * 0.75)
    expected_b = (a["b"] * 0.25 + b["b"] * 0.75)
    assert torch.allclose(result["w"], expected_w)
    assert torch.allclose(result["b"], expected_b)


def test_equal_weights_reduce_to_mean() -> None:
    states = [({"w": torch.full((3,), float(i))}, 1) for i in range(5)]
    result = weighted_state_dict(states)
    assert torch.allclose(result["w"], torch.full((3,), 2.0))


def test_num_batches_tracked_is_summed_not_averaged() -> None:
    a = {"bn.num_batches_tracked": torch.tensor(10), "bn.weight": torch.tensor([1.0])}
    b = {"bn.num_batches_tracked": torch.tensor(6), "bn.weight": torch.tensor([3.0])}
    result = weighted_state_dict([(a, 1), (b, 1)])
    assert int(result["bn.num_batches_tracked"]) == 16
    assert torch.allclose(result["bn.weight"], torch.tensor([2.0]))


def test_single_client_aggregation_is_identity() -> None:
    state = {"w": torch.tensor([0.5, -1.5])}
    result = weighted_state_dict([(state, 7)])
    assert torch.equal(result["w"], state["w"])


def test_aggregation_rejects_empty_client_set() -> None:
    with pytest.raises(FederatedError):
        weighted_state_dict([])


def test_aggregation_rejects_inconsistent_keys() -> None:
    with pytest.raises(FederatedError):
        weighted_state_dict([({"a": torch.tensor([1.0])}, 1), ({"b": torch.tensor([1.0])}, 1)])


def test_aggregate_models_uses_sample_counts() -> None:
    class Tiny(torch.nn.Module):
        def __init__(self, value):
            super().__init__()
            self.w = torch.nn.Parameter(torch.tensor([float(value)]))

    models = [Tiny(1.0), Tiny(3.0)]
    result = aggregate_models(models, [1, 3])
    assert torch.allclose(result["w"], torch.tensor([2.5]))


# ---------------------------------------------------------------- participation
def test_participation_is_deterministic_and_reproducible() -> None:
    ids = [f"client_{i:02d}" for i in range(1, 6)]
    first = select_participants(ids, 7, 0.6, 42)
    second = select_participants(ids, 7, 0.6, 42)
    assert first == second
    assert len(first) == 3
    assert set(first) <= set(ids)


def test_full_participation_includes_everyone() -> None:
    ids = [f"client_{i:02d}" for i in range(1, 6)]
    assert sorted(select_participants(ids, 3, 1.0, 42)) == ids


# ---------------------------------------------------------------- partitions
def test_frozen_partition_is_valid_and_complete(data) -> None:
    partition = frozen_partition(data)
    assert len(partition.client_records) == 5
    covered = {record for records in partition.client_records.values() for record in records}
    assert covered == training_records(data)


def test_frozen_partition_manifest_hashes_deterministically(data) -> None:
    first = partition_manifest(data, frozen_partition(data))
    second = partition_manifest(data, frozen_partition(data))
    assert first["manifest_sha256"] == second["manifest_sha256"]
    verify_partition_manifest(data, first)


def test_partition_manifest_tampering_is_rejected(data) -> None:
    document = partition_manifest(data, frozen_partition(data))
    document["clients"][0]["record_ids"] = document["clients"][0]["record_ids"][1:]
    with pytest.raises(PartitionError):
        verify_partition_manifest(data, document)


def test_duplicate_record_across_clients_is_rejected(data) -> None:
    partition = frozen_partition(data)
    records = {client: list(values) for client, values in partition.client_records.items()}
    stolen = records["client_01"][0]
    records["client_02"].append(stolen)
    with pytest.raises(PartitionError):
        validate_partition(data, records)


def test_missing_training_record_is_rejected(data) -> None:
    partition = frozen_partition(data)
    records = {client: list(values) for client, values in partition.client_records.items()}
    records["client_01"] = records["client_01"][1:]
    with pytest.raises(PartitionError):
        validate_partition(data, records)


def test_validation_and_test_records_are_never_assigned(data) -> None:
    partition = frozen_partition(data)
    assigned = {record for records in partition.client_records.values() for record in records}
    validation = {str(int(v)) for v in np.unique(data.splits["validation"].record_ids)}
    test = {str(int(v)) for v in np.unique(data.splits["test"].record_ids)}
    assert not assigned & validation
    assert not assigned & test


def test_dirichlet_partition_is_valid_and_deterministic(data) -> None:
    first = record_dirichlet_partition(data, concentration=0.5, seed=42)
    second = record_dirichlet_partition(data, concentration=0.5, seed=42)
    assert first.client_records == second.client_records
    validate_partition(data, first.client_records)


def test_dirichlet_partition_keeps_groups_whole(data) -> None:
    partition = record_dirichlet_partition(data, concentration=0.1, seed=42)
    # validate_partition already enforces this; assert it is exercised
    validate_partition(data, partition.client_records)


def test_dirichlet_rejects_non_positive_concentration(data) -> None:
    with pytest.raises(PartitionError):
        record_dirichlet_partition(data, concentration=0.0, seed=42)


def test_partition_sha256_ignores_stored_hash() -> None:
    document = {"a": 1, "manifest_sha256": "deadbeef"}
    assert partition_sha256(document) == partition_sha256({"a": 1})


def test_partition_class_counts_come_from_arrays_not_stored_manifest(data) -> None:
    """The frozen client manifest's stored class_counts are known to be inaccurate.

    Phase 5 derives class support from the frozen label arrays, so the partition
    manifest must reconcile with the arrays even though the Phase 3 client manifest's
    stored counts do not. See docs/PHASE_5_IMPLEMENTATION_PLAN.md section 3.1.
    """
    partition = frozen_partition(data)
    document = partition_manifest(data, partition)
    total = {name: 0 for name in CLASS_ORDER}
    for client in document["clients"]:
        for name in CLASS_ORDER:
            total[name] += int(client["class_counts"][name])
    expected = {
        name: int(np.count_nonzero(data.splits["train"].y == index))
        for index, name in enumerate(CLASS_ORDER)
    }
    assert total == expected

    stored = {name: 0 for name in CLASS_ORDER}
    for client in data.client_manifest["clients"]:
        for name in CLASS_ORDER:
            stored[name] += int(client["class_counts"][name])
    assert stored != expected, (
        "Phase 3 client manifest stored counts unexpectedly reconcile; "
        "update the documented limitation if this changed"
    )
