"""
Import HueForge filament data from .source_data/import/ directory.

This script imports new filament data and TD values from the HueForge data files.

Import Rules:
1. Exact match required: maker + type + finish + color name + hex code
2. If exact match found:
   - If our td_value is None AND new data has TD → update TD value only
   - Otherwise → skip (our data is authoritative)
3. If no match found → add as new filament
4. If name matches but hex differs → report conflict and skip

Usage:
    python tooling/import_hueforge_data.py              # Dry run (preview)
    python tooling/import_hueforge_data.py --apply      # Actually apply changes
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import hashlib

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))


@dataclass
class NewFilament:
    """Filament from import data."""
    maker: str
    name: str           # Color name
    type_raw: str       # Original type string (e.g., "PLA Basic")
    type: str           # Parsed material (e.g., "PLA")
    finish: Optional[str]  # Parsed finish (e.g., "Basic")
    hex: str            # Hex code
    td: Optional[float] # TD value


@dataclass
class ExistingFilament:
    """Filament from our current data."""
    id: str
    maker: str
    type: str
    finish: Optional[str]
    color: str
    hex: str
    td_value: Optional[float]


@dataclass
class ImportStats:
    """Statistics for import operation."""
    manufacturers_in_index: int = 0
    data_files_found: int = 0
    data_files_missing: int = 0
    new_manufacturers: list[str] = field(default_factory=list)  # Manufacturers not in our data yet
    existing_manufacturers: list[str] = field(default_factory=list)  # Manufacturers already in our data
    new_filaments: list[NewFilament] = field(default_factory=list)
    td_updates: list[tuple[ExistingFilament, float]] = field(default_factory=list)  # (existing, new_td)
    conflicts: list[tuple[NewFilament, ExistingFilament]] = field(default_factory=list)  # (new, existing)
    skipped_has_td: int = 0


def parse_type_finish(type_string: str) -> tuple[str, Optional[str]]:
    """
    Parse 'type' field into material type and finish.
    
    Examples:
        "PLA Silk" → ("PLA", "Silk")
        "PLA Basic" → ("PLA", "Basic")  
        "PLA" → ("PLA", None)
        "PLA+" → ("PLA+", None)
        "PETG-CF" → ("PETG-CF", None)
    
    Args:
        type_string: Raw type string from import data
    
    Returns:
        Tuple of (material_type, finish_or_None)
    """
    parts = type_string.strip().split(maxsplit=1)
    if len(parts) == 2:
        return (parts[0], parts[1])
    else:
        return (parts[0], None)


def normalize_hex(hex_code: str) -> str:
    """Normalize hex code to uppercase without # prefix."""
    if hex_code is None:
        return ''
    hex_clean = hex_code.strip().upper()
    if hex_clean.startswith('#'):
        hex_clean = hex_clean[1:]
    return hex_clean


def generate_filament_id(maker: str, type_name: str, finish: Optional[str], color: str) -> str:
    """
    Generate unique filament ID slug.
    
    Format: maker-type-finish-color (all lowercase, spaces to hyphens)
    
    Example:
        generate_filament_id("Bambu Lab", "PLA", "Basic", "Jade White")
        → "bambu-lab-pla-basic-jade-white"
    """
    parts = [maker, type_name]
    if finish:
        parts.append(finish)
    parts.append(color)
    
    slug = '-'.join(parts)
    slug = slug.lower()
    slug = slug.replace(' ', '-')
    slug = slug.replace('_', '-')
    slug = slug.replace('+', '-plus')
    # Remove any other special characters
    slug = ''.join(c if c.isalnum() or c == '-' else '' for c in slug)
    # Collapse multiple hyphens
    while '--' in slug:
        slug = slug.replace('--', '-')
    slug = slug.strip('-')
    
    return slug


def load_index(index_path: Path) -> list[dict]:
    """Load manufacturer index."""
    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_manufacturer_data(data_path: Path) -> list[NewFilament]:
    """Load filament data for a manufacturer."""
    with open(data_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # Extract maker name from path (e.g., "bambu-lab.json" → "Bambu Lab")
    # We'll get this from the index instead
    filaments = []
    for item in raw_data:
        # SKIP ENTRIES WITH NULL/MISSING COLOR DATA
        if item.get('color') is None:
            continue  # Cannot import filaments without hex codes
            
        type_parsed, finish_parsed = parse_type_finish(item['type'])
        
        filaments.append(NewFilament(
            maker='',  # Will be set by caller
            name=item['name'],
            type_raw=item['type'],
            type=type_parsed,
            finish=finish_parsed,
            hex=item['color'],
            td=item.get('td')
        ))
    
    return filaments


def load_existing_filaments(filaments_path: Path) -> list[ExistingFilament]:
    """Load our current filament database."""
    with open(filaments_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    return [
        ExistingFilament(
            id=item['id'],
            maker=item['maker'],
            type=item['type'],
            finish=item.get('finish'),
            color=item['color'],
            hex=item['hex'],
            td_value=item.get('td_value')
        )
        for item in raw_data
    ]


def find_matching_filament(
    new: NewFilament,
    existing_filaments: list[ExistingFilament]
) -> Optional[ExistingFilament]:
    """
    Find existing filament that matches new data.
    
    Match criteria (ALL must match):
    1. Maker name (exact, case-sensitive)
    2. Type (exact, case-sensitive)
    3. Finish (exact, case-sensitive, or both None)
    4. Color name (exact, case-sensitive)
    5. Hex code (normalized, case-insensitive)
    
    Returns:
        Matching ExistingFilament or None
    """
    new_hex = normalize_hex(new.hex)
    
    for existing in existing_filaments:
        # Check all criteria
        if (existing.maker == new.maker and
            existing.type == new.type and
            existing.finish == new.finish and
            existing.color == new.name and
            normalize_hex(existing.hex) == new_hex):
            return existing
    
    return None


def find_name_conflict(
    new: NewFilament,
    existing_filaments: list[ExistingFilament]
) -> Optional[ExistingFilament]:
    """
    Find existing filament with same maker/type/finish/color but DIFFERENT hex.
    
    This detects conflicts where the color name matches but hex differs.
    
    Returns:
        Conflicting ExistingFilament or None
    """
    new_hex = normalize_hex(new.hex)
    
    for existing in existing_filaments:
        if (existing.maker == new.maker and
            existing.type == new.type and
            existing.finish == new.finish and
            existing.color == new.name and
            normalize_hex(existing.hex) != new_hex):
            return existing
    
    return None


def process_import(
    import_dir: Path,
    index_path: Path,
    filaments_path: Path
) -> ImportStats:
    """
    Process the import and generate statistics.
    
    Args:
        import_dir: Directory containing manufacturer JSON files
        index_path: Path to _index.json
        filaments_path: Path to current filaments.json
    
    Returns:
        ImportStats with preview data
    """
    stats = ImportStats()
    
    # Load index
    index = load_index(index_path)
    stats.manufacturers_in_index = len(index)
    
    # Load existing filaments
    existing_filaments = load_existing_filaments(filaments_path)
    
    # Get unique manufacturers from existing data
    existing_maker_names = set(f.maker for f in existing_filaments)
    
    # Track IDs that will exist after import (existing + new)
    used_ids = set(f.id for f in existing_filaments)
    
    # Process each manufacturer
    for manufacturer in index:
        maker_name = manufacturer['name']
        data_file = manufacturer['filaments']
        
        # Convert path to local file path
        # "/data/filaments/bambu-lab.json" → "bambu-lab.json"
        filename = Path(data_file).name
        data_path = import_dir / filename
        
        if not data_path.exists():
            stats.data_files_missing += 1
            continue
        
        stats.data_files_found += 1
        
        # Load manufacturer data
        new_filaments = load_manufacturer_data(data_path)
        
        # Track if this is a new or existing manufacturer
        if maker_name in existing_maker_names:
            if maker_name not in stats.existing_manufacturers:
                stats.existing_manufacturers.append(maker_name)
        else:
            if maker_name not in stats.new_manufacturers:
                stats.new_manufacturers.append(maker_name)
        
        # Set maker name for all filaments
        for filament in new_filaments:
            filament.maker = maker_name
        
        # Process each filament
        for new_fil in new_filaments:
            # Generate ID to check for duplicates
            new_id = generate_filament_id(new_fil.maker, new_fil.type, new_fil.finish, new_fil.name)
            
            # Check if this ID is already used (duplicate detection)
            if new_id in used_ids:
                # This is a duplicate - skip it (already in existing data or processed earlier)
                stats.skipped_has_td += 1  # Count as skipped
                continue
            
            # Try to find exact match
            existing = find_matching_filament(new_fil, existing_filaments)
            
            if existing:
                # Exact match found - check if we should update TD
                if existing.td_value is None and new_fil.td is not None:
                    stats.td_updates.append((existing, new_fil.td))
                else:
                    # Already has TD or new data has no TD
                    stats.skipped_has_td += 1
            else:
                # No exact match - check for name conflict
                conflict = find_name_conflict(new_fil, existing_filaments)
                
                if conflict:
                    # Same name but different hex
                    stats.conflicts.append((new_fil, conflict))
                else:
                    # Completely new filament - add ID to used set
                    used_ids.add(new_id)
                    stats.new_filaments.append(new_fil)
    
    return stats


def print_preview(stats: ImportStats):
    """Print dry-run preview of import."""
    print("\n" + "="*60)
    print("IMPORT PREVIEW - DRY RUN")
    print("="*60)
    
    print(f"\nSummary:")
    print(f"  - {stats.manufacturers_in_index} manufacturers in index")
    print(f"  - {stats.data_files_found} data files found")
    if stats.data_files_missing > 0:
        print(f"  - {stats.data_files_missing} manufacturers without data files")
    print(f"  - {len(stats.new_manufacturers)} new manufacturers")
    print(f"  - {len(stats.existing_manufacturers)} existing manufacturers")
    
    # New filaments
    print(f"\nNEW FILAMENTS ({len(stats.new_filaments)} total):")
    if stats.new_filaments:
        # Group by maker
        by_maker = {}
        for fil in stats.new_filaments:
            by_maker.setdefault(fil.maker, []).append(fil)
        
        for maker in sorted(by_maker.keys()):
            count = len(by_maker[maker])
            print(f"  {maker}: {count} new")
            # Show first 3 as examples
            for fil in by_maker[maker][:3]:
                finish_str = f" {fil.finish}" if fil.finish else ""
                td_str = f" (TD: {fil.td})" if fil.td is not None else ""
                print(f"    - {fil.type}{finish_str} - {fil.name} ({fil.hex}){td_str}")
            if count > 3:
                print(f"    ... and {count - 3} more")
    
    # TD updates
    print(f"\nTD VALUE UPDATES ({len(stats.td_updates)} total):")
    if stats.td_updates:
        for existing, new_td in stats.td_updates[:10]:
            finish_str = f" {existing.finish}" if existing.finish else ""
            print(f"  {existing.maker} {existing.type}{finish_str} - {existing.color}: None → {new_td}")
        if len(stats.td_updates) > 10:
            print(f"  ... and {len(stats.td_updates) - 10} more")
    
    # Conflicts
    if stats.conflicts:
        print(f"\nCONFLICTS ({len(stats.conflicts)} total):")
        for new_fil, existing in stats.conflicts[:10]:
            finish_str = f" {new_fil.finish}" if new_fil.finish else ""
            print(f"  {new_fil.maker} {new_fil.type}{finish_str} - {new_fil.name}:")
            print(f"    Existing: {existing.hex}")
            print(f"    New data: {new_fil.hex}")
            print(f"    -> SKIPPED (keeping existing data)")
        if len(stats.conflicts) > 10:
            print(f"  ... and {len(stats.conflicts) - 10} more")
    
    # Skipped
    if stats.skipped_has_td > 0:
        print(f"\nSKIPPED: {stats.skipped_has_td} filaments already have TD values")
    
    # Totals summary
    print(f"\n{'='*60}")
    print("TOTALS:")
    print(f"  New filaments to add:     {len(stats.new_filaments)}")
    print(f"  TD values to update:      {len(stats.td_updates)}")
    print(f"  Conflicts (skipped):      {len(stats.conflicts)}")
    print(f"  Already have TD (skipped): {stats.skipped_has_td}")
    print("="*60)
    print("Run with --apply to perform the import")
    print("="*60 + "\n")


def apply_import(
    stats: ImportStats,
    filaments_path: Path,
    constants_path: Path
):
    """
    Actually apply the import changes.
    
    Args:
        stats: Import statistics with changes to apply
        filaments_path: Path to filaments.json
        constants_path: Path to constants.py
    """
    # Load current filaments
    with open(filaments_path, 'r', encoding='utf-8') as f:
        current_data = json.load(f)
    
    # Apply TD updates
    for existing, new_td in stats.td_updates:
        for record in current_data:
            if record['id'] == existing.id:
                record['td_value'] = new_td
                break
    
    # Add new filaments
    for new_fil in stats.new_filaments:
        new_id = generate_filament_id(new_fil.maker, new_fil.type, new_fil.finish, new_fil.name)
        
        new_record = {
            'id': new_id,
            'maker': new_fil.maker,
            'type': new_fil.type,
            'finish': new_fil.finish,
            'color': new_fil.name,
            'hex': new_fil.hex,
            'td_value': new_fil.td
        }
        current_data.append(new_record)
    
    # Sort by maker, then type, then finish, then color
    current_data.sort(key=lambda x: (
        x['maker'],
        x['type'],
        x.get('finish') or '',
        x['color']
    ))
    
    # Write updated filaments.json
    with open(filaments_path, 'w', encoding='utf-8') as f:
        json.dump(current_data, f, indent=2, ensure_ascii=False)
    
    # Regenerate hash
    file_hash = hashlib.sha256(filaments_path.read_bytes()).hexdigest()
    
    print(f"\n✅ Import complete!")
    print(f"  - Updated {len(stats.td_updates)} TD values")
    print(f"  - Added {len(stats.new_filaments)} new filaments")
    print(f"  - Total filaments: {len(current_data)}")
    print(f"\n📝 Next steps:")
    print(f"  1. Update FILAMENTS_JSON_HASH in constants.py:")
    print(f"     FILAMENTS_JSON_HASH = \"{file_hash}\"")
    print(f"  2. Run tests to verify: python -m unittest discover tests")
    print(f"  3. Update CHANGELOG.md with import details")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Import HueForge filament data")
    parser.add_argument('--apply', action='store_true', help="Actually apply changes (default is dry-run)")
    args = parser.parse_args()
    
    # Paths
    root_dir = Path(__file__).parent.parent
    import_dir = root_dir / '.source_data' / 'import'
    index_path = import_dir / '_index.json'
    filaments_path = root_dir / 'color_tools' / 'data' / 'filaments.json'
    constants_path = root_dir / 'color_tools' / 'constants.py'
    
    # Verify paths exist
    if not index_path.exists():
        print(f"❌ Error: Index file not found: {index_path}")
        sys.exit(1)
    
    if not filaments_path.exists():
        print(f"❌ Error: Filaments file not found: {filaments_path}")
        sys.exit(1)
    
    # Process import
    print("Processing import data...")
    stats = process_import(import_dir, index_path, filaments_path)
    
    # Show preview
    print_preview(stats)
    
    # Apply if requested
    if args.apply:
        print("\nApplying changes...")
        apply_import(stats, filaments_path, constants_path)
    else:
        print("💡 This was a dry-run. No files were modified.")


if __name__ == '__main__':
    main()
