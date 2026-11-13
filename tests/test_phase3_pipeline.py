import numpy as np
import pytest

from src.data.phase3_pipeline import (
    CLASS_ORDER,
    assign_training_clients,
    extract_annotated_windows,
    fit_standardization,
    group_record_ids,
    split_record_groups,
    standardize_windows,
    verify_manifest_hash,
    add_manifest_hash,
    validate_split_partition,
    window_offsets,
)


def test_group_split_is_deterministic_and_keeps_201_202_together():
    record_ids = [str(record_id) for record_id in range(100, 142)] + ["201", "202"]
    groups = group_record_ids(record_ids)

    split = split_record_groups(groups, seed=42)
    repeat = split_record_groups(groups, seed=42)

    assert split == repeat
    assert {name: len(group_ids) for name, group_ids in split.items()} == {
        "train": 30,
        "validation": 6,
        "test": 7,
    }
    assigned_split = {
        group_id: split_name
        for split_name, group_ids in split.items()
        for group_id in group_ids
    }
    assert assigned_split["subject:201-202"] in {"train", "validation", "test"}


def test_split_validator_rejects_cross_partition_record_leakage():
    groups = group_record_ids(["100", "201", "202", "203"])
    split_records = {
        "train": ["100", "201"],
        "validation": ["202"],
        "test": ["203"],
    }

    with pytest.raises(ValueError, match="different splits"):
        validate_split_partition(split_records, ["100", "201", "202", "203"], groups)


def test_clients_cover_training_groups_without_splitting_subject_pair():
    groups = group_record_ids(["100", "101", "102", "201", "202", "203"])
    training_groups = list(groups)
    group_counts = {
        group_id: {class_name: int(index == class_index) * (index + 1) for class_index, class_name in enumerate(CLASS_ORDER)}
        for index, group_id in enumerate(training_groups)
    }

    clients = assign_training_clients(training_groups, groups, group_counts, client_count=5)

    assigned_records = [record_id for client in clients for record_id in client["record_ids"]]
    assert sorted(assigned_records, key=int) == ["100", "101", "102", "201", "202", "203"]
    assert len(assigned_records) == len(set(assigned_records))
    client_group_counts = [len(client["group_ids"]) for client in clients]
    assert max(client_group_counts) - min(client_group_counts) <= 1
    for client in clients:
        if "201" in client["record_ids"]:
            assert "202" in client["record_ids"]
        if "202" in client["record_ids"]:
            assert "201" in client["record_ids"]


def test_annotation_windows_have_approved_shape_and_count_boundaries():
    signal = np.arange(1000, dtype=np.float32)

    windows, labels, retained_positions, retained_symbols, boundary_counts = extract_annotated_windows(
        signal=signal,
        sample_positions=[250, 0],
        symbols=["N", "N"],
        symbol_to_class={"N": "N"},
        class_order=CLASS_ORDER,
        sampling_frequency_hz=360,
    )

    assert window_offsets(360) == (90, 162, 253)
    assert windows.shape == (1, 253)
    np.testing.assert_array_equal(windows[0], np.arange(160, 413, dtype=np.float32))
    np.testing.assert_array_equal(labels, np.asarray([0], dtype=np.int8))
    np.testing.assert_array_equal(retained_positions, np.asarray([250], dtype=np.int32))
    np.testing.assert_array_equal(retained_symbols, np.asarray(["N"], dtype="U1"))
    assert boundary_counts["N"] == 1


def test_standardization_is_fit_from_training_windows_only():
    training = np.asarray([[1, 2], [3, 4]], dtype=np.float32)
    mean, standard_deviation = fit_standardization(training)

    assert mean == pytest.approx(2.5)
    assert standard_deviation == pytest.approx(np.std(training, dtype=np.float64))
    normalized_validation = standardize_windows(np.asarray([[1000, 1000]], dtype=np.float32), mean, standard_deviation)
    assert normalized_validation.mean() > 0


def test_manifest_hash_detects_content_changes():
    manifest = add_manifest_hash({"seed": 42, "records": ["100", "101"]})

    verify_manifest_hash(manifest)

    manifest["seed"] = 43
    with pytest.raises(ValueError, match="does not match"):
        verify_manifest_hash(manifest)
