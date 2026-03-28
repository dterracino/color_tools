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
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from color_tools.constants import ColorConstants
from color_tools.conversions import rgb_to_lab, hex_to_rgb
from color_tools.distance import delta_e_2000, delta_e_94, delta_e_76, delta_e_cmc, euclidean
from color_tools.config import get_dual_color_mode
from color_tools._palette_utils import _should_prefer_source, _ensure_list

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FilamentRecord:
    """
    Immutable record representing a 3D printing filament.
    
    Filament colors are pre-computed in all major color spaces for fast matching.
    Supports dual-color filaments (some have primary and secondary colors).
    
    The `other_names` field allows for alternative color names that can be used
    to find this filament.
    
    The `source` field tracks which JSON file this filament came from
    ('filaments.json' for core data, 'user-filaments.json' for user additions).
    When there are conflicts (e.g., same RGB from multiple sources), user data
    takes priority.
    
    Args:
        id: Unique identifier for this filament (e.g., "bambu-lab_pla-matte_jet-black")
        maker: Manufacturer name (e.g., "Bambu Lab")
        type: Material type (e.g., "PLA", "PETG", "ABS")
        finish: Surface finish (e.g., "Matte", "Glossy", "Silk"). Optional.
        color: Human-readable color name (e.g., "Jet Black")
        hex: RGB color in hex format (e.g., "#000000")
        td_value: Transmission density value (0.0-1.0) for light transmission simulation. Optional.
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
    
    # Dual-color support (some filaments have two colors)
    hex2: Optional[str] = field(default=None, repr=False)
    
    def __post_init__(self) -> None:
        """Compute derived color representations in all color spaces."""
        # Choose which hex to use based on dual-color mode
        mode = get_dual_color_mode()
        
        if mode == "second" and self.hex2 is not None:
            hex_to_use = self.hex2
        elif mode == "mix" and self.hex2 is not None:
            # Mix the two colors by averaging their RGB values
            rgb1 = hex_to_rgb(self.hex)
            rgb2 = hex_to_rgb(self.hex2)
            # Handle None returns from hex_to_rgb
            if rgb1 is None or rgb2 is None:
                # Fall back to first color if conversion fails
                rgb1 = rgb1 or (0, 0, 0)
                rgb2 = rgb2 or (0, 0, 0)
            mixed_rgb = (
                (rgb1[0] + rgb2[0]) // 2,
                (rgb1[1] + rgb2[1]) // 2,
                (rgb1[2] + rgb2[2]) // 2
            )
            object.__setattr__(self, 'rgb', mixed_rgb)
            object.__setattr__(self, 'lab', rgb_to_lab(mixed_rgb))
            return
        else:
            # Default: use first color (mode == "first" or hex2 is None)
            hex_to_use = self.hex
        
        # Convert from hex (single source of truth)
        rgb = hex_to_rgb(hex_to_use)
        # Handle None return from hex_to_rgb
        if rgb is None:
            rgb = (0, 0, 0)  # Default to black if conversion fails
        lab = rgb_to_lab(rgb)
        
        # Use object.__setattr__ for frozen dataclass
        object.__setattr__(self, 'rgb', rgb)
        object.__setattr__(self, 'lab', lab)
    
    # Derived color spaces (computed in __post_init__)
    rgb: Tuple[int, int, int] = field(init=False)
    lab: Tuple[float, float, float] = field(init=False)


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


def load_owned_filaments(json_path: Path | str | None = None) -> Set[str]:
    """
    Load owned filament IDs from JSON file.
    
    Loads a list of filament IDs that the user owns from owned-filaments.json.
    This file is optional - if it doesn't exist, an empty set is returned.
    
    The JSON format is:
    ```json
    {
        "owned_filaments": ["id1", "id2", "id3"]
    }
    ```
    
    Args:
        json_path: Path to directory containing owned-filaments.json, or path to
                   specific owned filaments JSON file. If None, looks for
                   owned-filaments.json in the package's data/ directory.
    
    Returns:
        Set of owned filament IDs (empty set if file doesn't exist)
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
        raise ValueError(f"Expected {{'owned_filaments': [...]}} structure in {json_path}")
    
    owned_ids = data["owned_filaments"]
    if not isinstance(owned_ids, list):
        raise ValueError(f"Expected 'owned_filaments' to be a list in {json_path}")
    
    return set(owned_ids)


def save_owned_filaments(owned_ids: Set[str], json_path: Path | str | None = None) -> None:
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
    
    # Sort IDs for consistent output
    sorted_ids = sorted(owned_ids)
    
    # Create data structure
    data = {"owned_filaments": sorted_ids}
    
    # Save to file
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


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
    
    def __init__(self, records: List[FilamentRecord], maker_synonyms: Optional[Dict[str, List[str]]] = None, owned_filaments: Optional[Set[str]] = None) -> None:
        self.records = records
        self.maker_synonyms = maker_synonyms or {}
        self.owned_filaments = owned_filaments if owned_filaments is not None else set()
        
        # Create various lookup indices (note: Lists, not single items!)
        # Multiple filaments can share the same maker/type/color
        self._by_maker: Dict[str, List[FilamentRecord]] = {}
        self._by_type: Dict[str, List[FilamentRecord]] = {}
        self._by_color: Dict[str, List[FilamentRecord]] = {}
        self._by_rgb: Dict[Tuple[int, int, int], List[FilamentRecord]] = {}
        self._by_finish: Dict[str, List[FilamentRecord]] = {}
        self._by_id: Dict[str, FilamentRecord] = {}
        
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
            
            # By ID (unique lookup for owned filaments management)
            if rec.id:
                self._by_id[rec.id] = rec
    
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
        Also loads maker synonyms and owned filaments automatically.
        
        Auto-detects owned filaments: If owned-filaments.json exists and contains IDs,
        owned filtering will be the default behavior in filter/nearest methods.
        """
        owned = load_owned_filaments()
        return cls(load_filaments(), load_maker_synonyms(), owned)

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
        color: Optional[str] = None,
        owned: Optional[bool] = None
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
        
        Returns:
            A list of FilamentRecord objects matching the criteria.
        """
        # Auto-detect owned filtering if not explicitly specified
        if owned is None:
            owned = len(self.owned_filaments) > 0
        
        # Start with owned or all records
        if owned:
            results = [r for r in self.records if r.id in self.owned_filaments]
        else:
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
        owned: Optional[bool] = None,
        cmc_l: float = ColorConstants.CMC_L_DEFAULT,
        cmc_c: float = ColorConstants.CMC_C_DEFAULT,
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
        
        Returns:
            (nearest_filament_record, distance) tuple.
        """
        target_lab = rgb_to_lab(target_rgb)
        
        # Handle "*" wildcard filters (ignore filter if "*" is passed)
        maker_filter = None if maker == "*" else maker
        type_filter = None if type_name == "*" else type_name
        finish_filter = None if finish == "*" else finish
        
        # Apply filters by calling our powerful filter() method first!
        candidates = self.filter(maker=maker_filter, type_name=type_filter, finish=finish_filter, owned=owned)
        
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
        owned: Optional[bool] = None,
        cmc_l: float = ColorConstants.CMC_L_DEFAULT,
        cmc_c: float = ColorConstants.CMC_C_DEFAULT,
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
        candidates = self.filter(maker=maker_filter, type_name=type_filter, finish=finish_filter, owned=owned)
        
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
                import json
                core_file = Path(__file__).parent / "data" / "maker_synonyms.json"
                core_synonyms = {}
                if core_file.exists():
                    with open(core_file, 'r') as f:
                        core_synonyms = json.load(f)
                
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
        owned_records = [self._by_id[fid] for fid in self.owned_filaments if fid in self._by_id]
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

    def remove_owned(self, filament_id: str, json_path: Path | str | None = None) -> None:
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
