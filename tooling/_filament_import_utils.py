"""Shared safety and database helpers for filament import tooling."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import json
from pathlib import Path
import tempfile
from typing import cast, Generic, Protocol, TypeVar

from color_tools import generate_filament_id, parse_hex_colors, rgb_to_hex


class _AdditiveCandidate(Protocol):
    """Candidate contract used by additive filament importers."""

    @property
    def identity(self) -> tuple[str, str, str, str]: ...

    @property
    def record_id(self) -> str: ...

    @property
    def source_description(self) -> str: ...

    @property
    def hex_value(self) -> str: ...

    def to_record(self) -> dict[str, object]: ...


_CandidateT = TypeVar("_CandidateT", bound=_AdditiveCandidate)


@dataclass(frozen=True, slots=True)
class _ImportConflict(Generic[_CandidateT]):
    candidate: _CandidateT
    reason: str


@dataclass(frozen=True, slots=True)
class _ImportCorrection(Generic[_CandidateT]):
    candidate: _CandidateT
    existing_id: str
    existing_hex: str


@dataclass(slots=True)
class _AdditiveImportPlan(Generic[_CandidateT]):
    additions: list[_CandidateT] = field(default_factory=list)
    unchanged: list[_CandidateT] = field(default_factory=list)
    corrections: list[_ImportCorrection[_CandidateT]] = field(default_factory=list)
    conflicts: list[_ImportConflict[_CandidateT]] = field(default_factory=list)


def _normalize_hex(value: str) -> str:
    """Return canonical ordered hex components."""
    return "-".join(rgb_to_hex(component) for component in parse_hex_colors(value))


def _normalize_identity_part(value: str | None) -> str:
    """Normalize one product-identity field for matching."""
    return " ".join((value or "").split()).casefold()


def _identity(
    maker: str,
    type_name: str,
    finish: str | None,
    color: str,
) -> tuple[str, str, str, str]:
    """Build a normalized maker/type/finish/color identity key."""
    return (
        _normalize_identity_part(maker),
        _normalize_identity_part(type_name),
        _normalize_identity_part(finish),
        _normalize_identity_part(color),
    )


def _filament_id(
    maker: str,
    type_name: str,
    finish: str | None,
    color: str,
) -> str:
    """Build a stable filament ID from its product identity."""
    return generate_filament_id(maker, type_name, finish, color)


def _load_database(path: Path) -> list[dict[str, object]]:
    """Load the filament database as JSON objects."""
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{path}: expected a JSON array of objects")
    return [cast(dict[str, object], item) for item in value]


def _required_text(record: dict[str, object], field_name: str) -> str:
    """Read a required string field from a database record."""
    value = record.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Filament record has invalid {field_name!r}: {value!r}")
    return value


def _record_identity(record: dict[str, object]) -> tuple[str, str, str, str]:
    """Return the normalized product identity of a database record."""
    finish = record.get("finish")
    if finish is not None and not isinstance(finish, str):
        raise ValueError(f"Filament record has invalid 'finish': {finish!r}")
    return _identity(
        _required_text(record, "maker"),
        _required_text(record, "type"),
        finish,
        _required_text(record, "color"),
    )


def _build_additive_import_plan(
    candidates: Sequence[_CandidateT],
    database: Sequence[dict[str, object]],
) -> _AdditiveImportPlan[_CandidateT]:
    """Classify additive candidates without changing the database."""
    return _build_import_plan(candidates, database, allow_corrections=False)


def _build_reconciling_import_plan(
    candidates: Sequence[_CandidateT],
    database: Sequence[dict[str, object]],
) -> _AdditiveImportPlan[_CandidateT]:
    """Classify candidates and permit reviewed hex corrections."""
    return _build_import_plan(candidates, database, allow_corrections=True)


def _build_import_plan(
    candidates: Sequence[_CandidateT],
    database: Sequence[dict[str, object]],
    *,
    allow_corrections: bool,
) -> _AdditiveImportPlan[_CandidateT]:
    """Classify candidates under the requested correction policy."""
    plan = _AdditiveImportPlan[_CandidateT]()
    by_identity: dict[tuple[str, str, str, str], list[dict[str, object]]] = {}
    by_id: dict[str, dict[str, object]] = {}
    for record in database:
        by_identity.setdefault(_record_identity(record), []).append(record)
        record_id = _required_text(record, "id")
        if record_id in by_id:
            raise ValueError(f"Database contains duplicate filament ID: {record_id}")
        by_id[record_id] = record

    seen_sources: dict[tuple[str, str, str, str], _CandidateT] = {}
    for candidate in candidates:
        previous = seen_sources.get(candidate.identity)
        if previous is not None:
            plan.conflicts.append(
                _ImportConflict(
                    candidate,
                    "duplicate source identity also in "
                    f"{previous.source_description}",
                )
            )
            continue
        seen_sources[candidate.identity] = candidate

        matches = by_identity.get(candidate.identity, [])
        if len(matches) > 1:
            plan.conflicts.append(
                _ImportConflict(
                    candidate,
                    f"database contains {len(matches)} matching identities",
                )
            )
            continue
        if matches:
            existing = matches[0]
            existing_id = _required_text(existing, "id")
            existing_hex = _normalize_hex(_required_text(existing, "hex"))
            if existing_hex == candidate.hex_value:
                plan.unchanged.append(candidate)
            elif allow_corrections:
                plan.corrections.append(
                    _ImportCorrection(candidate, existing_id, existing_hex)
                )
            else:
                plan.conflicts.append(
                    _ImportConflict(
                        candidate,
                        f"existing {existing_id} has "
                        f"{existing_hex}, source has {candidate.hex_value}",
                    )
                )
            continue

        collision = by_id.get(candidate.record_id)
        if collision is not None:
            plan.conflicts.append(
                _ImportConflict(
                    candidate,
                    f"generated ID {candidate.record_id!r} belongs to another identity",
                )
            )
            continue
        plan.additions.append(candidate)
        by_id[candidate.record_id] = candidate.to_record()

    return plan


def _database_sort_key(record: dict[str, object]) -> tuple[str, str, str, str]:
    """Sort one maker's records by type, finish, color, and ID."""
    finish = record.get("finish")
    return (
        _normalize_identity_part(_required_text(record, "type")),
        _normalize_identity_part(finish if isinstance(finish, str) else None),
        _normalize_identity_part(_required_text(record, "color")),
        _required_text(record, "id"),
    )


def _merge_maker_records(
    database: Sequence[dict[str, object]],
    maker: str,
    additions: Sequence[dict[str, object]],
    replacements: dict[str, dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    """Replace and add records while preserving the surrounding maker order."""
    replacement_map = replacements or {}
    merged = [replacement_map.get(_required_text(record, "id"), dict(record)) for record in database]
    maker_indices = [
        index
        for index, record in enumerate(merged)
        if _required_text(record, "maker") == maker
    ]
    new_records = [dict(record) for record in additions]
    if not maker_indices:
        return merged + sorted(new_records, key=_database_sort_key)

    first = maker_indices[0]
    last = maker_indices[-1]
    if maker_indices != list(range(first, last + 1)):
        raise ValueError(f"Existing {maker} records are not contiguous")
    maker_records = merged[first : last + 1] + new_records
    return (
        merged[:first]
        + sorted(maker_records, key=_database_sort_key)
        + merged[last + 1 :]
    )


def _write_database(path: Path, records: Sequence[dict[str, object]]) -> None:
    """Atomically replace the database with formatted JSON."""
    content = json.dumps(records, indent=2, ensure_ascii=False) + "\n"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(content)
            temporary_path = Path(stream.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
