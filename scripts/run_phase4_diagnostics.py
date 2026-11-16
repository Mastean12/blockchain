"""Run a Phase 4 diagnostic ablation (class weighting or balanced-accuracy selection)."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from src.training.phase4_diagnostics import run_diagnostic

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DIAGNOSTIC_CONFIGS = {
    "phase4_diag_d1_class_weighted": PROJECT_ROOT / "configs" / "models" / "phase4_diag_d1_class_weighted.yaml",
    "phase4_diag_d2_selection_balanced_accuracy": PROJECT_ROOT
    / "configs"
    / "models"
    / "phase4_diag_d2_selection_balanced_accuracy.yaml",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True, choices=sorted(DIAGNOSTIC_CONFIGS))
    parser.add_argument("--config", type=Path)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--device",
        default="cuda",
        help="Training device; defaults to cuda and never silently falls back to CPU.",
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    config_path = (args.config or DIAGNOSTIC_CONFIGS[args.experiment]).resolve()
    if args.output_dir is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = (
            project_root / "experiments" / "logs" / "phase4" / "diagnostics" / args.experiment / timestamp
        )
    else:
        output_dir = args.output_dir
        if not output_dir.is_absolute():
            output_dir = project_root / output_dir

    summary = run_diagnostic(
        project_root=project_root,
        config_path=config_path,
        output_dir=output_dir.resolve(),
        device_name=args.device,
    )
    print(f"Diagnostic {args.experiment} complete: {output_dir.resolve()}")
    print(f"CUDA device: {summary['environment'].get('cuda_device_name')}")
    test = summary["aggregate"]["test"]["overall"]
    print(
        "test accuracy mean "
        f"{test['accuracy']['mean']:.4f} sd {test['accuracy']['standard_deviation']:.4f}, "
        f"test macro-F1 mean {test['macro_f1']['mean']:.4f} sd {test['macro_f1']['standard_deviation']:.4f}"
        if test["macro_f1"]["mean"] is not None
        else f"test accuracy mean {test['accuracy']['mean']:.4f}"
    )


if __name__ == "__main__":
    main()
