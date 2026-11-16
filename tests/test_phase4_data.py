from pathlib import Path

import yaml

from src.training.phase4_data import load_phase4_data


def test_phase4_loader_verifies_frozen_artifacts_and_client_coverage():
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "configs" / "models" / "phase4_cnn_v1.yaml"
    with config_path.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)

    data = load_phase4_data(project_root, config)

    assert data.split_manifest_sha256 == config["expected_split_manifest_sha256"]
    assert data.client_manifest_sha256 == config["expected_client_manifest_sha256"]
    assert data.splits["train"].x.shape == (71927, 253)
    assert data.splits["validation"].x.shape == (13722, 253)
    assert data.splits["test"].x.shape == (15045, 253)
