# Wavelength Color Space Implementation Plan

## Overview

Add bidirectional wavelength ↔ RGB conversion functionality to provide unique scientific and educational features. This includes both RGB → wavelength (with confidence metrics) and wavelength → RGB (with gamut warnings) conversions, making the library stand out in the color science space.

## Core Concept: Intelligent Wavelength Conversion

Instead of simple mathematical conversion, provide **conversion with real-world context** that explains the physical and perceptual implications of the transformation.

### Key Insight: Lossy but Symmetric

- **RGB → Wavelength**: Inherently lossy (many RGB colors have no pure wavelength equivalent)
- **Wavelength → RGB**: Also lossy (pure wavelengths may be outside sRGB gamut)
- **Educational Value**: Show users the relationship between digital colors and physical light

## RGB → Wavelength Conversion

### The Physics Challenge

Converting RGB to wavelength isn't a simple mathematical transformation because:

1. **Many RGB colors have NO pure wavelength equivalent** - they're mixtures (like magenta)
2. **Spectral colors are a subset** - only colors on the spectrum boundary have direct wavelength mappings
3. **Multiple wavelengths can appear similar** due to human color perception

### Implementation Strategy

```python
def rgb_to_wavelength(rgb: tuple[int, int, int]) -> tuple[float, float, str]:
    """
    Convert RGB to closest wavelength match with confidence metrics.
    
    Args:
        rgb: RGB color tuple (0-255 range)
    
    Returns:
        (wavelength_nm, confidence_percent, status_message)
    """
    # Convert RGB → XYZ → chromaticity coordinates
    xyz = rgb_to_xyz(rgb)
    x, y = xyz_to_chromaticity(xyz)
    
    # Find closest point on spectral locus (horseshoe curve)
    closest_wavelength, distance = find_closest_spectral_point(x, y)
    
    # Calculate confidence based on perceptual distance
    confidence = calculate_spectral_confidence(distance)
    
    # Generate intelligent status message
    if confidence > 90:
        status = "Excellent spectral match"
    elif confidence > 70:
        status = "Good spectral approximation" 
    elif confidence > 40:
        status = "Moderate spectral match"
    else:
        status = "No good matches found. Multiple wavelengths may be necessary"
    
    return closest_wavelength, confidence, status
```

### Example Conversions

```python
# Pure spectral colors (high confidence)
rgb_to_wavelength((255, 0, 0))      # → (700nm, 98%, "Excellent spectral match")
rgb_to_wavelength((0, 255, 0))      # → (550nm, 95%, "Excellent spectral match") 
rgb_to_wavelength((0, 0, 255))      # → (470nm, 92%, "Excellent spectral match")

# Mixed colors (lower confidence)
rgb_to_wavelength((255, 255, 0))    # → (570nm, 78%, "Good spectral approximation")
rgb_to_wavelength((255, 128, 64))   # → (590nm, 65%, "Moderate spectral match")

# Non-spectral colors (very low confidence)
rgb_to_wavelength((255, 0, 255))    # → (410nm, 32%, "No good matches found. Multiple wavelengths may be necessary")
rgb_to_wavelength((128, 128, 128))  # → (550nm, 15%, "No good matches found. Gray has no dominant wavelength")
```

## Wavelength → RGB Conversion

### The Reverse Problem

Converting wavelength to RGB provides the complementary perspective and educational symmetry:

```python
def wavelength_to_rgb(wavelength_nm: float) -> tuple[tuple[int, int, int], dict]:
    """
    Convert wavelength to RGB representation with comprehensive metadata.
    
    Args:
        wavelength_nm: Wavelength in nanometers (380-780)
    
    Returns:
        (rgb_tuple, metadata_dict)
    """
    # Use CIE 1931 color matching functions to get XYZ
    xyz = wavelength_to_xyz(wavelength_nm)
    
    # Convert to RGB (may be out of gamut!)
    rgb_float = xyz_to_rgb(xyz)
    
    # Comprehensive metadata generation
    metadata = {
        'original_xyz': xyz,
        'gamut_status': 'in_gamut' if is_in_srgb_gamut(rgb_float) else 'out_of_gamut',
        'clamping_applied': False,
        'spectral_purity': 100.0,  # Pure wavelength = 100% spectral purity
        'color_name': get_wavelength_color_name(wavelength_nm),
        'notes': []
    }
    
    # Handle out-of-gamut colors with intelligent clamping
    if not is_in_srgb_gamut(rgb_float):
        rgb_clamped = clamp_to_srgb(rgb_float)
        metadata['clamping_applied'] = True
        metadata['notes'].append("Color clamped to sRGB gamut")
        metadata['notes'].append("Actual color is more saturated than displayable")
        metadata['gamut_loss_percent'] = calculate_gamut_loss(rgb_float, rgb_clamped)
        rgb_int = tuple(int(c) for c in rgb_clamped)
    else:
        rgb_int = tuple(int(c) for c in rgb_float)
        metadata['gamut_loss_percent'] = 0.0
    
    # Add wavelength-specific educational notes
    if wavelength_nm < 400:
        metadata['notes'].append("Deep violet - near UV boundary")
        metadata['visibility'] = 'barely_visible'
    elif wavelength_nm > 700:
        metadata['notes'].append("Deep red - near infrared boundary")
        metadata['visibility'] = 'barely_visible'
    elif 545 <= wavelength_nm <= 555:
        metadata['notes'].append("Peak sensitivity wavelength for human vision")
        metadata['visibility'] = 'maximum'
    else:
        metadata['visibility'] = 'good'
        
    return rgb_int, metadata
```

### Example Wavelength Conversions

```python
# Visible spectrum examples
wavelength_to_rgb(550)  # → ((0, 255, 146), {'gamut_status': 'in_gamut', ...})
wavelength_to_rgb(700)  # → ((255, 0, 0), {'gamut_status': 'in_gamut', ...})

# Out-of-gamut examples (highly saturated)
wavelength_to_rgb(480)  # → ((0, 146, 255), {'clamping_applied': True, ...})
wavelength_to_rgb(520)  # → ((0, 255, 108), {'clamping_applied': True, ...})
```

## CLI Integration

### Command Structure

Integrate wavelength conversions into the existing `convert` command structure:

```bash
# RGB → Wavelength conversions
python -m color_tools convert --from rgb --to wavelength --value 255 0 0
python -m color_tools convert --from rgb --to wavelength --hex "#FF0000"

# Wavelength → RGB conversions  
python -m color_tools convert --from wavelength --to rgb --value 550
python -m color_tools convert --from wavelength --to hex --value 700

# Cross-space wavelength conversions
python -m color_tools convert --from wavelength --to lab --value 550
python -m color_tools convert --from hsl --to wavelength --value 120 100 50
```

### CLI Output Examples

**RGB → Wavelength:**

```bash
$ python -m color_tools convert --from rgb --to wavelength --value 255 0 0

Input: RGB(255, 0, 0)
Closest wavelength: 700nm (98% confidence)
Status: Excellent spectral match
Color name: Red
Note: This is pure spectral red - a single wavelength LED at 700nm would closely match this color.
```

**Wavelength → RGB:**

```bash
$ python -m color_tools convert --from wavelength --to rgb --value 550

Input: 550nm
RGB: (0, 255, 146)
Hex: #00FF92
Gamut status: In sRGB gamut
Spectral purity: 100% (pure wavelength)
Color name: Green
Note: Peak sensitivity wavelength for human vision - appears brightest green possible.
**Out-of-gamut wavelength:**

```bash
$ python -m color_tools convert --from wavelength --to rgb --value 480

Input: 480nm  
RGB: (0, 146, 255) [clamped from (0, 146, 312)]
Hex: #0092FF
Gamut status: Out of sRGB gamut (19% saturation loss)
Spectral purity: 100% (pure wavelength)
Color name: Blue-Cyan
Warning: Actual color is more saturated than displayable on sRGB screens
Note: True 480nm light appears more vivid than any RGB display can show.
```

**Non-spectral color:**

```bash
$ python -m color_tools convert --from rgb --to wavelength --value 255 0 255

Input: RGB(255, 0, 255) - Magenta
Closest wavelength: 410nm (32% confidence)
Status: No good matches found. Multiple wavelengths may be necessary.
Color name: Deep Violet (closest approximation)
Note: Magenta doesn't exist in the spectrum - it's what we see when red and blue mix.
Explanation: This color requires both red (~700nm) AND violet (~410nm) wavelengths simultaneously.
```

## Round-Trip Analysis Feature

### Quality Assessment

Provide intelligent analysis of wavelength conversion quality:

```python
def analyze_wavelength_roundtrip(wavelength_nm: float) -> dict:
    """Analyze what happens in wavelength → RGB → wavelength conversion."""
    
    # Forward conversion
    rgb, wl_metadata = wavelength_to_rgb(wavelength_nm)
    
    # Reverse conversion  
    closest_wl, confidence, rgb_metadata = rgb_to_wavelength(rgb)
    
    # Quality assessment
    wavelength_shift = abs(wavelength_nm - closest_wl)
    
    if wavelength_shift < 2:
        quality = 'excellent'
    elif wavelength_shift < 5:
        quality = 'good'  
    elif wavelength_shift < 10:
        quality = 'moderate'
    else:
        quality = 'poor'
    
    return {
        'original_wavelength': wavelength_nm,
        'rgb_representation': rgb,
        'hex_representation': f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}",
        'closest_wavelength': closest_wl,
        'wavelength_shift': wavelength_shift,
        'confidence': confidence,
        'round_trip_quality': quality,
        'gamut_issues': wl_metadata['clamping_applied'],
        'analysis': generate_roundtrip_analysis(wavelength_nm, closest_wl, wl_metadata)
    }

def generate_roundtrip_analysis(original, recovered, metadata):
    """Generate intelligent analysis of conversion quality."""
    shift = abs(original - recovered)
    
    if shift < 2 and not metadata['clamping_applied']:
        return "Excellent round-trip accuracy - this wavelength converts perfectly to RGB and back."
    elif metadata['clamping_applied']:
        return f"Gamut limitations cause {shift:.1f}nm shift - the original wavelength is too saturated for sRGB."
    elif 490 <= original <= 520:  # Blue-green region
        return "Blue-green wavelengths are challenging due to RGB primary limitations."
    elif original < 420 or original > 680:
        return "Extreme wavelengths have lower accuracy due to vision system constraints."
    else:
        return f"Moderate accuracy loss of {shift:.1f}nm due to RGB quantization."
```

### CLI Round-Trip Analysis

```bash
# Analyze conversion quality
python -m color_tools convert --from wavelength --to wavelength --value 550 --analyze-roundtrip

# Output:
Original wavelength: 550nm
RGB representation: (0, 255, 146) #00FF92
Back-converted wavelength: 548nm (97% confidence)
Round-trip error: 2nm
Quality: Excellent
Analysis: Excellent round-trip accuracy - this wavelength converts perfectly to RGB and back.

# Problematic case
python -m color_tools convert --from wavelength --to wavelength --value 480 --analyze-roundtrip

# Output:
Original wavelength: 480nm
RGB representation: (0, 146, 255) #0092FF [clamped]
Back-converted wavelength: 465nm (73% confidence) 
Round-trip error: 15nm
Quality: Poor - significant gamut clamping
Analysis: Gamut limitations cause 15.0nm shift - the original wavelength is too saturated for sRGB.
```

## Advanced Wavelength Features

### 1. Visible Spectrum Analysis

```python
def analyze_visible_spectrum(start_nm=380, end_nm=780, step=10) -> list[dict]:
    """Generate RGB representation of entire visible spectrum."""
    spectrum_data = []
    
    for wl in range(start_nm, end_nm + 1, step):
        rgb, metadata = wavelength_to_rgb(wl)
        hex_color = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
        
        spectrum_data.append({
            'wavelength': wl,
            'rgb': rgb,
            'hex': hex_color,
            'in_gamut': metadata['gamut_status'] == 'in_gamut',
            'color_name': metadata['color_name'],
            'visibility': metadata['visibility'],
            'clamping_loss': metadata.get('gamut_loss_percent', 0.0)
        })
    
    return spectrum_data
```

### 2. LED Wavelength Matching

```python
def find_led_wavelengths_for_color(target_rgb: tuple[int, int, int]) -> list[dict]:
    """Find which LED wavelengths could approximate a target color."""
    
    # Convert target to spectral analysis
    target_wl, confidence, notes = rgb_to_wavelength(target_rgb)
    
    if confidence > 80:
        # Single wavelength solution
        return [{
            'type': 'single_wavelength',
            'primary_wavelength': target_wl,
            'intensity': 100,
            'accuracy': confidence,
            'notes': f'Single wavelength LED at {target_wl}nm will closely match this color'
        }]
    else:
        # Multiple wavelength solution needed
        return find_multi_led_approximation(target_rgb)

def find_multi_led_approximation(target_rgb: tuple[int, int, int]) -> list[dict]:
    """Find multi-LED combination to approximate non-spectral colors."""
    
    # For colors like magenta, white, etc.
    # This would involve more complex color matching
    
    if is_magenta_like(target_rgb):
        return [{
            'type': 'dual_wavelength',
            'wavelengths': [410, 700],  # Violet + Red
            'intensities': calculate_magenta_intensities(target_rgb),
            'notes': 'Magenta requires both red and violet LEDs'
        }]
    elif is_white_like(target_rgb):
        return [{
            'type': 'full_spectrum',
            'recommendation': 'white_led_with_phosphor',
            'notes': 'Use broad-spectrum white LED or RGB LED combination'
        }]
    else:
        # General case - find best two-wavelength approximation
        return find_optimal_dual_wavelength(target_rgb)
```

### 3. Wavelength Color Names

```python
def get_wavelength_color_name(wavelength_nm: float) -> str:
    """Get traditional color name for wavelength with precision."""
    
    # More precise color naming based on wavelength
    if wavelength_nm < 380:
        return "ultraviolet"
    elif wavelength_nm < 400:
        return "deep violet"
    elif wavelength_nm < 420:
        return "violet"
    elif wavelength_nm < 440:
        return "violet-blue"
    elif wavelength_nm < 460:
        return "blue"
    elif wavelength_nm < 480:
        return "blue-cyan"
    elif wavelength_nm < 500:
        return "cyan"
    elif wavelength_nm < 520:
        return "cyan-green"
    elif wavelength_nm < 540:
        return "green"
    elif wavelength_nm < 560:
        return "yellow-green"
    elif wavelength_nm < 580:
        return "yellow"
    elif wavelength_nm < 600:
        return "yellow-orange"
    elif wavelength_nm < 620:
        return "orange"
    elif wavelength_nm < 640:
        return "orange-red"
    elif wavelength_nm < 700:
        return "red"
    elif wavelength_nm < 750:
        return "deep red"
    else:
        return "infrared"

def is_peak_sensitivity(wavelength_nm: float) -> bool:
    """Check if wavelength is at peak human vision sensitivity."""
    return 545 <= wavelength_nm <= 555

def get_visibility_rating(wavelength_nm: float) -> str:
    """Get visibility rating for wavelength."""
    if wavelength_nm < 390 or wavelength_nm > 720:
        return "barely_visible"
    elif 545 <= wavelength_nm <= 555:
        return "maximum"
    elif 480 <= wavelength_nm <= 600:
        return "excellent"
    else:
        return "good"
```

## Technical Implementation Requirements

### Data Dependencies

#### CIE 1931 Color Matching Functions (x̄, ȳ, z̄)

- Maps wavelength to XYZ tristimulus values
- Needed for wavelength → RGB conversion
- Standard colorimetric data from CIE

#### Spectral Locus Data

- Wavelength → (x, y) chromaticity coordinates
- Needed for RGB → wavelength conversion
- Derived from color matching functions

#### Standard Illuminant Data

- D65 white point for normalization
- Already available in existing constants

### Example Spectral Locus Data Structure

```python
# Subset of spectral locus data needed
SPECTRAL_LOCUS = {
    # wavelength_nm: (x_chromaticity, y_chromaticity)
    380: (0.1741, 0.0050),    # Deep violet
    390: (0.1740, 0.0049),
    400: (0.1738, 0.0048),    # Violet-blue
    410: (0.1736, 0.0048),    # Magenta's "closest match"
    420: (0.1733, 0.0047),
    # ... continue through visible spectrum ...
    550: (0.3324, 0.6630),    # Peak green sensitivity  
    # ... continue to ...
    700: (0.7347, 0.2653),    # Deep red
    770: (0.7347, 0.2653),    # Far red
    780: (0.7347, 0.2653)     # Near-infrared
}

# Full CIE 1931 color matching functions
CIE_1931_CMF = {
    # wavelength_nm: (x_bar, y_bar, z_bar)
    380: (0.0014, 0.0000, 0.0065),
    390: (0.0042, 0.0001, 0.0201),
    # ... complete dataset ...
}
```

### Core Algorithm Implementation

```python
def find_closest_spectral_point(x: float, y: float) -> tuple[float, float]:
    """Find closest wavelength to given chromaticity coordinates."""
    min_distance = float('inf')
    closest_wavelength = 0
    
    for wavelength, (spec_x, spec_y) in SPECTRAL_LOCUS.items():
        # Euclidean distance in chromaticity space
        distance = math.sqrt((x - spec_x)**2 + (y - spec_y)**2)
        if distance < min_distance:
            min_distance = distance
            closest_wavelength = wavelength
    
    return closest_wavelength, min_distance

def calculate_spectral_confidence(chromaticity_distance: float) -> float:
    """Convert chromaticity distance to confidence percentage."""
    # This mapping would need calibration with real data
    # Lower distance = higher confidence
    max_distance = 0.3  # Approximate max distance to spectral locus
    confidence = max(0, (1.0 - chromaticity_distance / max_distance) * 100)
    return min(100, confidence)

def wavelength_to_xyz(wavelength_nm: float) -> tuple[float, float, float]:
    """Convert wavelength to XYZ using CIE 1931 color matching functions."""
    if wavelength_nm not in CIE_1931_CMF:
        # Interpolate between known values
        return interpolate_cmf(wavelength_nm)
    
    x_bar, y_bar, z_bar = CIE_1931_CMF[wavelength_nm]
    
    # Normalize to standard observer
    # This is simplified - actual implementation needs proper normalization
    return (x_bar, y_bar, z_bar)
```

## Integration with Existing Architecture

### Module Organization

**New module: `wavelength.py`**

```python
# Core wavelength conversion functions
def rgb_to_wavelength(rgb: tuple[int, int, int]) -> tuple[float, float, str]:
def wavelength_to_rgb(wavelength_nm: float) -> tuple[tuple[int, int, int], dict]:
def analyze_wavelength_roundtrip(wavelength_nm: float) -> dict:

# Utility functions
def get_wavelength_color_name(wavelength_nm: float) -> str:
def is_spectral_color(rgb: tuple[int, int, int]) -> bool:
def find_led_wavelengths_for_color(rgb: tuple[int, int, int]) -> list[dict]:

# Advanced analysis
def analyze_visible_spectrum(start_nm=380, end_nm=780, step=10) -> list[dict]:
def calculate_spectral_purity(rgb: tuple[int, int, int]) -> float:
```

### CLI Integration Points

**Modified files:**

- `cli.py`: Add wavelength support to convert command
- `conversions.py`: Add wavelength conversion wrappers if needed
- `__init__.py`: Export wavelength functions

### Conversion System Integration

```python
# Add to existing conversion system
SUPPORTED_SPACES = {
    'rgb': ...,
    'lab': ..., 
    'lch': ...,
    'wavelength': {  # New addition
        'channels': 1,
        'range': (380, 780),
        'unit': 'nm',
        'from_rgb': rgb_to_wavelength,
        'to_rgb': wavelength_to_rgb_simple,  # Wrapper that returns just RGB
        'metadata_supported': True
    }
}
```

## Educational and Scientific Applications

### 1. Physics Education

- Demonstrate relationship between light wavelength and perceived color
- Show limitations of RGB displays vs. real spectrum
- Illustrate concept of metamerism (different spectra, same color)

### 2. LED and Lighting Design

- Help select LED wavelengths for desired colors
- Analyze RGB color accuracy for different LED combinations
- Optimize LED arrays for color reproduction

### 3. Spectroscopy and Optics

- Convert spectral measurements to displayable colors
- Analyze color accuracy of optical instruments
- Design color filters and optical systems

### 4. Display Technology

- Analyze gamut limitations of different display types
- Compare LCD vs OLED vs laser display capabilities
- Optimize display calibration for specific applications

## CLI Command Examples

### Basic Conversions

```bash
# Simple wavelength lookup
python -m color_tools convert --from rgb --to wavelength --value 255 0 0
python -m color_tools convert --from wavelength --to rgb --value 550

# Hex input support  
python -m color_tools convert --from hex --to wavelength --value "#00FF00"

# Multiple format output
python -m color_tools convert --from wavelength --to rgb,hex,lab --value 550
```

### Advanced Analysis

```bash
# Round-trip quality analysis
python -m color_tools convert --value 550 --round-trip wavelength
python -m color_tools convert --value 480 --round-trip wavelength --verbose

# Spectrum analysis
python -m color_tools wavelength --analyze-spectrum --range 450:650:10
python -m color_tools wavelength --analyze-spectrum --format csv > spectrum.csv

# LED recommendations
python -m color_tools wavelength --find-leds --value 255 0 255
python -m color_tools wavelength --find-leds --hex "#FF00FF"
```

### Educational Commands

```bash
# Show gamut limitations
python -m color_tools wavelength --show-gamut-limits --range 380:780:20

# Compare wavelength vs RGB accuracy
python -m color_tools wavelength --accuracy-report --range 400:700:50

# Generate visible spectrum image (requires Pillow)
python -m color_tools wavelength --generate-spectrum --output spectrum.png
```

## Future Enhancements

### 1. Spectral Data Analysis

- Import/export spectral measurement data
- Analyze color accuracy of measurement devices
- Convert spectrometer data to RGB representations

### 2. Advanced LED Design

- Multi-LED optimization algorithms
- Color temperature considerations
- Power efficiency calculations

### 3. Display Gamut Analysis

- Compare different display technologies
- Optimize content for specific display types
- Generate gamut visualization tools

### 4. Real-World Applications

- Sunset/sunrise color analysis
- Gem and mineral color characterization
- Paint and pigment spectral analysis

## Testing Strategy

### Unit Tests

- Test known wavelength → RGB conversions
- Verify spectral locus distance calculations
- Test confidence metric accuracy
- Validate round-trip conversion quality

### Integration Tests  

- CLI command functionality
- Cross-space conversion accuracy
- Output formatting consistency
- Error handling for invalid wavelengths

### Scientific Validation

- Compare results with published spectral data
- Validate against other color science libraries
- Test with real spectrometer measurements
- Verify educational content accuracy

## Questions for Future Resolution

### Technical Decisions

1. **Data source**: Which spectral locus dataset to use as reference?
2. **Interpolation**: How to handle wavelengths between data points?
3. **Confidence mapping**: How to calibrate distance → confidence conversion?
4. **Gamut mapping**: Which clamping algorithm for out-of-gamut wavelengths?

### Feature Scope

1. **Wavelength range**: Support 380-780nm or extend further?
2. **Precision**: 1nm steps or higher resolution?
3. **Multi-wavelength**: Support for spectral power distributions?
4. **LED database**: Include specific LED wavelength characteristics?

### User Experience

1. **Output verbosity**: How much metadata to show by default?
2. **Educational content**: Level of scientific detail in explanations?
3. **Visualization**: ASCII spectrum display in terminal?
4. **Error guidance**: How to help users understand conversion limitations?

## Conclusion

The wavelength conversion feature represents a unique differentiator that bridges digital color and physical optics. By providing both directions of conversion with intelligent metadata and educational context, the library becomes valuable for:

- **Education**: Teaching relationship between light and color perception  
- **Science**: Converting spectral measurements to displayable colors
- **Engineering**: Designing LED arrays and optical systems
- **Art/Design**: Understanding color purity and spectral limitations

The key innovation is not just mathematical conversion, but **intelligent conversion with real-world context** that helps users understand the physical and perceptual implications of their color choices.
