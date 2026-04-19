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

User files (user/user-colors.json) always override core data when there
are conflicts. Override information is logged for transparency.

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
from dataclasses import dataclass
from typing import Tuple, Dict, List, Optional, Union, Set, Any
import json
import logging
from pathlib import Path

from color_tools.constants import ColorConstants
from color_tools.conversions import hex_to_rgb, rgb_to_lab, rgb_to_hsl, lab_to_rgb
from color_tools.distance import euclidean, hsl_euclidean, delta_e_2000, delta_e_94, delta_e_76, delta_e_cmc, delta_e_hyab
from color_tools._palette_utils import _should_prefer_source, _rounded_key, _ensure_list

# Set up logger for override tracking
logger = logging.getLogger(__name__)


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
    
    def __str__(self) -> str:
        """Human-readable color representation: name (#hex)"""
        return f"{self.name} ({self.hex})"


# ============================================================================
# Data Loading
# ============================================================================

def _parse_color_records(data: list, source_file: str = "JSON data") -> List[ColorRecord]:
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
            # Validate/coerce RGB to int to ensure numeric values
            rgb = (int(c["rgb"][0]), int(c["rgb"][1]), int(c["rgb"][2]))
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



def load_colors(json_path: Path | str | None = None) -> List[ColorRecord]:
    """
    Load CSS color database from JSON files (core + user additions).
    
    Loads colors from both the core colors.json file and optional user/user-colors.json
    file in the data directory. Core colors are loaded first, followed by user colors.
    
    Args:
        json_path: Path to directory containing JSON files, or path to specific
                   colors JSON file. If None, looks for colors.json in the 
                   package's data/ directory.
    
    Returns:
        List of ColorRecord objects (core colors + user colors)
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
    records = _parse_color_records(data, str(json_path))
    
    # Load optional user colors from same directory
    user_json_path = data_dir / ColorConstants.USER_COLORS_JSON_FILENAME
    if user_json_path.exists():
        with open(user_json_path, "r", encoding="utf-8") as f:
            user_data = json.load(f)
        
        if not isinstance(user_data, list):
            raise ValueError(f"Expected array of colors at root level in {user_json_path}")
        
        # Parse user color records using helper function
        user_records = _parse_color_records(user_data, str(user_json_path))
        
        # Detect and log overrides before merging
        if user_records:
            core_names = {r.name.lower(): r for r in records}
            core_rgbs = {r.rgb: r for r in records}
            
            name_overrides = []
            rgb_overrides = []
            
            for user_record in user_records:
                # Check for name conflicts
                if user_record.name.lower() in core_names:
                    core_record = core_names[user_record.name.lower()]
                    name_overrides.append((user_record.name, core_record.source, user_record.source))
                
                # Check for RGB conflicts (different records with same RGB)
                if user_record.rgb in core_rgbs:
                    core_record = core_rgbs[user_record.rgb]
                    if core_record.name.lower() != user_record.name.lower():  # Different names, same RGB
                        rgb_overrides.append((
                            f"{user_record.name} {user_record.rgb}",
                            f"{core_record.name} ({core_record.source})",
                            user_record.source
                        ))
            
            # Log override information
            if name_overrides:
                logger.info(f"User colors override {len(name_overrides)} core colors by name: {name_overrides}")
            if rgb_overrides:
                logger.info(f"User colors override {len(rgb_overrides)} core colors by RGB: {rgb_overrides}")
        
        records.extend(user_records)
    
    logger.debug("Loaded %d CSS colors from %s", len(records), json_path)
    return records




def load_palette(name: str, json_path: "Path | str | None" = None) -> 'Palette':
    """
    Load a named retro palette from the palettes directory.
    
    Palettes are loaded from:
    1. User palettes: data/user/palettes/{name}.json (if exists)  
    2. Core palettes: data/palettes/{name}.json (built-in)
    
    User palettes override core palettes with the same name.
    
    Common built-in palettes include:
    - cga4: CGA 4-color palette (Palette 1, high intensity) - classic gaming!
    - cga16: CGA 16-color palette (full RGBI)
    - ega16: EGA 16-color palette (standard/default)
    - ega64: EGA 64-color palette (full 6-bit RGB)
    - vga: VGA 256-color palette (Mode 13h)
    - web: Web-safe 216-color palette (6x6x6 RGB cube)
    - gameboy: Game Boy 4-shade green palette
    
    Args:
        name: Palette name (e.g., 'cga4', 'ega16', 'vga', 'web', or custom user palette)
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
        
        >>> # Load custom user palette
        >>> custom = load_palette("my_custom_palette")
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
        user_palette_file = data_dir / "user" / "palettes" / f"{name}.json"
        if user_palette_file.exists():
            palette_file = user_palette_file
    else:
        # Core palette requested
        core_palette_file = data_dir / "palettes" / f"{name}.json"
        if core_palette_file.exists():
            palette_file = core_palette_file
    
    if palette_file is None:
        # Build list of available palettes from both locations
        available = []
        
        # Core palettes
        core_palettes_dir = data_dir / "palettes"
        if core_palettes_dir.exists():
            available.extend([p.stem for p in core_palettes_dir.glob("*.json")])
        
        # User palettes (only user-*.json files)
        user_palettes_dir = data_dir / "user" / "palettes"
        if user_palettes_dir.exists():
            user_palettes = [p.stem for p in user_palettes_dir.glob("user-*.json")]
            available.extend(user_palettes)
        
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
    
    if not isinstance(data, list):
        raise ValueError(f"Expected array of colors at root level in {palette_file}")
    
    # Parse color records using shared helper function
    records = _parse_color_records(data, str(palette_file))
    
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
            name_key = record.name.lower()
            hsl_key = _rounded_key(record.hsl)
            lab_key = _rounded_key(record.lab)
            lch_key = _rounded_key(record.lch)
            
            # For each index, check if we should override existing entry
            if name_key not in self._by_name or _should_prefer_source(record.source, self._by_name[name_key].source):
                self._by_name[name_key] = record
                
            if record.rgb not in self._by_rgb or _should_prefer_source(record.source, self._by_rgb[record.rgb].source):
                self._by_rgb[record.rgb] = record
                
            if hsl_key not in self._by_hsl or _should_prefer_source(record.source, self._by_hsl[hsl_key].source):
                self._by_hsl[hsl_key] = record
                
            if lab_key not in self._by_lab or _should_prefer_source(record.source, self._by_lab[lab_key].source):
                self._by_lab[lab_key] = record
                
            if lch_key not in self._by_lch or _should_prefer_source(record.source, self._by_lch[lch_key].source):
                self._by_lch[lch_key] = record
    
    @classmethod
    def load_default(cls) -> 'Palette':
        """
        Load the default CSS color palette from the package data.
        
        This is a convenience method so you don't have to worry about
        file paths - just call Palette.load_default() and go!
        """
        return cls(load_colors())

    def find_by_name(self, name: str) -> Optional[ColorRecord]:
        """Find color by exact name match (case-insensitive)."""
        return self._by_name.get(name.lower())

    def find_by_rgb(self, rgb: Tuple[int, int, int]) -> Optional[ColorRecord]:
        """Find color by exact RGB match."""
        return self._by_rgb.get(rgb)

    def find_by_hsl(self, hsl: Tuple[float, float, float], rounding: int = 2) -> Optional[ColorRecord]:
        """Find color by HSL match (with rounding for fuzzy matching)."""
        return self._by_hsl.get(_rounded_key(hsl, rounding))

    def find_by_lab(self, lab: Tuple[float, float, float], rounding: int = 2) -> Optional[ColorRecord]:
        """Find color by LAB match (with rounding for fuzzy matching)."""
        return self._by_lab.get(_rounded_key(lab, rounding))

    def find_by_lch(self, lch: Tuple[float, float, float], rounding: int = 2) -> Optional[ColorRecord]:
        """Find color by LCH match (with rounding for fuzzy matching)."""
        return self._by_lch.get(_rounded_key(lch, rounding))

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
        
        Returns:
            (nearest_color_record, distance) tuple
        """
        best_rec: Optional[ColorRecord] = None
        best_d = float("inf")

        logger.debug("nearest_color: target=%s space=%s metric=%s", value, space, metric)

        # RGB space - use simple Euclidean distance
        if space.lower() == "rgb":
            for r in self.records:
                d = euclidean(tuple(map(float, value)), tuple(map(float, r.rgb)))
                if d < best_d or (d == best_d and best_rec and _should_prefer_source(r.source, best_rec.source)):
                    best_rec, best_d = r, d
            logger.debug("nearest_color result: %s (%.4f)", getattr(best_rec, "name", None), best_d)
            return best_rec, best_d  # type: ignore

        # HSL space - use circular hue distance
        if space.lower() == "hsl":
            for r in self.records:
                d = hsl_euclidean(value, r.hsl)
                if d < best_d or (d == best_d and best_rec and _should_prefer_source(r.source, best_rec.source)):
                    best_rec, best_d = r, d
            logger.debug("nearest_color result: %s (%.4f)", getattr(best_rec, "name", None), best_d)
            return best_rec, best_d  # type: ignore

        # LCH space - use Euclidean distance with hue wraparound
        if space.lower() == "lch":
            for r in self.records:
                # LCH has circular hue like HSL, so we need special handling
                d = hsl_euclidean(value, r.lch)  # hsl_euclidean handles circular hue properly
                if d < best_d or (d == best_d and best_rec and _should_prefer_source(r.source, best_rec.source)):
                    best_rec, best_d = r, d
            logger.debug("nearest_color result: %s (%.4f)", getattr(best_rec, "name", None), best_d)
            return best_rec, best_d  # type: ignore

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
            if d < best_d or (d == best_d and best_rec and _should_prefer_source(r.source, best_rec.source)):
                best_rec, best_d = r, d

        logger.debug(
            "nearest_color: target=%s space=%s metric=%s → %s (%.4f)",
            value, space, metric, getattr(best_rec, "name", None), best_d,
        )
        return best_rec, best_d  # type: ignore

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
            results.sort(key=lambda x: x[1])
            return results[:count]

        # HSL space - use circular hue distance
        if space.lower() == "hsl":
            for r in self.records:
                d = hsl_euclidean(value, r.hsl)
                results.append((r, d))
            results.sort(key=lambda x: x[1])
            return results[:count]

        # LCH space - use Euclidean distance with hue wraparound
        if space.lower() == "lch":
            for r in self.records:
                d = hsl_euclidean(value, r.lch)  # hsl_euclidean handles circular hue properly
                results.append((r, d))
            results.sort(key=lambda x: x[1])
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
        
        results.sort(key=lambda x: x[1])
        return results[:count]

    def get_override_info(self) -> Dict[str, Dict[str, Dict[str, Tuple[str, str]]]]:
        """
        Get information about user overrides in this palette.
        
        Returns:
            Dictionary with override information structure:
            
            .. code-block:: python
            
                {
                    "colors": {
                        "name": {"color_name": ("core_source", "user_source")},
                        "rgb": {"(r,g,b)": ("core_source", "user_source")}
                    }
                }
        """
        overrides: Dict[str, Dict[str, Dict[str, Tuple[str, str]]]] = {
            "colors": {"name": {}, "rgb": {}}
        }
        
        # Group records by name and RGB to detect overrides
        name_groups: Dict[str, List[ColorRecord]] = {}
        rgb_groups: Dict[Tuple[int, int, int], List[ColorRecord]] = {}
        
        for record in self.records:
            name_key = record.name.lower()
            if name_key not in name_groups:
                name_groups[name_key] = []
            name_groups[name_key].append(record)
            
            if record.rgb not in rgb_groups:
                rgb_groups[record.rgb] = []
            rgb_groups[record.rgb].append(record)
        
        # Check for name overrides
        for name, records in name_groups.items():
            if len(records) > 1:
                # Multiple records with same name - find override pattern
                core_records = [r for r in records if not r.source.startswith('user-')]
                user_records = [r for r in records if r.source.startswith('user-')]
                if core_records and user_records:
                    overrides["colors"]["name"][name] = (core_records[0].source, user_records[0].source)
        
        # Check for RGB overrides  
        for rgb, records in rgb_groups.items():
            if len(records) > 1:
                # Multiple records with same RGB - find override pattern
                core_records = [r for r in records if not r.source.startswith('user-')]
                user_records = [r for r in records if r.source.startswith('user-')]
                if core_records and user_records:
                    overrides["colors"]["rgb"][str(rgb)] = (core_records[0].source, user_records[0].source)
        
        return overrides


