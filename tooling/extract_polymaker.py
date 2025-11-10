#!/usr/bin/env python3
"""
Extract Polymaker filament data from PDF.

This script reads the Polymaker.pdf file and extracts filament information
including correct types (PLA, PETG, PC-PBT, etc.), colors, and hex codes.
"""

import pdfplumber
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict


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


def extract_hex_code(text: str) -> Optional[str]:
    """
    Extract hex code from text.
    
    Args:
        text: Text that may contain a hex code
    
    Returns:
        Hex code with # prefix, or None
    """
    # Look for patterns like #RRGGBB or RRGGBB
    match = re.search(r'#?([0-9A-Fa-f]{6})', text)
    if match:
        return '#' + match.group(1).upper()
    return None


def parse_product_name(product_name: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse product name into type and finish.
    
    Examples:
        "PolyLite PLA" -> ("PLA", "PolyLite")
        "PolyMax PC" -> ("PC", "PolyMax")
        "PolyFlex TPU90" -> ("TPU90", "PolyFlex")
        "Panchroma CoPE" -> (None, None) - skip Panchroma
        "PolyLite LW-PLA" -> ("LW-PLA", "PolyLite")
        "PolySupport for PA12" -> (None, None) - skip support materials
        "PolyDissolve S1" -> (None, None) - skip dissolve materials
        "PolyCast" -> (None, None) - skip cast materials
        "Fiberon PPS-CF10" -> ("PPS-CF10", "Fiberon")
    
    Args:
        product_name: Product name from PDF
    
    Returns:
        Tuple of (type, finish) or (None, None) if should skip
    """
    # Clean up newlines and extra spaces
    product_name = product_name.replace('\n', ' ').strip()
    product_name = ' '.join(product_name.split())  # Normalize whitespace
    
    # Skip Panchroma products (different maker)
    if 'Panchroma' in product_name:
        return None, None
    
    # Skip support/dissolve/cast materials
    skip_products = ['PolySupport', 'PolyDissolve', 'PolyCast', 'for Production']
    for skip in skip_products:
        if skip in product_name:
            return None, None
    
    # Handle different Polymaker product lines
    parts = product_name.split()
    
    # Special case: "Polylite PLA Pro - 3D Print General" -> "Polylite PLA Pro"
    # Special case: "Polylite PLA Pro - LM Show" -> "Polylite PLA Pro"
    if 'PLA Pro - 3D Print General' in product_name or 'PLA Pro - LM Show' in product_name:
        return 'PLA Pro', 'PolyLite'
    
    if len(parts) >= 2:
        # Standard pattern: "Finish Type"
        finish = parts[0]  # PolyLite, PolyMax, PolyFlex, PolySonic, PolySmooth, Fiberon, etc.
        filament_type = ' '.join(parts[1:])  # PLA, PETG, PC, TPU90, LW-PLA, PPS-CF10, etc.
        
        # Clean up any remaining spaces around hyphens in type
        filament_type = filament_type.replace(' -', '-').replace('- ', '-')
        
        # Special case: Fiberon products have no finish
        if finish == 'Fiberon':
            return filament_type, None
        
        return filament_type, finish
    
    return None, None


def parse_color_name(color_name: str, product_name: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse color name, handling special cases.
    
    Args:
        color_name: Color name from PDF
        product_name: Product name for context
    
    Returns:
        Tuple of (type_override, finish_override, color)
        If type_override or finish_override is not None, use it instead of parsed value
    """
    # Clean up
    color_name = color_name.replace('\n', ' ').strip()
    color_name = ' '.join(color_name.split())
    
    # Special case: "Hedgehog Makes - Galaxy Red" with product "Hedgehog Makes-Galaxy"
    # Should be: type="PLA", finish="Galaxy", color="Galaxy Red"
    if 'Hedgehog Makes - Galaxy' in color_name:
        # Extract color after "Galaxy"
        color = color_name.replace('Hedgehog Makes - ', '')
        return 'PLA', 'Galaxy', color
    
    # Special case: "3D Print General Flat Dark Earth" -> color includes the full name
    # These are branded/special editions, keep as-is
    
    return None, None, color_name


def parse_polymaker_pdf(pdf_path: Path) -> List[Dict]:
    """
    Parse Polymaker PDF and extract filament data.
    
    Args:
        pdf_path: Path to Polymaker.pdf
    
    Returns:
        List of filament dictionaries
    """
    print(f"📖 Opening PDF: {pdf_path}")
    
    filaments = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"   Total pages: {len(pdf.pages)}\n")
        
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"📄 Processing page {page_num}...", end=' ')
            
            # Extract tables
            tables = page.extract_tables()
            
            if tables:
                entries_found = 0
                for table in tables:
                    # Skip header row
                    for row in table[1:]:  # Skip first row (headers)
                        if len(row) >= 4:  # Need at least SKU, Product, Color, HEX
                            sku = row[0] if row[0] else ''
                            product_name = row[1] if row[1] else ''
                            color_name = row[2] if row[2] else ''
                            hex_code = row[3] if row[3] else ''
                            td_value = row[4] if len(row) > 4 and row[4] else None
                            
                            # Skip empty rows
                            if not product_name or not color_name or not hex_code:
                                continue
                            
                            # Parse product name into type and finish
                            filament_type, finish = parse_product_name(product_name)
                            
                            # Skip if should be excluded
                            if filament_type is None:
                                continue
                            
                            # Clean up color name and check for special cases
                            type_override, finish_override, color_name = parse_color_name(color_name, product_name)
                            
                            # Use overrides if provided (e.g., Galaxy special case)
                            if type_override:
                                filament_type = type_override
                            if finish_override:
                                finish = finish_override
                            
                            # Extract hex code (handle dual-color filaments with commas)
                            hex_codes = [extract_hex_code(h.strip()) for h in hex_code.split(',')]
                            hex_codes = [h for h in hex_codes if h]  # Remove None values
                            
                            if not hex_codes:
                                continue
                            
                            # Handle dual-color filaments
                            if len(hex_codes) > 1:
                                hex_value = '-'.join(hex_codes)
                            else:
                                hex_value = hex_codes[0]
                            
                            # Parse TD value
                            td_float = None
                            if td_value:
                                try:
                                    td_float = float(td_value)
                                except (ValueError, TypeError):
                                    pass
                            
                            filament = {
                                'maker': 'Polymaker',
                                'type': filament_type,
                                'finish': finish,
                                'color': color_name,
                                'hex': hex_value,
                                'td_value': td_float
                            }
                            
                            filaments.append(filament)
                            entries_found += 1
                
                print(f"Found {entries_found} filaments")
            else:
                print("No tables")
    
    return filaments


def main():
    """Main entry point."""
    
    source_dir = Path(__file__).parent.parent / '.source_data'
    pdf_path = source_dir / 'Polymaker.pdf'
    
    if not pdf_path.exists():
        print(f"❌ Error: PDF not found at {pdf_path}")
        return 1
    
    print("=" * 80)
    print("POLYMAKER PDF DATA EXTRACTION")
    print("=" * 80)
    print()
    
    # Extract data
    filaments = parse_polymaker_pdf(pdf_path)
    
    print("=" * 80)
    print(f"Extraction complete!")
    print("=" * 80)
    
    if filaments:
        # Generate slugs with collision detection
        slug_counts = defaultdict(int)
        for filament in filaments:
            base_slug = generate_slug(filament)
            slug_counts[base_slug] += 1
            if slug_counts[base_slug] > 1:
                filament['slug'] = f"{base_slug}-{slug_counts[base_slug]}"
            else:
                filament['slug'] = base_slug
        
        # Save preview
        output_file = Path(__file__).parent / 'polymaker_extracted.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filaments, f, indent=2, ensure_ascii=False)
        
        # Count collisions
        collisions = sum(1 for count in slug_counts.values() if count > 1)
        unique_slugs = len(set(f['slug'] for f in filaments))
        
        print(f"✅ Extracted {len(filaments)} filaments")
        print(f"📝 Saved to: {output_file}")
        print(f"🏷️  Generated {unique_slugs} unique slugs ({collisions} collision patterns)")
    else:
        print("⚠️  No filaments extracted yet - script needs to be adjusted based on PDF structure")
        print("   Review the output above to understand the PDF format")
    
    return 0


if __name__ == '__main__':
    exit(main())
