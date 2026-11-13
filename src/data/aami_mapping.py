"""Validation helpers for the candidate AAMI-derived annotation mapping."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml


@dataclass(frozen=True)
class AamiMapping:
    version: int
    status: str
    annotation_extension: str
    class_order: tuple[str, ...]
    classes: dict[str, tuple[str, ...]]
    exclusions: dict[str, dict[str, str]]
    record_exclusions: dict[str, dict[str, str]]

    @property
    def symbol_to_class(self) -> dict[str, str]:
        assignments: dict[str, str] = {}
        for class_name, symbols in self.classes.items():
            for symbol in symbols:
                if symbol in assignments:
                    raise ValueError(f"Annotation symbol {symbol!r} maps to multiple classes")
                assignments[symbol] = class_name
        return assignments

    def validate_observed_symbols(self, symbols: Iterable[str]) -> None:
        mapped = set(self.symbol_to_class)
        excluded = set(self.exclusions)
        overlap = mapped & excluded
        if overlap:
            raise ValueError(f"Symbols have both mapping and exclusion decisions: {sorted(overlap)}")

        unresolved = set(symbols) - mapped - excluded
        if unresolved:
            raise ValueError(f"Observed symbols have no explicit decision: {sorted(unresolved)}")

    def validate_record_exclusions(self, record_ids: Iterable[str]) -> None:
        unresolved = set(self.record_exclusions) - set(record_ids)
        if unresolved:
            raise ValueError(f"Excluded record IDs are not present in the dataset: {sorted(unresolved)}")

    def decision_for(self, symbol: str) -> tuple[str, str]:
        target = self.symbol_to_class.get(symbol)
        if target is not None:
            return "map", target
        exclusion = self.exclusions.get(symbol)
        if exclusion is not None:
            return "exclude", exclusion["reason"]
        raise ValueError(f"Annotation symbol {symbol!r} has no explicit decision")


def build_mapping(
    version: int,
    status: str,
    class_order: Iterable[str],
    classes: dict[str, Iterable[str]],
    exclusions: dict[str, dict[str, str]],
    annotation_extension: str = "atr",
    record_exclusions: dict[str, dict[str, str]] | None = None,
) -> AamiMapping:
    normalized_classes = {
        str(class_name): tuple(str(symbol) for symbol in symbols)
        for class_name, symbols in classes.items()
    }
    normalized_exclusions = {
        str(symbol): {str(key): str(value) for key, value in decision.items()}
        for symbol, decision in exclusions.items()
    }
    normalized_record_exclusions = {
        str(record_id): {str(key): str(value) for key, value in decision.items()}
        for record_id, decision in (record_exclusions or {}).items()
    }
    order = tuple(str(class_name) for class_name in class_order)
    if len(order) != len(set(order)) or set(order) != set(normalized_classes):
        raise ValueError("Class order must list each configured class exactly once")

    mapping = AamiMapping(
        version=int(version),
        status=str(status),
        annotation_extension=str(annotation_extension),
        class_order=order,
        classes=normalized_classes,
        exclusions=normalized_exclusions,
        record_exclusions=normalized_record_exclusions,
    )
    mapping.symbol_to_class
    overlap = set(mapping.symbol_to_class) & set(mapping.exclusions)
    if overlap:
        raise ValueError(f"Symbols have both mapping and exclusion decisions: {sorted(overlap)}")
    for symbol, decision in mapping.exclusions.items():
        if not decision.get("reason"):
            raise ValueError(f"Exclusion for {symbol!r} must include a reason")
    for record_id, decision in mapping.record_exclusions.items():
        if not decision.get("reason"):
            raise ValueError(f"Record exclusion for {record_id!r} must include a reason")
    return mapping


def load_mapping(path: Path) -> AamiMapping:
    with path.open(encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise ValueError("Mapping configuration must be a YAML object")
    return build_mapping(
        version=config["version"],
        status=config["status"],
        class_order=config["class_order"],
        classes=config["classes"],
        exclusions=config["exclusions"],
        annotation_extension=config.get("annotation_extension", "atr"),
        record_exclusions=config.get("record_exclusions", {}),
    )
