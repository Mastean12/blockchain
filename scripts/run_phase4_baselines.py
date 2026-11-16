"""Run the Phase 4 majority, centralized, or local-only ECG baselines."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from src.training.phase4 import load_config, run_phase4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "models" / "phase4_cnn_v1.yaml"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--device",
        default="cuda",
        help="Training device; defaults to cuda and never silently falls back to CPU.",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run one CNN forward/backward/update batch; does not train full baselines.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a compatible incomplete full run in the existing output directory.",
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    config_path = args.config.resolve()
    if args.output_dir is None:
        run_kind = "smoke" if args.smoke_test else "full"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = project_root / "experiments" / "logs" / "phase4" / f"{run_kind}_{timestamp}"
    else:
        output_dir = args.output_dir
        if not output_dir.is_absolute():
            output_dir = project_root / output_dir

    result = run_phase4(
        project_root=project_root,
        config_path=config_path,
        output_dir=output_dir.resolve(),
        device_name=args.device,
        smoke_test=args.smoke_test,
        resume=args.resume,
    )
    print(
        f"Phase 4 {'smoke test' if args.smoke_test else 'baseline run'} "
        f"{result['status']}: {output_dir.resolve()}"
    )
    environment = result.get("environment", {})
    if "cuda_device_name" in environment:
        print(f"CUDA device: {environment['cuda_device_name']}")


if __name__ == "__main__":
    main()
