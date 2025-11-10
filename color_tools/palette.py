"""
Color and filament palette management with fast lookup.

This module provides:
1. Data classes for colors (ColorRecord) and filaments (FilamentRecord)
2. Functions to load color/filament data from JSON
3. Palette classes with multiple indices for O(1) lookups
4. Nearest-color search using various distance metrics

The palette classes are like databases with multiple indexes - you can
search by name, RGB, HSL, maker, type, etc. and get instant results!
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Dict, List, Optional, Union, Set
import json
from pathlib import Path

from .constants import ColorConstants
from .conversions import hex_to_rgb, rgb_to_lab, rgb_to_hsl, lab_to_rgb
from .distance import euclidean, hsl_euclidean, delta_e_2000, delta_e_94, delta_e_76, delta_e_cmc
from .config import get_dual_color_mode


# ============================================================================
# Data Classes
# ============================================================================

@dataclass(frozen=True)
class ColorRecord:
    """
    Immutable record representing a CSS color.
    
    Frozen dataclass = immutable. Once created, you can't change it.
    This is perfect for colors - a color IS what it IS! 🎨
    """
    name: str
    hex: str
    rgb: Tuple[int, int, int]
    hsl: Tuple[float, float, float]   # (H°, S%, L%)
    lab: Tuple[float, float, float]   # (L*, a*, b*)
    lch: Tuple[float, float, float]   # (L*, C*, H°)


@dataclass(frozen=True)
class FilamentRecord:
    """
    Immutable record representing a 3D printing filament.
    
    The clever part: rgb is a @property that handles dual-color filaments!
    Some silk filaments have TWO colors twisted together (e.g., "#AABBCC-#DDEEFF"),
    and we can extract either the first, last, or perceptually blend them.
    """
    id: str  # Unique identifier slug (e.g., "bambu-lab-pla-silk-plus-red")
    maker: str
    type: str
    finish: Optional[str]
    color: str
    hex: str
    td_value: Optional[float] = None  # Translucency/transparency value
    other_names: Optional[List[str]] = None  # Alternative names (regional, historical, etc.)
    
    @property
    def rgb(self) -> Tuple[int, int, int]:
        """
        Convert hex to RGB tuple, handling dual-color filaments.
        
        This is where the dual-color magic happens! If hex contains a dash
        (e.g., "#333333-#666666"), we parse BOTH colors and handle them based
        on the global dual_color_mode setting:
        - "first": Use first color (default)
        - "last": Use second color
        - "mix": Perceptually blend in LAB space (the proper way!)
        
        Returns:
            RGB tuple (0-255 for each component)
        """
        hex_clean = self.hex.strip()
        
        # Check for dual-color format (e.g., "#333333-#666666")
        if '-' in hex_clean:
            # Split into individual colors and clean them
            hex_parts = [h.strip() for h in hex_clean.split('-')]
            
            # Parse both colors using our existing hex_to_rgb function
            rgb_colors = []
            for hex_part in hex_parts[:2]:  # Only take first 2 if more exist
                try:
                    result = hex_to_rgb(hex_part)
                    rgb_colors.append(result if result is not None else (0, 0, 0))
                except (ValueError, TypeError):
                    rgb_colors.append((0, 0, 0))
            
            # If we didn't get 2 valid colors, fall back to first
            if len(rgb_colors) < 2:
                return rgb_colors[0] if rgb_colors else (0, 0, 0)
            
            # Apply dual-color mode (this is where config comes in!)
            mode = get_dual_color_mode()
            if mode == "last":
                return rgb_colors[1]
            elif mode == "mix":
                # Perceptual blend in LAB space! 🌈
                # This is the RIGHT way to blend colors - not in RGB!
                lab1 = rgb_to_lab(rgb_colors[0])
                lab2 = rgb_to_lab(rgb_colors[1])
                # Average in LAB space (perceptually uniform)
                lab_avg = (
                    (lab1[0] + lab2[0]) / 2.0,
                    (lab1[1] + lab2[1]) / 2.0,
                    (lab1[2] + lab2[2]) / 2.0
                )
                return lab_to_rgb(lab_avg)
            else:  # "first" (default)
                return rgb_colors[0]
        
        # Single color - use our existing hex_to_rgb function
        try:
            result = hex_to_rgb(hex_clean)
            return result if result is not None else (0, 0, 0)
        except (ValueError, TypeError):
            return (0, 0, 0)
    
    @property
    def lab(self) -> Tuple[float, float, float]:
        """Convert to LAB color space."""
        return rgb_to_lab(self.rgb)
    
    @property
    def lch(self) -> Tuple[float, float, float]:
        """Convert to LCH color space."""
        from .conversions import lab_to_lch
        return lab_to_lch(self.lab)
    
    @property
    def hsl(self) -> Tuple[float, float, float]:
        """Convert to HSL color space."""
        return rgb_to_hsl(self.rgb)
    
    def __str__(self) -> str:
        """Pretty string representation for printing."""
        finish_str = f" {self.finish}" if self.finish else ""
        td_str = f" (TD: {self.td_value})" if self.td_value is not None else ""
        return f"{self.maker} {self.type}{finish_str} - {self.color} {self.hex}{td_str}"


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
        source_file: Name of the source file for error messages
    
    Returns:
        List of ColorRecord objects
    
    Raises:
        KeyError: If required keys are missing from the color data
        ValueError: If color data values are invalid
    """
    records: List[ColorRecord] = []
    
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
    
    Loads colors from both the core colors.json file and optional user-colors.json
    file in the same directory. Core colors are loaded first, followed by user colors.
    
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
        records.extend(user_records)
    
    return records


def load_filaments(json_path: Path | str | None = None) -> List[FilamentRecord]:
    """
    Load filament database from JSON files (core + user additions).
    
    Loads filaments from both the core filaments.json file and optional 
    user-filaments.json file in the same directory. Core filaments are loaded 
    first, followed by user filaments.
    
    Args:
        json_path: Path to directory containing JSON files, or path to specific
                   filaments JSON file. If None, looks for filaments.json in 
                   the package's data/ directory.
    
    Returns:
        List of FilamentRecord objects (core filaments + user filaments)
    """
    if json_path is None:
        # Default: look in package's data/ directory
        data_dir = Path(__file__).parent / "data"
        json_path = data_dir / ColorConstants.FILAMENTS_JSON_FILENAME
    else:
        json_path = Path(json_path)
        # If it's a directory, append the filename
        if json_path.is_dir():
            data_dir = json_path
            json_path = json_path / ColorConstants.FILAMENTS_JSON_FILENAME
        else:
            data_dir = json_path.parent
    
    # Load core filaments
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Data should be an array of filament objects at the root level
    if not isinstance(data, list):
        raise ValueError(f"Expected array of filaments at root level in {json_path}")
    
    records: List[FilamentRecord] = []
    for f in data:
        records.append(FilamentRecord(
            id=f["id"],
            maker=f["maker"],
            type=f["type"],
            finish=f.get("finish"),  # finish can be None
            color=f["color"],
            hex=f["hex"],
            td_value=f.get("td_value"),  # td_value can be None
            other_names=f.get("other_names"),  # other_names can be None
        ))
    
    # Load optional user filaments from same directory
    user_json_path = data_dir / ColorConstants.USER_FILAMENTS_JSON_FILENAME
    if user_json_path.exists():
        with open(user_json_path, "r", encoding="utf-8") as f:
            user_data = json.load(f)
        
        if not isinstance(user_data, list):
            raise ValueError(f"Expected array of filaments at root level in {user_json_path}")
        
        for f in user_data:
            records.append(FilamentRecord(
                id=f.get("id", ""),  # User files may not have IDs yet
                maker=f["maker"],
                type=f["type"],
                finish=f.get("finish"),
                color=f["color"],
                hex=f["hex"],
                td_value=f.get("td_value"),
                other_names=f.get("other_names"),
            ))
    
    return records


def load_maker_synonyms(json_path: Path | str | None = None) -> Dict[str, List[str]]:
    """
    Load maker synonyms from JSON files (core + user additions).
    
    Loads synonyms from both the core maker_synonyms.json file and optional
    user-synonyms.json file in the same directory. Synonyms are merged, with
    user additions extending (not replacing) core synonyms.
    
    Args:
        json_path: Path to directory containing JSON files, or path to specific
                   maker_synonyms JSON file. If None, looks for maker_synonyms.json 
                   in the package's data/ directory.
    
    Returns:
        Dictionary mapping canonical maker names to lists of synonyms
    """
    if json_path is None:
        # Default: look in package's data/ directory
        data_dir = Path(__file__).parent / "data"
        json_path = data_dir / ColorConstants.MAKER_SYNONYMS_JSON_FILENAME
    else:
        json_path = Path(json_path)
        # If it's a directory, append the filename
        if json_path.is_dir():
            data_dir = json_path
            json_path = json_path / ColorConstants.MAKER_SYNONYMS_JSON_FILENAME
        else:
            data_dir = json_path.parent
    
    # Load core synonyms
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            synonyms = json.load(f)
    except FileNotFoundError:
        synonyms = {}
    
    # Load optional user synonyms from same directory and merge
    user_json_path = data_dir / ColorConstants.USER_SYNONYMS_JSON_FILENAME
    if user_json_path.exists():
        with open(user_json_path, "r", encoding="utf-8") as f:
            user_synonyms = json.load(f)
        
        # Merge user synonyms into core synonyms
        for maker, user_syn_list in user_synonyms.items():
            if maker in synonyms:
                # Extend existing synonym list (avoid duplicates)
                existing = set(synonyms[maker])
                for syn in user_syn_list:
                    if syn not in existing:
                        synonyms[maker].append(syn)
            else:
                # Add new maker with their synonyms
                synonyms[maker] = user_syn_list
    
    return synonyms


def load_palette(name: str) -> 'Palette':
    """
    Load a named retro palette from the palettes directory.
    
    Available palettes:
    - cga4: CGA 4-color palette (Palette 1, high intensity) - classic gaming!
    - cga16: CGA 16-color palette (full RGBI)
    - ega16: EGA 16-color palette (standard/default)
    - ega64: EGA 64-color palette (full 6-bit RGB)
    - vga: VGA 256-color palette (Mode 13h)
    - web: Web-safe 216-color palette (6x6x6 RGB cube)
    
    Args:
        name: Palette name (e.g., 'cga4', 'ega16', 'vga', 'web')
    
    Returns:
        Palette object loaded from the specified palette file
    
    Raises:
        FileNotFoundError: If the palette file doesn't exist
        ValueError: If the palette file is malformed or contains invalid data
    
    Example:
        >>> cga = load_palette("cga4")
        >>> color, dist = cga.nearest_color((128, 64, 200))
        >>> print(f"Nearest CGA color: {color.name}")
    """
    palettes_dir = Path(__file__).parent / "data" / "palettes"
    palette_file = palettes_dir / f"{name}.json"
    
    if not palette_file.exists():
        available = sorted([p.stem for p in palettes_dir.glob("*.json")])
        raise FileNotFoundError(
            f"Palette '{name}' not found. Available palettes: {', '.join(available)}"
        )
    
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

def _rounded_key(nums: Tuple[float, ...], ndigits: int = 2) -> str:
    """
    Create a string key from rounded numeric values.
    
    Used for fuzzy matching in dictionaries. Instead of looking for
    EXACTLY (50.0, 25.0, 100.0), we round to (50.00, 25.00, 100.00)
    so nearby values will match.
    """
    return ",".join(str(round(x, ndigits)) for x in nums)

def _ensure_list(value: Union[str, List[str]]) -> List[str]:
    """Ensures the input is a list of strings, wrapping if it's a single string."""
    if isinstance(value, str):
        return [value]
    return value

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
        
        # Build multiple indices for O(1) lookups
        self._by_name: Dict[str, ColorRecord] = {r.name.lower(): r for r in records}
        self._by_rgb: Dict[Tuple[int, int, int], ColorRecord] = {r.rgb: r for r in records}
        self._by_hsl: Dict[str, ColorRecord] = {_rounded_key(r.hsl): r for r in records}
        self._by_lab: Dict[str, ColorRecord] = {_rounded_key(r.lab): r for r in records}
        self._by_lch: Dict[str, ColorRecord] = {_rounded_key(r.lch): r for r in records}
    
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

        # RGB space - use simple Euclidean distance
        if space.lower() == "rgb":
            for r in self.records:
                d = euclidean(tuple(map(float, value)), tuple(map(float, r.rgb)))
                if d < best_d:
                    best_rec, best_d = r, d
            return best_rec, best_d  # type: ignore

        # HSL space - use circular hue distance
        if space.lower() == "hsl":
            for r in self.records:
                d = hsl_euclidean(value, r.hsl)
                if d < best_d:
                    best_rec, best_d = r, d
            return best_rec, best_d  # type: ignore

        # LCH space - use Euclidean distance with hue wraparound
        if space.lower() == "lch":
            for r in self.records:
                # LCH has circular hue like HSL, so we need special handling
                d = hsl_euclidean(value, r.lch)  # hsl_euclidean handles circular hue properly
                if d < best_d:
                    best_rec, best_d = r, d
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
        else:
            raise ValueError("Unknown metric. Use 'euclidean'/'de76'/'de94'/'de2000'/'cmc'.")

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
            if d < best_d:
                best_rec, best_d = r, d
        return best_rec, best_d  # type: ignore


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
    
    def __init__(self, records: List[FilamentRecord], maker_synonyms: Optional[Dict[str, List[str]]] = None) -> None:
        self.records = records
        self.maker_synonyms = maker_synonyms or {}
        
        # Create various lookup indices (note: Lists, not single items!)
        # Multiple filaments can share the same maker/type/color
        self._by_maker: Dict[str, List[FilamentRecord]] = {}
        self._by_type: Dict[str, List[FilamentRecord]] = {}
        self._by_color: Dict[str, List[FilamentRecord]] = {}
        self._by_rgb: Dict[Tuple[int, int, int], List[FilamentRecord]] = {}
        self._by_finish: Dict[str, List[FilamentRecord]] = {}
        
        # Build indices
        for rec in records:
            # By maker
            if rec.maker not in self._by_maker:
                self._by_maker[rec.maker] = []
            self._by_maker[rec.maker].append(rec)
            
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
    
    def _expand_maker_names(self, makers: List[str]) -> Set[str]:
        """
        Expand maker names to include synonyms.
        
        For example, if "Bambu" is provided and "Bambu Lab" has synonyms ["Bambu", "BLL"],
        this will return {"Bambu Lab", "Bambu", "BLL"}.
        
        Args:
            makers: List of maker names or synonyms to expand
        
        Returns:
            Set of all canonical names and synonyms that match
        """
        expanded = set()
        for maker in makers:
            # Add the original name
            expanded.add(maker)
            
            # Check if this maker IS a canonical name
            if maker in self.maker_synonyms:
                expanded.update(self.maker_synonyms[maker])
            
            # Check if this maker is a synonym for a canonical name
            for canonical, synonyms in self.maker_synonyms.items():
                if maker in synonyms:
                    expanded.add(canonical)
                    expanded.update(synonyms)
        
        return expanded
    
    def _normalize_filter_values(self, value: Optional[Union[str, List[str]]]) -> Optional[Set[str]]:
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
            return {value}
        return set(value)

    @classmethod
    def load_default(cls) -> 'FilamentPalette':
        """
        Load the default filament palette from the package data.
        
        Convenience method for quick loading without worrying about paths.
        Also loads maker synonyms automatically.
        """
        return cls(load_filaments(), load_maker_synonyms())

    def find_by_maker(self, maker: Union[str, List[str]]) -> List[FilamentRecord]:
        """
        Find all filaments by a single maker or a list of makers.
        
        Supports synonyms: searching for "Bambu" will find "Bambu Lab" filaments.
        
        Args:
            maker: A single maker name (str) or a list of names (can use synonyms).
            
        Returns:
            A list of all matching FilamentRecord objects.
        """
        makers_to_find = _ensure_list(maker)
        expanded_makers = self._expand_maker_names(makers_to_find)
        
        all_filaments = []
        for m in expanded_makers:
            all_filaments.extend(self._by_maker.get(m, []))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_filaments = []
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
        types_to_find = _ensure_list(type_name)

        all_filaments = []
        for t in types_to_find:
            all_filaments.extend(self._by_type.get(t, []))
        return all_filaments

    def find_by_color(self, color: str) -> List[FilamentRecord]:
        """Find all filaments by color name (case-insensitive)."""
        return self._by_color.get(color.lower(), [])

    def find_by_rgb(self, rgb: Tuple[int, int, int]) -> List[FilamentRecord]:
        """Find all filaments by exact RGB match."""
        return self._by_rgb.get(rgb, [])

    def find_by_finish(self, finish: Union[str, List[str]]) -> List[FilamentRecord]:
        """
        Find all filaments by a single finish or a list of finishes.
        
        Args:
            finish: A single filament finish (str) or a list of finishes.
            
        Returns:
            A list of all matching FilamentRecord objects.
        """
        finishes_to_find = _ensure_list(finish)
            
        all_filaments = []
        for f in finishes_to_find:
            all_filaments.extend(self._by_finish.get(f, []))
        return all_filaments

    def filter(
        self,
        maker: Optional[Union[str, List[str]]] = None,
        type_name: Optional[Union[str, List[str]]] = None,
        finish: Optional[Union[str, List[str]]] = None,
        color: Optional[str] = None
    ) -> List[FilamentRecord]:
        """
        Filter filaments by multiple criteria.
        
        This is like SQL WHERE clauses! Start with all records, then filter
        down by each criterion that's provided. Maker, type, and finish
        can accept a single string or a list of strings.
        
        Supports maker synonyms: filtering by "Bambu" will include "Bambu Lab".
        
        Args:
            maker: A maker name or list of maker names (can use synonyms).
            type_name: A filament type or list of types.
            finish: A filament finish or list of finishes.
            color: A single color name to match (case-insensitive).
        
        Returns:
            A list of FilamentRecord objects matching the criteria.
        """
        results = self.records
        
        makers_set = self._normalize_filter_values(maker)
        types_set = self._normalize_filter_values(type_name)
        finishes_set = self._normalize_filter_values(finish)
        
        # Expand maker names to include synonyms
        if makers_set:
            makers_set = self._expand_maker_names(list(makers_set))
        
        if makers_set:
            results = [r for r in results if r.maker in makers_set]
        if types_set:
            results = [r for r in results if r.type in types_set]
        if finishes_set:
            results = [r for r in results if r.finish and r.finish in finishes_set]
        if color:
            results = [r for r in results if r.color.lower() == color.lower()]
            
        return results

    def nearest_filament(
        self,
        target_rgb: Tuple[int, int, int],
        metric: str = "de2000",
        *,
        maker: Optional[Union[str, List[str]]] = None,
        type_name: Optional[Union[str, List[str]]] = None,
        finish: Optional[Union[str, List[str]]] = None,
        cmc_l: float = ColorConstants.CMC_L_DEFAULT,
        cmc_c: float = ColorConstants.CMC_C_DEFAULT,
    ) -> Tuple[FilamentRecord, float]:
        """
        Find nearest filament by color similarity, with optional filters.
        
        The killer feature for 3D printing! "I want this exact color... what
        filament should I buy?" 🎨🖨️
        
        Args:
            target_rgb: Target RGB color tuple.
            metric: Distance metric - 'euclidean', 'de76', 'de94', 'de2000', 'cmc'.
            maker: Optional maker name or list of names to filter by.
            type_name: Optional filament type or list of types to filter by.
            finish: Optional filament finish or list of finishes to filter by.
            cmc_l, cmc_c: Parameters for CMC metric.
        
        Returns:
            (nearest_filament_record, distance) tuple.
        """
        target_lab = rgb_to_lab(target_rgb)
        
        # Apply filters by calling our powerful filter() method first!
        candidates = self.filter(maker=maker, type_name=type_name, finish=finish)
        
        if not candidates:
            raise ValueError("No filaments match the specified filters")
        
        best_rec: Optional[FilamentRecord] = None
        best_d = float("inf")

        # Choose distance function
        metric_l = metric.lower()
        if metric_l in ("de2000", "ciede2000"):
            distance_fn = delta_e_2000
        elif metric_l in ("de94", "cie94"):
            distance_fn = delta_e_94
        elif metric_l in ("de76", "cie76"):
            distance_fn = delta_e_76
        elif metric_l == "euclidean":
            distance_fn = lambda lab1, lab2: euclidean(lab1, lab2)
        elif metric_l in ("cmc", "decmc"):
            distance_fn = lambda lab1, lab2: delta_e_cmc(lab1, lab2, l=cmc_l, c=cmc_c)
        else:
            raise ValueError("Unknown metric. Use 'euclidean'/'de76'/'de94'/'de2000'/'cmc'.")

        for rec in candidates:
            try:
                d = distance_fn(target_lab, rec.lab)
                if d < best_d:
                    best_rec, best_d = rec, d
            except:
                # Skip filaments with invalid colors
                continue
        
        if best_rec is None:
            raise ValueError("No valid filaments found")
            
        return best_rec, best_d

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

