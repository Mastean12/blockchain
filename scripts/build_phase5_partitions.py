"""Build and freeze Phase 5 client partition manifests (whole training records only)."""

import argparse
import json
from pathlib import Path

from src.federated.partitions import (
    frozen_partition,
    partition_manifest,
    record_dirichlet_partition,
    verify_partition_manifest,
)
from src.training.phase4 import load_config
from src.training.phase4_data import load_phase4_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "models" / "phase4_cnn_v1.yaml",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    data = load_phase4_data(project_root, load_config(args.config))
    output_dir = (args.output_dir or project_root / "data" / "splits" / "phase5").resolve()

    partitions = {
        "phase5_f1_iid_like": frozen_partition(data),
    }
    for name, concentration in (("phase5_f2_moderate", 0.5), ("phase5_f3_severe", 0.1)):
        partitions[name] = record_dirichlet_partition(
            data, concentration=concentration, seed=args.seed
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, partition in partitions.items():
        document = partition_manifest(data, partition)
        path = output_dir / f"{name}.json"
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing.get("manifest_sha256") != document["manifest_sha256"]:
                raise SystemExit(
                    f"Refusing to overwrite {path.name} with different content; "
                    "existing partition was already frozen"
                )
        path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        verify_partition_manifest(data, document)
        summary[name] = {
            "manifest_sha256": document["manifest_sha256"],
            "family": document["family"],
            "clients": [
                {
                    "client_id": client["client_id"],
                    "records": client["record_count"],
                    "samples": client["sample_count"],
                    "class_counts": client["class_counts"],
                    "absent": client["absent_classes"],
                }
                for client in document["clients"]
            ],
        }
        print(name, document["manifest_sha256"])

    (output_dir / "index.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("wrote", output_dir)


if __name__ == "__main__":
    main()
