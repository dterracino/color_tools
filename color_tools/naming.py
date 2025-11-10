"""
Color naming utilities for generating descriptive names from RGB values.

This module provides intelligent color naming that:
- Matches exact CSS colors when possible
- Identifies near matches to CSS colors
- Generates descriptive names based on HSL properties
- Avoids collisions with existing color names
"""

from __future__ import annotations
from typing import Literal
from .conversions import rgb_to_hsl, rgb_to_lab
from .distance import delta_e_2000
from .palette import Palette

MatchType = Literal["exact", "near", "generated"]


def get_lightness_modifier(l: float) -> str:
    """
    Get lightness modifier based on LAB L* value.
    
    Args:
        l: LAB L* value (0-100)
        
    Returns:
        Lightness modifier: "very light", "light", "medium", "dark", "very dark", or ""
    """
    if l > 80:
        return "very light"
    elif l > 60:
        return "light"
    elif l > 40:
        return "medium"
    elif l > 20:
        return "dark"
    else:
        return "very dark"


def get_saturation_modifier(s: float, l: float) -> str:
    """
    Get saturation modifier based on HSL saturation and lightness.
    
    Args:
        s: HSL saturation (0-100)
        l: LAB L* value (0-100) for context
        
    Returns:
        Saturation modifier: "pale", "muted", "dull", "bright", "deep", "vivid", or ""
    """
    if s < 35:
        # Low saturation - pale for light colors, muted for dark
        return "pale" if l > 50 else "muted"
    elif s < 50:
        # Slightly desaturated - noticeable but not as extreme as pale/muted
        return "dull"
    elif s >= 95:
        # Maximum saturation - the most intense possible
        return "vivid"
    elif s >= 85:
        # Very high saturation approaching maximum
        return "deep"
    elif s >= 70:
        return "bright"
    else:
        return ""  # No modifier for medium saturation (50-70)


def get_hue_with_ish(h: float, s: float) -> str | None:
    """
    Get "-ish" hue variant if near a boundary, otherwise None.
    
    When a hue is within ±8° of a major hue boundary, we can describe it
    with an "-ish" modifier for more variety and precision.
    
    Args:
        h: HSL hue (0-360)
        s: HSL saturation (0-100) - only apply -ish to saturated colors
        
    Returns:
        "-ish" hue variant (e.g., "reddish orange") or None if not near boundary
    """
    # Only apply -ish to colors with reasonable saturation
    if s < 40:
        return None
    
    transition_width = 8  # degrees on each side of boundary
    
    # Define boundaries: (boundary_angle, lower_hue_base, upper_hue_base)
    boundaries = [
        (20, "red", "orange"),          # red/orange boundary
        (50, "orange", "yellow"),       # orange/yellow boundary  
        (80, "yellow", "green"),        # yellow/green boundary
        (140, "green", "teal"),         # green/teal boundary
        (170, "teal", "cyan"),          # teal/cyan boundary
        (190, "cyan", "blue"),          # cyan/blue boundary
        (270, "blue", "purple"),        # blue/purple boundary
        (310, "purple", "magenta"),     # purple/magenta boundary
        (350, "magenta", "red"),        # magenta/red boundary
    ]
    
    for boundary, hue_lower, hue_upper in boundaries:
        # Check if we're in the transition zone
        if boundary - transition_width <= h < boundary:
            # Just below boundary: "yellowish orange" (approaching orange from yellow side)
            return f"{hue_lower}ish {hue_upper}"
        elif boundary <= h < boundary + transition_width:
            # Just above boundary: "orangish yellow" (just entered yellow from orange side)
            return f"{hue_upper}ish {hue_lower}"
    
    # Handle red wraparound (350-360 and 0-20)
    if h >= 360 - transition_width or h < transition_width:
        # Very near red center - not a transition
        return None
    
    return None


def determine_base_hue(h: float, s: float, l: float) -> str:
    """
    Determine base hue name including special cases and "-ish" variants.
    
    Special cases like brown, pink, gold, etc. are determined by
    combinations of hue, saturation, and lightness.
    
    When near hue boundaries (±8°), returns "-ish" variants for more
    descriptive names (e.g., "yellowish orange", "reddish brown").
    
    Args:
        h: HSL hue (0-360)
        s: HSL saturation (0-100)
        l: LAB L* value (0-100)
        
    Returns:
        Base hue name (e.g., "red", "brown", "teal", "yellowish orange")
    """
    # Check for -ish variant first (works for all hues)
    ish_variant = get_hue_with_ish(h, s)
    if ish_variant:
        # For special cases, we still want to check if they apply
        # but use the -ish hue instead of the base
        pass  # Will check special cases below
    # Check for -ish variant first (works for all hues)
    ish_variant = get_hue_with_ish(h, s)
    if ish_variant:
        # For special cases, we still want to check if they apply
        # but use the -ish hue instead of the base
        pass  # Will check special cases below
    
    # Gold (yellow hues with moderate low saturation, not too dark)
    # Check BEFORE brown family since it's more specific
    # Requires slightly higher saturation (30-50%) to avoid beige/tan
    if 40 <= h <= 70 and 30 <= s < 50 and l > 40:
        if ish_variant and s >= 40:
            ish_part = ish_variant.split()[0]
            return f"{ish_part} gold"
        return "gold"
    
    # Brown family (orange/yellow hues that are desaturated or dark)
    # Wider range as fallback after gold
    if 20 <= h <= 80:
        if l > 70 and 15 < s < 50:
            base = "beige"
        elif 50 < l <= 70 and 15 < s < 50:
            base = "tan"
        elif l <= 50 and s < 70:
            base = "brown"
        else:
            # In brown hue range but not special case - use -ish if available
            return ish_variant if ish_variant else get_generic_hue(h)
        
        # Have a brown-family color - check if -ish variant applies
        if ish_variant and s >= 40:
            # Extract the -ish part (e.g., "yellowish" from "yellowish orange")
            ish_part = ish_variant.split()[0]
            return f"{ish_part} {base}"
        return base
    
    # Pink (light reds with saturation)
    if (h < 20 or h > 340) and l > 60 and s > 30:
        if ish_variant and s >= 40:
            ish_part = ish_variant.split()[0]
            return f"{ish_part} pink"
        return "pink"
    
    # Olive (dark muted yellow-green)
    if 70 <= h <= 100 and l < 50 and s < 50:
        # Olive is already muted, -ish doesn't apply well
        return "olive"
    
    # Navy (very dark blue)
    if 190 <= h <= 270 and l < 30:
        if ish_variant and s >= 40:
            ish_part = ish_variant.split()[0]
            return f"{ish_part} navy"
        return "navy"
    
    # Maroon (very dark red)
    if (h < 20 or h > 340) and l < 30:
        if ish_variant and s >= 40:
            ish_part = ish_variant.split()[0]
            return f"{ish_part} maroon"
        return "maroon"
    
    # Teal (cyan-green range) - this is already a transition color
    if 140 <= h <= 170:
        # Teal is its own thing, but can be modified
        if ish_variant and s >= 60:  # Higher threshold for teal
            ish_part = ish_variant.split()[0]
            return f"{ish_part} teal"
        return "teal"
    
    # Lime (bright yellow-green)
    if 70 <= h <= 100 and s >= 70:
        if ish_variant:
            ish_part = ish_variant.split()[0]
            return f"{ish_part} lime"
        return "lime"
    
    # No special case matched - use -ish variant if available, else standard hue
    if ish_variant:
        return ish_variant
    
    # Standard hue ranges (no special case matched)
    return get_generic_hue(h)


def get_generic_hue(h: float) -> str:
    """
    Get generic hue name from hue angle (fallback for collision avoidance).
    
    This uses simple hue ranges without special cases like brown, teal, etc.
    
    Args:
        h: HSL hue (0-360)
        
    Returns:
        Generic hue name
    """
    if h < 20 or h >= 340:
        return "red"
    elif h < 40:
        return "orange"
    elif h < 70:
        return "yellow"
    elif h < 100:
        return "yellow-green"
    elif h < 140:
        return "green"
    elif h < 170:
        return "cyan-green"
    elif h < 190:
        return "cyan"
    elif h < 220:
        return "blue"
    elif h < 250:
        return "blue"  # Wider blue range
    elif h < 270:
        return "indigo"
    elif h < 290:
        return "violet"
    elif h < 310:
        return "purple"
    else:
        return "magenta"


def is_unique_near_claim(
    rgb: tuple[int, int, int],
    css_name: str,
    palette_colors: list[tuple[int, int, int]] | None = None,
    threshold: float = 5.0
) -> bool:
    """
    Check if this RGB is the uniquely closest color to claim "near [css_name]".
    
    A color can only be named "near X" if no other color in the palette
    would also be within threshold distance to X.
    
    Args:
        rgb: RGB tuple to check
        css_name: CSS color name being claimed
        palette_colors: List of all RGB colors in the palette (optional)
        threshold: Delta E threshold for "near" match
        
    Returns:
        True if this is the unique closest color to css_name
    """
    if palette_colors is None:
        return True  # No palette context, allow the claim
    
    # Load CSS colors to get the target RGB
    palette = Palette.load_default()
    css_color = palette.find_by_name(css_name)
    if not css_color:
        return False
    
    css_rgb = css_color.rgb
    css_lab = rgb_to_lab(css_rgb)
    my_lab = rgb_to_lab(rgb)
    my_distance = delta_e_2000(my_lab, css_lab)
    
    # Check if any other palette color is also close to this CSS color
    for other_rgb in palette_colors:
        if other_rgb == rgb:
            continue  # Skip self
        
        other_lab = rgb_to_lab(other_rgb)
        other_distance = delta_e_2000(other_lab, css_lab)
        
        if other_distance < threshold:
            # Another color is also close - not a unique claim
            return False
    
    return True


def generate_color_name(
    rgb: tuple[int, int, int],
    palette_colors: list[tuple[int, int, int]] | None = None,
    near_threshold: float = 5.0
) -> tuple[str, MatchType]:
    """
    Generate a descriptive name for an RGB color.
    
    This function follows a priority-based naming strategy:
    1. Exact match with CSS colors
    2. Near match with CSS colors (within threshold, uniquely)
    3. Generated descriptive name based on HSL properties
    
    Generated names avoid collisions with CSS color names by falling back
    to generic hue names when necessary.
    
    Args:
        rgb: RGB tuple (0-255 for each component)
        palette_colors: Optional list of all RGB colors in palette (for near match uniqueness)
        near_threshold: Delta E threshold for "near" matches (default 5.0)
        
    Returns:
        Tuple of (name, match_type) where:
        - name: Color name string
        - match_type: "exact", "near", or "generated"
        
    Examples:
        >>> generate_color_name((255, 0, 0))
        ('red', 'exact')
        
        >>> generate_color_name((255, 10, 10))
        ('near red', 'near')
        
        >>> generate_color_name((128, 128, 255))
        ('medium bright blue', 'generated')
    """
    # Load CSS colors palette
    palette = Palette.load_default()
    
    # Step 1: Check for exact match in CSS colors
    css_match = palette.find_by_rgb(rgb)
    if css_match:
        return (css_match.name, "exact")
    
    # Step 2: Check for near match (using perceptual Delta E in LAB space)
    # Convert RGB to LAB for perceptual distance calculation
    lab = rgb_to_lab(rgb)
    nearest_css, distance = palette.nearest_color(lab, space="lab", metric="de2000")
    if distance < near_threshold:
        # Check if this is a unique claim
        if is_unique_near_claim(rgb, nearest_css.name, palette_colors, near_threshold):
            return (f"near {nearest_css.name}", "near")
    
    # Step 3: Generate descriptive name
    h, s, l_hsl = rgb_to_hsl(rgb)
    # LAB already calculated above for near-match check
    l_lab = lab[0]  # Use LAB L* for lightness (more perceptually uniform)
    
    # Check for achromatic (grays)
    if s < 15:
        lightness_mod = get_lightness_modifier(l_lab)
        gray_name = f"{lightness_mod} gray".strip()
        return (gray_name, "generated")
    
    # Determine base hue (including special cases)
    base_hue = determine_base_hue(h, s, l_lab)
    
    # Get modifiers
    lightness_mod = get_lightness_modifier(l_lab)
    saturation_mod = get_saturation_modifier(s, l_lab)
    
    # Assemble name
    parts = [lightness_mod, saturation_mod, base_hue]
    generated_name = " ".join(p for p in parts if p)
    
    # Step 4: Check for collision with CSS colors
    collision = palette.find_by_name(generated_name)
    if collision:
        # Name exists in CSS - check if it's the same color
        if collision.rgb == rgb:
            # Lucky! Our generated name exactly matches CSS
            return (generated_name, "exact")
        else:
            # Collision with different color - use fallback
            fallback_hue = get_generic_hue(h)
            parts = [lightness_mod, saturation_mod, fallback_hue]
            fallback_name = " ".join(p for p in parts if p)
            return (fallback_name, "generated")
    
    # No collision, use generated name
    return (generated_name, "generated")
