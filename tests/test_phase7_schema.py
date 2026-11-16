"""Phase 7 personal-information control tests.

These tests are the enforcement mechanism for
``docs/threat_model/SECURITY_THREAT_MODEL.md`` §3.2. Any schema change that reintroduces a
prohibited category must fail here before it can reach a ledger.
"""

import pytest

from src.blockchain.commitments import commitment, safe_basename, scale_privacy_value
from src.blockchain.schema import (
    AuditSchemaError,
    allowed_fields,
    assert_no_sensitive_payload,
    validate_event,
)


def _run_payload(**overrides):
    payload = {
        "run_id": "f3_seed42",
        "config_sha256": "a" * 64,
        "split_sha256": "b" * 64,
        "client_manifest_sha256": "c" * 64,
        "model_arch_id": "compact_cnn_v1",
        "seed": 42,
    }
    payload.update(overrides)
    return payload


# ------------------------------------------------------------------ happy path
def test_valid_run_registration_is_accepted():
    record = validate_event("RunRegistered", _run_payload())
    assert record.event_type == "RunRegistered"
    assert record.fields["seed"] == 42


def test_all_event_types_validate_with_their_own_fields():
    cases = {
        "RunRegistered": _run_payload(),
        "RoundOpened": {"run_id": "r", "round_index": 1, "participant_set_sha256": "d" * 64},
        "UpdateCommitted": {
            "run_id": "r", "round_index": 1, "client_id": "client_01",
            "update_sha256": "e" * 64, "update_bytes": 145428,
        },
        "RoundClosed": {
            "run_id": "r", "round_index": 1, "global_model_sha256": "f" * 64,
            "aggregation_rule_id": "fedavg_sample_weighted",
        },
        "MissingCommitment": {
            "run_id": "r", "round_index": 1,
            "expected_participant_set_sha256": "0" * 64,
            "received_participant_set_sha256": "1" * 64,
        },
        "CheckpointSealed": {
            "run_id": "r", "selected_round": 2, "checkpoint_sha256": "2" * 64,
        },
        "PrivacyAttested": {
            "run_id": "r", "epsilon_scaled": 57301692825, "delta_scaled": 10000,
            "sigma_scaled": 1000000000, "clip_scaled": 3440000000,
            "accountant_id": "opacus_rdp_1.6.0",
        },
    }
    for event_type, payload in cases.items():
        assert validate_event(event_type, payload).event_type == event_type


# ------------------------------------------------------- unknown fields rejected
def test_unknown_field_is_rejected_not_ignored():
    with pytest.raises(AuditSchemaError, match="closed whitelist"):
        validate_event("RunRegistered", _run_payload(notes="free text"))


def test_missing_field_is_rejected():
    payload = _run_payload()
    del payload["split_sha256"]
    with pytest.raises(AuditSchemaError, match="missing required fields"):
        validate_event("RunRegistered", payload)


def test_unknown_event_type_is_rejected():
    with pytest.raises(AuditSchemaError, match="Unknown event type"):
        validate_event("PatientUploaded", {"run_id": "r"})


# ---------------------------------------------- prohibited personal information
@pytest.mark.parametrize(
    "field",
    [
        "record_ids",
        "record_number",
        "patient_id",
        "subject_id",
        "sample_count",
        "clip_norm",
        "norm_before_clip",
        "epsilon_client",
        "noise_magnitude",
        "secret_key",
        "private_key",
        "context_key",
        "galois_keys",
        "symbols",
        "annotation_labels",
        "waveform",
        "signal",
        "tensor",
        "parameters",
        "weights",
        "update_vector",
        "class_counts",
        "path",
        "filename",
        "username",
    ],
)
def test_prohibited_field_names_are_rejected(field):
    with pytest.raises(AuditSchemaError):
        validate_event("RunRegistered", _run_payload(**{field: "x"}))


def test_validated_event_fields_never_contain_prohibited_categories():
    """The whitelist itself must not name a prohibited category."""
    for event_type in (
        "RunRegistered", "RoundOpened", "UpdateCommitted", "RoundClosed",
        "MissingCommitment", "CheckpointSealed", "PrivacyAttested",
    ):
        for field in allowed_fields(event_type):
            assert_no_sensitive_payload({field: 0})


# --------------------------------------------------------- value-level controls
def test_client_id_must_be_a_slot_label_not_a_record_number():
    base = {
        "run_id": "r", "round_index": 1, "update_sha256": "a" * 64, "update_bytes": 10,
    }
    for bad in ("232", "record_232", "patient_01", "client_1"):
        with pytest.raises(AuditSchemaError):
            validate_event("UpdateCommitted", {**base, "client_id": bad})
    assert validate_event(
        "UpdateCommitted", {**base, "client_id": "client_03"}
    ).fields["client_id"] == "client_03"


def test_identifier_that_looks_like_a_record_number_is_rejected():
    with pytest.raises(AuditSchemaError, match="record number"):
        validate_event(
            "RoundClosed",
            {
                "run_id": "r", "round_index": 1, "global_model_sha256": "a" * 64,
                "aggregation_rule_id": "232",
            },
        )


def test_floats_are_rejected_in_favour_of_scaled_integers():
    with pytest.raises(AuditSchemaError):
        validate_event(
            "PrivacyAttested",
            {
                "run_id": "r", "epsilon_scaled": 57.3, "delta_scaled": 10000,
                "sigma_scaled": 1000000000, "clip_scaled": 3440000000,
                "accountant_id": "opencus",
            },
        )


def test_booleans_are_not_accepted_as_integers():
    with pytest.raises(AuditSchemaError, match="must be an integer"):
        validate_event("RunRegistered", _run_payload(seed=True))


def test_hash_fields_must_be_64_lowercase_hex():
    for bad in ("abc", "A" * 64, "g" * 64, 123):
        with pytest.raises(AuditSchemaError):
            validate_event("RunRegistered", _run_payload(config_sha256=bad))


# -------------------------------------------------- deep payload scan (defence)
def test_deep_scan_rejects_model_tensor_like_arrays():
    with pytest.raises(AuditSchemaError, match="tensor/vector"):
        assert_no_sensitive_payload({"safe": [0.0] * 100})


def test_deep_scan_rejects_absolute_paths_with_usernames():
    with pytest.raises(AuditSchemaError, match="absolute filesystem path"):
        assert_no_sensitive_payload({"note": r"C:\Users\someone\model.pt"})
    with pytest.raises(AuditSchemaError, match="absolute filesystem path"):
        assert_no_sensitive_payload({"note": "/home/someone/model.pt"})


def test_deep_scan_rejects_nested_prohibited_keys():
    with pytest.raises(AuditSchemaError):
        assert_no_sensitive_payload({"outer": {"record_ids": [101, 102]}})


def test_deep_scan_rejects_overlong_strings():
    with pytest.raises(AuditSchemaError, match="128 characters"):
        assert_no_sensitive_payload({"note": "x" * 200})


# ---------------------------------------------------------------- path hygiene
def test_safe_basename_strips_the_account_name():
    assert safe_basename(r"C:\Users\adni\Desktop\project\checkpoints\c.pt") == "c.pt"
    assert safe_basename("/home/someone/x/model.pt") == "model.pt"


def test_commitment_never_contains_a_path():
    digest = commitment({"checkpoint_basename": "central_seed_42.pt"})
    assert len(digest) == 64
    with pytest.raises(AuditSchemaError):
        commitment({"path": r"C:\Users\adni\x.pt"})


# --------------------------------------------------------- privacy scaling
def test_privacy_scaling_round_trips_to_reported_precision():
    assert scale_privacy_value(57.30169282486775) == 57301692825
    assert scale_privacy_value(1e-5) == 10000
    assert scale_privacy_value(3.44) == 3440000000


def test_privacy_scaling_rejects_negative_and_non_finite():
    for bad in (-1.0, float("nan"), float("inf")):
        with pytest.raises(Exception):
            scale_privacy_value(bad)
