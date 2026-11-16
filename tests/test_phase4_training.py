from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
import yaml

torch = pytest.importorskip("torch")

from src.training.phase4 import fit_and_evaluate, run_phase4
from src.training import phase4 as phase4_module
from src.training.phase4_data import Phase4Data, SplitArrays


def _split(labels, seed):
    rng = np.random.default_rng(seed)
    return SplitArrays(
        x=rng.normal(size=(len(labels), 253)).astype(np.float32),
        y=np.asarray(labels, dtype=np.int8),
        record_ids=np.full(len(labels), seed, dtype=np.int16),
        sample_positions=np.arange(len(labels), dtype=np.int32),
    )


def test_fit_selects_checkpoint_on_supported_validation_classes_only(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    with (project_root / "configs" / "models" / "phase4_cnn_v1.yaml").open(
        encoding="utf-8"
    ) as file:
        config = deepcopy(yaml.safe_load(file))
    config["training"]["batch_size"] = 8
    config["training"]["maximum_epochs"] = 1
    config["training"]["early_stopping"]["patience"] = 1
    config["training"]["seeds"] = [42]

    train = _split([0, 1, 2, 3] * 4, 100)
    validation = _split([0, 1, 2, 3] * 2, 101)
    test = _split([0, 1, 2, 4] * 2, 102)

    result = fit_and_evaluate(
        config,
        train,
        validation,
        test,
        torch.device("cpu"),
        seed=42,
        checkpoint_path=tmp_path / "best.pt",
    )

    assert result["best_epoch"] in {0, 1}
    assert result["best_validation_metrics"]["macro_classes_included"] == ["N", "S", "V", "F"]
    assert result["test_metrics"]["absent_true_classes"] == ["F"]
    assert result["test_metrics"]["per_class"]["F"]["f1"] is None
    assert result["checkpoint_sha256"]
    assert (tmp_path / "best.pt").is_file()


def test_cuda_request_fails_explicitly_without_cpu_fallback(tmp_path):
    if torch.cuda.is_available():
        pytest.skip("This test exercises behavior only on CPU-only runtimes")
    project_root = Path(__file__).resolve().parents[1]

    with pytest.raises(RuntimeError, match="no CPU fallback"):
        run_phase4(
            project_root=project_root,
            config_path=project_root / "configs" / "models" / "phase4_cnn_v1.yaml",
            output_dir=tmp_path / "phase4",
            device_name="cuda",
            smoke_test=True,
        )

    assert not (tmp_path / "phase4").exists()


def _fake_metrics():
    per_class = {
        name: {
            "precision": 0.5,
            "recall": 0.5,
            "f1": 0.5,
            "specificity": 0.5,
            "auroc_ovr": 0.5,
            "auprc_ovr": 0.5,
            "support": 1,
            "predicted_support": 1,
        }
        for name in ("N", "S", "V", "F", "Q")
    }
    return {
        "class_order": ["N", "S", "V", "F", "Q"],
        "confusion_matrix": [[1, 0, 0, 0, 0]] * 5,
        "per_class": per_class,
        "accuracy": 0.5,
        "macro_precision": 0.5,
        "macro_recall": 0.5,
        "macro_f1": 0.5,
        "macro_auroc_ovr": 0.5,
        "macro_auprc_ovr": 0.5,
        "weighted_precision": 0.5,
        "weighted_recall": 0.5,
        "weighted_f1": 0.5,
    }


def test_full_run_resume_skips_verified_fits_and_consolidates_metrics(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "configs" / "models" / "phase4_cnn_v1.yaml"
    train_base = _split([0, 1, 2, 3, 4], 100)
    train = SplitArrays(
        x=train_base.x,
        y=train_base.y,
        record_ids=np.arange(100, 105, dtype=np.int16),
        sample_positions=train_base.sample_positions,
    )
    validation = _split([0, 1, 2, 3], 101)
    test = _split([0, 1, 2, 4], 102)
    clients = [
        {"client_id": f"client_{index}", "record_ids": [str(100 + index)]}
        for index in range(5)
    ]
    data = Phase4Data(
        splits={"train": train, "validation": validation, "test": test},
        split_manifest={},
        client_manifest={"clients": clients},
        split_manifest_sha256="split-hash",
        client_manifest_sha256="client-hash",
        preprocessing_report_sha256="preprocess-hash",
    )
    monkeypatch.setattr(phase4_module, "load_phase4_data", lambda *_: data)
    fit_calls = []

    def fake_fit(config, train_split, validation_split, test_split, device, seed, checkpoint_path):
        fit_calls.append((seed, int(train_split.record_ids[0])))
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_bytes(f"{seed}:{int(train_split.record_ids[0])}".encode())
        return {
            "seed": seed,
            "checkpoint": str(checkpoint_path),
            "checkpoint_sha256": phase4_module._sha256_file(checkpoint_path),
            "best_validation_metrics": _fake_metrics(),
            "test_metrics": _fake_metrics(),
        }

    monkeypatch.setattr(phase4_module, "fit_and_evaluate", fake_fit)
    output_dir = tmp_path / "phase4-run"
    first = run_phase4(project_root, config_path, output_dir, "cpu")
    assert len(fit_calls) == 30
    assert first["status"] == "complete"
    assert first["aggregate_test_metrics"]["centralized"]["test"]["per_class"]["N"]["f1"][
        "mean"
    ] == 0.5
    assert len(first["centralized_runs"][0]["test_metrics"]["confusion_matrix"]) == 5

    resumed = run_phase4(project_root, config_path, output_dir, "cpu", resume=True)
    assert len(fit_calls) == 30
    assert resumed["resume_count"] == 1
    assert resumed["execution_seconds"]["sum_of_fit_times"] > 0

    interrupted_run_report = output_dir / "client_0_seed_42.json"
    interrupted_run_report.unlink()
    resumed_after_orphan = run_phase4(
        project_root, config_path, output_dir, "cpu", resume=True
    )
    assert len(fit_calls) == 31
    assert resumed_after_orphan["resume_count"] == 2
    assert list((output_dir / "checkpoints" / "unverified").glob("client_0_seed_42_*.pt"))

    checkpoint = output_dir / "checkpoints" / "central_seed_42.pt"
    checkpoint.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="Checkpoint hash mismatch"):
        run_phase4(project_root, config_path, output_dir, "cpu", resume=True)
