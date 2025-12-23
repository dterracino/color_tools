"""
Color and filament palette management with fast lookup.

This module provides:
1. Data classes for colors (ColorRecord) and filaments (FilamentRecord)
2. Functions to load color/filament data from JSON with user override support
3. Palette classes with multiple indices for O(1) lookups
4. Nearest-color search using various distance metrics

The palette classes are like databases with multiple indexes - you can
search by name, RGB, HSL, maker, type, etc. and get instant results!

User files (user/user-colors.json, user/user-filaments.json) always override core
data when there are conflicts. Override information is logged for transparency.

Example:
    >>> from color_tools import Palette, FilamentPalette
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
    >>> 
    >>> # Load 3D printing filaments 
    >>> filaments = FilamentPalette.load_default()
    >>> 
    >>> # Search by maker and material
    >>> pla_colors = filaments.find_by_maker("Bambu", type_name="PLA")
    >>> print(f"Found {len(pla_colors)} Bambu PLA colors")
    Found 24 Bambu PLA colors
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Dict, List, Optional, Union, Set
import json
import logging
from pathlib import Path

from .constants import ColorConstants
from .conversions import hex_to_rgb, rgb_to_lab, rgb_to_hsl, lab_to_rgb
from .distance import euclidean, hsl_euclidean, delta_e_2000, delta_e_94, delta_e_76, delta_e_cmc
from .config import get_dual_color_mode

# Set up logger for override tracking
logger = logging.getLogger(__name__)


def _should_prefer_source(new_source: str, current_source: str) -> bool:
    """
    Determine if new_source should be preferred over current_source for ties.
    
    User files always win over core files when distances are equal.
    This ensures consistent behavior between index lookups and distance-based searches.
    
    Args:
        new_source: Source filename of the candidate record
        current_source: Source filename of the current best record
    
    Returns:
        True if new_source should be preferred over current_source
    """
    # Core filenames (these are overridden by user files)
    core_files = {"colors.json", "filaments.json"}
    
    new_is_core = new_source in core_files
    current_is_core = current_source in core_files
    
    # If current is core and new is user, prefer new (user override)
    if current_is_core and not new_is_core:
        return True
    
    # If current is user and new is core, keep current (user wins)
    if not current_is_core and new_is_core:
        return False
    
    # Both are same type (core or user), don't prefer either
    return False


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


@dataclass(frozen=True)
class FilamentRecord:
    """
    Immutable record representing a 3D printing filament color.
    
    This dataclass handles both single-color and dual-color filaments (like silk/rainbow
    filaments with two twisted colors). The rgb property intelligently handles dual-color
    hex codes (e.g., "#AABBCC-#DDEEFF") based on the global dual_color_mode setting.
    
    The source field tracks which JSON file provided this filament, enabling user
    override detection and debugging.
    
    Attributes:
        id: Unique identifier slug (e.g., "bambu-lab-pla-silk-plus-red")
        maker: Manufacturer name (e.g., "Bambu Lab", "Polymaker", "Prusament")
        type: Filament material type (e.g., "PLA", "PETG", "ABS")
        finish: Surface finish type (e.g., "Matte", "Silk", "PolyMax") or None
        color: Color name as labeled by manufacturer (e.g., "Jet Black", "Signal Red")
        hex: Hex color code with # prefix, may contain dash for dual colors (e.g., "#333333-#666666")
        td_value: Translucency/transparency value 0.0-1.0 (None for opaque)
        other_names: Alternative color names (regional variants, historical names) or None
        source: JSON filename where this record originated (default: "filaments.json")
    
    Properties:
        rgb: RGB tuple (0-255 each) computed from hex, handles dual-color filaments
            based on dual_color_mode ("first", "last", or "mix")
        lab: CIE LAB tuple computed on-demand from RGB
        lch: CIE LCH tuple computed on-demand from RGB
    
    Example:
        >>> from color_tools import FilamentPalette
        >>> palette = FilamentPalette.load_default()
        >>> filament = palette.find_by_maker("Bambu Lab", type_name="PLA")[0]
        >>> print(f"{filament.maker} {filament.type} - {filament.color}")
        Bambu Lab PLA - Jet Black
        >>> print(f"RGB: {filament.rgb}, Hex: {filament.hex}")
        RGB: (51, 51, 51), Hex: #333333
    """
    id: str  # Unique identifier slug (e.g., "bambu-lab-pla-silk-plus-red")
    maker: str
    type: str
    finish: Optional[str]
    color: str
    hex: str
    td_value: Optional[float] = None  # Translucency/transparency value
    other_names: Optional[List[str]] = None  # Alternative names (regional, historical, etc.)
    source: str = "filaments.json"   # JSON filename where this record originated
    
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


def _parse_filament_records(data: list, source_file: str = "JSON data") -> List[FilamentRecord]:
    """
    Parse a list of filament data dictionaries into FilamentRecord objects.
    
    This is a helper function used by load_filaments() to avoid code duplication
    and ensure consistent source tracking.
    
    Args:
        data: List of dictionaries containing filament data
        source_file: Name of the source file for error messages and source tracking.
                    Should be just the filename (e.g., 'filaments.json', 'user-filaments.json')
    
    Returns:
        List of FilamentRecord objects with source field set to source_file
    
    Raises:
        KeyError: If required keys are missing from the filament data
        ValueError: If filament data values are invalid
    """
    records: List[FilamentRecord] = []
    
    # Extract just the filename from path for source tracking
    from pathlib import Path
    source_filename = Path(source_file).name if source_file != "JSON data" else "unknown.json"
    
    for i, f in enumerate(data):
        try:
            records.append(FilamentRecord(
                id=f.get("id", ""),  # User files may not have IDs
                maker=f["maker"],
                type=f["type"],
                finish=f.get("finish"),
                color=f["color"],
                hex=f["hex"],
                td_value=f.get("td_value"),
                other_names=f.get("other_names"),
                source=source_filename,
            ))
        except KeyError as e:
            raise ValueError(
                f"Missing required key {e} in filament at index {i} in {source_file}"
            ) from e
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Invalid filament data at index {i} in {source_file}: {e}"
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
    
    return records


def load_filaments(json_path: Path | str | None = None) -> List[FilamentRecord]:
    """
    Load filament database from JSON files (core + user additions).
    
    Loads filaments from both the core filaments.json file and optional 
    user/user-filaments.json file in the data directory. Core filaments are loaded 
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
    
    # Parse core filament records using helper function
    records = _parse_filament_records(data, str(json_path))
    
    # Load optional user filaments from same directory
    user_json_path = data_dir / ColorConstants.USER_FILAMENTS_JSON_FILENAME
    if user_json_path.exists():
        with open(user_json_path, "r", encoding="utf-8") as f:
            user_data = json.load(f)
        
        if not isinstance(user_data, list):
            raise ValueError(f"Expected array of filaments at root level in {user_json_path}")
        
        # Parse user filament records using helper function
        user_records = _parse_filament_records(user_data, str(user_json_path))
        
        # Detect and log overrides before merging
        if user_records:
            # For filaments, we consider a conflict when maker+type+color+hex all match
            core_sigs = {}
            for r in records:
                sig = (r.maker, r.type, r.color, r.hex)
                core_sigs[sig] = r
            
            exact_overrides = []
            rgb_overrides = []
            core_rgbs = {r.rgb: r for r in records}
            
            for user_record in user_records:
                # Check for exact filament match (same maker+type+color+hex)
                user_sig = (user_record.maker, user_record.type, user_record.color, user_record.hex)
                if user_sig in core_sigs:
                    core_record = core_sigs[user_sig]
                    exact_overrides.append((
                        f"{user_record.maker} {user_record.type} {user_record.color}",
                        core_record.source,
                        user_record.source
                    ))
                
                # Check for RGB conflicts (different filaments with same RGB)
                elif user_record.rgb in core_rgbs:
                    core_record = core_rgbs[user_record.rgb]
                    rgb_overrides.append((
                        f"{user_record.maker} {user_record.type} {user_record.color} {user_record.rgb}",
                        f"{core_record.maker} {core_record.type} {core_record.color} ({core_record.source})",
                        user_record.source
                    ))
            
            # Log override information
            if exact_overrides:
                logger.info(f"User filaments override {len(exact_overrides)} core filaments exactly: {exact_overrides}")
            if rgb_overrides:
                logger.info(f"User filaments override {len(rgb_overrides)} core filaments by RGB: {rgb_overrides}")
        
        records.extend(user_records)
    
    return records


def load_maker_synonyms(json_path: Path | str | None = None) -> Dict[str, List[str]]:
    """
    Load maker synonyms from JSON files (core + user additions).
    
    Loads synonyms from both the core maker_synonyms.json file and optional
    user/user-synonyms.json file in the data directory. Synonyms are merged, with
    user additions extending or replacing core synonyms per maker.
    
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
        
        # Log synonym overrides before merging
        overridden_makers = []
        extended_makers = []
        
        # Merge user synonyms into core synonyms
        for maker, user_syn_list in user_synonyms.items():
            if maker in synonyms:
                # Check if user completely replaces or extends existing synonyms
                existing = set(synonyms[maker])
                new_synonyms = set(user_syn_list)
                
                if existing == new_synonyms:
                    # Same synonyms - no conflict
                    continue
                elif existing.isdisjoint(new_synonyms):
                    # Completely different - user replaces core synonyms
                    overridden_makers.append((maker, synonyms[maker], user_syn_list))
                    synonyms[maker] = user_syn_list
                else:
                    # Some overlap - extend existing synonym list (avoid duplicates)
                    original_count = len(synonyms[maker])
                    for syn in user_syn_list:
                        if syn not in existing:
                            synonyms[maker].append(syn)
                    if len(synonyms[maker]) > original_count:
                        extended_makers.append((maker, original_count, len(synonyms[maker])))
            else:
                # Add new maker with their synonyms
                synonyms[maker] = user_syn_list
        
        # Log override information
        if overridden_makers:
            logger.info(f"User synonyms override {len(overridden_makers)} core makers: {[(m, f'core: {c}', f'user: {u}') for m, c, u in overridden_makers]}")
        if extended_makers:
            logger.info(f"User synonyms extend {len(extended_makers)} core makers: {[(m, f'{old}->{new} synonyms') for m, old, new in extended_makers]}")
    
    return synonyms


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

        # RGB space - use simple Euclidean distance
        if space.lower() == "rgb":
            for r in self.records:
                d = euclidean(tuple(map(float, value)), tuple(map(float, r.rgb)))
                if d < best_d or (d == best_d and best_rec and _should_prefer_source(r.source, best_rec.source)):
                    best_rec, best_d = r, d
            return best_rec, best_d  # type: ignore

        # HSL space - use circular hue distance
        if space.lower() == "hsl":
            for r in self.records:
                d = hsl_euclidean(value, r.hsl)
                if d < best_d or (d == best_d and best_rec and _should_prefer_source(r.source, best_rec.source)):
                    best_rec, best_d = r, d
            return best_rec, best_d  # type: ignore

        # LCH space - use Euclidean distance with hue wraparound
        if space.lower() == "lch":
            for r in self.records:
                # LCH has circular hue like HSL, so we need special handling
                d = hsl_euclidean(value, r.lch)  # hsl_euclidean handles circular hue properly
                if d < best_d or (d == best_d and best_rec and _should_prefer_source(r.source, best_rec.source)):
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
            if d < best_d or (d == best_d and best_rec and _should_prefer_source(r.source, best_rec.source)):
                best_rec, best_d = r, d
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
        """Find all filaments by exact RGB match, with user filaments prioritized."""
        matches = self._by_rgb.get(rgb, [])
        # Sort to prioritize user sources over core sources
        return sorted(matches, key=lambda r: (not r.source.startswith('user-'), r.maker, r.type, r.color))

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
            maker: Optional maker name or list of names to filter by. Use "*" to ignore filter.
            type_name: Optional filament type or list of types to filter by. Use "*" to ignore filter.
            finish: Optional filament finish or list of finishes to filter by. Use "*" to ignore filter.
            cmc_l, cmc_c: Parameters for CMC metric.
        
        Returns:
            (nearest_filament_record, distance) tuple.
        """
        target_lab = rgb_to_lab(target_rgb)
        
        # Handle "*" wildcard filters (ignore filter if "*" is passed)
        maker_filter = None if maker == "*" else maker
        type_filter = None if type_name == "*" else type_name
        finish_filter = None if finish == "*" else finish
        
        # Apply filters by calling our powerful filter() method first!
        candidates = self.filter(maker=maker_filter, type_name=type_filter, finish=finish_filter)
        
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
                if d < best_d or (d == best_d and best_rec and _should_prefer_source(rec.source, best_rec.source)):
                    best_rec, best_d = rec, d
            except:
                # Skip filaments with invalid colors
                continue
        
        if best_rec is None:
            raise ValueError("No valid filaments found")
            
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
        cmc_l: float = ColorConstants.CMC_L_DEFAULT,
        cmc_c: float = ColorConstants.CMC_C_DEFAULT,
    ) -> List[Tuple[FilamentRecord, float]]:
        """
        Find nearest N filaments by color similarity, with optional filters.
        
        Similar to nearest_filament but returns multiple results sorted by distance.
        
        Args:
            target_rgb: Target RGB color tuple.
            metric: Distance metric - 'euclidean', 'de76', 'de94', 'de2000', 'cmc'.
            count: Number of results to return (default: 5, max: 50)
            maker: Optional maker name or list of names to filter by. Use "*" to ignore filter.
            type_name: Optional filament type or list of types to filter by. Use "*" to ignore filter.
            finish: Optional filament finish or list of finishes to filter by. Use "*" to ignore filter.
            cmc_l, cmc_c: Parameters for CMC metric.
        
        Returns:
            List of (filament_record, distance) tuples sorted by distance (closest first).
        """
        # Limit count to reasonable maximum
        count = min(count, 50)
        count = max(count, 1)
        
        target_lab = rgb_to_lab(target_rgb)
        
        # Handle "*" wildcard filters (ignore filter if "*" is passed)
        maker_filter = None if maker == "*" else maker
        type_filter = None if type_name == "*" else type_name
        finish_filter = None if finish == "*" else finish
        
        # Apply filters by calling our powerful filter() method first!
        candidates = self.filter(maker=maker_filter, type_name=type_filter, finish=finish_filter)
        
        if not candidates:
            raise ValueError("No filaments match the specified filters")

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

        results: List[Tuple[FilamentRecord, float]] = []
        for rec in candidates:
            try:
                d = distance_fn(target_lab, rec.lab)
                results.append((rec, d))
            except:
                # Skip filaments with invalid colors
                continue
        
        if not results:
            raise ValueError("No valid filaments found")
        
        results.sort(key=lambda x: x[1])
        return results[:count]

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

    def get_override_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about user overrides in this filament palette.
        
        Returns:
            Dictionary with override information structure:
            
            .. code-block:: python
            
                {
                    "filaments": {
                        "rgb": {"(r,g,b)": {"core": [sources], "user": [sources]}}
                    },
                    "synonyms": {
                        "maker_name": {
                            "type": "replaced|extended",
                            "old": [core_synonyms],
                            "new": [user_synonyms]
                        }
                    }
                }
        """
        from typing import Any
        
        overrides: Dict[str, Dict[str, Any]] = {
            "filaments": {"rgb": {}},
            "synonyms": {}
        }
        
        # Check for filament RGB overrides
        rgb_groups: Dict[Tuple[int, int, int], List[FilamentRecord]] = {}
        for record in self.records:
            if record.rgb not in rgb_groups:
                rgb_groups[record.rgb] = []
            rgb_groups[record.rgb].append(record)
        
        for rgb, records in rgb_groups.items():
            core_records = [r for r in records if not r.source.startswith('user-')]
            user_records = [r for r in records if r.source.startswith('user-')]
            if core_records and user_records:
                overrides["filaments"]["rgb"][str(rgb)] = {
                    "core": [r.source for r in core_records],
                    "user": [r.source for r in user_records]
                }
        
        # Check for synonym overrides
        if self.maker_synonyms:
            # We need to reconstruct what the core synonyms were vs user synonyms
            # This is complex since synonyms are already merged, but we can infer from source patterns
            # For testing purposes, we'll create a basic detection
            
            # Load core synonyms to compare
            try:
                from color_tools.palette import load_maker_synonyms
                core_synonyms = {}
                try:
                    # Try to load core synonyms from default location
                    import json
                    from pathlib import Path
                    core_file = Path(__file__).parent / "data" / "maker_synonyms.json"
                    if core_file.exists():
                        with open(core_file, 'r') as f:
                            core_synonyms = json.load(f)
                except:
                    pass
                
                # Compare current synonyms with core synonyms
                for maker, current_synonyms in self.maker_synonyms.items():
                    if maker in core_synonyms:
                        core_syns = core_synonyms[maker]
                        if set(current_synonyms) != set(core_syns):
                            overrides["synonyms"][maker] = {
                                "type": "replaced",
                                "old": core_syns,
                                "new": current_synonyms
                            }
                    # If maker not in core synonyms, it's an addition (not override)
            except:
                # If we can't load core synonyms, skip synonym override detection
                pass
        
        return overrides

