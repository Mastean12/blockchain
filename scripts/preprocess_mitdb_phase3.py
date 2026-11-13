"""Build annotation-centered Phase 3 windows without fitting on validation/test data."""

import argparse
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path

import numpy as np
import wfdb

from src.data.aami_mapping import load_mapping
from src.data.phase3_pipeline import (
    CLASS_ORDER,
    SPLIT_ORDER,
    extract_annotated_windows,
    fit_standardization,
    standardize_windows,
    verify_manifest_hash,
    group_record_ids,
    validate_split_partition,
    window_offsets,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DOCS = PROJECT_ROOT / "docs" / "data_and_labels"
MAPPING_PATH = PROJECT_ROOT / "configs" / "data" / "aami5_mapping_v1.yaml"
AUDIT_SUMMARY_PATH = DATA_DOCS / "MITBIH_AUDIT_SUMMARY.json"
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "mit-bih-arrhythmia-database-1.0.0"
DEFAULT_SPLIT_MANIFEST = PROJECT_ROOT / "data" / "splits" / "phase3_split_manifest.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "phase3"
DEFAULT_REPORT_PATH = DATA_DOCS / "PHASE3_PREPROCESSING_AUDIT.json"
EXPECTED_FS_HZ = 360
EXPECTED_CHANNEL = "MLII"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashed_json(path: Path, payload: dict[str, object]) -> dict[str, object]:
    from src.data.phase3_pipeline import add_manifest_hash

    document = add_manifest_hash(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(document, file, indent=2, sort_keys=True)
        file.write("\n")
    return document


def _read_split_inputs(
    split_name: str,
    record_ids: list[str],
    data_dir: Path,
    mapping,
) -> tuple[list[dict[str, object]], dict[str, int], dict[str, int], Counter[str]]:
    plans: list[dict[str, object]] = []
    mapped_annotation_counts = {class_name: 0 for class_name in CLASS_ORDER}
    boundary_excluded_counts = {class_name: 0 for class_name in CLASS_ORDER}
    excluded_symbol_counts: Counter[str] = Counter()

    for record_id in record_ids:
        record_base = data_dir / record_id
        header = wfdb.rdheader(str(record_base))
        if float(header.fs) != EXPECTED_FS_HZ:
            raise ValueError(
                f"Record {record_id} has sampling rate {header.fs}; expected {EXPECTED_FS_HZ} Hz"
            )
        if not header.sig_name or EXPECTED_CHANNEL not in header.sig_name:
            raise ValueError(f"Record {record_id} has no {EXPECTED_CHANNEL} channel")
        annotation = wfdb.rdann(str(record_base), mapping.annotation_extension)
        mapping.validate_observed_symbols(annotation.symbol)
        before, after, window_size = window_offsets(float(header.fs))
        eligible_count = 0
        record_boundary_counts = {class_name: 0 for class_name in CLASS_ORDER}
        for sample_position, symbol in zip(annotation.sample, annotation.symbol):
            decision_type, decision = mapping.decision_for(str(symbol))
            if decision_type == "exclude":
                excluded_symbol_counts[str(symbol)] += 1
                continue
            mapped_annotation_counts[decision] += 1
            if sample_position < 0 or sample_position >= header.sig_len:
                raise ValueError(f"Annotation sample is outside record {record_id}")
            start = int(sample_position) - before
            stop = int(sample_position) + after + 1
            if start < 0 or stop > header.sig_len:
                boundary_excluded_counts[decision] += 1
                record_boundary_counts[decision] += 1
            else:
                eligible_count += 1
        plans.append({
            "record_id": record_id,
            "header": header,
            "annotation": annotation,
            "window_size": window_size,
            "eligible_count": eligible_count,
            "boundary_excluded_by_class": record_boundary_counts,
        })

    if not any(int(plan["eligible_count"]) for plan in plans):
        raise ValueError(f"No valid mapped beats in {split_name} split")
    return plans, mapped_annotation_counts, boundary_excluded_counts, excluded_symbol_counts


def _extract_split(
    split_name: str,
    record_ids: list[str],
    data_dir: Path,
    mapping,
    expected_class_counts: dict[str, int],
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    plans, mapped_counts, boundary_counts, excluded_symbols = _read_split_inputs(
        split_name, record_ids, data_dir, mapping
    )
    window_size = int(plans[0]["window_size"])
    if any(int(plan["window_size"]) != window_size for plan in plans):
        raise ValueError(f"Records in {split_name} use inconsistent ECG window sizes")

    output_count = sum(int(plan["eligible_count"]) for plan in plans)
    x = np.empty((output_count, window_size), dtype=np.float32)
    class_to_index = {class_name: index for index, class_name in enumerate(CLASS_ORDER)}
    y = np.empty(output_count, dtype=np.int8)
    output_record_ids = np.empty(output_count, dtype=np.int16)
    sample_positions = np.empty(output_count, dtype=np.int32)
    symbols = np.empty(output_count, dtype="U1")
    cursor = 0

    for plan in plans:
        record_id = str(plan["record_id"])
        if int(plan["eligible_count"]) == 0:
            continue
        header = plan["header"]
        annotation = plan["annotation"]
        channel_index = header.sig_name.index(EXPECTED_CHANNEL)
        record = wfdb.rdrecord(
            str(data_dir / record_id),
            channels=[channel_index],
            physical=True,
        )
        if record.p_signal is None or record.p_signal.shape != (header.sig_len, 1):
            raise ValueError(f"Signal shape does not match header for record {record_id}")
        if not np.isfinite(record.p_signal).all():
            raise ValueError(f"Non-finite signal value in record {record_id}")

        record_windows, record_labels, positions, record_symbols, record_boundary_counts = (
            extract_annotated_windows(
                signal=record.p_signal[:, 0],
                sample_positions=annotation.sample,
                symbols=annotation.symbol,
                symbol_to_class=mapping.symbol_to_class,
                class_order=CLASS_ORDER,
                sampling_frequency_hz=float(header.fs),
            )
        )
        if record_windows.shape[0] != int(plan["eligible_count"]):
            raise ValueError(f"Annotation count changed while extracting record {record_id}")
        for class_name in CLASS_ORDER:
            expected_boundary_count = int(plan["boundary_excluded_by_class"][class_name])
            if record_boundary_counts[class_name] != expected_boundary_count:
                raise ValueError(f"Boundary count changed while extracting record {record_id}")

        next_cursor = cursor + record_windows.shape[0]
        x[cursor:next_cursor] = record_windows
        y[cursor:next_cursor] = record_labels
        output_record_ids[cursor:next_cursor] = int(record_id)
        sample_positions[cursor:next_cursor] = positions
        symbols[cursor:next_cursor] = record_symbols
        cursor = next_cursor

    if cursor != output_count:
        raise ValueError(f"Extracted row count does not match planned count for {split_name}")
    processed_counts = {
        class_name: int(np.count_nonzero(y == class_to_index[class_name]))
        for class_name in CLASS_ORDER
    }
    for class_name in CLASS_ORDER:
        if processed_counts[class_name] + boundary_counts[class_name] != expected_class_counts[class_name]:
            raise ValueError(
                f"{split_name} {class_name} counts do not reconcile: "
                f"processed {processed_counts[class_name]} + boundary "
                f"{boundary_counts[class_name]} != audited {expected_class_counts[class_name]}"
            )

    arrays = {
        "x": x,
        "y": y,
        "record_ids": output_record_ids,
        "sample_positions": sample_positions,
        "symbols": symbols,
    }
    details = {
        "record_ids": record_ids,
        "window_count": output_count,
        "class_counts": processed_counts,
        "boundary_excluded_by_class": boundary_counts,
        "excluded_symbol_counts": dict(sorted(excluded_symbols.items())),
        "signal_quality_marker_count": excluded_symbols.get("~", 0),
        "array_shape": list(x.shape),
        "dtype": str(x.dtype),
    }
    return arrays, details


def preprocess_dataset(
    data_dir: Path,
    split_manifest_path: Path,
    output_dir: Path,
    report_path: Path,
) -> dict[str, object]:
    mapping = load_mapping(MAPPING_PATH)
    if mapping.status != "research_lead_approved":
        raise ValueError(f"Mapping is not approved: {mapping.status}")
    if mapping.class_order != CLASS_ORDER:
        raise ValueError("Approved mapping class order differs from the Phase 3 pipeline")
    with split_manifest_path.open(encoding="utf-8") as file:
        split_manifest = json.load(file)
    split_hash = verify_manifest_hash(split_manifest)
    if split_manifest["mapping_status"] != mapping.status:
        raise ValueError("Split manifest and mapping approval statuses differ")
    if split_manifest["mapping_config_sha256"] != sha256_file(MAPPING_PATH):
        raise ValueError("Mapping configuration changed after split manifest creation")
    with AUDIT_SUMMARY_PATH.open(encoding="utf-8") as file:
        audit_summary = json.load(file)
    if split_manifest["raw_archive_sha256"] != audit_summary["archive_sha256"]:
        raise ValueError("Split manifest does not reference the audited raw dataset")
    if split_manifest["class_order"] != list(CLASS_ORDER):
        raise ValueError("Split manifest class order differs from the approved mapping")
    approved_record_ids = set(audit_summary["approved_protocol_record_ids"])
    groups = group_record_ids(approved_record_ids)
    if split_manifest["record_group_mapping"] != groups:
        raise ValueError("Split manifest record groups differ from the approved group policy")
    manifest_splits = {
        split_name: list(split_manifest["splits"][split_name]["record_ids"])
        for split_name in SPLIT_ORDER
    }
    record_assignments = validate_split_partition(manifest_splits, approved_record_ids, groups)
    if record_assignments != split_manifest["record_assignments"]:
        raise ValueError("Split record assignments do not match the manifest partitions")

    split_arrays: dict[str, dict[str, np.ndarray]] = {}
    split_details: dict[str, dict[str, object]] = {}
    for split_name in SPLIT_ORDER:
        split = split_manifest["splits"][split_name]
        record_ids = list(split["record_ids"])
        arrays, details = _extract_split(
            split_name=split_name,
            record_ids=record_ids,
            data_dir=data_dir,
            mapping=mapping,
            expected_class_counts={
                class_name: int(split["class_counts"][class_name])
                for class_name in CLASS_ORDER
            },
        )
        split_arrays[split_name] = arrays
        split_details[split_name] = details

    mean, standard_deviation = fit_standardization(split_arrays["train"]["x"])
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_hashes: dict[str, str] = {}
    artifact_paths: dict[str, str] = {}
    for split_name in SPLIT_ORDER:
        arrays = split_arrays[split_name]
        arrays["x"] = standardize_windows(arrays["x"], mean, standard_deviation)
        for array_name, values in arrays.items():
            path = output_dir / f"{split_name}_{array_name}.npy"
            np.save(path, values, allow_pickle=False)
            artifact_paths[f"{split_name}_{array_name}"] = path.relative_to(PROJECT_ROOT).as_posix()
            artifact_hashes[path.name] = sha256_file(path)

    report_payload: dict[str, object] = {
        "schema_version": 1,
        "dataset": audit_summary["dataset"],
        "dataset_version": audit_summary["dataset_version"],
        "split_manifest_sha256": split_hash,
        "mapping_config_sha256": sha256_file(MAPPING_PATH),
        "preprocessing_code_version": "1.0.0",
        "python_version": platform.python_version(),
        "wfdb_version": wfdb.__version__,
        "numpy_version": np.__version__,
        "policy": {
            "lead": EXPECTED_CHANNEL,
            "sampling_frequency_hz": EXPECTED_FS_HZ,
            "sampling_frequency_source": "record header; mismatch causes an explicit error",
            "beat_locations": "reference .atr annotation sample positions",
            "interpretation": (
                "Classification conditional on reference beat locations; this does not evaluate "
                "end-to-end beat detection."
            ),
            "window_offsets_samples_inclusive": {
                "before": -90,
                "after": 162,
                "window_size": 253,
            },
            "window_offsets_seconds": {
                "before": 0.25,
                "after": 0.45,
            },
            "boundary_windows": "drop and count by approved class; never pad or wrap",
            "resampling": "none; retain native 360 Hz",
            "filtering_and_baseline_removal": "none",
            "normalization": {
                "method": "global z-score over all training-window samples",
                "fit_split": "train only",
                "mean": mean,
                "standard_deviation": standard_deviation,
            },
            "signal_quality_annotations": (
                "The ~ symbol is non-beat metadata, not a class. Its count is reported; "
                "nearby beats are not automatically removed."
            ),
            "augmentation_or_oversampling": "none",
            "source_protocol": (
                "Kachuee et al. (2018), https://doi.org/10.1109/ICHI.2018.00092; "
                "this project uses reference annotations and a fixed window rather than "
                "the paper's detector/adaptive-window procedure."
            ),
        },
        "split_details": split_details,
        "processed_artifacts": artifact_paths,
        "processed_artifact_sha256": artifact_hashes,
    }
    report = write_hashed_json(report_path, report_payload)
    return {
        "preprocessing_report_sha256": report["manifest_sha256"],
        "split_manifest_sha256": split_hash,
        "normalization_mean": mean,
        "normalization_standard_deviation": standard_deviation,
        "split_window_counts": {
            split_name: split_details[split_name]["window_count"]
            for split_name in SPLIT_ORDER
        },
        "split_class_counts": {
            split_name: split_details[split_name]["class_counts"]
            for split_name in SPLIT_ORDER
        },
        "outputs": {
            "data_directory": output_dir.relative_to(PROJECT_ROOT).as_posix(),
            "report": report_path.relative_to(PROJECT_ROOT).as_posix(),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--split-manifest", type=Path, default=DEFAULT_SPLIT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()
    print(json.dumps(
        preprocess_dataset(args.data_dir, args.split_manifest, args.output_dir, args.report),
        indent=2,
    ))


if __name__ == "__main__":
    main()
