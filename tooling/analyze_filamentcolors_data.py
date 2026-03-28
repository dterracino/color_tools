"""
Analyze FilamentColors.xyz data against our filament database.

This script compares the filtered swatches data (based on manufacturers-import.json)
with our existing filaments.json to generate a summary report showing:
- Missing/Matched Manufacturers
- Missing/Matched Filaments
- TD Data Completions (where we can add missing TD values)

Usage:
    python analyze_filamentcolors_data.py
"""

import json
import random
import re
from pathlib import Path
from collections import defaultdict

# Paths
SOURCE_DIR = Path(__file__).parent.parent / ".source_data" / "filamentcolors.xyz"
SWATCHES_FILE = SOURCE_DIR / "swatches.json"
MANUFACTURERS_IMPORT_FILE = SOURCE_DIR / "manufacturers-import.json"
OUTPUT_DIR = SOURCE_DIR / "import_data"  # Output directory for generated files
OUR_DATA_DIR = Path(__file__).parent.parent / "color_tools" / "data"
OUR_FILAMENTS_FILE = OUR_DATA_DIR / "filaments.json"
OUR_SYNONYMS_FILE = OUR_DATA_DIR / "maker_synonyms.json"


def extract_finish_from_name(color_name):
    """
    Extract finish from color name ONLY if we're absolutely certain.
    
    Conservative extraction - only for known manufacturer patterns.
    Otherwise returns (None, original_name) to avoid data corruption.
    
    Returns:
        tuple: (finish or None, cleaned_color_name or original_name)
    """
    # ONLY extract finishes we're 100% certain about
    # These are manufacturer-specific naming conventions we trust
    certain_finishes = [
        "Matte ",      # Bambu Lab convention
        "Silk ",       # Bambu Lab convention  
        "Basic ",      # Bambu Lab convention
    ]
    
    for finish_prefix in certain_finishes:
        if color_name.startswith(finish_prefix):
            finish = finish_prefix.strip()
            cleaned_name = color_name.replace(finish_prefix, "", 1)
            return finish, cleaned_name
    
    # For everything else: keep original name, no finish extraction
    # We can post-process these later with better logic or manual curation
    return None, color_name


def extract_finish_from_type(type_name):
    """
    Extract finish from type field if present.
    
    Many manufacturers use patterns like "Silk PLA", "PLA Matte", "Glow PLA".
    
    Returns:
        tuple: (base_type, finish or None)
    """
    # Known finish patterns in type names
    type_patterns = [
        ("Silk PLA", "PLA", "Silk"),
        ("PLA Silk", "PLA", "Silk"),
        ("Matte PLA", "PLA", "Matte"),
        ("PLA Matte", "PLA", "Matte"),
        ("Glow PLA", "PLA", "Glow"),
        ("PLA Glow", "PLA", "Glow"),
    ]
    
    for pattern, base_type, finish in type_patterns:
        if type_name == pattern:
            return base_type, finish
    
    # No finish in type
    return type_name, None


def normalize_maker_name(name):
    """Normalize manufacturer name for matching (lowercase, strip)."""
    return name.lower().strip()


def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug.
    
    Args:
        text: Input text to slugify
    
    Returns:
        Lowercase slug with hyphens
    """
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special chars with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text


def generate_slug(filament: dict, include_finish: bool = True) -> str:
    """
    Generate a slug ID for a filament.
    
    Args:
        filament: Filament dictionary
        include_finish: Whether to include finish in slug (if it exists)
    
    Returns:
        Slug string
    """
    parts = [
        slugify(filament['maker']),
        slugify(filament['type']),
    ]
    
    # Add finish if it exists and we want to include it
    if include_finish and filament.get('finish'):
        parts.append(slugify(filament['finish']))
    
    # Add color
    parts.append(slugify(filament['color']))
    
    return '-'.join(parts)


def expand_maker_with_synonyms(maker_name, synonyms_dict):
    """
    Expand a maker name to include all synonyms and canonical forms.
    
    Returns a set of all normalized names that could match this maker.
    """
    normalized = normalize_maker_name(maker_name)
    matches = {normalized}
    
    # Check if this is a canonical name in our synonyms
    for canonical, synonym_list in synonyms_dict.items():
        canonical_norm = normalize_maker_name(canonical)
        
        # If the name matches the canonical name, add all synonyms
        if normalized == canonical_norm:
            matches.update(normalize_maker_name(s) for s in synonym_list)
        
        # If the name matches any synonym, add the canonical and all other synonyms
        if any(normalized == normalize_maker_name(s) for s in synonym_list):
            matches.add(canonical_norm)
            matches.update(normalize_maker_name(s) for s in synonym_list)
    
    return matches


def load_our_filaments():
    """Load our existing filaments database."""
    with open(OUR_FILAMENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_maker_synonyms():
    """Load our maker synonyms."""
    if OUR_SYNONYMS_FILE.exists():
        with open(OUR_SYNONYMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def create_filament_key(maker, type_name, finish, color):
    """Create a unique key for filament matching."""
    # Normalize all components
    maker_norm = normalize_maker_name(maker)
    type_norm = type_name.upper().strip()
    finish_norm = (finish or "").strip()
    color_norm = color.lower().strip()
    
    return f"{maker_norm}|{type_norm}|{finish_norm}|{color_norm}"


def analyze_data():
    """Analyze FilamentColors.xyz data against our database."""
    
    # Load our data
    print("Loading our filament database...")
    our_filaments = load_our_filaments()
    our_synonyms = load_maker_synonyms()
    
    print(f"  - {len(our_filaments)} filaments in our database")
    
    # Build our filament lookup (by key) and expand maker names with synonyms
    our_filaments_by_key = {}
    our_makers_expanded = set()
    
    for fil in our_filaments:
        maker = fil.get("maker", "")
        type_name = fil.get("type", "")
        finish = fil.get("finish", "")
        color = fil.get("color", "")
        
        # Add all synonym variations of this maker
        our_makers_expanded.update(expand_maker_with_synonyms(maker, our_synonyms))
        
        key = create_filament_key(maker, type_name, finish, color)
        our_filaments_by_key[key] = fil
    
    print(f"  - {len(our_makers_expanded)} unique manufacturer names (including synonyms)")
    
    # Load import manufacturers
    print("\nLoading manufacturers-import.json...")
    if not MANUFACTURERS_IMPORT_FILE.exists():
        print(f"Error: {MANUFACTURERS_IMPORT_FILE} not found")
        print("Run extract_filamentcolors_manufacturers.py and create the import file first.")
        return
    
    with open(MANUFACTURERS_IMPORT_FILE, "r", encoding="utf-8") as f:
        import_manufacturers = json.load(f)
    
    import_maker_ids = {m["id"] for m in import_manufacturers}
    import_maker_names = {m["id"]: m["name"] for m in import_manufacturers}
    
    print(f"  - {len(import_manufacturers)} manufacturers selected for import")
    
    # Load swatches
    print("\nLoading swatches.json...")
    if not SWATCHES_FILE.exists():
        print(f"Error: {SWATCHES_FILE} not found")
        print("Run filamentcolors_library.py first to download the data.")
        return
    
    with open(SWATCHES_FILE, "r", encoding="utf-8") as f:
        all_swatches = json.load(f)
    
    print(f"  - {len(all_swatches)} total swatches")
    
    # Filter swatches to selected manufacturers
    filtered_swatches = []
    their_makers = set()
    
    for swatch in all_swatches:
        mfr_id = swatch.get("manufacturer", {}).get("id")
        if mfr_id in import_maker_ids:
            filtered_swatches.append(swatch)
            mfr_name = swatch.get("manufacturer", {}).get("name", "")
            their_makers.add(normalize_maker_name(mfr_name))
    
    print(f"  - {len(filtered_swatches)} swatches from selected manufacturers")
    
    # Match filaments
    print("\nAnalyzing filament matches...")
    
    matched_filaments = 0
    matched_no_td = 0
    missing_filaments = 0
    td_completions = 0
    missing_filament_details = []
    td_completion_details = []
    matched_no_td_details = []
    
    # Debug: TD value tracking
    swatches_with_td = 0
    swatches_without_td = 0
    
    # Debug: Finish extraction tracking
    finish_extracted_samples = []
    finish_not_extracted_samples = []
    
    for swatch in filtered_swatches:
        maker = swatch.get("manufacturer", {}).get("name", "")
        type_name = swatch.get("filament_type", {}).get("name", "")
        color_name = swatch.get("color_name", "")
        td_value = swatch.get("td")
        
        # Debug: Track TD values in source data
        if td_value is not None:
            swatches_with_td += 1
        else:
            swatches_without_td += 1
        
        # Extract finish from TYPE field first (e.g., "Silk PLA" → PLA + Silk)
        base_type, type_finish = extract_finish_from_type(type_name)
        
        # Extract finish from color name (e.g., "Matte Black" → Matte + Black)
        name_finish, cleaned_color = extract_finish_from_name(color_name)
        
        # Prefer finish from type over finish from name
        finish = type_finish or name_finish
        
        # Create matching key
        key = create_filament_key(maker, base_type, finish, cleaned_color)
        
        if key in our_filaments_by_key:
            matched_filaments += 1
            
            # Check for TD completion opportunity
            our_fil = our_filaments_by_key[key]
            our_td = our_fil.get("td_value")
            
            # Count matched filaments missing TD
            if our_td is None:
                matched_no_td += 1
                matched_no_td_details.append({
                    "maker": maker,
                    "type": type_name,
                    "finish": finish,
                    "color": cleaned_color,
                    "their_td": td_value
                })
            
            if our_td is None and td_value is not None:
                td_completions += 1
                td_completion_details.append({
                    "maker": maker,
                    "type": type_name,
                    "finish": finish,
                    "color": cleaned_color,
                    "their_td": td_value
                })
        else:
            missing_filaments += 1
            missing_filament_details.append({
                "maker": maker,
                "type": base_type,
                "finish": finish or "(no finish detected)",
                "color": cleaned_color,
                "hex": swatch.get("hex_color", ""),
                "td": td_value
            })
            
            # Track finish extraction samples
            if finish:
                finish_extracted_samples.append({
                    "maker": maker,
                    "original_name": color_name,
                    "original_type": type_name,
                    "extracted_finish": finish,
                    "cleaned_color": cleaned_color,
                    "base_type": base_type
                })
            else:
                finish_not_extracted_samples.append({
                    "maker": maker,
                    "original_name": color_name,
                    "type": type_name
                })
    
    # Calculate manufacturer matches (using synonym-expanded sets)
    matched_makers = our_makers_expanded & their_makers
    missing_makers = their_makers - our_makers_expanded
    
    # Separate missing filaments by manufacturer type (new vs existing)
    new_manufacturer_filaments = {}  # {maker_name: [filaments]}
    existing_manufacturer_filaments = []  # List of filaments from manufacturers we have
    
    for detail in missing_filament_details:
        maker = detail["maker"]
        maker_norm = normalize_maker_name(maker)
        
        # Check if this is a new manufacturer or existing
        if maker_norm in missing_makers:
            # New manufacturer
            if maker not in new_manufacturer_filaments:
                new_manufacturer_filaments[maker] = []
            new_manufacturer_filaments[maker].append(detail)
        else:
            # Existing manufacturer with missing filament
            existing_manufacturer_filaments.append(detail)
    
    # Generate report
    print("\n" + "="*60)
    print("FILAMENTCOLORS.XYZ DATA ANALYSIS REPORT")
    print("="*60)
    
    print("\nMANUFACTURERS:")
    print(f"  Matched Manufacturers:  {len(matched_makers)}")
    print(f"  Missing Manufacturers:  {len(missing_makers)}")
    
    if missing_makers:
        print("\n  Missing manufacturer details:")
        for maker_norm in sorted(missing_makers):
            # Find original name
            for swatch in filtered_swatches:
                if normalize_maker_name(swatch.get("manufacturer", {}).get("name", "")) == maker_norm:
                    print(f"    - {swatch.get('manufacturer', {}).get('name', '')}")
                    break
    
    print("\nFILAMENTS:")
    print(f"  Matched Filaments:      {matched_filaments}")
    print(f"  Matched Filaments (No TD): {matched_no_td}")
    print(f"  Missing Filaments:      {missing_filaments}")
    print(f"  TD Data Completions:    {td_completions}")
    
    print("\nTD DATA AVAILABILITY:")
    print(f"  Swatches with TD:       {swatches_with_td}")
    print(f"  Swatches without TD:    {swatches_without_td}")
    print(f"  TD Coverage:            {swatches_with_td / len(filtered_swatches) * 100:.1f}%")
    
    # Show matched filaments missing TD (to understand why no completions)
    if matched_no_td_details:
        print(f"\n  Matched filaments missing TD in our DB (all {len(matched_no_td_details)}):")
        for fil in matched_no_td_details:
            finish_str = fil['finish'] or "NO_FINISH"
            their_td_str = f"TD={fil['their_td']}" if fil['their_td'] is not None else "TD=None"
            print(f"    - {fil['maker']} {fil['type']} {finish_str} - {fil['color']} ({their_td_str})")
    
    # Show sample of missing filaments
    if missing_filament_details:
        print(f"\n  Sample missing filaments (first 10):")
        for fil in missing_filament_details[:10]:
            finish_str = fil['finish'] if fil['finish'] != "(no finish detected)" else "NO_FINISH"
            print(f"    - {fil['maker']} {fil['type']} {finish_str} - {fil['color']} (#{fil['hex']}, TD={fil['td']})")
        
        if len(missing_filament_details) > 10:
            print(f"    ... and {len(missing_filament_details) - 10} more")
    
    # Show sample of TD completions
    if td_completion_details:
        print(f"\n  Sample TD completions (first 10):")
        for fil in td_completion_details[:10]:
            finish_str = fil['finish'] or "NO_FINISH"
            print(f"    - {fil['maker']} {fil['type']} {finish_str} - {fil['color']} (TD={fil['their_td']})")
        
        if len(td_completion_details) > 10:
            print(f"    ... and {len(td_completion_details) - 10} more")
    
    # Show finish extraction samples
    print("\nFINISH EXTRACTION ANALYSIS:")
    print(f"  Finishes extracted:     {len(finish_extracted_samples)}")
    print(f"  No finish detected:     {len(finish_not_extracted_samples)}")
    
    if finish_extracted_samples:
        sample_size = min(50, len(finish_extracted_samples))
        samples = random.sample(finish_extracted_samples, sample_size)
        print(f"\n  Random sample of EXTRACTED finishes ({sample_size}):")
        for sample in samples:
            type_info = f" (from type: {sample['original_type']})" if sample['original_type'] != sample['base_type'] else ""
            print(f"    {sample['maker']} - Original: '{sample['original_name']}'{type_info}")
            print(f"      → Type: {sample['base_type']}, Finish: {sample['extracted_finish']}, Color: {sample['cleaned_color']}")
    
    if finish_not_extracted_samples:
        sample_size = min(50, len(finish_not_extracted_samples))
        samples = random.sample(finish_not_extracted_samples, sample_size)
        print(f"\n  Random sample of NO FINISH detected ({sample_size}):")
        for sample in samples:
            print(f"    {sample['maker']} {sample['type']} - '{sample['original_name']}'")
    
    print("\n" + "="*60)
    print(f"\nTotal swatches analyzed: {len(filtered_swatches)}")
    print(f"Our database size:       {len(our_filaments)}")
    print("="*60)
    
    # Generate import data files
    print("\nGenerating import data files...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write one file per new manufacturer
    for maker, filaments in new_manufacturer_filaments.items():
        # Convert to our filament format
        output_filaments = []
        for fil in filaments:
            finish = None if fil["finish"] == "(no finish detected)" else fil["finish"]
            finish = None if finish == "" else finish
            
            filament_dict = {
                "maker": maker,
                "type": fil["type"],
                "finish": finish,
                "color": fil["color"],
                "hex": f"#{fil['hex']}",
                "td_value": fil["td"]
            }
            
            output_filaments.append({
                "id": generate_slug(filament_dict),
                **filament_dict
            })
        
        # Create safe filename from maker name
        safe_maker = maker.replace(" ", "_").replace("/", "-")
        output_file = OUTPUT_DIR / f"new_maker_{safe_maker}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_filaments, f, indent=2, ensure_ascii=False)
        
        print(f"  - {output_file.name}: {len(output_filaments)} filaments from {maker}")
    
    # Write one file for all missing filaments from existing manufacturers
    if existing_manufacturer_filaments:
        output_filaments = []
        for fil in existing_manufacturer_filaments:
            finish = None if fil["finish"] == "(no finish detected)" else fil["finish"]
            finish = None if finish == "" else finish
            
            filament_dict = {
                "maker": fil["maker"],
                "type": fil["type"],
                "finish": finish,
                "color": fil["color"],
                "hex": f"#{fil['hex']}",
                "td_value": fil["td"]
            }
            
            output_filaments.append({
                "id": generate_slug(filament_dict),
                **filament_dict
            })
        
        output_file = OUTPUT_DIR / "existing_makers_missing_filaments.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_filaments, f, indent=2, ensure_ascii=False)
        
        print(f"  - {output_file.name}: {len(output_filaments)} filaments from existing manufacturers")
    
    print(f"\nData files written to: {OUTPUT_DIR}")
    print("="*60)


if __name__ == "__main__":
    analyze_data()
