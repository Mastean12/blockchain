from pathlib import Path

import pytest

from src.data.aami_mapping import build_mapping, load_mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = PROJECT_ROOT / "configs" / "data" / "aami5_mapping_v1.yaml"


def test_observed_symbols_have_one_explicit_approved_decision():
    mapping = load_mapping(MAPPING_PATH)
    observed = {
        "!", '"', "+", "/", "A", "E", "F", "J", "L", "N", "Q", "R",
        "S", "V", "[", "]", "a", "e", "f", "j", "x", "|", "~",
    }

    mapping.validate_observed_symbols(observed)

    assert len(mapping.symbol_to_class) == len(set(mapping.symbol_to_class))
    assert set(mapping.symbol_to_class).isdisjoint(mapping.exclusions)


def test_unseen_symbol_cannot_silently_fall_through():
    mapping = load_mapping(MAPPING_PATH)

    with pytest.raises(ValueError, match="no explicit decision"):
        mapping.validate_observed_symbols({"?"})


def test_duplicate_class_mapping_is_rejected():
    with pytest.raises(ValueError, match="multiple classes"):
        build_mapping(
            version=1,
            status="test",
            class_order=("N", "S"),
            classes={"N": ("N", "L"), "S": ("L", "A")},
            exclusions={},
        )


def test_mapping_symbol_cannot_also_be_excluded():
    with pytest.raises(ValueError, match="both mapping and exclusion"):
        build_mapping(
            version=1,
            status="test",
            class_order=("N",),
            classes={"N": ("N",)},
            exclusions={"N": {"reason": "conflict"}},
        )


def test_approved_record_exclusions_match_audited_paced_records():
    mapping = load_mapping(MAPPING_PATH)

    mapping.validate_record_exclusions({"100", "102", "104", "107", "217"})

    assert set(mapping.record_exclusions) == {"102", "104", "107", "217"}


def test_unknown_record_exclusion_is_rejected():
    mapping = load_mapping(MAPPING_PATH)

    with pytest.raises(ValueError, match="not present in the dataset"):
        mapping.validate_record_exclusions({"100", "101"})
