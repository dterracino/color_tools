"""
Color validation functions to check if a hex code matches a color name.
Uses fuzzy matching and perceptual color distance (Delta E 2000).
Useful for validating imported color data or user input.

Note: For best fuzzy matching results, install the optional fuzzywuzzy package:
    pip install fuzzywuzzy
    
A hybrid fallback matcher (exact/substring/Levenshtein) is used when 
fuzzywuzzy is not available.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

try:
    from fuzzywuzzy import process
    HAS_FUZZYWUZZY = True
except ImportError:
    HAS_FUZZYWUZZY = False

from .palette import Palette
from .conversions import hex_to_rgb, rgb_to_lab
from .distance import delta_e_2000

# Load the default color palette once to be used by the validation function
_palette = Palette.load_default()
_color_names = [r.name for r in _palette.records]


def _levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance between two strings.
    
    The Levenshtein distance is the minimum number of single-character edits
    (insertions, deletions, or substitutions) required to change one string
    into another.
    
    Args:
        s1: First string
        s2: Second string
    
    Returns:
        The edit distance between the two strings
    """
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def _fuzzy_match_fallback(query: str, choices: list[str]) -> tuple[str, int]:
    """
    Hybrid fuzzy matching fallback when fuzzywuzzy is not available.
    
    Uses multiple strategies for best results:
    1. Exact match (after normalization) - 100 score
    2. Substring match - 90-95 score
    3. Levenshtein distance - variable score
    
    Args:
        query: The string to search for
        choices: List of strings to search in
    
    Returns:
        Tuple of (best_match, score) where score is 0-100
    """
    query_norm = query.lower().replace(" ", "").replace("-", "")
    
    # Strategy 1: Exact match (normalized)
    for choice in choices:
        choice_norm = choice.lower().replace(" ", "").replace("-", "")
        if query_norm == choice_norm:
            return (choice, 100)
    
    # Strategy 2: Substring match + Strategy 3: Levenshtein fallback
    best_match = None
    best_score = 0
    
    for choice in choices:
        choice_norm = choice.lower().replace(" ", "").replace("-", "")
        
        if query_norm in choice_norm:
            # Substring match - higher score for better coverage
            score = int((len(query_norm) / len(choice_norm)) * 95)
        elif choice_norm in query_norm:
            # Reverse substring match - slightly lower score
            score = int((len(choice_norm) / len(query_norm)) * 90)
        else:
            # Strategy 3: Use Levenshtein for non-matches
            distance = _levenshtein_distance(query_norm, choice_norm)
            max_len = max(len(query_norm), len(choice_norm))
            if max_len > 0:
                score = int(100 * (1 - (distance / max_len)))
            else:
                score = 0
        
        if score > best_score:
            best_score = score
            best_match = choice
    
    return (best_match or choices[0], best_score)


@dataclass(frozen=True)
class ColorValidationRecord:
    """
    Result record from validating if a hex code matches a color name.
    
    This immutable dataclass contains comprehensive validation results including
    fuzzy name matching confidence, perceptual color distance (Delta E), and
    helpful suggestions for mismatches.
    
    Attributes:
        is_match: True if the color name and hex code are a good match
        name_match: Best matching CSS color name from the database (e.g., "lightblue")
        name_confidence: Fuzzy matching confidence 0.0-1.0 (1.0 = exact match)
        hex_value: The hex code that was validated (normalized with # prefix)
        suggested_hex: Suggested hex code for the matched name, or None if exact match
        delta_e: Perceptual color distance (Delta E 2000) between provided and suggested colors
        message: Human-readable validation result message
    
    Example:
        >>> from color_tools.validation import validate_color
        >>> result = validate_color("light blue", "#ADD8E6")
        >>> print(f"Match: {result.is_match}")
        Match: True
        >>> print(f"Matched '{result.name_match}' with {result.name_confidence:.0%} confidence")
        Matched 'lightblue' with 100% confidence
        >>> print(f"Delta E: {result.delta_e:.2f}")
        Delta E: 0.00
    """
    is_match: bool
    name_match: Optional[str]
    name_confidence: float
    hex_value: str
    suggested_hex: Optional[str]
    delta_e: float
    message: str
    
    def __str__(self) -> str:
        """Human-readable validation result."""
        match_status = "✓ Match" if self.is_match else "✗ Mismatch"
        confidence = f"{self.name_confidence:.0%}"
        return f"{match_status}: '{self.name_match}' ({confidence} confidence, ΔE {self.delta_e:.1f})"


def validate_color(
    color_name: str,
    hex_code: str,
    de_threshold: float = 20.0
) -> ColorValidationRecord:
    """
    Validates if a given hex code approximately matches a given color name.

    Args:
        color_name: The name of the color to check (e.g., "light red").
        hex_code: The hex code to validate (e.g., "#FFC0CB").
        de_threshold: The Delta E 2000 threshold for a color to be considered a match.
                      Lower is stricter. Default is 20.0.

    Returns:
        A ColorValidationRecord with the validation results.
        
    Note:
        Uses fuzzywuzzy for fuzzy matching if available, otherwise falls back
        to a hybrid matcher using exact/substring/Levenshtein matching.
    """
    # 1. Find the best matching color name from our CSS palette
    if HAS_FUZZYWUZZY:
        match_result = process.extractOne(color_name, _color_names)
        if match_result is None:
            return ColorValidationRecord(
                is_match=False,
                name_match=None,
                name_confidence=0.0,
                hex_value=hex_code,
                suggested_hex=None,
                delta_e=float('inf'),
                message="No matching color name could be found."
            )
        best_match, name_confidence_raw = match_result[0], match_result[1]
        name_confidence = float(name_confidence_raw) / 100.0
    else:
        # Use fallback matcher
        best_match, name_confidence_raw = _fuzzy_match_fallback(color_name, _color_names)
        name_confidence = float(name_confidence_raw) / 100.0
    
    # 2. Get the official record for the best matching color name
    matched_color_record = _palette.find_by_name(best_match)
    if not matched_color_record:
        # This should theoretically never happen if _color_names is in sync
        return ColorValidationRecord(
            is_match=False,
            name_match=best_match,
            name_confidence=name_confidence,
            hex_value=hex_code,
            suggested_hex=None,
            delta_e=float('inf'),
            message="Could not find the matched color in the palette."
        )

    suggested_hex = matched_color_record.hex
    suggested_lab = matched_color_record.lab

    # 3. Convert the user's input hex to LAB for comparison
    input_rgb = hex_to_rgb(hex_code)
    if input_rgb is None:
        return ColorValidationRecord(
            is_match=False,
            name_match=best_match,
            name_confidence=name_confidence,
            hex_value=hex_code,
            suggested_hex=suggested_hex,
            delta_e=float('inf'),
            message=f"Invalid hex code format: {hex_code}"
        )
    input_lab = rgb_to_lab(input_rgb)

    # 4. Calculate the perceptual distance (Delta E 2000)
    delta_e = delta_e_2000(input_lab, suggested_lab)

    # 5. Determine if it's a match
    is_match = delta_e <= de_threshold
    
    message = "Match" if is_match else "No Match"
    if not is_match:
        message += f" (Delta E of {delta_e:.2f} is above threshold of {de_threshold})"

    return ColorValidationRecord(
        is_match=is_match,
        name_match=best_match,
        name_confidence=name_confidence,
        hex_value=hex_code,
        suggested_hex=suggested_hex,
        delta_e=delta_e,
        message=message
    )


