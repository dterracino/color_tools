#!/usr/bin/env python3
"""
Extract Panchroma filament data from Polymaker PDF.

Panchroma products appear in the Polymaker PDF but are a separate brand.
This script extracts them into a separate JSON file for validation.
"""

import json
import re
from pathlib import Path
from collections import defaultdict
import pdfplumber


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    # Replace + with -plus (e.g., "PLA+" -> "pla-plus", "Silk+" -> "silk-plus")
    text = text.replace('+', '-plus')
    # Remove other special chars
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def generate_slug(filament: dict) -> str:
    """Generate a slug ID for a filament."""
    parts = [slugify(filament['maker']), slugify(filament['type'])]
    if filament.get('finish'):
        parts.append(slugify(filament['finish']))
    parts.append(slugify(filament['color']))
    return '-'.join(parts)


def parse_product_name(product_name: str) -> tuple[str | None, str | None]:
    """
    Parse Panchroma product name to extract type and finish.
    
    Examples:
        "Panchroma CoPE" -> ("CoPE", None)
        "Panchroma PLA" -> ("PLA", None)
        "Panchroma Translucent" -> ("PLA", "Translucent")
        "Panchroma Celestial" -> ("PLA", "Celestial")
        "Panchroma Starlight" -> ("PLA", "Starlight")
        "Panchroma Galaxy" -> ("PLA", "Galaxy")
        "Panchroma Neon" -> ("PLA", "Neon")
        "Panchroma Metallic" -> ("PLA", "Metallic")
    
    Args:
        product_name: Product name from PDF
    
    Returns:
        Tuple of (type, finish) or (None, None) if should skip
    """
    # Clean up newlines and extra spaces
    product_name = product_name.replace('\n', ' ').strip()
    product_name = ' '.join(product_name.split())  # Normalize whitespace
    
    # Only process Panchroma products
    if 'Panchroma' not in product_name:
        return None, None
    
    # Parse Panchroma product format: "Panchroma TYPE" or "Panchroma FINISH"
    parts = product_name.split()
    
    if len(parts) >= 2 and parts[0] == 'Panchroma':
        type_or_finish = ' '.join(parts[1:])
        
        # Known finishes (everything else defaults to type)
        finishes = ['Translucent', 'Celestial', 'Starlight', 'Galaxy', 'Neon', 
                   'Metallic', 'Dual Matte', 'Dual Silk', 'Matte', 'Silk', 
                   'Satin', 'Marble', 'Glow', 'Luminous', 'UV Shift']
        
        if type_or_finish in finishes or any(f in type_or_finish for f in ['Dual', 'UV']):
            # It's a finish - type is PLA
            return 'PLA', type_or_finish
        else:
            # It's a type (CoPE, etc.) with no finish
            return type_or_finish, None
    
    return None, None


def extract_panchroma_filaments(pdf_path: Path) -> list[dict]:
    """Extract Panchroma filament data from PDF."""
    filaments = []
    
    print("=" * 80)
    print("PANCHROMA PDF DATA EXTRACTION")
    print("=" * 80)
    print(f"\n📖 Opening PDF: {pdf_path}")
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"   Total pages: {len(pdf.pages)}")
        
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"\n📄 Processing page {page_num}...", end=" ")
            
            tables = page.extract_tables()
            if not tables:
                print("No tables")
                continue
            
            page_filaments = []
            for table in tables:
                if not table or len(table) < 2:
                    continue
                
                # Find header row (might not be first row, or might not exist)
                header_row = None
                product_idx = color_idx = hex_idx = None
                
                for i, row in enumerate(table[:3]):  # Check first 3 rows
                    if row and any(cell and 'Product' in str(cell) for cell in row):
                        header_row = i
                        break
                
                if header_row is not None:
                    # We found a header row - use it to find column indices
                    headers = [str(cell).strip() if cell else '' for cell in table[header_row]]
                    
                    # Find column indices
                    try:
                        product_idx = next(i for i, h in enumerate(headers) if 'Product' in h or 'Name' in h)
                        color_idx = next(i for i, h in enumerate(headers) if 'Color' in h and 'Name' in h)
                        hex_idx = next(i for i, h in enumerate(headers) if 'HEX' in h.upper() or 'Code' in h)
                    except StopIteration:
                        continue
                    
                    data_start = header_row + 1
                else:
                    # No header row - assume standard column order: SKU, Product Name, Color Name, HEX Code, TD
                    product_idx = 1
                    color_idx = 2
                    hex_idx = 3
                    data_start = 0
                
                # Process data rows
                for row in table[data_start:]:
                    if not row or len(row) < max(product_idx, color_idx, hex_idx) + 1:
                        continue
                    
                    # Clean up linefeeds and extra spaces FIRST
                    product_name = str(row[product_idx]) if row[product_idx] else ''
                    product_name = product_name.replace('\n', ' ').strip()
                    product_name = ' '.join(product_name.split())  # Collapse multiple spaces
                    
                    color_name = str(row[color_idx]) if row[color_idx] else ''
                    color_name = color_name.replace('\n', ' ').strip()
                    color_name = ' '.join(color_name.split())  # Collapse multiple spaces
                    
                    # Fix spaces around hyphens in parentheses: "(Gold- Magenta)" -> "(Gold-Magenta)"
                    import re
                    color_name = re.sub(r'\(\s*([^)]+?)\s*-\s*([^)]+?)\s*\)', r'(\1-\2)', color_name)
                    
                    hex_value = str(row[hex_idx]) if row[hex_idx] else ''
                    hex_value = hex_value.replace('\n', ' ').strip()
                    hex_value = ' '.join(hex_value.split())  # Collapse multiple spaces
                    
                    if not product_name or not color_name:
                        continue
                    
                    # Skip filaments with no hex value (gradient filaments, etc.)
                    # These can't be used for color matching anyway
                    if not hex_value:
                        continue
                    
                    # Parse product name
                    filament_type, finish = parse_product_name(product_name)
                    
                    if not filament_type:
                        continue  # Skip non-Panchroma products
                    
                    # Clean hex value
                    hex_value = hex_value.upper()
                    if not hex_value.startswith('#'):
                        hex_value = '#' + hex_value
                    
                    # Handle dual-color filaments: convert comma separator to dash
                    # Library expects "#AABBCC-#DDEEFF" but PDF has "#AABBCC, #DDEEFF"
                    if ',' in hex_value:
                        hex_parts = [h.strip() for h in hex_value.split(',')]
                        # Ensure both parts have # prefix
                        hex_parts = [h if h.startswith('#') else '#' + h for h in hex_parts]
                        hex_value = '-'.join(hex_parts)
                    
                    filament = {
                        'maker': 'Panchroma',
                        'type': filament_type,
                        'finish': finish,
                        'color': color_name,
                        'hex': hex_value,
                        'td_value': None
                    }
                    
                    page_filaments.append(filament)
            
            print(f"Found {len(page_filaments)} filaments")
            filaments.extend(page_filaments)
    
    print("\n" + "=" * 80)
    print("Extraction complete!")
    print("=" * 80)
    print(f"✅ Extracted {len(filaments)} filaments")
    
    return filaments


def main():
    # Paths
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    pdf_path = project_dir / '.source_data' / 'Polymaker.pdf'
    output_path = script_dir / 'panchroma_extracted.json'
    
    # Extract
    filaments = extract_panchroma_filaments(pdf_path)
    
    # Generate slugs with collision detection
    slug_counts = defaultdict(int)
    for filament in filaments:
        base_slug = generate_slug(filament)
        slug_counts[base_slug] += 1
        if slug_counts[base_slug] > 1:
            filament['slug'] = f"{base_slug}-{slug_counts[base_slug]}"
        else:
            filament['slug'] = base_slug
    
    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filaments, f, indent=2, ensure_ascii=False)
    
    # Count collisions
    collisions = sum(1 for count in slug_counts.values() if count > 1)
    unique_slugs = len(set(f['slug'] for f in filaments))
    
    print(f"📝 Saved to: {output_path}")
    print(f"🏷️  Generated {unique_slugs} unique slugs ({collisions} collision patterns)")


if __name__ == '__main__':
    main()
