# Palette Metadata Format Planning

**Status**: Planning / Deferred  
**Target Version**: TBD (post v6.0.0)  
**Created**: 2026-02-26

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
| `name` | string | Yes | Human-readable palette name |
| `description` | string | No | Detailed description (may contain HTML) |
| `author` | string | No | Original creator/source |
| `source` | string | No | Source identifier (e.g., "built-in", "lospec", "user") |
| `url` | string | No | Original URL if imported from external source |
| `license` | string | No | License information |
| `tags` | array[string] | No | Categorization tags |
| `created` | string | No | Creation date (ISO 8601 format) |
| `colors` | array[object] | Yes | Array of color objects (existing format) |

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

## Implementation Requirements

### Breaking Changes

⚠️ **This is a breaking change** to the palette file format.

**Migration Strategy**:

1. Bump to v7.0.0 (major version change)
2. Support both formats during transition period
3. Provide migration tool to convert old palettes
4. Update all built-in palettes to new format

### Code Changes Required

#### 1. Palette Loading (`palette.py`)

- Detect format version (array vs object)
- Parse metadata fields
- Maintain backward compatibility during transition
- Add `PaletteMetadata` dataclass

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

class Palette:
    def __init__(
        self, 
        colors: List[ColorRecord],
        metadata: Optional[PaletteMetadata] = None
    ):
        self.colors = colors
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
                created=data.get('created')
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
        import requests
        from pathlib import Path
        
        # Fetch from Lospec API
        url = f"https://lospec.com/palette-list/{palette_name}.json"
        response = requests.get(url)
        response.raise_for_status()
        lospec_data = response.json()
        
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

## Timeline

**Deferred** - This change is planned but not scheduled for immediate implementation.

**Prerequisites**:

- Complete v6.0.0 stabilization
- User feedback on current palette system
- Lospec integration testing

**Estimated Effort**:

- Planning/Design: 2-4 hours ✅ (completed 2026-02-26)
- Implementation: 8-12 hours
- Testing: 4-6 hours
- Documentation: 2-3 hours
- Migration: 1-2 hours
- **Total**: ~20-25 hours

## Related Features

- **Lospec Integration**: Import palettes from Lospec.com API
- **Bit-Width Palettes**: Support calculated palettes (15/16-bit RGB)
- **Palette Browser**: Interactive palette selection with metadata display
- **Palette Tags**: Search and filter palettes by metadata
- **Version Tracking**: Track palette versions and updates

## References

- [Lospec Palette List](https://lospec.com/palette-list)
- [Lospec API Documentation](https://lospec.com/palette-list/load.json)
- Current palette files: `color_tools/data/palettes/`
- Current loading code: `color_tools/palette.py`

---

**Document Status**: ✅ Complete planning document  
**Next Steps**: Monitor user requests, evaluate priority for v7.0.0 or later
