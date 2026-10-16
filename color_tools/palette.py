"""
Color palette management with fast lookup.

This module provides:
1. Data class for colors (ColorRecord)
2. Functions to load color data from JSON with user override support
3. Palette class with multiple indices for O(1) lookups
4. Nearest-color search using various distance metrics

For filament management, see color_tools.filament_palette module.

The Palette class is like a database with multiple indexes - you can
search by name, RGB, HSL, etc. and get instant results!

User colors contain authored names and hex values. They replace system colors
by normalized name, append otherwise, and are reported through structured load
events.

Example:
    >>> from color_tools import Palette
    >>> 
    >>> # Load CSS color database
    >>> palette = Palette.load_default()
    >>> print(f"Loaded {len(palette.colors)} CSS colors")
    Loaded 148 CSS colors
    >>> 
    >>> # Find exact color by name
    >>> coral = palette.get_by_name("coral")
    >>> print(f"Coral: RGB{coral.rgb} (#{coral.hex})")
    Coral: RGB(255, 127, 80) (#FF7F50)
    >>> 
    >>> # Find nearest color to custom RGB
    >>> custom_orange = (255, 140, 60)
    >>> nearest, distance = palette.nearest_color(custom_orange)
    >>> print(f"Nearest to RGB{custom_orange}: {nearest.name} (ΔE: {distance:.1f})")
    Nearest to RGB(255, 140, 60): darkorange (ΔE: 7.2)
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from functools import cmp_to_key
from typing import Dict, List, Literal, Optional, Tuple, TypedDict, cast, overload
import json
import logging
from pathlib import Path
from collections.abc import Iterable

from color_tools.constants import ColorConstants
from color_tools.conversions import rgb_to_lab, rgb_to_hsl, rgb_to_hex, lab_to_lch
from color_tools.distance import euclidean, hsl_euclidean, hue_diff_deg, delta_e_2000, delta_e_94, delta_e_76, delta_e_cmc, delta_e_hyab
from color_tools._palette_utils import compare_distance_matches, get_palette_files, rounded_key, should_prefer_source
from color_tools._palette_document import parse_indexed_palette_document
from color_tools._color_utils import parse_hex, validate_rgb
from color_tools.color_load_report import ColorLoadEvent, ColorLoadReport
from color_tools._record_swatches import (
    render_record_swatch as _render_record_swatch,
    save_record_swatch as _save_record_swatch,
)

# Compatibility alias retained for callers that imported the historical helper.
_should_prefer_source = should_prefer_source
_get_palette_files = get_palette_files

# Set up logger for override tracking
logger: logging.Logger = logging.getLogger(__name__)


def _normalize_color_name(name: str) -> str:
    """Normalize a color name for matching and uniqueness checks."""
    return name.strip().casefold()


def _lch_euclidean(
    lch1: tuple[float, float, float],
    lch2: tuple[float, float, float],
) -> float:
    """Return Euclidean LCH distance with circular hue at tuple index two."""
    lightness_delta = lch1[0] - lch2[0]
    chroma_delta = lch1[1] - lch2[1]
    hue_delta = hue_diff_deg(lch1[2], lch2[2])
    return math.sqrt(
        lightness_delta * lightness_delta
        + chroma_delta * chroma_delta
        + hue_delta * hue_delta
    )
class _ColorRecordData(TypedDict):
    """Validated shape of one color record loaded from JSON."""

    name: str
    hex: str
    rgb: list[int]
    hsl: list[float]
    lab: list[float]
    lch: list[float]


# ============================================================================
# Data Classes
# ============================================================================

@dataclass(frozen=True)
class ColorRecord:
    """
    Immutable record representing a named CSS color with precomputed color space values.
    
    This dataclass is frozen (immutable) - once created, you can't change it.
    This is perfect for colors: a color IS what it IS! 🎨
    
    All color space values are precomputed and stored for fast access without
    conversion overhead. The source field tracks which JSON file provided this
    color, enabling user override detection and debugging.
    
    Attributes:
        name: Color name (e.g., "coral", "lightblue", "darkslategray")
        hex: Hex color code with # prefix (e.g., "#FF7F50")
        rgb: RGB color tuple with values 0-255 (e.g., (255, 127, 80))
        hsl: HSL color tuple (H: 0-360°, S: 0-100%, L: 0-100%)
        lab: CIE LAB color tuple (L: 0-100, a: ~-128 to +127, b: ~-128 to +127)
        lch: CIE LCH color tuple (L: 0-100, C: 0-100+, H: 0-360°)
        source: JSON filename where this record originated (default: "colors.json")
    
    Example:
        >>> from color_tools import Palette
        >>> palette = Palette.load_default()
        >>> color = palette.get_by_name("coral")
        >>> print(f"{color.name}: RGB{color.rgb}")
        coral: RGB(255, 127, 80)
        >>> print(f"LAB: {color.lab}")
        LAB: (67.29, 44.61, 49.72)
    """
    name: str
    hex: str
    rgb: Tuple[int, int, int]
    hsl: Tuple[float, float, float]   # (H°, S%, L%)
    lab: Tuple[float, float, float]   # (L*, a*, b*)
    lch: Tuple[float, float, float]   # (L*, C*, H°)
    source: str = "colors.json"      # JSON filename where this record originated

    @classmethod
    def from_rgb(
        cls,
        rgb: tuple[int, int, int] | list[int],
        *,
        name: str | None = None,
        source: str = "custom",
        auto_name: bool = False,
    ) -> ColorRecord:
        """Create a record from 8-bit RGB, computing all derived color values.

        Explicit names take precedence over auto-naming. Without either, the
        name is ``Color 1``. Auto-naming uses the built-in CSS/descriptive namer.
        Invalid channel counts, non-integers, and out-of-range values raise
        ValueError rather than being coerced or clamped.

        Example:
            >>> ColorRecord.from_rgb((255, 0, 0), auto_name=True).name
            'red'
        """
        validate_rgb(rgb)
        rgb = (rgb[0], rgb[1], rgb[2])
        if name is None:
            if auto_name:
                # Local import avoids the naming module's dependency on Palette.
                from color_tools.naming import generate_color_name
                name, _ = generate_color_name(rgb)
            else:
                name = "Color 1"
        lab = rgb_to_lab(rgb)
        return cls(
            name=name,
            hex=rgb_to_hex(rgb),
            rgb=rgb,
            hsl=rgb_to_hsl(rgb),
            lab=lab,
            lch=lab_to_lch(lab),
            source=source,
        )

    @classmethod
    def from_hex(
        cls,
        hex_code: str,
        *,
        name: str | None = None,
        source: str = "custom",
        auto_name: bool = False,
    ) -> ColorRecord:
        """Create a record from RGB/RGBA/RRGGBB/RRGGBBAA, optionally prefixed with #.

        Naming follows from_rgb(); malformed hex raises ValueError.
        Alpha uses CSS/PNG ordering and is validated then dropped.

        Example:
            >>> ColorRecord.from_hex("#f00", auto_name=True).name
            'red'
        """
        return cls.from_rgb(
            parse_hex(hex_code), name=name, source=source, auto_name=auto_name
        )

    def to_swatch_png(
        self,
        *,
        width: int = 64,
        height: int = 64,
        mode: Literal["solid", "blocks", "gradient"] = "solid",
    ) -> bytes:
        """Render a dependency-free PNG swatch for this color.

        A color record has one RGB component, so every supported mode produces
        the same solid image. Dimensions must be positive built-in integers.
        """
        return _render_record_swatch(
            self.rgb,
            (self.rgb,),
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
            (self.rgb,),
            path,
            width=width,
            height=height,
            mode=mode,
        )
    
    def __str__(self) -> str:
        """Human-readable color representation: name (#hex)"""
        return f"{self.name} ({self.hex})"


# ============================================================================
# Data Loading
# ============================================================================

def _parse_color_records(
    data: list[_ColorRecordData],
    source_file: str = "JSON data",
) -> List[ColorRecord]:
    """
    Parse a list of color data dictionaries into ColorRecord objects.
    
    This is a helper function used by load_colors() and load_palette() to avoid
    code duplication. It handles the common parsing logic for color JSON data.
    
    Args:
        data: List of dictionaries containing color data
        source_file: Name of the source file for error messages and source tracking.
                    Should be just the filename (e.g., 'colors.json', 'user-colors.json')
    
    Returns:
        List of ColorRecord objects with source field set to source_file
    
    Raises:
        KeyError: If required keys are missing from the color data
        ValueError: If color data values are invalid
    """
    records: List[ColorRecord] = []
    
    # Extract just the filename from path for source tracking
    from pathlib import Path
    source_filename = Path(source_file).name if source_file != "JSON data" else "unknown.json"
    
    for i, c in enumerate(data):
        try:
            # Parse color data (all values should be arrays/tuples)
            validate_rgb(c["rgb"])
            parse_hex(c["hex"])
            rgb = (c["rgb"][0], c["rgb"][1], c["rgb"][2])
            hsl = (float(c["hsl"][0]), float(c["hsl"][1]), float(c["hsl"][2]))
            lab = (float(c["lab"][0]), float(c["lab"][1]), float(c["lab"][2]))
            lch = (float(c["lch"][0]), float(c["lch"][1]), float(c["lch"][2]))
            
            records.append(ColorRecord(
                name=c["name"],
                hex=c["hex"],
                rgb=rgb,
                hsl=hsl,
                lab=lab,
                lch=lch,
                source=source_filename,
            ))
        except KeyError as e:
            raise ValueError(
                f"Missing required key {e} in color at index {i} in {source_file}"
            ) from e
        except (TypeError, IndexError, ValueError) as e:
            raise ValueError(
                f"Invalid color data at index {i} in {source_file}: {e}"
            ) from e
    
    return records



def _parse_user_color_records(
    data: list[object],
    source_file: str,
) -> List[ColorRecord]:
    """Build user-authored records from exactly their name and hex fields."""
    records: List[ColorRecord] = []
    expected_fields = {"name", "hex"}

    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(
                f"Invalid color data at index {index} in {source_file}: "
                "expected an object"
            )

        fields = cast(dict[object, object], item)
        if not all(isinstance(key, str) for key in fields):
            raise ValueError(
                f"Invalid color data at index {index} in {source_file}: "
                "field names must be strings"
            )

        actual_fields = cast(set[str], set(fields))
        unexpected_fields = actual_fields - expected_fields
        if unexpected_fields:
            formatted = ", ".join(sorted(unexpected_fields))
            raise ValueError(
                f"Invalid color data at index {index} in {source_file}: "
                f"unexpected field(s): {formatted}; user colors accept only "
                "'name' and 'hex' because derived values are calculated"
            )

        name = fields.get("name")
        hex_code = fields.get("hex")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"Missing or invalid 'name' in color at index {index} in {source_file}"
            )
        if not isinstance(hex_code, str):
            raise ValueError(
                f"Missing or invalid 'hex' in color at index {index} in {source_file}"
            )

        try:
            records.append(
                ColorRecord.from_hex(
                    hex_code,
                    name=name.strip(),
                    source=Path(source_file).name,
                )
            )
        except ValueError as error:
            raise ValueError(
                f"Invalid color data at index {index} in {source_file}: {error}"
            ) from error

    return records


def _merge_user_color_records(
    system_records: List[ColorRecord],
    user_records: List[ColorRecord],
) -> tuple[List[ColorRecord], tuple[ColorLoadEvent, ...]]:
    """Merge user colors sequentially by name while preserving RGB uniqueness."""
    merged = list(system_records)
    events: list[ColorLoadEvent] = []
    seen_user_names: set[str] = set()

    for index, user_record in enumerate(user_records):
        name_key = _normalize_color_name(user_record.name)
        if name_key in seen_user_names:
            raise ValueError(
                f"Duplicate user color name '{user_record.name}' at index {index} "
                f"in {user_record.source}"
            )
        seen_user_names.add(name_key)

        replacement_index = next(
            (
                record_index
                for record_index, record in enumerate(merged)
                if _normalize_color_name(record.name) == name_key
            ),
            None,
        )
        conflicting_record = next(
            (
                record
                for record_index, record in enumerate(merged)
                if record.rgb == user_record.rgb
                and record_index != replacement_index
            ),
            None,
        )
        if conflicting_record is not None:
            raise ValueError(
                f"User color '{user_record.name}' ({user_record.hex}) in "
                f"{user_record.source} conflicts with existing color "
                f"'{conflicting_record.name}' ({conflicting_record.hex}) from "
                f"{conflicting_record.source}"
            )

        if replacement_index is None:
            merged.append(user_record)
            events.append(ColorLoadEvent("added", user_record))
        else:
            replaced_record = merged[replacement_index]
            merged[replacement_index] = user_record
            events.append(
                ColorLoadEvent("overridden", user_record, replaced_record)
            )

    return merged, tuple(events)


@overload
def load_colors(
    json_path: Path | str | None = None,
    *,
    include_report: Literal[False] = False,
) -> List[ColorRecord]: ...


@overload
def load_colors(
    json_path: Path | str | None = None,
    *,
    include_report: Literal[True],
) -> tuple[List[ColorRecord], ColorLoadReport]: ...


def load_colors(
    json_path: Path | str | None = None,
    *,
    include_report: bool = False,
) -> List[ColorRecord] | tuple[List[ColorRecord], ColorLoadReport]:
    """
    Load and merge the color database, optionally returning structured changes.
    
    Loads colors from both the core colors.json file and optional user/user-colors.json
    file in the data directory. User colors replace records by normalized name
    or append in file order. Effective RGB values must remain unique.
    
    Args:
        json_path: Path to directory containing JSON files, or path to specific
                   colors JSON file. If None, looks for colors.json in the 
                   package's data/ directory.
        include_report: When true, return the records together with a typed
                        summary of user additions and name replacements.
    
    Returns:
        The merged records, or ``(records, report)`` when ``include_report`` is
        true.
    """
    if json_path is None:
        # Default: look in package's data/ directory
        data_dir = Path(__file__).parent / "data"
        json_path = data_dir / ColorConstants.COLORS_JSON_FILENAME
    else:
        json_path = Path(json_path)
        # If it's a directory, append the filename
        if json_path.is_dir():
            data_dir = json_path
            json_path = json_path / ColorConstants.COLORS_JSON_FILENAME
        else:
            data_dir = json_path.parent
    
    # Load core colors
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Data should be an array of color objects at the root level
    if not isinstance(data, list):
        raise ValueError(f"Expected array of colors at root level in {json_path}")
    
    # Parse color records using helper function
    records = _parse_color_records(
        cast(list[_ColorRecordData], data),
        str(json_path),
    )
    
    system_count = len(records)
    user_records: List[ColorRecord] = []
    events: tuple[ColorLoadEvent, ...] = ()

    # Load optional user colors from same directory
    user_json_path = data_dir / ColorConstants.USER_COLORS_JSON_FILENAME
    if user_json_path.exists():
        with open(user_json_path, "r", encoding="utf-8") as f:
            user_data = json.load(f)
        
        if not isinstance(user_data, list):
            raise ValueError(f"Expected array of colors at root level in {user_json_path}")
        
        user_records = _parse_user_color_records(
            cast(list[object], user_data),
            str(user_json_path),
        )
        records, events = _merge_user_color_records(records, user_records)
    
    logger.debug("Loaded %d CSS colors from %s", len(records), json_path)
    report = ColorLoadReport(
        system_colors_loaded=system_count,
        user_colors_loaded=len(user_records),
        total_colors_available=len(records),
        events=events,
    )
    if include_report:
        return records, report
    return records


def load_palette(name: str, json_path: "Path | str | None" = None) -> 'Palette':
    """
    Load a named retro palette from the palettes directory.
    
    Built-in palettes are loaded from ``data/palettes/{name}.json``.
    User palettes are loaded from ``data/user/palettes/user-{name}.json`` and
    must be requested with the ``user-`` prefix. Built-in and user palettes use
    the same versioned document envelope. User palette color records require
    only ``name`` and ``hex``; all other color-space values are calculated from
    the hex value when loaded. Files ending in ``example.json`` are excluded
    from palette discovery.

    Built-in system palettes are presentation-style sRGB representations for
    simulating how an image would look on the named platform. They are not
    guarantees of electrically exact output from every hardware revision,
    video standard, signal path, display, capture, specification, or emulator.
    
    Common built-in palettes include:
    - cga4: CGA 4-color palette (Palette 1, high intensity) - classic gaming!
    - cga16: CGA 16-color palette (full RGBI)
    - ega16: EGA 16-color palette (standard/default)
    - ega64: EGA 64-color palette (full 6-bit RGB)
    - vga: VGA 256-color palette (Mode 13h)
    - web: Web-safe 216-color palette (6x6x6 RGB cube)
    - gameboy: GB Studio 4-shade authoring palette
    - gameboy-dmg: Original Game Boy screen approximation
    - gameboy-light: Backlit Game Boy Light screen approximation
    - gameboy-pocket: Neutral 4-shade Game Boy Pocket grayscale
    - ti-99-4a: TI-99/4A CRT-style TMS9918 palette
    - colecovision: ColecoVision CRT-style TMS9918 palette
    - sg-1000: SG-1000 CRT-style TMS9918 palette
    - msx1: MSX1 CRT-style TMS9918 palette
    - bbc-micro: BBC Micro 8-color physical palette
    - zx-spectrum: ZX Spectrum 15-color display approximation
    - amstrad-cpc: Amstrad CPC 27-color hardware palette
    - tic80: TIC-80 default SWEETIE-16 palette
    
    Args:
        name: Palette name (e.g., 'cga4', 'ega16', 'vga', 'web', or 'user-mycustom')
        json_path: Optional custom data directory. If None, uses package default.
    
    Returns:
        Palette object loaded from the specified palette file
    
    Raises:
        FileNotFoundError: If the palette file doesn't exist
        ValueError: If the palette file is malformed or contains invalid data
    
    Example:
        >>> cga = load_palette("cga4")
        >>> color, dist = cga.nearest_color((128, 64, 200))
        >>> print(f"Nearest CGA color: {color.name}")
        
        >>> # Load custom user palette from data/user/palettes/user-mycustom.json
        >>> custom = load_palette("user-mycustom")
        >>> print(f"Loaded {len(custom.records)} colors from user palette")
    """
    # Determine data directory
    if json_path is None:
        data_dir = Path(__file__).parent / "data"
    else:
        data_dir = Path(json_path)
    
    # Determine palette file location
    palette_file = None
    
    if name.startswith("user-"):
        # User palette requested
        user_palettes_dir = data_dir / "user" / "palettes"
        palette_file = next(
            (
                path
                for path in get_palette_files(user_palettes_dir, "user-*.json")
                if path.name == f"{name}.json"
            ),
            None,
        )
    else:
        # Core palette requested
        core_palettes_dir = data_dir / "palettes"
        palette_file = next(
            (
                path
                for path in get_palette_files(core_palettes_dir, "*.json")
                if path.name == f"{name}.json"
            ),
            None,
        )
    
    if palette_file is None:
        # Build list of available palettes from both locations
        available: list[str] = []
        
        # Core palettes
        core_palettes_dir = data_dir / "palettes"
        available.extend(
            path.stem for path in get_palette_files(core_palettes_dir, "*.json")
        )
        
        # User palettes (only user-*.json files)
        user_palettes_dir = data_dir / "user" / "palettes"
        available.extend(
            path.stem for path in get_palette_files(user_palettes_dir, "user-*.json")
        )
        
        available.sort()
        
        # Check if there's a non-prefixed file that user might be trying to access
        error_msg = f"Palette '{name}' not found. Available palettes: {', '.join(available)}"
        
        if not name.startswith("user-"):
            non_prefixed_file = data_dir / "user" / "palettes" / f"{name}.json"
            if non_prefixed_file.exists():
                error_msg += f"\nNote: File '{name}.json' exists in user/palettes/ but must be named 'user-{name}.json' to be accessible."
        
        raise FileNotFoundError(error_msg)
    
    # Load the palette JSON data
    try:
        with open(palette_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in palette file {palette_file}: {e}") from e
    
    colors = parse_indexed_palette_document(
        data,
        expected_id=palette_file.stem,
        source_file=str(palette_file),
    )
    
    if name.startswith("user-"):
        records = _parse_user_color_records(
            colors,
            palette_file.name,
        )
    else:
        records = _parse_color_records(
            cast(list[_ColorRecordData], colors),
            str(palette_file),
        )
    
    return Palette(records)



# ============================================================================
# Helper Functions
# ============================================================================

# ============================================================================
# Palette Classes
# ============================================================================

class Palette:
    """
    CSS color palette with multiple indexing strategies for fast lookup.
    
    Think of this as a database with multiple indexes. Want to find a color
    by name? O(1). By RGB? O(1). By LAB? O(1). The tradeoff is memory -
    we keep multiple dictionaries pointing to the same ColorRecords.
    
    For a palette with ~150 CSS colors, this is totally fine! 🚀
    """
    
    def __init__(self, records: List[ColorRecord]) -> None:
        self.records = records
        
        # Build multiple indices for O(1) lookups with user override priority
        self._by_name: Dict[str, ColorRecord] = {}
        self._by_rgb: Dict[Tuple[int, int, int], ColorRecord] = {}
        self._by_hsl: Dict[str, ColorRecord] = {}
        self._by_lab: Dict[str, ColorRecord] = {}
        self._by_lch: Dict[str, ColorRecord] = {}
        
        # Populate indices with override priority
        for record in records:
            name_key = _normalize_color_name(record.name)
            hsl_key = rounded_key(record.hsl)
            lab_key = rounded_key(record.lab)
            lch_key = rounded_key(record.lch)
            
            # For each index, check if we should override existing entry
            if name_key not in self._by_name or should_prefer_source(record.source, self._by_name[name_key].source):
                self._by_name[name_key] = record
                
            if record.rgb not in self._by_rgb or should_prefer_source(record.source, self._by_rgb[record.rgb].source):
                self._by_rgb[record.rgb] = record
                
            if hsl_key not in self._by_hsl or should_prefer_source(record.source, self._by_hsl[hsl_key].source):
                self._by_hsl[hsl_key] = record
                
            if lab_key not in self._by_lab or should_prefer_source(record.source, self._by_lab[lab_key].source):
                self._by_lab[lab_key] = record
                
            if lch_key not in self._by_lch or should_prefer_source(record.source, self._by_lch[lch_key].source):
                self._by_lch[lch_key] = record
    
    @classmethod
    def from_rgb(
        cls,
        rgb_colors: Iterable[tuple[int, int, int] | list[int]],
        *,
        names: Iterable[str] | None = None,
        name_prefix: str = "Color",
        source: str = "custom",
        auto_name: bool = False,
    ) -> Palette:
        """Build a searchable palette, preserving input order and duplicates.

        Explicit names must match the color count and override auto-naming.
        Otherwise names are ``Color 1``, ``Color 2``, etc. (or name_prefix).
        With auto_name=True, the built-in namer receives the entire RGB list
        for near-match uniqueness checks. Generated names are not deduplicated.
        Empty input creates an empty palette. Invalid RGB or name counts raise
        ValueError.

        Example:
            >>> Palette.from_rgb([(255, 0, 0)], auto_name=True).records[0].name
            'red'
        """
        colors: list[tuple[int, int, int]] = []
        for rgb in rgb_colors:
            validate_rgb(rgb)
            colors.append((rgb[0], rgb[1], rgb[2]))
        color_names = list(names) if names is not None else None
        if color_names is not None and len(color_names) != len(colors):
            raise ValueError("The number of names must match the number of colors")
        if color_names is None:
            if auto_name:
                from color_tools.naming import generate_color_names
                color_names = [
                    name
                    for name, _match_type in generate_color_names(
                        colors,
                        palette_colors=colors,
                    )
                ]
            else:
                color_names = [
                    f"{name_prefix} {index}" for index in range(1, len(colors) + 1)
                ]
        return cls([
            ColorRecord.from_rgb(rgb, name=name, source=source)
            for rgb, name in zip(colors, color_names)
        ])

    @classmethod
    def from_hex(
        cls,
        hex_colors: Iterable[str],
        *,
        names: Iterable[str] | None = None,
        name_prefix: str = "Color",
        source: str = "custom",
        auto_name: bool = False,
    ) -> Palette:
        """Build a palette from RGB/RGBA/RRGGBB/RRGGBBAA strings, with optional #.

        Naming, ordering, and validation follow from_rgb(). Invalid hex raises
        ValueError. CSS/PNG alpha is validated then dropped.

        Example:
            >>> Palette.from_hex(["#f00", "00ff00"]).records[1].hex
            '#00FF00'
        """
        return cls.from_rgb(
            (parse_hex(value) for value in hex_colors),
            names=names,
            name_prefix=name_prefix,
            source=source,
            auto_name=auto_name,
        )

    @classmethod
    def load_default(cls) -> 'Palette':
        """
        Load the default CSS color palette from the package data.
        
        This is a convenience method so you don't have to worry about
        file paths - just call Palette.load_default() and go!
        """
        return cls(load_colors())

    def save_lut_png(self, path: str | Path) -> Path:
        """Export this palette as an N×1 RGB PNG lookup texture.

        Colors retain their palette order and duplicate entries. The registered
        ``palette_lut`` exporter owns encoding, validation, and directory
        creation. The returned path is the destination supplied by the caller.

        Args:
            path: Destination PNG file.

        Returns:
            The destination as a ``Path``.

        Raises:
            ValueError: If the palette is empty.
            OSError: If creating directories or writing the file fails.
        """
        # Local import avoids the export facade's dependency on Palette.
        from color_tools.exporters import get_exporter

        exported_path = get_exporter("palette_lut").export_colors(
            self.records,
            path,
        )
        return Path(exported_path)

    def find_by_name(self, name: str) -> Optional[ColorRecord]:
        """Find color by trimmed, case-insensitive name."""
        return self._by_name.get(_normalize_color_name(name))

    def find_by_rgb(self, rgb: Tuple[int, int, int]) -> Optional[ColorRecord]:
        """Find color by exact RGB match."""
        return self._by_rgb.get(rgb)

    def find_by_hsl(self, hsl: Tuple[float, float, float], rounding: int = 2) -> Optional[ColorRecord]:
        """Find color by HSL match (with rounding for fuzzy matching)."""
        return self._by_hsl.get(rounded_key(hsl, rounding))

    def find_by_lab(self, lab: Tuple[float, float, float], rounding: int = 2) -> Optional[ColorRecord]:
        """Find color by LAB match (with rounding for fuzzy matching)."""
        return self._by_lab.get(rounded_key(lab, rounding))

    def find_by_lch(self, lch: Tuple[float, float, float], rounding: int = 2) -> Optional[ColorRecord]:
        """Find color by LCH match (with rounding for fuzzy matching)."""
        return self._by_lch.get(rounded_key(lch, rounding))

    def nearest_color(
        self,
        value: Tuple[float, float, float],
        space: str = "lab",
        metric: str = "de2000",
        *,
        cmc_l: float = ColorConstants.CMC_L_DEFAULT,
        cmc_c: float = ColorConstants.CMC_C_DEFAULT,
    ) -> Tuple[ColorRecord, float]:
        """
        Find nearest color by space/metric.
        
        This is the main search function! It iterates through all colors
        and finds the one with minimum distance in the specified space.
        
        Args:
            value: Color in the specified space (RGB, HSL, LAB, or LCH)
            space: Color space - 'rgb', 'hsl', 'lab', or 'lch' (default: 'lab')
            metric: Distance metric - 'euclidean', 'de76', 'de94', 'de2000', 'cmc'
            cmc_l, cmc_c: Parameters for CMC metric (default 2:1 for acceptability)
        
        Exact distance ties prefer records from ``user-*`` sources. Remaining
        ties retain the records' original order. An empty palette returns
        ``(None, inf)``.

        Returns:
            (nearest_color_record, distance) tuple
        """
        logger.debug("nearest_color: target=%s space=%s metric=%s", value, space, metric)
        matches = self.nearest_colors(
            value,
            space=space,
            metric=metric,
            count=1,
            cmc_l=cmc_l,
            cmc_c=cmc_c,
        )
        if not matches:
            return cast(ColorRecord, None), float("inf")
        record, distance = matches[0]
        logger.debug("nearest_color result: %s (%.4f)", record.name, distance)
        return record, distance

    def nearest_colors(
        self,
        value: Tuple[float, float, float],
        space: str = "lab",
        metric: str = "de2000",
        count: int = 5,
        *,
        cmc_l: float = ColorConstants.CMC_L_DEFAULT,
        cmc_c: float = ColorConstants.CMC_C_DEFAULT,
    ) -> List[Tuple[ColorRecord, float]]:
        """
        Find the nearest N colors by space/metric.
        
        Similar to nearest_color but returns multiple results sorted by distance.
        
        Args:
            value: Color in the specified space (RGB, HSL, LAB, or LCH)
            space: Color space - 'rgb', 'hsl', 'lab', or 'lch' (default: 'lab')
            metric: Distance metric - 'euclidean', 'de76', 'de94', 'de2000', 'cmc'
            count: Number of results to return (default: 5, max: 50)
            cmc_l, cmc_c: Parameters for CMC metric (default 2:1 for acceptability)
        
        Exact distance ties prefer records from ``user-*`` sources. Remaining
        ties retain the records' original order.

        Returns:
            List of (color_record, distance) tuples sorted by distance (closest first)
        """
        # Limit count to reasonable maximum
        count = min(count, 50)
        count = max(count, 1)
        
        results: List[Tuple[ColorRecord, float]] = []

        # RGB space - use simple Euclidean distance
        if space.lower() == "rgb":
            for r in self.records:
                d = euclidean(tuple(map(float, value)), tuple(map(float, r.rgb)))
                results.append((r, d))
            results.sort(key=cmp_to_key(compare_distance_matches))
            return results[:count]

        # HSL space - use circular hue distance
        if space.lower() == "hsl":
            for r in self.records:
                d = hsl_euclidean(value, r.hsl)
                results.append((r, d))
            results.sort(key=cmp_to_key(compare_distance_matches))
            return results[:count]

        # LCH space - use Euclidean distance with hue wraparound
        if space.lower() == "lch":
            for r in self.records:
                d = _lch_euclidean(value, r.lch)
                results.append((r, d))
            results.sort(key=cmp_to_key(compare_distance_matches))
            return results[:count]

        # LAB space - choose the appropriate Delta E metric
        metric_l = metric.lower()
        if metric_l in ("de2000", "ciede2000"):
            fn = delta_e_2000
        elif metric_l in ("de94", "cie94"):
            fn = delta_e_94
        elif metric_l in ("de76", "cie76", "euclidean"):
            fn = delta_e_76
        elif metric_l in ("cmc", "decmc", "cmc21", "cmc11"):
            # CMC has special handling for l:c ratios
            fn = None  # Will handle specially below
        elif metric_l == "hyab":
            fn = delta_e_hyab
        else:
            raise ValueError("Unknown metric. Use 'euclidean'/'de76'/'de94'/'de2000'/'cmc'/'hyab'.")

        for r in self.records:
            if metric_l in ("cmc", "decmc", "cmc21", "cmc11"):
                # Allow shorthands
                l, c = cmc_l, cmc_c
                if metric_l == "cmc21":
                    l, c = ColorConstants.CMC_L_DEFAULT, ColorConstants.CMC_C_DEFAULT
                elif metric_l == "cmc11":
                    l, c = ColorConstants.CMC_C_DEFAULT, ColorConstants.CMC_C_DEFAULT
                d = delta_e_cmc(value, r.lab, l=l, c=c)
            else:
                d = fn(value, r.lab)  # type: ignore
            results.append((r, d))
        
        results.sort(key=cmp_to_key(compare_distance_matches))
        return results[:count]
