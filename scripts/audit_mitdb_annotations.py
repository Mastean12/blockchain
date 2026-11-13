"""Audit MIT-BIH records and the approved AAMI-derived annotation mapping."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import wfdb

from src.data.aami_mapping import load_mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "mit-bih-arrhythmia-database-1.0.0"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "data_and_labels"
MAPPING_PATH = PROJECT_ROOT / "configs" / "data" / "aami5_mapping_v1.yaml"
DEFAULT_ARCHIVE = PROJECT_ROOT / "data" / "raw" / "downloads" / "mitdb-1.0.0.zip"


def write_sha256_manifest(data_dir: Path, archive_path: Path, output_dir: Path) -> Path:
    files = [archive_path, *sorted(path for path in data_dir.rglob("*") if path.is_file())]
    output_path = output_dir / "MITBIH_v1.0.0_SHA256SUMS.csv"
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["relative_path", "size_bytes", "sha256"])
        for path in files:
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            writer.writerow([
                path.relative_to(PROJECT_ROOT).as_posix(),
                path.stat().st_size,
                digest.hexdigest(),
            ])
    return output_path


def audit_dataset(data_dir: Path, output_dir: Path, archive_path: Path) -> dict:
    mapping = load_mapping(MAPPING_PATH)
    if not archive_path.is_file():
        raise FileNotFoundError(f"Dataset source archive not found: {archive_path}")
    record_ids = sorted((path.stem for path in data_dir.glob("*.hea")), key=int)
    if len(record_ids) != 48:
        raise ValueError(f"Expected 48 MIT-BIH record headers; found {len(record_ids)}")
    mapping.validate_record_exclusions(record_ids)

    for record_id in record_ids:
        for extension in (".hea", ".dat", ".atr"):
            path = data_dir / f"{record_id}{extension}"
            if not path.is_file():
                raise FileNotFoundError(f"Missing required file: {path}")

    symbol_counts: Counter[str] = Counter()
    record_rows = []
    sample_rate_counts: Counter[str] = Counter()
    channel_counts: Counter[str] = Counter()
    annotation_total = 0
    invalid_annotation_samples = []
    wfdb_descriptions = {
        str(row.symbol): str(row.description)
        for row in wfdb.io.annotation.ann_label_table.itertuples(index=False)
        if str(row.symbol)
    }

    for record_id in record_ids:
        record_base = data_dir / record_id
        header = wfdb.rdheader(str(record_base))
        signal = wfdb.rdrecord(str(record_base), physical=True)
        annotation = wfdb.rdann(str(record_base), mapping.annotation_extension)

        if signal.p_signal is None or signal.p_signal.shape != (header.sig_len, header.n_sig):
            raise ValueError(f"Signal shape does not match header for record {record_id}")
        if not np.isfinite(signal.p_signal).all():
            raise ValueError(f"Non-finite signal value in record {record_id}")
        if len(annotation.sample) != len(annotation.symbol):
            raise ValueError(f"Annotation sample/symbol lengths differ for record {record_id}")
        invalid = [int(sample) for sample in annotation.sample if sample < 0 or sample >= header.sig_len]
        if invalid:
            invalid_annotation_samples.append({"record": record_id, "samples": invalid[:10]})

        counts = Counter(annotation.symbol)
        symbol_counts.update(counts)
        annotation_total += len(annotation.symbol)
        per_class = {
            class_name: sum(counts.get(symbol, 0) for symbol in symbols)
            for class_name, symbols in mapping.classes.items()
        }
        exclusions = {symbol: counts.get(symbol, 0) for symbol in mapping.exclusions}
        record_exclusion = mapping.record_exclusions.get(record_id)
        record_rows.append({
            "record": record_id,
            "included_in_approved_protocol": record_exclusion is None,
            "record_exclusion_reason": record_exclusion["reason"] if record_exclusion else "",
            "sampling_frequency_hz": header.fs,
            "signal_channels": header.n_sig,
            "signal_samples_per_channel": header.sig_len,
            "annotation_count": len(annotation.symbol),
            **{f"mapped_{name}_count": per_class[name] for name in mapping.class_order},
            "paced_slash_count": counts.get("/", 0),
            "paced_fusion_f_count": counts.get("f", 0),
            "excluded_annotation_count": sum(exclusions.values()),
            "has_paced_annotations": bool(counts.get("/", 0) or counts.get("f", 0)),
        })
        sample_rate_counts[str(header.fs)] += 1
        channel_counts[str(header.n_sig)] += 1

    observed_symbols = set(symbol_counts)
    mapping.validate_observed_symbols(observed_symbols)
    if invalid_annotation_samples:
        raise ValueError(f"Annotations outside signal bounds: {invalid_annotation_samples}")

    inventory_rows = []
    targets = mapping.symbol_to_class
    for symbol, count in sorted(symbol_counts.items()):
        if symbol in targets:
            decision_type, decision = "approved_map", targets[symbol]
        else:
            decision_type, decision = "approved_exclusion", mapping.exclusions[symbol]["reason"]
        inventory_rows.append({
            "symbol": symbol,
            "wfdb_description": wfdb_descriptions.get(symbol, "Description unavailable in WFDB table"),
            "count": count,
            "decision_type": decision_type,
            "class_or_exclusion_reason": decision,
            "approval_status": mapping.status,
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    checksum_path = write_sha256_manifest(data_dir, archive_path, output_dir)
    inventory_path = output_dir / "MITBIH_RAW_ANNOTATION_INVENTORY.csv"
    record_path = output_dir / "MITBIH_PER_RECORD_AAMI_COUNTS.csv"
    summary_path = output_dir / "MITBIH_AUDIT_SUMMARY.json"

    with inventory_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=inventory_rows[0].keys())
        writer.writeheader()
        writer.writerows(inventory_rows)
    with record_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=record_rows[0].keys())
        writer.writeheader()
        writer.writerows(record_rows)

    class_totals = {
        class_name: sum(row[f"mapped_{class_name}_count"] for row in record_rows)
        for class_name in mapping.class_order
    }
    paced_records = [
        row["record"] for row in record_rows if row["has_paced_annotations"]
    ]
    paced_record_set = set(paced_records)
    non_paced_rows = [
        row for row in record_rows if row["record"] not in paced_record_set
    ]
    non_paced_class_totals = {
        class_name: sum(row[f"mapped_{class_name}_count"] for row in non_paced_rows)
        for class_name in mapping.class_order
    }
    approved_protocol_rows = [
        row for row in record_rows if row["included_in_approved_protocol"]
    ]
    approved_protocol_class_totals = {
        class_name: sum(row[f"mapped_{class_name}_count"] for row in approved_protocol_rows)
        for class_name in mapping.class_order
    }
    with checksum_path.open(encoding="utf-8") as file:
        checksum_rows = list(csv.DictReader(file))
    archive_relative_path = archive_path.relative_to(PROJECT_ROOT).as_posix()
    archive_sha256 = next(
        row["sha256"] for row in checksum_rows
        if row["relative_path"] == archive_relative_path
    )
    summary = {
        "dataset": "MIT-BIH Arrhythmia Database",
        "dataset_version": "1.0.0",
        "official_source": "https://physionet.org/content/mitdb/1.0.0/",
        "license": "Open Data Commons Attribution License v1.0",
        "audit_date": date.today().isoformat(),
        "wfdb_version": wfdb.__version__,
        "mapping_config": "configs/data/aami5_mapping_v1.yaml",
        "mapping_status": mapping.status,
        "record_count": len(record_ids),
        "record_ids": record_ids,
        "approved_record_exclusions": mapping.record_exclusions,
        "approved_protocol_record_count": len(approved_protocol_rows),
        "approved_protocol_record_ids": [
            row["record"] for row in approved_protocol_rows
        ],
        "approved_protocol_class_totals": approved_protocol_class_totals,
        "approved_protocol_class_record_support": {
            class_name: sum(row[f"mapped_{class_name}_count"] > 0 for row in approved_protocol_rows)
            for class_name in mapping.class_order
        },
        "total_annotations": annotation_total,
        "unique_observed_symbols": len(observed_symbols),
        "symbol_counts": dict(sorted(symbol_counts.items())),
        "mapped_class_totals_all_48_records": class_totals,
        "mapped_class_record_support_all_48_records": {
            class_name: sum(row[f"mapped_{class_name}_count"] > 0 for row in record_rows)
            for class_name in mapping.class_order
        },
        "excluded_annotation_total_all_48_records": sum(
            symbol_counts.get(symbol, 0) for symbol in mapping.exclusions
        ),
        "paced_record_ids": paced_records,
        "paced_symbol_counts": {
            "/": symbol_counts.get("/", 0),
            "f": symbol_counts.get("f", 0),
        },
        "sensitivity_class_totals_excluding_paced_records": non_paced_class_totals,
        "raw_Q_count_excluding_paced_symbols": symbol_counts.get("Q", 0),
        "Q_record_support_excluding_paced_records": sum(
            row["mapped_Q_count"] > 0 for row in non_paced_rows
        ),
        "checksum_manifest_entries": len(checksum_rows),
        "archive_sha256": archive_sha256,
        "sampling_frequency_record_counts": dict(sample_rate_counts),
        "signal_channel_record_counts": dict(channel_counts),
        "all_signal_values_finite": True,
        "all_annotations_within_signal_bounds": True,
        "approval_status": mapping.status,
        "outputs": [
            checksum_path.name,
            inventory_path.name,
            record_path.name,
            summary_path.name,
        ],
    }
    with summary_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)
        file.write("\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    summary = audit_dataset(args.data_dir, args.output_dir, args.archive)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
