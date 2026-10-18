"""
Filament palette management for 3D printing color matching.

This module provides classes and functions for managing 3D printing filament databases,
with support for:
- Maker-based filtering and synonym resolution
- Material type and finish filtering (PLA, PETG, Matte, Glossy, etc.)
- Color distance matching with multiple metrics
- Owned filaments tracking for personalized recommendations
- User extensions via user-filaments.json

The FilamentPalette class offers indexed lookups (O(1)) for maker/type/finish filtering,
followed by perceptually accurate nearest-neighbor searches in LAB color space.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from functools import cmp_to_key
from pathlib import Path
from typing import (
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
    overload,
)

from color_tools.constants import ColorConstants
from color_tools.conversions import rgb_to_lab, rgb_to_hex, lab_to_lch
from color_tools._color_utils import parse_hex_colors
from color_tools.distance import (
    delta_e_2000,
    delta_e_94,
    delta_e_76,
    delta_e_cmc,
    delta_e_hyab,
    euclidean,
)
from color_tools.config import get_config
from color_tools._palette_utils import compare_distance_matches, ensure_list
from color_tools.filament_filter_criteria import FilamentFilterCriteria
from color_tools.filament_id import validate_filament_id
from color_tools.filament_load_report import FilamentLoadEvent, FilamentLoadReport
from color_tools.synonym_load_report import SynonymLoadEvent, SynonymLoadReport
from color_tools._record_swatches import (
    render_record_swatch as _render_record_swatch,
    save_record_swatch as _save_record_swatch,
)
from color_tools._filament_data import (
    load_filament_records_file,
    merge_user_filaments,
)
from color_tools._filament_sorting import filament_sort_key

logger: logging.Logger = logging.getLogger(__name__)

LabColor = tuple[float, float, float]
DistanceFunction = Callable[[LabColor, LabColor], float]
_FilamentMatch = tuple["FilamentRecord", float]


@dataclass(frozen=True)
class FilamentRecord:
    """
    Immutable record representing a 3D printing filament.

    Filament colors are pre-computed in all major color spaces for fast matching.
    Original hex text and ordered RGB components are retained. The current
    multi-color mode resolves RGB/LAB once at construction, not on later reads.

    The `other_names` field allows for alternative color names that can be used
    to find this filament.

    The `source` field tracks which JSON file this filament came from
    ('filaments.json' for core data, 'user-filaments.json' for user additions).
    User records replace system records only when their stable IDs match.
    Different filament records may share an RGB value.

    Args:
        id: Unique identifier for this filament (e.g., "bambu-lab-pla-matte-jet-black")
        maker: Manufacturer name (e.g., "Bambu Lab")
        type: Material type (e.g., "PLA", "PETG", "ABS")
        finish: Surface finish (e.g., "Matte", "Glossy", "Silk"). Optional.
        color: Human-readable color name (e.g., "Jet Black")
        hex: Original single or compound hex text. Components may be separated
            by hyphen, space, comma, underscore, slash, colon, or semicolon.
            CSS/PNG RGBA alpha is allowed but dropped from RGB components.
        td_value: Transmission-distance value when available. Values are not
            normalized percentages. Optional.
        other_names: Alternative names this filament is known by. Optional.
        source: Source JSON file this record came from (auto-set during loading)
    """

    # Identity and classification
    id: str
    maker: str
    type: str
    finish: Optional[str]
    color: str

    # Color representation (hex is primary source)
    hex: str

    # Optional metadata
    td_value: Optional[float] = None
    other_names: Optional[List[str]] = None
    source: str = "unknown.json"

    def __post_init__(self) -> None:
        """Compute derived color representations in all color spaces."""
        mode = get_config().multi_color_mode
        components = parse_hex_colors(self.hex)
        if mode == "last":
            rgb = components[-1]
        elif mode == "srgb_mean":
            count = len(components)
            rgb = (
                round(sum(component[0] for component in components) / count),
                round(sum(component[1] for component in components) / count),
                round(sum(component[2] for component in components) / count),
            )
        else:
            rgb = components[0]
        object.__setattr__(self, "rgb_components", components)
        object.__setattr__(self, "rgb", rgb)
        object.__setattr__(self, "lab", rgb_to_lab(rgb))

    # Derived color spaces (computed in __post_init__)
    rgb: Tuple[int, int, int] = field(init=False)
    lab: Tuple[float, float, float] = field(init=False)
    rgb_components: tuple[tuple[int, int, int], ...] = field(init=False)

    @property
    def effective_hex(self) -> str:
        """Normalized single-color hex derived from the captured effective RGB."""
        return rgb_to_hex(self.rgb)

    def to_swatch_png(
        self,
        *,
        width: int = 64,
        height: int = 64,
        mode: Literal["solid", "blocks", "gradient"] = "solid",
    ) -> bytes:
        """Render a dependency-free PNG swatch for this filament.

        Solid output uses the captured effective RGB. Blocks and gradients use
        the immutable source components in their original order without reading
        the current ambient multi-color configuration.
        """
        return _render_record_swatch(
            self.rgb,
            self.rgb_components,
            width=width,
            height=height,
            mode=mode,
        )

    def save_swatch_png(
        self,
        path: str | Path,
        *,
        width: int = 64,
        height: int = 64,
        mode: Literal["solid", "blocks", "gradient"] = "solid",
    ) -> Path:
        """Save a PNG swatch, create parent directories, and return its Path."""
        return _save_record_swatch(
            self.rgb,
            self.rgb_components,
            path,
            width=width,
            height=height,
            mode=mode,
        )

    def __str__(self) -> str:
        """Return a human-readable string representation of the filament."""
        return get_canonical_filament_name(
            maker=self.maker,
            type_name=self.type,
            finish=self.finish,
            color=self.color,
            hex_value=self.hex,
        )


@overload
def load_filaments(
    json_path: Path | str | None = None,
    *,
    include_report: Literal[False] = False,
) -> List[FilamentRecord]: ...


@overload
def load_filaments(
    json_path: Path | str | None = None,
    *,
    include_report: Literal[True],
) -> tuple[List[FilamentRecord], FilamentLoadReport]: ...


def load_filaments(
    json_path: Path | str | None = None,
    *,
    include_report: bool = False,
) -> List[FilamentRecord] | tuple[List[FilamentRecord], FilamentLoadReport]:
    """Load and merge filaments, optionally returning structured changes.

    A user record with an existing ID replaces that complete system record.
    Duplicate colors and product descriptions are allowed; IDs alone define
    record identity. The effective records are returned in canonical
    case-insensitive maker, type, finish, color, and ID order.
    """
    if json_path is None:
        data_dir = Path(__file__).parent / "data"
        database_path = data_dir / ColorConstants.FILAMENTS_JSON_FILENAME
    else:
        database_path = Path(json_path)
        if database_path.is_dir():
            data_dir = database_path
            database_path /= ColorConstants.FILAMENTS_JSON_FILENAME
        else:
            data_dir = database_path.parent

    system_records = load_filament_records_file(database_path)
    records = system_records
    user_records: list[FilamentRecord] = []
    events: tuple[FilamentLoadEvent, ...] = ()

    user_path = data_dir / ColorConstants.USER_FILAMENTS_JSON_FILENAME
    if user_path.exists():
        user_records = load_filament_records_file(user_path)
        records, events = merge_user_filaments(system_records, user_records)

    records.sort(key=filament_sort_key)

    report = FilamentLoadReport(
        system_filaments_loaded=len(system_records),
        user_filaments_loaded=len(user_records),
        total_filaments_available=len(records),
        events=events,
    )
    logger.debug("Loaded %d filaments from %s", len(records), database_path)
    if include_report:
        return records, report
    return records


def _parse_synonyms(data: object, source_file: str) -> dict[str, list[str]]:
    """Validate a maker-synonym JSON object."""
    if not isinstance(data, dict):
        raise ValueError(
            f"Expected object of maker synonyms at root level in {source_file}"
        )
    result: dict[str, list[str]] = {}
    seen_makers: set[str] = set()
    for maker_value, synonyms_value in cast(dict[object, object], data).items():
        if (
            not isinstance(maker_value, str)
            or not maker_value.strip()
            or maker_value != maker_value.strip()
        ):
            raise ValueError(f"Invalid maker name {maker_value!r} in {source_file}")
        maker_key = maker_value.casefold()
        if maker_key in seen_makers:
            raise ValueError(
                f"Duplicate maker name {maker_value!r} in {source_file}; "
                "maker names are case-insensitive"
            )
        seen_makers.add(maker_key)
        if not isinstance(synonyms_value, list):
            raise ValueError(
                f"Synonyms for {maker_value!r} in {source_file} must be an array"
            )
        parsed: list[str] = []
        seen: set[str] = set()
        for synonym in cast(list[object], synonyms_value):
            if (
                not isinstance(synonym, str)
                or not synonym.strip()
                or synonym != synonym.strip()
            ):
                raise ValueError(
                    f"Synonyms for {maker_value!r} in {source_file} must be non-empty strings without surrounding whitespace"
                )
            key = synonym.casefold()
            if key in seen:
                raise ValueError(
                    f"Duplicate synonym {synonym!r} for {maker_value!r} in {source_file}"
                )
            seen.add(key)
            parsed.append(synonym)
        result[maker_value] = parsed
    return result


def _merge_user_synonyms(
    system_synonyms: dict[str, list[str]],
    user_synonyms: dict[str, list[str]],
    known_makers: list[str],
) -> tuple[dict[str, list[str]], tuple[SynonymLoadEvent, ...]]:
    loaded_makers: dict[str, str] = {}
    for maker in known_makers:
        loaded_makers.setdefault(maker.casefold(), maker)
    canonical_makers = dict(loaded_makers)
    for maker in system_synonyms:
        canonical_makers.setdefault(maker.casefold(), maker)
    merged: dict[str, list[str]] = {}
    alias_owners: dict[str, str] = {}

    def resolve_user_maker(maker: str) -> str:
        canonical = loaded_makers.get(maker.casefold())
        if canonical is None:
            raise ValueError(
                f"Unknown maker {maker!r} in {ColorConstants.USER_SYNONYMS_JSON_FILENAME}; "
                "maker keys must match "
                "a maker in the merged filament database"
            )
        return canonical

    def add_alias(alias: str, canonical: str, source: str) -> bool:
        alias_key = alias.casefold()
        canonical_collision = canonical_makers.get(alias_key)
        if canonical_collision is not None:
            raise ValueError(
                f"Synonym {alias!r} for {canonical!r} in {source} conflicts "
                f"with canonical maker {canonical_collision!r}"
            )
        owner = alias_owners.get(alias_key)
        if owner is not None:
            if owner != canonical:
                raise ValueError(
                    f"Synonym {alias!r} for {canonical!r} in {source} is already "
                    f"assigned to maker {owner!r}"
                )
            return False
        alias_owners[alias_key] = canonical
        return True

    for maker, values in system_synonyms.items():
        canonical = canonical_makers[maker.casefold()]
        if canonical in merged:
            raise ValueError(
                f"Duplicate maker name {maker!r} in "
                f"{ColorConstants.MAKER_SYNONYMS_JSON_FILENAME}; maker names are case-insensitive"
            )
        merged[canonical] = []
        for value in values:
            if add_alias(value, canonical, ColorConstants.MAKER_SYNONYMS_JSON_FILENAME):
                merged[canonical].append(value)

    events: list[SynonymLoadEvent] = []
    for maker, user_values in user_synonyms.items():
        canonical = resolve_user_maker(maker)
        previous = merged.get(canonical)
        if previous is None:
            effective: list[str] = []
            action: Literal["added", "unchanged", "extended"] = "added"
        else:
            effective = list(previous)
            action = "unchanged"
        for value in user_values:
            if add_alias(value, canonical, ColorConstants.USER_SYNONYMS_JSON_FILENAME):
                effective.append(value)
                if previous is not None:
                    action = "extended"
        merged[canonical] = effective
        events.append(
            SynonymLoadEvent(
                action,
                canonical,
                tuple(user_values),
                tuple(previous or ()),
                tuple(effective),
            )
        )
    return merged, tuple(events)


@overload
def load_maker_synonyms(
    json_path: Path | str | None = None,
    *,
    include_report: Literal[False] = False,
) -> Dict[str, List[str]]: ...


@overload
def load_maker_synonyms(
    json_path: Path | str | None = None,
    *,
    include_report: Literal[True],
) -> tuple[Dict[str, List[str]], SynonymLoadReport]: ...


def load_maker_synonyms(
    json_path: Path | str | None = None,
    *,
    include_report: bool = False,
) -> Dict[str, List[str]] | tuple[Dict[str, List[str]], SynonymLoadReport]:
    """Load additive, case-insensitive maker synonyms with reporting.

    Maker keys must identify a maker in the merged filament database. Synonyms
    are globally unique after case folding, cannot duplicate a canonical maker
    name, and never remove bundled synonyms.
    """
    if json_path is None:
        data_dir = Path(__file__).parent / "data"
        database_path = data_dir / ColorConstants.MAKER_SYNONYMS_JSON_FILENAME
    else:
        database_path = Path(json_path)
        if database_path.is_dir():
            data_dir = database_path
            database_path /= ColorConstants.MAKER_SYNONYMS_JSON_FILENAME
        else:
            data_dir = database_path.parent

    try:
        with database_path.open("r", encoding="utf-8") as file:
            system_synonyms = _parse_synonyms(json.load(file), str(database_path))
    except FileNotFoundError:
        system_synonyms = {}
    synonyms = system_synonyms
    user_synonyms: dict[str, list[str]] = {}
    events: tuple[SynonymLoadEvent, ...] = ()
    user_path = data_dir / ColorConstants.USER_SYNONYMS_JSON_FILENAME
    if user_path.exists():
        with user_path.open("r", encoding="utf-8") as file:
            user_synonyms = _parse_synonyms(json.load(file), str(user_path))
    filament_records = load_filaments(data_dir)
    known_makers = list(dict.fromkeys(record.maker for record in filament_records))
    synonyms, events = _merge_user_synonyms(
        system_synonyms,
        user_synonyms,
        known_makers,
    )

    report = SynonymLoadReport(
        system_makers_loaded=len(system_synonyms),
        user_makers_loaded=len(user_synonyms),
        total_makers_available=len(synonyms),
        events=events,
    )
    if include_report:
        return synonyms, report
    return synonyms


def get_canonical_filament_name(
    maker: str,
    type_name: str,
    finish: str | None,
    color: str,
    hex_value: str,
) -> str:
    """Return the canonical human-readable display name for a filament.

    The format is ``"{maker} {type}[ {finish}] - {color} ({hex})"``.
    The finish and its preceding space are omitted when ``finish`` is
    ``None`` or empty. Input values are otherwise preserved unchanged.

    This function does not perform any validation or normalization of the
    input values; it simply formats them into the canonical display name.
    Those responsibilities lie with the caller.

    Args:
        maker: Filament manufacturer.
        type_name: Filament material or type.
        finish: Optional filament finish.
        color: Filament color name.
        hex_value: Original hexadecimal color value.

    Returns:
        The formatted filament display name.
    """
    finish_str = f" {finish}" if finish else ""
    return f"{maker} {type_name}{finish_str} - {color} ({hex_value})"


def load_owned_filaments(json_path: Path | str | None = None) -> Set[str]:
    """
    Load owned filament IDs from JSON file.

    Loads a list of filament IDs that the user owns from owned-filaments.json.
    This file is optional - if it doesn't exist, an empty set is returned.

    The JSON format is::

        {
            "owned_filaments": ["id1", "id2", "id3"]
        }

    Args:
        json_path: Path to directory containing owned-filaments.json, or path to
                   specific owned filaments JSON file. If None, looks for
                   owned-filaments.json in the package's data/ directory.

    Returns:
        Set of canonical owned filament IDs (empty set if file doesn't exist).

    Raises:
        ValueError: If the document shape or any owned filament ID is invalid.
    """
    if json_path is None:
        # Default: look in package's data/ directory
        data_dir = Path(__file__).parent / "data"
        json_path = data_dir / ColorConstants.OWNED_FILAMENTS_JSON_FILENAME
    else:
        json_path = Path(json_path)
        # If it's a directory, append the filename
        if json_path.is_dir():
            json_path = json_path / ColorConstants.OWNED_FILAMENTS_JSON_FILENAME

    # Return empty set if file doesn't exist (optional file)
    if not json_path.exists():
        return set()

    # Load owned filaments
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate structure
    if not isinstance(data, dict) or "owned_filaments" not in data:
        raise ValueError(
            f"Expected {{'owned_filaments': [...]}} structure in {json_path}"
        )

    data_mapping = cast(dict[str, object], data)
    unknown_fields = data_mapping.keys() - {"owned_filaments"}
    if unknown_fields:
        raise ValueError(
            f"Unknown field(s) in {json_path}: {', '.join(sorted(unknown_fields))}"
        )
    owned_ids = data_mapping["owned_filaments"]
    if not isinstance(owned_ids, list):
        raise ValueError(f"Expected 'owned_filaments' to be a list in {json_path}")
    owned_items = cast(list[object], owned_ids)
    if not all(isinstance(item, str) for item in owned_items):
        raise ValueError(f"Expected owned filament IDs to be strings in {json_path}")

    validated_ids: set[str] = set()
    for index, item in enumerate(cast(list[str], owned_items)):
        try:
            filament_id = validate_filament_id(item)
        except ValueError as error:
            raise ValueError(
                f"Invalid owned filament ID at index {index} in {json_path}: {error}"
            ) from error
        if filament_id in validated_ids:
            raise ValueError(
                f"Duplicate owned filament ID {filament_id!r} in {json_path}"
            )
        validated_ids.add(filament_id)

    return validated_ids


def save_owned_filaments(
    owned_ids: Set[str], json_path: Path | str | None = None
) -> None:
    """
    Save owned filament IDs to JSON file.

    Saves the list of owned filament IDs to owned-filaments.json.

    Args:
        owned_ids: Set of filament IDs to save
        json_path: Path to directory for owned-filaments.json, or path to
                   specific file. If None, saves to package's data/ directory.
    """
    if json_path is None:
        # Default: save to package's data/ directory
        data_dir = Path(__file__).parent / "data"
        json_path = data_dir / ColorConstants.OWNED_FILAMENTS_JSON_FILENAME
    else:
        json_path = Path(json_path)
        # If it's a directory, append the filename
        if json_path.is_dir():
            json_path = json_path / ColorConstants.OWNED_FILAMENTS_JSON_FILENAME

    # Validate and sort IDs for consistent output
    validated_ids: list[str] = []
    for filament_id in owned_ids:
        try:
            validated_ids.append(validate_filament_id(filament_id))
        except ValueError as error:
            raise ValueError(
                f"Cannot save invalid owned filament ID {filament_id!r}: {error}"
            ) from error
    sorted_ids = sorted(validated_ids)

    # Create data structure
    data = {"owned_filaments": sorted_ids}

    # Save to file
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# Minimum LCH chroma value below which hue is considered undefined (achromatic).
# Colors with chroma below this threshold skip hue-delta filtering.
_ACHROMATIC_CHROMA_THRESHOLD = 5.0


def _hue_angular_delta(h1: float, h2: float) -> float:
    """Compute the shortest angular distance between two hue angles (0-360°)."""
    delta = abs(h1 - h2) % 360.0
    return min(delta, 360.0 - delta)


def _filter_by_hue(
    candidates: List[FilamentRecord],
    target_lab: Tuple[float, float, float],
    max_hue_delta: float,
) -> List[FilamentRecord]:
    """
    Filter filament candidates by LCH hue angle proximity.

    Achromatic targets (LCH chroma < threshold) and achromatic candidates are
    excluded from hue filtering and are always retained.

    Args:
        candidates: List of FilamentRecord to filter.
        target_lab: Target color in LAB space.
        max_hue_delta: Maximum allowed hue angle difference in degrees.

    Returns:
        Filtered list of FilamentRecord objects.
    """
    target_lch = lab_to_lch(target_lab)
    target_chroma, target_hue = target_lch[1], target_lch[2]

    # If the target itself is achromatic, hue filtering is meaningless — skip it
    if target_chroma < _ACHROMATIC_CHROMA_THRESHOLD:
        return candidates

    result: List[FilamentRecord] = []
    for rec in candidates:
        rec_lch = lab_to_lch(rec.lab)
        rec_chroma, rec_hue = rec_lch[1], rec_lch[2]
        # Always keep achromatic candidates (their hue is undefined)
        if rec_chroma < _ACHROMATIC_CHROMA_THRESHOLD:
            result.append(rec)
            continue
        if _hue_angular_delta(target_hue, rec_hue) <= max_hue_delta:
            result.append(rec)

    return result


def _resolve_distance_function(
    metric: str, cmc_l: float, cmc_c: float
) -> DistanceFunction:
    """Resolve a supported metric name to its LAB distance function."""
    metric_name = metric.casefold()
    if metric_name in ("de2000", "ciede2000"):
        return delta_e_2000
    if metric_name in ("de94", "cie94"):
        return delta_e_94
    if metric_name in ("de76", "cie76"):
        return delta_e_76
    if metric_name == "euclidean":
        return euclidean
    if metric_name in ("cmc", "decmc"):
        return lambda lab1, lab2: delta_e_cmc(lab1, lab2, l=cmc_l, c=cmc_c)
    if metric_name == "hyab":
        return delta_e_hyab
    raise ValueError(
        "Unknown metric. Use 'euclidean'/'de76'/'de94'/'de2000'/'cmc'/'hyab'."
    )


class FilamentPalette:
    """
    Filament palette with multiple indexing strategies for fast lookup.

    Similar to Palette, but designed for 3D printing filaments which have
    additional properties (maker, type, finish) that we want to search by.

    The indices allow for fast filtering: "Show me all Bambu Lab PLA Matte filaments"
    becomes a simple dictionary lookup instead of scanning the whole list! 📇

    Supports maker synonyms: you can search for "Bambu" and it will find "Bambu Lab"
    filaments automatically.
    """

    def __init__(
        self,
        records: List[FilamentRecord],
        maker_synonyms: Optional[Dict[str, List[str]]] = None,
        owned_filaments: Optional[Set[str]] = None,
    ) -> None:
        self.records = records
        self.maker_synonyms: Dict[str, List[str]] = maker_synonyms or {}
        self.owned_filaments: Set[str] = (
            owned_filaments if owned_filaments is not None else set()
        )

        # Create various lookup indices (note: Lists, not single items!)
        # Multiple filaments can share the same maker/type/color
        self._by_maker: Dict[str, List[FilamentRecord]] = {}
        self._by_type: Dict[str, List[FilamentRecord]] = {}
        self._by_color: Dict[str, List[FilamentRecord]] = {}
        self._by_rgb: Dict[Tuple[int, int, int], List[FilamentRecord]] = {}
        self._by_finish: Dict[str, List[FilamentRecord]] = {}
        self._by_id: Dict[str, FilamentRecord] = {}
        self._canonical_makers: dict[str, str] = {}

        # Build indices
        for rec in records:
            # By maker
            if rec.maker not in self._by_maker:
                self._by_maker[rec.maker] = []
            self._by_maker[rec.maker].append(rec)
            self._canonical_makers.setdefault(rec.maker.strip().casefold(), rec.maker)

            # By type
            if rec.type not in self._by_type:
                self._by_type[rec.type] = []
            self._by_type[rec.type].append(rec)

            # By color (case-insensitive)
            color_key = rec.color.lower()
            if color_key not in self._by_color:
                self._by_color[color_key] = []
            self._by_color[color_key].append(rec)

            # By RGB
            rgb = rec.rgb
            if rgb not in self._by_rgb:
                self._by_rgb[rgb] = []
            self._by_rgb[rgb].append(rec)

            # By finish (if present)
            if rec.finish:
                if rec.finish not in self._by_finish:
                    self._by_finish[rec.finish] = []
                self._by_finish[rec.finish].append(rec)

            # By ID (unique lookup for owned filaments management)
            if rec.id:
                self._by_id[rec.id] = rec

    def _expand_maker_names(self, makers: List[str]) -> Set[str]:
        """
        Expand maker names to include synonyms.

        For example, if "Bambu" is provided and "Bambu Lab" has that synonym,
        this will return {"Bambu Lab"}.

        Args:
            makers: List of maker names or synonyms to expand

        Returns:
            Set of all canonical names and synonyms that match
        """
        expanded: set[str] = set()
        for maker in makers:
            normalized_maker = maker.strip().casefold()
            canonical_match = self._canonical_makers.get(normalized_maker)
            matched = canonical_match is not None
            if canonical_match is not None:
                expanded.add(canonical_match)

            # Match synonyms case-insensitively.
            for canonical, synonyms in self.maker_synonyms.items():
                normalized_synonyms = {
                    synonym.strip().casefold() for synonym in synonyms
                }
                if normalized_maker in normalized_synonyms:
                    expanded.add(canonical)
                    matched = True
            if not matched:
                expanded.add(maker)

        return expanded

    def _normalize_filter_values(
        self, value: Optional[Union[str, List[str]]]
    ) -> Optional[Set[str]]:
        """
        Convert a filter value (str or list) to a set for fast lookups.

        Args:
            value: A string, a list of strings, or None.

        Returns:
            A set of strings, or None if the input was None.
        """
        if value is None:
            return None
        if isinstance(value, str):
            return {value.strip().casefold()}
        return {item.strip().casefold() for item in value}

    def _expand_criteria_makers(
        self,
        criteria: FilamentFilterCriteria | None,
    ) -> FilamentFilterCriteria | None:
        """Return criteria with maker synonyms expanded by this palette."""
        if criteria is None or criteria.maker_values is None:
            return criteria
        expanded_makers = self._expand_maker_names(list(criteria.maker_values))
        return FilamentFilterCriteria(
            maker=expanded_makers,
            type_name=criteria.type_name_values,
            finish=criteria.finish_values,
            color=criteria.color_values,
            has_td=criteria.has_td,
        )

    def _filter_records(
        self,
        include: FilamentFilterCriteria | None,
        exclude: FilamentFilterCriteria | None,
        owned: bool | None,
    ) -> list[FilamentRecord]:
        """Apply ownership, inclusion, and exclusion criteria."""
        use_owned = bool(self.owned_filaments) if owned is None else owned
        results = (
            [record for record in self.records if record.id in self.owned_filaments]
            if use_owned
            else list(self.records)
        )

        expanded_include = self._expand_criteria_makers(include)
        expanded_exclude = self._expand_criteria_makers(exclude)
        if expanded_include is not None and not expanded_include.is_empty:
            results = [
                record
                for record in results
                if expanded_include.matches(
                    record.maker,
                    record.type,
                    record.finish,
                    record.color,
                    record.td_value,
                )
            ]
        if expanded_exclude is not None and not expanded_exclude.is_empty:
            results = [
                record
                for record in results
                if not expanded_exclude.matches(
                    record.maker,
                    record.type,
                    record.finish,
                    record.color,
                    record.td_value,
                )
            ]
        return results

    @classmethod
    def load_default(cls, json_path: Path | str | None = None) -> "FilamentPalette":
        """
        Load the default filament palette from the package data.

        Convenience method for quick loading without worrying about paths.
        Also loads maker synonyms and owned filaments automatically.

        Auto-detects owned filaments: If owned-filaments.json exists and contains IDs,
        owned filtering will be the default behavior in filter/nearest methods.

        Args:
            json_path: Optional custom data directory containing the system and
                user JSON files.
        """
        owned = load_owned_filaments(json_path)
        return cls(
            load_filaments(json_path),
            load_maker_synonyms(json_path),
            owned,
        )

    def find_by_maker(self, maker: Union[str, List[str]]) -> List[FilamentRecord]:
        """
        Find all filaments by a single maker or a list of makers.

        Supports synonyms: searching for "Bambu" will find "Bambu Lab" filaments.

        Args:
            maker: A single maker name (str) or a list of names (can use synonyms).

        Returns:
            A list of all matching FilamentRecord objects.
        """
        makers_to_find = ensure_list(maker)
        expanded_makers = self._expand_maker_names(makers_to_find)

        all_filaments: list[FilamentRecord] = []
        for m in expanded_makers:
            all_filaments.extend(self._by_maker.get(m, []))

        # Remove duplicates while preserving order
        seen: set[int] = set()
        unique_filaments: list[FilamentRecord] = []
        for filament in all_filaments:
            filament_id = id(filament)  # Use object identity
            if filament_id not in seen:
                seen.add(filament_id)
                unique_filaments.append(filament)

        return unique_filaments

    def find_by_type(self, type_name: Union[str, List[str]]) -> List[FilamentRecord]:
        """
        Find all filaments by a single type or a list of types.

        Args:
            type_name: A single filament type (str) or a list of types.

        Returns:
            A list of all matching FilamentRecord objects.
        """
        types_to_find = ensure_list(type_name)

        all_filaments: list[FilamentRecord] = []
        for t in types_to_find:
            all_filaments.extend(self._by_type.get(t, []))
        return all_filaments

    def find_by_color(self, color: str) -> List[FilamentRecord]:
        """Find all filaments by color name (case-insensitive)."""
        return self._by_color.get(color.lower(), [])

    def find_by_rgb(self, rgb: Tuple[int, int, int]) -> List[FilamentRecord]:
        """Find all filaments by exact RGB match, with user filaments prioritized."""
        matches = self._by_rgb.get(rgb, [])
        # Sort to prioritize user sources over core sources
        return sorted(
            matches,
            key=lambda r: (not r.source.startswith("user-"), r.maker, r.type, r.color),
        )

    def find_by_finish(self, finish: Union[str, List[str]]) -> List[FilamentRecord]:
        """
        Find all filaments by a single finish or a list of finishes.

        Args:
            finish: A single filament finish (str) or a list of finishes.

        Returns:
            A list of all matching FilamentRecord objects.
        """
        finishes_to_find = ensure_list(finish)

        all_filaments: list[FilamentRecord] = []
        for f in finishes_to_find:
            all_filaments.extend(self._by_finish.get(f, []))
        return all_filaments

    def filter(
        self,
        maker: Optional[Union[str, List[str]]] = None,
        type_name: Optional[Union[str, List[str]]] = None,
        finish: Optional[Union[str, List[str]]] = None,
        color: Optional[str] = None,
        owned: Optional[bool] = None,
        has_td: bool | None = None,
    ) -> List[FilamentRecord]:
        """
        Filter filaments by multiple criteria.

        This is like SQL WHERE clauses! Start with all records, then filter
        down by each criterion that's provided. Maker, type, and finish
        can accept a single string or a list of strings.

        Supports maker synonyms: filtering by "Bambu" will include "Bambu Lab".

        Auto-detects owned filtering: If owned-filaments.json exists with IDs,
        defaults to owned filaments only unless owned=False is explicitly passed.

        Args:
            maker: A maker name or list of maker names (can use synonyms).
            type_name: A filament type or list of types.
            finish: A filament finish or list of finishes.
            color: A single color name to match (case-insensitive).
            owned: Filter to owned filaments only. None (default) = auto-detect,
                   True = owned only, False = all filaments.
            has_td: True selects records with TD values, False selects records
                    without TD values, and None does not filter by TD.

        Returns:
            A list of FilamentRecord objects matching the criteria.
        """
        include = FilamentFilterCriteria(
            maker=maker,
            type_name=type_name,
            finish=finish,
            color=color if color else None,
            has_td=has_td,
        )
        return self._filter_records(include, None, owned)

    def filter_by_criteria(
        self,
        include: FilamentFilterCriteria | None = None,
        exclude: FilamentFilterCriteria | None = None,
        *,
        owned: bool | None = None,
    ) -> list[FilamentRecord]:
        """Filter filaments with reusable inclusion and exclusion criteria.

        Active fields within each criterion use AND semantics, while multiple
        values within a field use OR semantics. An exclusion removes a record
        only when the complete exclusion criterion matches.
        """
        return self._filter_records(include, exclude, owned)

    def nearest_filament(
        self,
        target_rgb: Tuple[int, int, int],
        metric: str = "de2000",
        *,
        maker: Optional[Union[str, List[str]]] = None,
        type_name: Optional[Union[str, List[str]]] = None,
        finish: Optional[Union[str, List[str]]] = None,
        owned: Optional[bool] = None,
        cmc_l: float = ColorConstants.CMC_L_DEFAULT,
        cmc_c: float = ColorConstants.CMC_C_DEFAULT,
        max_hue_delta: Optional[float] = None,
    ) -> Tuple[FilamentRecord, float]:
        """
        Find nearest filament by color similarity, with optional filters.

        The killer feature for 3D printing! "I want this exact color... what
        filament should I buy?" 🎨🖨️

        Auto-detects owned filtering: If owned-filaments.json exists with IDs,
        defaults to searching owned filaments only unless owned=False is explicitly passed.

        Args:
            target_rgb: Target RGB color tuple.
            metric: Distance metric - 'euclidean', 'de76', 'de94', 'de2000', 'cmc'.
            maker: Optional maker name or list of names to filter by. Use "*" to ignore filter.
            type_name: Optional filament type or list of types to filter by. Use "*" to ignore filter.
            finish: Optional filament finish or list of finishes to filter by. Use "*" to ignore filter.
            owned: Filter to owned filaments only. None (default) = auto-detect,
                   True = owned only, False = all filaments.
            cmc_l, cmc_c: Parameters for CMC metric.
            max_hue_delta: Maximum allowed hue angle difference in degrees (LCH hue, 0-180).
                           Filters out candidates whose hue differs by more than this amount.
                           Achromatic targets (chroma < 5) skip hue filtering automatically.
                           Example: 30.0 keeps results within the same hue family.

        Returns:
            (nearest_filament_record, distance) tuple.
        """
        best_rec, best_d = self.nearest_filaments(
            target_rgb,
            metric,
            1,
            maker=maker,
            type_name=type_name,
            finish=finish,
            owned=owned,
            cmc_l=cmc_l,
            cmc_c=cmc_c,
            max_hue_delta=max_hue_delta,
        )[0]
        logger.debug(
            "nearest_filament: target=%s metric=%s → %s %s %s (%.4f)",
            target_rgb,
            metric,
            best_rec.maker,
            best_rec.type,
            best_rec.color,
            best_d,
        )
        return best_rec, best_d

    def nearest_filaments(
        self,
        target_rgb: Tuple[int, int, int],
        metric: str = "de2000",
        count: int = 5,
        *,
        maker: Optional[Union[str, List[str]]] = None,
        type_name: Optional[Union[str, List[str]]] = None,
        finish: Optional[Union[str, List[str]]] = None,
        owned: Optional[bool] = None,
        cmc_l: float = ColorConstants.CMC_L_DEFAULT,
        cmc_c: float = ColorConstants.CMC_C_DEFAULT,
        max_hue_delta: Optional[float] = None,
    ) -> List[Tuple[FilamentRecord, float]]:
        """
        Find nearest N filaments by color similarity, with optional filters.

        Similar to nearest_filament but returns multiple results sorted by distance.

        Auto-detects owned filtering: If owned-filaments.json exists with IDs,
        defaults to searching owned filaments only unless owned=False is explicitly passed.

        Args:
            target_rgb: Target RGB color tuple.
            metric: Distance metric - 'euclidean', 'de76', 'de94', 'de2000', 'cmc'.
            count: Number of results to return (default: 5, max: 50)
            maker: Optional maker name or list of names to filter by. Use "*" to ignore filter.
            type_name: Optional filament type or list of types to filter by. Use "*" to ignore filter.
            finish: Optional filament finish or list of finishes to filter by. Use "*" to ignore filter.
            owned: Filter to owned filaments only. None (default) = auto-detect,
                   True = owned only, False = all filaments.
            cmc_l, cmc_c: Parameters for CMC metric.
            max_hue_delta: Maximum allowed hue angle difference in degrees (LCH hue, 0-180).
                           Filters out candidates whose hue differs by more than this amount.
                           Achromatic targets (chroma < 5) skip hue filtering automatically.
                           Example: 30.0 keeps results within the same hue family.

        Returns:
            List of (filament_record, distance) tuples sorted by distance (closest first).
        """
        maker_filter = None if maker == "*" else maker
        type_filter = None if type_name == "*" else type_name
        finish_filter = None if finish == "*" else finish
        include = FilamentFilterCriteria(
            maker=maker_filter,
            type_name=type_filter,
            finish=finish_filter,
        )
        return self.nearest_filaments_by_criteria(
            target_rgb,
            metric,
            count,
            include=include,
            owned=owned,
            cmc_l=cmc_l,
            cmc_c=cmc_c,
            max_hue_delta=max_hue_delta,
        )

    def nearest_filament_by_criteria(
        self,
        target_rgb: tuple[int, int, int],
        metric: str = "de2000",
        *,
        include: FilamentFilterCriteria | None = None,
        exclude: FilamentFilterCriteria | None = None,
        owned: bool | None = None,
        cmc_l: float = ColorConstants.CMC_L_DEFAULT,
        cmc_c: float = ColorConstants.CMC_C_DEFAULT,
        max_hue_delta: float | None = None,
    ) -> tuple[FilamentRecord, float]:
        """Find the nearest filament using reusable inclusion and exclusion criteria."""
        best_record, best_distance = self.nearest_filaments_by_criteria(
            target_rgb,
            metric,
            1,
            include=include,
            exclude=exclude,
            owned=owned,
            cmc_l=cmc_l,
            cmc_c=cmc_c,
            max_hue_delta=max_hue_delta,
        )[0]
        logger.debug(
            "nearest_filament_by_criteria: target=%s metric=%s → %s %s %s (%.4f)",
            target_rgb,
            metric,
            best_record.maker,
            best_record.type,
            best_record.color,
            best_distance,
        )
        return best_record, best_distance

    def nearest_filaments_by_criteria(
        self,
        target_rgb: tuple[int, int, int],
        metric: str = "de2000",
        count: int = 5,
        *,
        include: FilamentFilterCriteria | None = None,
        exclude: FilamentFilterCriteria | None = None,
        owned: bool | None = None,
        cmc_l: float = ColorConstants.CMC_L_DEFAULT,
        cmc_c: float = ColorConstants.CMC_C_DEFAULT,
        max_hue_delta: float | None = None,
    ) -> list[tuple[FilamentRecord, float]]:
        """Find the nearest filaments using reusable inclusion and exclusion criteria."""
        limited_count = max(1, min(count, 50))
        target_lab = rgb_to_lab(target_rgb)
        candidates = self.filter_by_criteria(include, exclude, owned=owned)
        if not candidates:
            raise ValueError("No filaments match the specified filters")

        if max_hue_delta is not None:
            candidates = _filter_by_hue(candidates, target_lab, max_hue_delta)
            if not candidates:
                raise ValueError(
                    f"No filaments found within {max_hue_delta}° hue of the target color. "
                    "Try a larger --max-hue-delta value."
                )

        distance_fn = _resolve_distance_function(metric, cmc_l, cmc_c)
        results: list[_FilamentMatch] = []
        for record in candidates:
            try:
                distance = distance_fn(target_lab, record.lab)
                results.append((record, distance))
            except (ArithmeticError, ValueError):
                continue

        if not results:
            raise ValueError("No valid filaments found")

        results.sort(key=cmp_to_key(compare_distance_matches))
        return results[:limited_count]

    @property
    def makers(self) -> List[str]:
        """Get sorted list of all makers."""
        return sorted(self._by_maker.keys())

    @property
    def types(self) -> List[str]:
        """Get sorted list of all types."""
        return sorted(self._by_type.keys())

    @property
    def finishes(self) -> List[str]:
        """Get sorted list of all finishes."""
        return sorted(self._by_finish.keys())

    def get_filament_by_id(self, filament_id: str) -> Optional[FilamentRecord]:
        """
        Get a filament by its ID.

        Args:
            filament_id: Filament ID to look up

        Returns:
            FilamentRecord if found, None otherwise
        """
        return self._by_id.get(filament_id)

    def list_owned(self) -> List[FilamentRecord]:
        """
        Get list of all owned filament records.

        Returns:
            List of FilamentRecord objects that are marked as owned (sorted by maker, type, color)
        """
        owned_records = [
            self._by_id[fid] for fid in self.owned_filaments if fid in self._by_id
        ]
        # Sort for consistent output
        return sorted(owned_records, key=lambda r: (r.maker, r.type, r.color))

    def add_owned(self, filament_id: str, json_path: Path | str | None = None) -> None:
        """
        Add a filament ID to the owned list and save to file.

        Args:
            filament_id: Filament ID to add
            json_path: Optional path to owned-filaments.json file (uses default if None)

        Raises:
            ValueError: If the filament ID doesn't exist in the database
        """
        if filament_id not in self._by_id:
            raise ValueError(f"Filament ID '{filament_id}' not found in database")

        self.owned_filaments.add(filament_id)
        save_owned_filaments(self.owned_filaments, json_path)

    def remove_owned(
        self, filament_id: str, json_path: Path | str | None = None
    ) -> None:
        """
        Remove a filament ID from the owned list and save to file.

        Args:
            filament_id: Filament ID to remove
            json_path: Optional path to owned-filaments.json file (uses default if None)

        Raises:
            ValueError: If the filament ID is not in the owned list
        """
        if filament_id not in self.owned_filaments:
            raise ValueError(f"Filament ID '{filament_id}' is not in owned list")

        self.owned_filaments.remove(filament_id)
        save_owned_filaments(self.owned_filaments, json_path)

    def save_owned(self, json_path: Path | str | None = None) -> None:
        """
        Save the current owned filaments list to file.

        Useful after programmatic modifications to owned_filaments set.

        Args:
            json_path: Optional path to owned-filaments.json file (uses default if None)
        """
        save_owned_filaments(self.owned_filaments, json_path)
