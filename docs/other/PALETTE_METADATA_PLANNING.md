# Palette Metadata Format Planning

**Status**: Planning / Ready to Implement

## Overview

This document outlines a planned enhancement to the palette file format to support metadata fields. This change would enable better integration with external palette sources like Lospec.com and provide richer context for color palettes.

## Current Format

Currently, palette JSON files contain a simple array of color objects:

```json
[
  {
    "name": "black",
    "hex": "#000000",
    "rgb": [0, 0, 0],
    "hsl": [0.0, 0.0, 0.0],
    "lab": [0.0, 0.0, 0.0],
    "lch": [0.0, 0.0, 0.0]
  },
  {
    "name": "red",
    "hex": "#dd0033",
    "rgb": [221, 0, 51],
    "hsl": [346.2, 100.0, 43.3],
    "lab": [46.5, 72.8, 38.3],
    "lch": [46.5, 82.2, 27.8]
  }
]
```

**Characteristics**:

- Simple, flat structure
- Only contains color data
- No metadata about the palette itself
- Works well for basic palette storage

## Proposed Format

Wrap the color array in an object with metadata fields:

```json
{
  "name": "Apple II",
  "description": "The Apple II was an 8-bit home computer and one of the first highly successful mass-produced microcomputer products.",
  "author": "Apple Computer",
  "source": "built-in",
  "url": "https://example.com/palette-source",
  "license": "Public Domain",
  "tags": ["retro", "8-bit", "computer"],
  "created": "1977-04-01",
  "native_resolution": [280, 192],
  "pixel_aspect_ratio": [1, 1],
  "display_aspect_ratio": [4, 3],
  "display_scale_mode": "integer",
  "colors": [
    {
      "name": "black",
      "hex": "#000000",
      "rgb": [0, 0, 0],
      "hsl": [0.0, 0.0, 0.0],
      "lab": [0.0, 0.0, 0.0],
      "lch": [0.0, 0.0, 0.0]
    }
  ]
}
```

### Metadata Fields

| Field | Type | Required | Description |
| ------- | ------ | ---------- | ------------- |
| `id` | string | No | Machine-readable identifier for loading (e.g., `"sierra_agi"`). Defaults to file stem if absent. |
| `name` | string | Yes | Human-readable palette name |
| `description` | string | No | Detailed description (may contain HTML) |
| `author` | string | No | Original creator/source |
| `source` | string | No | Source identifier (e.g., "built-in", "lospec", "user") |
| `url` | string | No | Original URL if imported from external source |
| `license` | string | No | License information |
| `tags` | array[string] | No | Categorization tags |
| `created` | string | No | Creation date (ISO 8601 format) |
| `native_resolution` | array[int, int] | No | Native pixel dimensions `[width, height]` |
| `pixel_aspect_ratio` | array[int, int] | No | Pixel aspect ratio as integer scale factors `[W, H]` (e.g., `[8, 7]` for NES NTSC) |
| `display_aspect_ratio` | array[int, int] | No | Intended display ratio `[W, H]` (e.g., `[4, 3]` for CRT) |
| `display_scale_mode` | string | No | Upscaling mode: `"integer"` (default), `"nearest"`, or `"smooth"` |
| `pixel_expansion` | array[int, int] | No | Integer pixel doubling per axis `[W, H]` (e.g., `[2, 1]` for AGI's horizontal doubling). More explicit than PAR for systems using whole-pixel multiplication. |
| `preferred_integer_scales` | array[int] | No | List of clean integer display multipliers (e.g., `[2, 3, 4]`). Hints to a renderer which scale factors look correct for this system. |
| `simultaneous_color_limit` | int | No | Maximum colors displayable at once (e.g., `256` for SNES, `25` for NES). Informational; full quantization support requires a two-pass approach. |
| `parent` | string | No | File stem of palette to inherit colors from (e.g., `"ega"`) |
| `colors` | array[object] | No* | Color objects. Required unless `parent` is set. |

\* `colors` may be omitted when `parent` is specified; the parent's colors are used in full.

## Use Cases

### 1. Lospec.com Integration

Lospec provides palettes in a similar format via their API:

```text
https://lospec.com/palette-list/{palette_name}.json
```

**Import Strategy**:

- Fetch palette from Lospec API
- Save as user palette: `data/user/user-{lospecname}.json`
- Set `source` field to "lospec"
- Preserve original URL in `url` field
- Include Lospec's description and author attribution

With metadata support, we could:

- Import palettes directly from Lospec
- Preserve attribution and source information
- Display palette descriptions in interactive tools
- Link back to original source via URL field

### 2. User Palette Management

Users could:

- Organize palettes by tags
- Search by description content
- Credit original authors
- Track palette versions

### 3. Future Bit-Width Palettes

This format could support calculated palettes (15-16 bit) by adding:

- `bit_width`: Number of bits per channel
- `calculated`: Boolean flag indicating colors are generated
- `total_colors`: Total possible colors in the palette

Example for 15-bit palette (5-5-5 RGB):

```json
{
  "name": "15-bit RGB",
  "bit_width": 15,
  "calculated": true,
  "total_colors": 32768,
  "colors": []  // Empty, colors calculated at runtime
}
```

### 4. Retro Display Accuracy

The `native_resolution`, `pixel_aspect_ratio`, and `display_aspect_ratio` fields enable accurate period-correct rendering of images as they would appear on original hardware.

**Retro palette display reference:**

| File | Colors | `native_resolution` | `pixel_aspect_ratio` | `pixel_expansion` | `display_aspect_ratio` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `agi.json` | 16 EGA | `[160, 200]` | `[5, 3]` | `[2, 1]` | `[4, 3]` | Horizontal pixel doubling to 320×200 |
| `sci16.json` | 16 EGA | `[320, 200]` | `[5, 6]` | — | `[4, 3]` | Inherits `ega` colors |
| `sci256.json` | 256 VGA | `[320, 200]` | `[5, 6]` | — | `[4, 3]` | Inherits `vga256` colors |
| `scumm16.json` | 16 EGA | `[320, 200]` | `[5, 6]` | — | `[4, 3]` | Inherits `ega` colors |
| `scumm256.json` | 256 VGA | `[320, 200]` | `[5, 6]` | — | `[4, 3]` | Inherits `vga256` colors |
| `nes.json` | 54 NES | `[256, 224]` | `[8, 7]` | — | `[4, 3]` | |
| `snes.json` | 32768 (5-5-5) | `[256, 224]` | `[8, 7]` | — | `[4, 3]` | `BitDepthPalette`; 256 simultaneous |

> **Note on integer PAR values:** Always express `pixel_aspect_ratio` as integers (e.g., `[8, 7]`), not floats (e.g., `[1.0, 1.12]`). Floats introduce rounding errors and make the direction of stretch ambiguous. PAR is derivable from `native_resolution` + `display_aspect_ratio` — see Open Question 10.

**How the three fields combine — NES example:**

1. Pixelate input image to `native_resolution` → `256×224`
2. Apply `pixel_aspect_ratio` `[8, 7]` in `"integer"` mode → scale width ×8, height ×7 → `2048×1568`
3. Verify against `display_aspect_ratio`: `2048 ÷ 1568 ≈ 1.306 ≈ 4:3` ✓

**`display_scale_mode` values:**

| Mode | Behavior | Use case |
| --- | --- | --- |
| `"integer"` (default) | Scale by integer multiples from PAR. Every logical pixel maps to an identical-sized rectangle of screen pixels. | Pixel art, retro systems |
| `"nearest"` | Apply PAR as a float multiply and round. Slightly uneven pixel sizes. | When output canvas size matters more than pixel uniformity |
| `"smooth"` | Float multiply + bilinear interpolation. Soft edges. | Photos, non-pixel-art images |

When `pixel_aspect_ratio` is `[1, 1]` (square pixels), all three modes produce identical output — no stretching is applied.

### 5. Palette Inheritance

A palette can declare a `parent` to inherit its color data from another palette file, avoiding duplication. This is particularly useful for system palette families where only display metadata differs.

**Example — `sci16.json` inheriting EGA colors:**

```json
{
  "name": "Sierra SCI (16-color EGA)",
  "description": "Sierra SCI0 engine palette. Standard EGA 16 colors at 320x200.",
  "author": "Sierra On-Line",
  "source": "built-in",
  "tags": ["retro", "ega", "sierra", "sci"],
  "parent": "ega",
  "native_resolution": [320, 200],
  "pixel_aspect_ratio": [5, 6],
  "display_aspect_ratio": [4, 3],
  "display_scale_mode": "integer"
}
```

No `colors` field — the loader resolves `ega.json` and uses its colors entirely.

**Inheritance rules:**

- `parent` is the file stem of another palette in the same directory (e.g., `"ega"` → `ega.json`)
- `colors` omitted + `parent` set → use parent's colors in full
- `colors` present + `parent` set → use child's colors; parent colors are ignored
- Child metadata fields always win; parent only ever supplies colors
- Maximum depth: **1 level** — a parent palette must not itself declare a `parent`
- Missing parent → hard error at load time
- Circular reference → hard error (caught by depth limit)

**Base palette files (color data only, no display metadata):**

- `ega.json` — 16 standard EGA colors
- `vga256.json` — 256 standard VGA system colors (0–15: EGA compatible, 16–231: 6×6×6 RGB cube, 232–255: grayscale ramp)

## Implementation Requirements

### Breaking Changes

⚠️ **This is a breaking change** to the palette file format.

**Migration Strategy**:

1. Bump the major version
2. Support both formats during transition period
3. Provide migration tool to convert old palettes
4. Update all built-in palettes to new format

### Code Changes Required

#### 1. Palette Loading (`palette.py`)

- Detect format version (array vs object)
- Parse all metadata fields including display and parent fields
- Resolve `parent` palette when `colors` is absent (max depth: 1 level)
- Hard error on missing or circular parent references
- Maintain backward compatibility during transition
- Add `PaletteMetadata` dataclass
- Detect `bit_depth` field and return `BitDepthPalette` instead of `Palette`

#### 1a. New: `BitDepthPalette` class (`palette.py`)

A new class for palettes defined by per-channel bit depth (e.g., SNES 5-5-5). Lives in `palette.py` alongside `Palette`. Does **not** inherit from `Palette` — no shared implementation to reuse.

- Constructed from `bit_depth: list[int]` (e.g., `[5, 5, 5]`)
- `nearest_color(rgb)` — per-channel rounding, O(1), returns a `ColorRecord` constructed on the fly
- No `records` list, no indexes
- Duck-typed alongside `Palette` — callers using only `nearest_color()` need no changes
- `quantize_image_to_palette()` in `basic.py` needs an explicit `isinstance(palette, BitDepthPalette)` branch since it bypasses `nearest_color()` and iterates `records` directly
- `simultaneous_color_limit` stored as metadata; two-pass quantization (bit-depth reduce → histogram top-N remap) deferred to future work

#### 1b. New: `DisplayPalette` class (`color_tools/image/display_palette.py`)

A new class in the image module that wraps a `Palette` (or `BitDepthPalette`) and adds display rendering metadata. This is the intended home for retro display pipeline logic — it does **not** replace `Palette` for color science use.

- Contains a `Palette | BitDepthPalette` instance for color matching
- Carries display metadata: `native_resolution`, `pixel_aspect_ratio`, `pixel_expansion`, `display_aspect_ratio`, `display_scale_mode`, `preferred_integer_scales`, `simultaneous_color_limit`
- `DisplayPalette.load(name)` — resolves file, loads color data via `load_palette()`, wraps result with display metadata
- `nearest_color(rgb)` — delegates to internal palette
- Future: `apply(image)` — runs the full display pipeline (quantize → scale → aspect correct)
- `Palette` and `load_palette()` in `palette.py` remain **unchanged**

#### 2. Exporter Updates

Exporters that support metadata:

- **JSON exporter** - Include full metadata
- **GPL (GIMP)** - Add as comments
- **Lospec exporter** - NEW: Export in Lospec format

Exporters that don't support metadata:

- CSV, hex, pal, paintnet - Metadata lost (document this)

#### 3. Documentation Updates

- README.md - Palette file format section
- docs/Usage.md - Palette loading examples
- docs/Customization.md - Creating palettes with metadata
- .github/copilot-instructions.md - Update file structure rules

#### 4. Hash Integrity

- Update palette hash generation to include/exclude metadata
- Regenerate all palette hashes after format change
- Update `constants.py` with new hashes
- Document in `docs/Hash_Update_Guide.md`

#### 5. Testing

- Create test palettes in both formats
- Test backward compatibility
- Test metadata preservation through export/import cycles
- Test Lospec import functionality

### API Design

```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass(frozen=True)
class PaletteMetadata:
    """Metadata for a color palette."""
    name: str
    description: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    license: Optional[str] = None
    tags: Optional[List[str]] = None
    created: Optional[str] = None
    native_resolution: Optional[tuple[int, int]] = None
    pixel_aspect_ratio: Optional[tuple[int, int]] = None
    display_aspect_ratio: Optional[tuple[int, int]] = None
    display_scale_mode: Optional[str] = None  # "integer" | "nearest" | "smooth"
    parent: Optional[str] = None

class Palette:
    def __init__(
        self, 
        colors: List[ColorRecord],
        metadata: Optional[PaletteMetadata] = None
    ):
        self.records = colors
        self.metadata = metadata or PaletteMetadata(name="Unnamed Palette")
    
    @classmethod
    def load_from_file(cls, path: Path) -> 'Palette':
        """Load palette, detecting format automatically."""
        data = json.loads(path.read_text())
        
        # Detect format
        if isinstance(data, list):
            # Old format: array of colors
            colors = [ColorRecord(**c) for c in data]
            metadata = PaletteMetadata(name=path.stem)
        else:
            # New format: object with metadata
            colors = [ColorRecord(**c) for c in data['colors']]
            metadata = PaletteMetadata(
                name=data['name'],
                description=data.get('description'),
                author=data.get('author'),
                source=data.get('source'),
                url=data.get('url'),
                license=data.get('license'),
                tags=data.get('tags'),
                created=data.get('created'),
                native_resolution=tuple(data['native_resolution']) if 'native_resolution' in data else None,
                pixel_aspect_ratio=tuple(data['pixel_aspect_ratio']) if 'pixel_aspect_ratio' in data else None,
                display_aspect_ratio=tuple(data['display_aspect_ratio']) if 'display_aspect_ratio' in data else None,
                display_scale_mode=data.get('display_scale_mode'),
                parent=data.get('parent'),
            )
        
        return cls(colors, metadata)
    
    @classmethod
    def from_lospec(cls, palette_name: str) -> 'Palette':
        """
        Import palette directly from Lospec.com.
        
        Saves to: data/user/user-{palette_name}.json
        
        Args:
            palette_name: Lospec palette identifier
            
        Returns:
            Palette instance with full metadata
        """
        import urllib.request
        import json
        from pathlib import Path
        
        # Fetch from Lospec API
        url = f"https://lospec.com/palette-list/{palette_name}.json"
        with urllib.request.urlopen(url) as response:
            lospec_data = json.loads(response.read().decode())
        
        # Convert Lospec format to our format
        colors = []
        for hex_color in lospec_data['colors']:
            rgb = hex_to_rgb(hex_color)
            colors.append(ColorRecord(
                name=f"color_{len(colors)}",  # Lospec doesn't provide names
                hex=hex_color,
                rgb=rgb,
                hsl=rgb_to_hsl(rgb),
                lab=rgb_to_lab(rgb),
                lch=rgb_to_lch(rgb)
            ))
        
        # Build metadata
        metadata = PaletteMetadata(
            name=lospec_data.get('name', palette_name),
            description=lospec_data.get('description'),
            author=lospec_data.get('author'),
            source="lospec",
            url=url,
            tags=lospec_data.get('tags', [])
        )
        
        # Create palette instance
        palette = cls(colors, metadata)
        
        # Save as user palette
        user_dir = Path("color_tools/data/user")
        user_dir.mkdir(exist_ok=True)
        save_path = user_dir / f"user-{palette_name}.json"
        palette.save(save_path)
        
        return palette
```

## Open Questions

1. **Backward Compatibility Duration**: How long should we support the old format?
   - Option A: Forever (auto-detect on load)
   - Option B: 2-3 major versions
   - **Recommendation**: Option A - minimal overhead, maximum compatibility

2. **Built-in Palette Sources**: What should go in the `source` field?
   - "built-in" for system palettes (stored in `data/palettes/`)
   - "lospec" for Lospec imports (stored as `data/user/user-{name}.json`)
   - "user" for user-created palettes (stored in `data/user/`)
   - "import" for generic imports from other sources
   - **File Naming Convention**:
     - Built-in: `data/palettes/{name}.json` (e.g., `cga16.json`)
     - Lospec: `data/user/user-{lospec_name}.json` (e.g., `user-sweetie16.json`)
     - User: `data/user/{custom_name}.json` (user's choice)

3. **HTML in Descriptions**: Should we allow HTML in description fields?
   - Lospec uses HTML in descriptions
   - Security concern for user-generated content
   - **Recommendation**: Allow but sanitize on display

4. **Metadata in Export Formats**: Which formats should preserve metadata?
   - JSON: Yes (full preservation)
   - GPL: Comments only
   - CSV: Extra columns?
   - **Recommendation**: Document limitations per format

5. **Display Fields as a Group**: Should `native_resolution`, `pixel_aspect_ratio`, and `display_aspect_ratio` be required together or allowed independently?
   - Partial specification (e.g., resolution without PAR) is ambiguous
   - **Recommendation**: Treat as a group — either all three are present or none. Emit a warning if partially specified.

6. **Parent Resolution Path**: Where should the loader look for the parent palette file?
   - Option A: Same directory as the child file only
   - Option B: Search all palette directories (built-in + user)
   - **Recommendation**: Option A — simpler and avoids ambiguity. User palettes should not be parents of built-in palettes.

7. **Inheritance and Hash Integrity**: Should hash verification cover the raw file or the fully-resolved (post-parent) palette?
   - Hashing the resolved palette means parent changes invalidate child hashes
   - **Recommendation**: Hash the raw file only. Each file is independently verified; the parent is a separate hashed entity.

9. **`load_palette()` belongs to two worlds**: `load_palette()` is currently a public API function in `palette.py` and exported from `color_tools.__init__`. It has legitimate color science uses (e.g., match a filament RGB to the nearest Crayola color) that have nothing to do with image rendering. But it also loads retro display palettes (NES, CGA, Game Boy) that are image-module concerns. These two use cases share the same file format and loader today.
   - Moving `load_palette()` entirely into the image module would break the color science use case
   - Keeping it in `palette.py` means color science code stays aware of retro display palettes
   - Option A: Keep `load_palette()` in `palette.py` for color science; `DisplayPalette` has its own loader that wraps it
   - Option B: Split the palette files — named color palettes (crayola, web) stay with `palette.py`; retro display palettes move to `image/data/`; two separate loaders
   - Option C: `load_palette()` stays public and generic; `DisplayPalette.load()` calls it internally and layers display metadata on top
   - **Recommendation**: Option C — least disruption, cleanest layering. `Palette` and `load_palette()` remain unchanged; `DisplayPalette` is purely additive.

10. **PAR derivability**: `pixel_aspect_ratio` is mathematically derivable from `native_resolution` + `display_aspect_ratio` via `PAR = (DAR_w × native_h) / (DAR_h × native_w)`. Storing all three is redundant but explicit.
    - Option A: Store only `native_resolution` + `display_aspect_ratio`; derive PAR at load time
    - Option B: Store all three explicitly; validate consistency on load and warn if inconsistent
    - Option C: Store only `native_resolution` + `pixel_expansion` for systems with integer doubling; derive the rest
    - **Recommendation**: Option B — explicit is safer than derived, and a consistency check catches errors like the `[1.0, 1.12]` mistake in the earlier draft.

## Estimated Effort

- Planning/Design: 2-4 hours ✅
- Implementation: 8-12 hours
- Testing: 4-6 hours
- Documentation: 2-3 hours
- Migration: 1-2 hours
- **Total**: ~20-25 hours

## Future Scope (Out of This Implementation)

The following capabilities were identified during planning but are explicitly deferred:

- **Dither defaults** (`method`, `strength`) — per-palette suggested dither settings (e.g., ordered Bayer for AGI)
- **Color style adjustments** (`contrast`, `saturation`, `gamma`) — per-palette rendering tone adjustments
- **CRT post-processing** (`scanlines`, `crt_softness`) — visual effects to simulate phosphor/raster display
- **Two-pass quantization** for `simultaneous_color_limit` — bit-depth reduce first, then histogram top-N remap
- **Nested JSON format** — the `metadata` / `palette` / `display_profile` section structure seen in the `new/` draft files. Flat format adopted for now; nested can be revisited if field count grows unwieldy.

## Related Features

- **Lospec Integration**: Import palettes from Lospec.com API
- **`BitDepthPalette`**: New class for computed palettes (SNES 5-5-5, etc.)
- **`DisplayPalette`**: New image-module class wrapping palette + display metadata
- **Retro Display Accuracy**: Render images in correct aspect ratio for period hardware
- **Palette Inheritance**: Share color data across system-variant palettes via `parent`
- **Retro Palette Pack**: `agi`, `sci16`, `sci256`, `scumm16`, `scumm256`, `nes`, `snes` built-in palettes
- **Palette Browser**: Interactive palette selection with metadata display
- **Palette Tags**: Search and filter palettes by metadata

## References

- [Lospec Palette List](https://lospec.com/palette-list)
- [Lospec API Documentation](https://lospec.com/palette-list/load.json)
- Current palette files: `color_tools/data/palettes/`
- Current loading code: `color_tools/palette.py`

---

**Document Status**: ✅ Ready to implement
