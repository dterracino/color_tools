"""
Color science tools for matching, conversion, and analysis.

A comprehensive toolkit for working with colors in multiple color spaces,
finding nearest color matches, and working with 3D printing filament colors.

Quick Start:
    >>> from color_tools import rgb_to_lab, delta_e_2000, Palette
    >>> 
    >>> # Convert RGB to LAB
    >>> lab = rgb_to_lab((255, 128, 64))
    >>> 
    >>> # Find nearest CSS color
    >>> palette = Palette.load_default()
    >>> nearest, distance = palette.nearest_color(lab)
    >>> print(f"Nearest color: {nearest.name}")

Color Validation:
    >>> from color_tools import validate_color
    >>> 
    >>> # Validate if a hex code matches a color name
    >>> # Note: Install [fuzzy] extra for improved matching: pip install color-match-tools[fuzzy]
    >>> result = validate_color("light blue", "#ADD8E6")
    >>> print(f"Match: {result.is_match}, Confidence: {result.name_confidence:.0%}")
    Match: True, Confidence: 100%

Image Processing (requires pip install color-match-tools[image]):
    >>> from color_tools.image import simulate_cvd_image, quantize_image_to_palette
    >>> 
    >>> # Test accessibility - simulate colorblindness
    >>> sim_image = simulate_cvd_image("chart.png", "deuteranopia")
    >>> sim_image.save("colorblind_view.png")
    >>> 
    >>> # Create retro artwork - convert to CGA palette
    >>> retro_image = quantize_image_to_palette("photo.jpg", "cga4", dither=True)
    >>> retro_image.save("retro_art.png")

Three Ways to Use:
    1. As a library: from color_tools import rgb_to_lab
    2. As a CLI tool: python -m color_tools color --name coral
    3. As installed command: color_tools filament --list-makers (needs pip install)
"""

__version__ = "5.5.0"

# ============================================================================
# Core Conversion Functions (Most Commonly Used)
# ============================================================================

from .conversions import (
    # Hex ↔ RGB (basic web colors)
    hex_to_rgb,
    rgb_to_hex,
    
    # RGB ↔ LAB (the main event!)
    rgb_to_lab,
    lab_to_rgb,
    
    # RGB ↔ LCH (cylindrical LAB - great for hue/chroma work)
    rgb_to_lch,
    lch_to_rgb,
    
    # LAB ↔ LCH (convert between rectangular and cylindrical)
    lab_to_lch,
    lch_to_lab,
    
    # RGB ↔ XYZ (the universal translator)
    rgb_to_xyz,
    xyz_to_rgb,
    
    # XYZ ↔ LAB (for power users)
    xyz_to_lab,
    lab_to_xyz,
    
    # RGB ↔ HSL (common web dev color space)
    rgb_to_hsl,
    hsl_to_rgb,
    rgb_to_winhsl,  # Windows HSL (0-240 range)
)

# ============================================================================
# Distance Metrics (Color Difference Formulas)
# ============================================================================

from .distance import (
    # The main Delta E formulas
    delta_e_2000,   # 👈 Use this one! Gold standard
    delta_e_94,
    delta_e_76,
    delta_e_cmc,
    
    # Simple distance functions
    euclidean,
    hsl_euclidean,
    hue_diff_deg,
)

# ============================================================================
# Gamut Operations (Can Your Monitor Show This Color?)
# ============================================================================

from .gamut import (
    is_in_srgb_gamut,
    find_nearest_in_gamut,
    clamp_to_gamut,
)

# ============================================================================
# Palettes & Data Classes (The Search Engine!)
# ============================================================================

from .palette import (
    # Main palette classes
    Palette,
    FilamentPalette,
    
    # Data classes
    ColorRecord,
    FilamentRecord,
    
    # Loading functions
    load_colors,
    load_filaments,
    load_maker_synonyms,
    load_palette,
)

# ============================================================================
# Color Naming (Generate Names from RGB Values)
# ============================================================================

from .naming import (
    generate_color_name,
)

# ============================================================================
# Import/Export (Data Export to Various Formats)
# ============================================================================

from .export import (
    # Export functions
    export_filaments,
    export_colors,
    
    # Format listing
    list_export_formats,
    
    # Individual format exporters (advanced use)
    export_filaments_autoforge,
    export_filaments_csv,
    export_filaments_json,
    export_colors_csv,
    export_colors_json,
    
    # Filename generation
    generate_filename,
)

# ============================================================================
# Color Validation (Fuzzy Name Matching + Delta E)
# ============================================================================

from .validation import (
    validate_color,
    ColorValidationRecord,
)

# ============================================================================
# Color Vision Deficiency (Colorblindness Simulation and Correction)
# ============================================================================

from .color_deficiency import (
    # Simulation functions - see how colors appear to CVD individuals
    simulate_cvd,
    simulate_protanopia,
    simulate_deuteranopia,
    simulate_tritanopia,
    
    # Correction functions - improve discriminability for CVD individuals
    correct_cvd,
    correct_protanopia,
    correct_deuteranopia,
    correct_tritanopia,
)

# ============================================================================
# Configuration (Usually Don't Need These Directly)
# ============================================================================

from .config import (
    set_dual_color_mode,
    get_dual_color_mode,
)

# ============================================================================
# Submodules Available for Import
# ============================================================================
# Power users can access these for advanced features:
#   from color_tools import constants    # ColorConstants class
#   from color_tools import config       # All config functions
#   from color_tools import conversions  # All conversion functions
#   from color_tools import distance     # All distance functions
#   from color_tools import gamut        # All gamut functions
#   from color_tools import palette      # Everything palette-related

# ============================================================================
# Public API Definition
# ============================================================================

__all__ = [
    # Version
    "__version__",
    
    # Conversion functions (most commonly used)
    "hex_to_rgb",
    "rgb_to_hex",
    "rgb_to_lab",
    "lab_to_rgb",
    "rgb_to_lch",
    "lch_to_rgb",
    "lab_to_lch",
    "lch_to_lab",
    "rgb_to_xyz",
    "xyz_to_rgb",
    "xyz_to_lab",
    "lab_to_xyz",
    "rgb_to_hsl",
    "hsl_to_rgb",
    "rgb_to_winhsl",
    
    # Distance metrics
    "delta_e_2000",
    "delta_e_94",
    "delta_e_76",
    "delta_e_cmc",
    "euclidean",
    "hsl_euclidean",
    "hue_diff_deg",
    
    # Gamut operations
    "is_in_srgb_gamut",
    "find_nearest_in_gamut",
    "clamp_to_gamut",
    
    # Palettes and data classes
    "Palette",
    "FilamentPalette",
    "ColorRecord",
    "FilamentRecord",
    "load_colors",
    "load_filaments",
    "load_maker_synonyms",
    "load_palette",
    
    # Color naming
    "generate_color_name",
    
    # Color validation
    "validate_color",
    "ColorValidationRecord",
    
    # Import/Export
    "export_filaments",
    "export_colors",
    "list_export_formats",
    "export_filaments_autoforge",
    "export_filaments_csv",
    "export_filaments_json",
    "export_colors_csv",
    "export_colors_json",
    "generate_filename",
    
    # Color vision deficiency
    "simulate_cvd",
    "simulate_protanopia",
    "simulate_deuteranopia",
    "simulate_tritanopia",
    "correct_cvd",
    "correct_protanopia",
    "correct_deuteranopia",
    "correct_tritanopia",
    
    # Config functions
    "set_dual_color_mode",
    "get_dual_color_mode",
]