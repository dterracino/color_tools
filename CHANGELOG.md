<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### CMY and CMYK color space support

- `conversions.py`: `rgb_to_cmy(rgb)` — converts RGB (0-255) to CMY percentages (0-100 each).
  CMY is the simple 3-channel subtractive complement of RGB with no black channel.
- `conversions.py`: `cmy_to_rgb(cmy)` — converts CMY percentages back to RGB (0-255).
- `conversions.py`: `rgb_to_cmyk(rgb)` — converts RGB (0-255) to CMYK percentages (0-100 each).
  Extracts the K (black) channel from the CMY values so that pure black maps to `(0, 0, 0, 100)`
  instead of `(100, 100, 100, 0)`, matching standard print workflow conventions.
- `conversions.py`: `cmyk_to_rgb(cmyk)` — converts CMYK percentages back to RGB (0-255).
- All four functions exported from `color_tools.__init__`.
- CLI `convert` command: `--from` / `--to` now accept `cmy` and `cmyk` as choices.
- CLI `convert --value` now accepts a variable number of components (`nargs='+'`) so that
  CMYK's 4-value tuples are handled alongside the existing 3-value spaces.
  The handler validates the component count against the chosen space and exits with a clear
  error if the count is wrong.

```python
from color_tools import rgb_to_cmyk, cmyk_to_rgb, rgb_to_cmy, cmy_to_rgb

# RGB → CMYK (print workflow)
rgb_to_cmyk((255, 128, 0))    # → (0.0, 49.8039, 100.0, 0.0)

# RGB → CMY (simple subtractive)
rgb_to_cmy((255, 128, 0))     # → (0.0, 49.8039, 100.0)

# Round-trip
cmyk_to_rgb((0.0, 50.0, 100.0, 0.0))  # → (255, 128, 0)
cmy_to_rgb((0.0, 50.0, 100.0))         # → (255, 128, 0)
```

```bash
color-tools convert --from rgb --to cmyk --value 255 128 0
color-tools convert --from cmyk --to rgb --value 0 50 100 0
color-tools convert --from rgb --to cmy --value 255 128 0
color-tools convert --from cmy --to rgb --value 0 50 100
```

## [6.3.0] - 2026-04-13

### Added

- **`distance.py`** — New `delta_e_hyab()` HyAB distance metric (Abasi et al. 2020).

  ```text
  HyAB(L1,L2, a1,a2, b1,b2) = l_weight × |L1−L2| + √((a1−a2)² + (b1−b2)²)
  ```

  - Separates lightness and chromatic contributions (hybrid metric)
  - `l_weight=1.0` — pure HyAB; `l_weight=2.0` — recommended for k-means quantization
  - Exported from `color_tools` top-level package and listed in `__all__`
  - Accepted by `Palette.nearest_color()`, `nearest_colors()`, `FilamentPalette.nearest_filament()`,
    `nearest_filaments()` as `metric="hyab"`
  - Added to `--metric` choices for all three CLI commands (`color`, `filament`, `image`)

- **`image/analysis.py`** — Enhanced `extract_color_clusters()` with new keyword-only parameters:

  | Parameter | Default | Description |
  | --- | --- | --- |
  | `distance_metric` | `"lab"` | `"lab"`, `"rgb"`, or `"hyab"` |
  | `l_weight` | `1.0` | Lightness weight for HyAB mode |
  | `use_l_median` | `False` | Use median (not mean) of L for centroid update |
  | `n_iter` | `10` | Number of k-means iterations |

  - `use_lab_distance` retained for backward compatibility
  - Clusters now sorted by `pixel_count` descending (most dominant first)

- **`image/analysis.py`** — New `quantize_image_hyab(image_path, n_colors=16, *, n_iter=10, l_weight=2.0, use_l_median=True) -> PIL.Image.Image` convenience function.

  Runs HyAB k-means clustering, remaps every pixel to its nearest centroid, and returns a
  quantized `PIL.Image.Image`. Defaults mirror the Abasi et al. recommendations.

  ```python
  from color_tools.image import quantize_image_hyab
  img = quantize_image_hyab("photo.jpg", n_colors=8)
  img.save("photo_quantized.png")
  ```

  CLI:

  ```bash
  color-tools image --file photo.jpg --quantize-hyab --colors 16
  color-tools image --file photo.jpg --quantize-hyab --colors 8 --l-weight 1.5 --output out.png
  ```

- **`image/__init__.py`** — `quantize_image_hyab` exported and added to `__all__`
- **`tests/test_hyab.py`** — 36 new unit tests covering `delta_e_hyab`, palette dispatch,
  `extract_color_clusters` new params, and `quantize_image_hyab`
- **`conversions.py`** — New `rgb_to_winhsl240()` (Windows Paint / Win32 GDI variant) and
  `rgb_to_winhsl255()` (Microsoft Office variant) conversion functions.

  | Variant | H range | S range | L range | Used by |
  | --- | --- | --- | --- | --- |
  | winHSL240 | 0–239 | 0–240 | 0–240 | Windows Paint, WordPad, Win32 GDI |
  | winHSL255 | 0–254 | 0–255 | 0–255 | Microsoft Office colour picker |

  `rgb_to_winhsl()` is retained as a backward-compatible alias for `rgb_to_winhsl240()`.

- **`constants.py`** — Added `WIN_HSL240_HUE_MAX = 239`, `WIN_HSL240_SL_MAX = 240`,
  `WIN_HSL255_HUE_MAX = 254`, `WIN_HSL255_SL_MAX = 255` constants (constants hash updated).

### Fixed

- **`conversions.py`** — `rgb_to_winhsl()` hue clamping bug: `round(h * 240)` could produce
  `240` when the fractional hue was ≥ 239.5/240 (≈ 0.9979), which is out-of-spec because hue
  240 wraps back to 0° (red). Fixed in `rgb_to_winhsl240()` with `min(..., 239)`; same guard
  applied for the 255 variant (`min(..., 254)`).

### Added

- **`image/blend.py`** — New module implementing all 27 Photoshop-compatible blend modes for
  compositing two images together. Uses numpy for efficient per-pixel math and Pillow for I/O
  (no OpenCV dependency).

  **Blend modes implemented:**

  | Category | Modes |
  | ------------- | ------- |
  | Normal | `normal`, `dissolve` |
  | Darken | `darken`, `multiply`, `color_burn`, `linear_burn`, `darker_color` |
  | Lighten | `lighten`, `screen`, `color_dodge`, `linear_dodge`, `lighter_color` |
  | Contrast | `overlay`, `soft_light`, `hard_light`, `vivid_light`, `linear_light`, `pin_light`, `hard_mix` |
  | Comparative | `difference`, `exclusion`, `subtract`, `divide` |
  | Component | `hue`, `saturation`, `color`, `luminosity` |

  **Key implementation details:**
  - `soft_light` uses the correct W3C/Photoshop piecewise formula (not the Pegtop approximation)
  - `darker_color` / `lighter_color` compare full-pixel BT.601 luminance (not per-channel)
  - `hue` / `saturation` / `color` / `luminosity` use a fully vectorized `_set_sat()` replacing a
    prior O(W×H) Python pixel loop
  - Alpha channels are handled separately from RGB blending using src-over compositing:
    `out_α = blend_α × opacity + base_α × (1 − blend_α × opacity)`
  - `dissolve` uses opacity as the random selection threshold in `blend_images()` while
    remaining a clean 50/50 selector as a standalone function

  **Public API (exported from `color_tools.image`):**

  ```python
  from color_tools.image import blend_images, BLEND_MODES

  # Blend two images using multiply mode at 80% opacity
  result = blend_images("base.png", "layer.png", mode="multiply", opacity=0.8)
  result.save("output.png")

  # List all available blend modes
  print(sorted(BLEND_MODES.keys()))
  ```

### Fixed

- **`image/basic.py`** — Two type errors in `quantize_image_to_palette()`:
  - `quantized_colors` list comprehension now uses explicit 3-tuple construction
    `(int(...), int(...), int(...))` instead of `tuple(... for c in centroid)`, resolving
    `tuple[int, ...]` → `tuple[int, int, int]` inference failure.
  - `unique_colors` dict is now annotated as `dict[tuple[int, int, int], int]`, resolving
    `Unknown` key type that propagated to `palette.nearest_color()` call site.
- **`image/watermark.py`** — Removed orphaned `__all__` declaration that had been incorrectly
  placed at the bottom of the file. Public API is controlled exclusively by `image/__init__.py`,
  consistent with every other module in the package.

### Tests

- **`tests/test_image_blend.py`** — New test file with 217 tests covering all 27 blend mode
  functions, internal helpers (`_clip01`, `_lum`, `_sat`, `_set_lum`, `_set_sat`), and
  `blend_images()` I/O including opacity, alpha compositing, resize, file save, and input
  validation.
- **`tests/test_watermark.py`** — Added 48 tests across three new test classes:
  - `TestCalculatePosition` — all 9 position presets with margin arithmetic, custom tuple
    passthrough, `margin=0`, and invalid position string raises `KeyError`
  - `TestLoadFont` — both-args `ValueError`, missing file `FileNotFoundError`, default fallback,
    and bundled font file lookup by bare filename
  - `TestTextWatermarkPixelEffects` — `opacity=0.0` pixel-identity verification, output always
    RGBA regardless of input mode, size preservation, and `watermark_path` accepts both `Path`
    and `str`

### Documentation

- **`docs/sphinx/conf.py`** — `release` now reads from `color_tools.__version__` automatically
  instead of being hardcoded; copyright year is dynamic; `intersphinx_mapping` extended with
  `prompt_toolkit`; `autodoc_typehints = 'description'` set explicitly; `todo_include_todos`
  declared; `"linkify"` MyST extension removed (dependency was absent from `docs/requirements.txt`).
- **`docs/sphinx/api/color_tools.image.blend.rst`** — New API doc page for the blend module;
  added to the Image Processing section of `docs/sphinx/index.rst`.
- **`image/blend.py`** — Module docstring updated: blend mode categories reformatted as a
  preformatted literal block (fixes RST indentation errors in Sphinx build); added *Primary API*
  section explaining that `blend_images()` and `BLEND_MODES` are the standard entry points and
  that the 27 individual mode functions are exposed for advanced numpy-pipeline use only.
- **`image/basic.py`** — Removed stale "Public API" listing from module docstring; autodoc
  renders the actual function inventory, making the prose list redundant and drift-prone.
- **`exporters/__init__.py`** — Removed stale "Public API" listing from module docstring for the
  same reason.
- **`color_tools/image/README.md`** — Added a callout block to the blend modes section explaining
  that `blend_images()` and `BLEND_MODES` are the primary API and that the individual mode
  functions require normalized float32 numpy arrays if called directly.
- **`NEXTSTEPS.md`** — New root-level file. The `### Planned` section that had been living inside
  the 6.2.0 CHANGELOG entry was moved here; planned items are not part of a release record.
- **`docs/sphinx/conf.py`** — Added `html_theme_options`: GA4 analytics (`G-Y7FDTT39XW`),
  `collapse_navigation: False` (sidebar no longer collapses when navigating to submodule pages),
  and explicit `navigation_depth: 4`.
- **`matrices.py`** — All 6 matrix constants (`PROTANOPIA_SIMULATION`, `DEUTERANOPIA_SIMULATION`,
  `TRITANOPIA_SIMULATION`, `PROTANOPIA_CORRECTION`, `DEUTERANOPIA_CORRECTION`,
  `TRITANOPIA_CORRECTION`) now appear in the Sphinx docs. Previously used `#` comments which
  autodoc ignores; converted to `#:` attribute docstrings. `Matrix3x3` type alias upgraded from
  a bare assignment to a proper `TypeAlias` annotation so Sphinx renders the clean alias name
  instead of the fully-expanded tuple type in each constant's signature.

## [6.1.4] - 2026-03-29

### Changed

- **`image/analysis.py` docstrings**: Clarified that `l_value_to_hueforge_layer` and
  `redistribute_luminance` operate on **LCH L values** (perceptual lightness, 0–100), not HSL
  lightness. The implementation was already correct; only the documentation was ambiguous.
- **`pyproject.toml`**: `[all]` extra now uses self-referencing sub-extras
  (`color-match-tools[fuzzy,image,interactive]`) instead of a manually duplicated flat list,
  preventing silent drift when individual extras are updated. Also excludes `[docs]` and `[dev]`
  from `[all]` since those are not user-facing.
- **`pyproject.toml`**: Added `coverage>=7.0.0` to `[dev]` extra to match `requirements-dev.txt`.
- **`pyproject.toml`** / **`copilot-instructions.md`**: Removed `[mcp]` extra — MCP server is
  planned but not yet implemented, so advertising it as an installable extra was incorrect.
- **`requirements-*.txt`**: All requirements files now delegate to `pyproject.toml` extras via
  `-e .[extra]` instead of duplicating package lists. `pyproject.toml` is the single source of
  truth; the `.txt` files are just convenient shortcuts for `pip install -r`.
- **`pyproject.toml [image]`**: Added missing `cairosvg>=2.7.0` — it was in
  `requirements-image.txt` and actively used by `image/watermark.py` but absent from the extras
  definition, meaning `pip install color-match-tools[image]` would silently omit it.
- **`pyproject.toml [dev]`**: Added `coverage>=7.0.0` to match prior `requirements-dev.txt`.

## [6.1.3] - 2026-03-29

### Fixed

- **`ResourceWarning` unclosed PIL file handles** — three locations where `PIL.Image.open()` was
  called without a context manager left file handles open on Windows, generating `ResourceWarning`
  during tests:
  - `cli_commands/handlers/image.py`: watermark handler now uses `with Image.open(...) as _f: img = _f.copy()`
  - `image/basic.py` (`apply_pixel_transform`): replaced bare `PIL.Image.open()` with context manager + `.copy()`
  - `image/basic.py` (`quantize_image_to_palette`): replaced chained `.open().convert()` with context manager

## [6.1.2] - 2026-03-29

### Fixed

- **`export.py` incorrect `FilamentRecord` import** — `FilamentRecord` was incorrectly imported from
  `color_tools.palette` under `TYPE_CHECKING`; it resides in `color_tools.filament_palette`. This caused
  Sphinx to emit `Cannot resolve forward reference` warnings for all functions with `FilamentRecord`
  type annotations (`export_filaments`, `export_filaments_autoforge`, `export_filaments_csv`,
  `export_filaments_json`)
- **`exporters/base.py` same `FilamentRecord` wrong import** — identical fix applied to the exporter
  base class which had the same incorrect import
- **Sphinx docs: duplicate object description warnings eliminated** — Frozen dataclass attribute fields
  (`ColorRecord`, `ColorValidationRecord`, `ColorCluster`, `ColorChange`) were documented twice because
  Napoleon's Attributes section and autodoc both registered the same `py:attribute` domain entries.
  Fixed by setting `napoleon_use_ivar = True` in `docs/sphinx/conf.py` so Napoleon emits `:ivar:` field
  lists instead of standalone attribute directives, preventing the collision
- **Sphinx docs: stale metadata updated** — `docs/sphinx/conf.py` had `release = '5.2.0'` (now `6.1.2`)
  and `copyright = '2024, ...'` (now `2024-2026, ...`); also removed unnecessary `'special-members':
  '__init__'` from `autodoc_default_options` and set `always_document_param_types = False` to avoid
  redundant `__init__` parameter documentation on auto-generated dataclass constructors
- **Sphinx docs: 27 modules missing from API docs** — `docs/sphinx/index.rst` previously listed only
  12 top-level modules; the following were not documented at all:
  - `color_tools.filament_palette`
  - `color_tools.exporters` + all 8 exporter submodules (`base`, `csv_exporter`, `json_exporter`,
    `gpl_exporter`, `hex_exporter`, `jascpal_exporter`, `autoforge_exporter`, `lospec_exporter`,
    `paintnet_exporter`)
  - `color_tools.image.analysis`, `image.basic`, `image.conversion`, `image.watermark`
  - `color_tools.cli`, `cli_commands`, `cli_commands.utils`, `cli_commands.reporting`,
    `cli_commands.handlers` + all 7 handler modules
  - `color_tools.interactive_manager`
  
  Index now organizes all modules into labeled sections: *Color Science*, *Color & Filament Data*,
  *Export System*, *Image Processing*, *Command Line Interface*, *Optional Features*
- **Docstring RST formatting fixed in newly-exposed modules** — several modules had docstring
  formatting that caused Sphinx parse warnings once included in the docs:
  - `exporters/lospec_exporter.py`: converted bare indented blocks to RST literal blocks (`::`)
  - `filament_palette.py` (`load_owned_filaments`): converted markdown fenced code block to RST `::` syntax
  - `image/basic.py`: removed developer TODO notes from module docstring (caused RST indentation errors)
  - `interactive_manager.py`: added `__all__` to prevent autodoc from pulling in imported
    `prompt_toolkit` classes and generating unresolvable forward reference warnings

## [6.1.1] - 2026-03-28

### Fixed

- **Stray merge conflict marker removed from CHANGELOG.md** — a leftover `>>>>>>>` git conflict marker
  from a prior merge was present in the 6.1.0 release, causing a markdownlint MD032 warning
- **Pyright type errors fixed in `tests/test_image_transform.py`** — narrowed `Image.getpixel()` return
  type with `isinstance` assertions; cast `dict` value to `float` for `assertAlmostEqual` calls

- **Case-insensitive maker and finish matching** - Currently maker names and finishes are case-sensitive in FilamentPalette
  - **Problem**: Searching for `--maker "Flashforge"` won't match database entry "FlashForge" (case mismatch)
  - **Problem**: Similar issue with finish matching (e.g., "matte" vs "Matte")
  - **Fix planned**: Normalize maker and finish names to lowercase during index construction and input lookups

## [6.1.0] - 2026-03-28

### Added

- **Plugin-based exporter architecture** - New extensible exporter system in `exporters/` folder
  - **Plugin pattern:** Add new exporters without modifying existing code
  - **Auto-registration:** Exporters use `@register_exporter` decorator for automatic discovery
  - **Metadata-driven:** Each exporter declares capabilities (colors/filaments, binary/text, file extension)
  - **Base classes:** `PaletteExporter` abstract base class and `ExporterMetadata` dataclass
  - **Registry system:** `get_exporter()` and `list_export_formats()` for format discovery
  - **Backward compatible:** All existing export functions work identically (delegate to new system)
  - **Easy to extend:** See exporter files in `color_tools/exporters/` for examples
  - **Future-ready:** Designed for binary formats (Adobe ACO/ACT), image formats (PNG swatches), etc.
  
  Example usage:

  ```python
  from color_tools.exporters import get_exporter, list_export_formats
  from color_tools import Palette
  
  # List available formats
  formats = list_export_formats('colors')
  # {'csv': '...', 'json': '...', 'gpl': '...', 'hex': '...', ...}
  
  # Use any exporter
  exporter = get_exporter('gpl')
  palette = Palette.load_default()
  path = exporter.export_colors(palette.records[:20], 'my_palette.gpl')
  ```
  
  For developers: Create new exporters by subclassing `PaletteExporter` - see `color_tools/exporters/base.py`

- **Five new palette export formats** - Text-based formats for graphics tools and palette sharing:
  
  **1. Hex format (.hex)** - Simple hex color list

  ```python
  from color_tools.exporters import get_exporter
  exporter = get_exporter('hex')
  exporter.export_colors(colors, 'palette.hex')
  # Output: Uppercase hex codes, one per line (no # prefix)
  # 000000
  # FF0000
  # 00FF00
  ```
  
  **2. JASC-PAL (.pal)** - Paint Shop Pro palette format

  ```python
  exporter = get_exporter('pal')
  exporter.export_colors(colors, 'palette.pal')
  # Format: JASC-PAL header + RGB decimal values
  # Compatible with Paint Shop Pro, Aseprite, and many image editors
  ```
  
  **3. PAINT.NET (.txt)** - PAINT.NET palette format

  ```python
  exporter = get_exporter('paintnet')
  exporter.export_colors(colors, 'palette.txt')
  # Format: AARRGGBB hex codes with comment headers
  # FF000000 (fully opaque black)
  ```
  
  **4. Lospec JSON (.json)** - Lospec.com palette format

  ```python
  exporter = get_exporter('lospec')
  exporter.export_colors(colors, 'palette.json')
  # Format: {"name": "...", "author": "", "colors": ["hex", ...]}
  # Perfect for sharing palettes on Lospec.com/palette-list
  ```
  
  **5. GIMP Palette (.gpl)** - GIMP/Inkscape/Krita format

  ```python
  exporter = get_exporter('gpl')
  exporter.export_colors(colors, 'palette.gpl')
  # Format: GIMP Palette with RGB values and color names
  # Compatible with GIMP, Inkscape, Krita, and other graphics applications
  ```
  
  All formats support both colors and filaments (except where noted).
  Use `list_export_formats('colors')` or `list_export_formats('filaments')` to see available formats.

- **Owned filaments tracking** - Track which filaments you own for personalized recommendations
  - **File:** `data/user/owned-filaments.json` - Simple list of filament IDs you own
  - **Auto-detect:** If file exists with IDs, filament searches default to owned filaments only
  - **Override:** Use `--all-filaments` flag to search all filaments (shopping/browsing mode)
  - **Management:** Add/remove filaments with `--add-owned` and `--remove-owned` commands
  - **List:** See owned filaments with `--list-owned` command
  - **Format:** `{"owned_filaments": ["id1", "id2", ...]}` - future-proof nested structure
  - **Zero impact:** Users without owned-filaments.json see no behavior changes
  - **Fast:** O(1) lookup using set-based filtering
  
  Example usage:

  ```bash
  # Add filaments you own
  color-tools filament --add-owned "bambu-lab_pla-matte_jet-black"
  color-tools filament --add-owned "polymaker_polyterra-pla_charcoal-black"
  
  # List owned filaments
  color-tools filament --list-owned
  
  # Find nearest match (auto-searches owned only)
  color-tools filament --nearest --hex "#FF5733"
  
  # Override to search ALL filaments (shopping mode)
  color-tools filament --nearest --hex "#FF5733" --all-filaments
  
  # Remove a filament
  color-tools filament --remove-owned "bambu-lab_pla-matte_jet-black"
  ```
  
  Python API:

  ```python
  from color_tools import FilamentPalette, load_owned_filaments, save_owned_filaments
  
  # Load with auto-detection
  palette = FilamentPalette.load_default()  # Auto-loads owned filaments if file exists
  
  # Filtering auto-detects owned (searches owned if file exists)
  matches = palette.filter(maker="Bambu Lab")  # Owned only if file exists
  matches = palette.filter(maker="Bambu Lab", owned=False)  # Force all filaments
  
  # Nearest filament searches respect owned by default
  filament, distance = palette.nearest_filament((255, 87, 51))  # Owned only if file exists
  filament, distance = palette.nearest_filament((255, 87, 51), owned=False)  # All filaments
  
  # Manage owned list programmatically
  palette.add_owned("bambu-lab_pla-matte_white")  # Auto-saves
  palette.remove_owned("bambu-lab_pla-matte_white")  # Auto-saves
  owned_records = palette.list_owned()  # Get FilamentRecord objects
  
  # Manual loading/saving
  owned_ids = load_owned_filaments()  # Returns set of IDs
  owned_ids.add("new-filament-id")
  save_owned_filaments(owned_ids)
  ```

- **Interactive filament library manager** - Full-featured TUI for managing owned filaments (requires `[interactive]` extra)
  - **Rich terminal UI:** Built with prompt_toolkit for modern, responsive interface
  - **Visual feedback:** Cyan highlighting for owned filaments, yellow asterisk for unsaved changes
  - **Quick navigation:** Arrow keys, Page Up/Down, Home/End for fast browsing
  - **Live filtering:** Press `f` to filter by Maker/Type/Finish/Color with Tab navigation
  - **Batch operations:** Space to toggle owned status, works with all 913 filaments
  - **Safe editing:** Changes tracked with visual indicator, prompt to save on quit
  - **Session summary:** Shows added/removed filaments with full details on exit
  - **Zero dependencies:** Only requires prompt_toolkit (installed with `[interactive]` extra)
  
  Launch the manager:

  ```bash
  # Install the interactive extra first
  pip install color-match-tools[interactive]
  
  # Launch interactive manager
  color-tools filament --manage
  ```
  
  Key bindings:
  - **Spc** - Toggle owned status of selected filament
  - **↑↓/PgUp/PgDn/Home/End** - Navigate filament list
  - **(f)** - Enter filter mode (Maker/Type/Finish/Color fields)
  - **Tab** - Navigate between filter fields (in filter mode)
  - **Esc** - Exit filter mode or quit (if no unsaved changes)
  - **(c)** - Clear all active filters
  - **(r)** - Revert unsaved ownership changes
  - **(s)** - Save changes to owned-filaments.json
  - **(q)** - Quit (prompts to save if changes exist)
  
  Features:
  - **Live filtering** - Type in filter fields to narrow down 913 filaments instantly
  - **Visual indicators** - Owned filaments shown in cyan, asterisk shows unsaved changes
  - **Smart confirmation** - Prompts y/n/Esc when quitting with unsaved changes
  - **Exit summary** - Shows detailed list of added/removed filaments on exit
  - **Frame-perfect UI** - Clean bordered display that adapts to filter state
  
  Example workflow:
  1. `color-tools filament --manage` - Launch manager
  2. Press `f` - Enter filter mode
  3. Type "Bambu" in Maker field - See only Bambu Lab filaments
  4. Tab to Type field, type "PLA" - Narrow to just PLA
  5. Esc - Exit filter mode
  6. Space - Toggle owned status on visible filaments
  7. `s` - Save changes
  8. `q` - Quit and see summary of changes

- **Comprehensive exporter test coverage** - Added 14 new unit tests for plugin architecture
  - Registry system tests (get_exporter, metadata validation, filtering)
  - CSV exporter tests (structure, empty exports, field validation)
  - JSON exporter tests (structure, Unicode handling)
  - Error handling tests (unsupported formats, type mismatches)
  - Total export tests: 32 (increased from 18, 78% increase)
  - All tests passing with 100% backward compatibility

- **Comprehensive CLI and image test coverage** - Significantly expanded test suite for CLI commands and image processing
  - Added `tests/test_cli_utils.py`, `tests/test_exporters_palette_formats.py`, `tests/test_cli_handlers.py`, `tests/test_cli_reporting.py`, `tests/test_cli_main.py`
  - Added `tests/test_image_transform.py` covering `transform_image()`, `simulate_cvd_image()`, `correct_cvd_image()`, `quantize_image_to_palette()`, dependency error paths, and noise level sigma branches
  - Expanded `TestHandleImageCommandOperations` class covering all image handler operation branches
  - **Coverage improvements**: `handlers/image.py` 27% → 84%, `image/basic.py` 42% → 94%
  - Total tests: 846 (increased from 502)

### Changed

- **Palette module architecture** - Split large palette.py (1,733 lines) into focused modules
  - `palette.py` (654 lines) - CSS color palettes and search (ColorRecord, Palette class)
  - `filament_palette.py` (1,004 lines) - 3D printing filament palettes and search (FilamentRecord, FilamentPalette class)
  - `_palette_utils.py` (76 lines) - Shared utility functions (private module)
  - Each module has a single, well-defined responsibility following separation of concerns
  - **100% backward compatible** - All imports from `color_tools` package work identically
  - Updated `constants.py` hash after adding `MATRICES_EXPECTED_HASH` constant
  - No user-facing changes - all functionality remains identical

- **Exporter code organization** - Separated AutoForge exporter into dedicated file
  - `csv_exporter.py` now only handles generic CSV export (single responsibility)
  - `autoforge_exporter.py` contains specialized AutoForge filament export format
  - Each exporter file has one clear purpose following separation of concerns
  - No user-facing changes - all functionality remains identical

### Fixed

- **Exporter format categorization** - Corrected which formats support filaments
  - **Universal formats** (preserve full metadata): CSV, JSON only
  - **Palette formats** (colors-only): Hex, JASC-PAL, PAINT.NET, Lospec, GIMP Palette
  - **Filament formats**: AutoForge
  - Palette formats technically could export filament color values but lose critical metadata (maker, type, finish, TD values)
  - Changed `supports_filaments=False` for hex, pal, paintnet, lospec exporters
  - Documentation and behavior now correctly reflect that only CSV and JSON preserve full filament data

## [6.0.0] - 2026-02-26

### Added

- **PICO-8 retro palette** - Added official PICO-8 fantasy console palette (16 colors)
  - Palette name: `pico8`
  - Includes all 16 official PICO-8 colors with proper names (black, dark-blue, dark-purple, dark-green, brown, dark-grey, light-grey, white, red, orange, yellow, green, blue, lavender, pink, light-peach)
  - Available for color matching, image quantization, and all palette operations
  - Added `PICO8_PALETTE_HASH` constant for data integrity verification
  - Example: `color-tools color --palette pico8 --name orange`

- **User data example files** - Added example files to help users get started with custom data
  - `data/user/user-colors.example.json` - Example custom color entries
  - `data/user/user-filaments.example.json` - Example custom filament entries (shows full, minimal, and null optional fields)
  - `data/user/user-synonyms.example.json` - Example maker name synonyms
  - Copy/rename these `.example.json` files to the actual filenames to start adding custom data

### Changed

- **BREAKING: Palette listing output format** - Both `color --palette list` and `image --list-palettes` now display color counts
  - **Old format:** Simple list of palette names
  - **New format:** Aligned table with palette names and color counts (e.g., "pico8 - 16 colors")
  - **Impact:** Scripts parsing palette list output will need updates
  - **Benefit:** Users can now see palette sizes at a glance, and both commands show identical output
  - Both commands now use the same underlying function (`get_available_palettes()`) for consistency (DRY)

### Fixed

- **Palette listing bug** - Fixed `get_available_palettes()` path calculation
  - Was looking in wrong directory (`cli_commands/data/` instead of `color_tools/data/`)
  - Now correctly finds all core and user palettes
  - Fixed `color --palette list` to show all palettes (was returning "No palettes found")
  - Fixed `image --list-palettes` to include user palettes (previously only showed core palettes)

- **Documentation correction** - Updated documentation to correctly reflect that user data verification is optional (not disabled)
  - Corrected `docs/Customization.md` to explain optional `.sha256` verification for user data
  - Corrected `docs/Troubleshooting.md` to clarify user files are "optionally verified" not "not verified"
  - Added code examples for `--generate-user-hashes` and `--verify-user-data` commands
  - Previous docs incorrectly stated user files weren't verified, but v4.0.0 added optional hash verification
  - Updated `docs/FAQ.md` to document both palette listing commands and include pico8 in palette list

### Migration Guide

If you have scripts that parse the output of `color --palette list` or `image --list-palettes`:

**Before (5.x):**

```text
Available palettes:
  cga4
  ega16
  vga
```

**After (6.0.0):**

```text
Available palettes:
  cga4            - 4 colors
  ega16           - 16 colors
  vga             - 256 colors
```

**To adapt your scripts:**

- Parse the first column (palette name) only
- Or use `awk '{print $1}'` to extract just the palette name
- Example: `color-tools color --palette list | grep -v "Available" | awk '{print $1}'`

## [5.6.1] - 2024-12-24

### Fixed

- **CLI documentation** - Updated all CLI help text and docstrings to document image conversion and watermarking features
  - Updated main CLI epilog with conversion and watermarking examples
  - Expanded image parser description to list all 6 operation types
  - Updated `color_tools/__init__.py` docstring with conversion/watermarking examples
  - Updated `color_tools/image/__init__.py` docstring with comprehensive examples
  - Updated `color_tools/cli_commands/handlers/image.py` docstring
  - Added detailed sections in `color_tools/image/README.md` for:
    - Section 6: Image Format Conversion (formats, quality defaults, CLI/API examples)
    - Section 7: Image Watermarking (text/image/SVG types, positioning, styling)

## [5.6.0] - 2024-12-24

### Added

- **Image format conversion** - Simple, high-quality conversion between image formats
  - **CLI usage:**

    ```bash
    # Convert WebP to PNG (auto-generates output.png)
    color-tools image --file input.webp --convert png
    
    # Convert with custom output path
    color-tools image --file photo.jpg --convert webp --output result.webp
    
    # JPEG with custom quality (default: 67, Photoshop quality 8 equivalent)
    color-tools image --file photo.png --convert jpg --quality 85
    
    # WebP with lossy compression (default: lossless)
    color-tools image --file photo.jpg --convert webp --lossy --quality 80
    ```

  - **Supported formats:**
    - Standard: PNG, JPEG, WebP, BMP, GIF, TIFF, AVIF, ICO, PCX, PPM, SGI, TGA
    - HEIC/HEIF: Supported via `pillow-heif` (included in `[image]` extras)
  - **Quality defaults:**
    - JPEG: Quality 67 (Photoshop quality 8/12 equivalent)
    - WebP: Lossless by default (use `--lossy` for lossy compression)
    - AVIF: Quality 80 for lossy, 100 for lossless
    - PNG: Always lossless with optimized compression
  - **Features:**
    - Auto-detects input format from file extension
    - Auto-generates output filename (e.g., `input.webp` → `input.png`)
    - Case-insensitive format names
    - Handles format aliases (jpg/jpeg, tif/tiff)
    - Automatic RGBA → RGB conversion for formats that don't support transparency
  - **Python API:**

    ```python
    from color_tools.image import convert_image
    
    # Simple conversion
    convert_image("photo.webp", output_format="png")
    
    # Custom quality
    convert_image("photo.png", output_format="jpg", quality=90)
    
    # Lossy WebP
    convert_image("photo.jpg", output_format="webp", lossless=False, quality=80)
    ```

  - **Dependencies:** Added `pillow-heif>=0.14.0` to `[image]` extras for HEIC support
  - **Tests:** 21 comprehensive tests covering format conversion, quality settings, and edge cases

- **Comprehensive CLI integration tests** - Added 30 integration tests for command-line interface
  - **Test coverage:**
    - Basic CLI functionality (help, version, no-args behavior)
    - All 7 commands (color, filament, convert, name, validate, cvd, image)
    - Verification flags (--verify-constants, --verify-data, --verify-matrices, --verify-all)
    - Error handling and exit codes
    - JSON output formatting
  - **Implementation:** Subprocess-based tests calling actual CLI commands for real-world validation
  - **Windows Unicode handling:** UTF-8 encoding configured in CLI for Unicode checkmarks (✓/✗)
  - **Test suite total:** 522 tests (471 existing + 30 CLI + 21 conversion tests)

- **Image watermarking functionality** - Add text, image, or SVG watermarks to images with full customization
  - **Three watermark types:**
    - **Text watermarks** - Custom text with font control, colors, stroke/outline
    - **Image watermarks** - PNG/image file overlays with transparency support
    - **SVG watermarks** - Vector logo support (requires cairosvg)
  - **Position control:**
    - 9 preset positions: top-left, top-center, top-right, center-left, center, center-right, bottom-left, bottom-center, bottom-right
    - Custom x,y coordinates for precise placement
    - Adjustable margins from edges
  - **Text styling options:**
    - System fonts by name (e.g., Arial, Times New Roman) via `--font-name`
    - Custom font files (.ttf, .otf) via `--font-file`
    - Font files can be placed in `color_tools/image/fonts/` directory for easy access
    - Adjustable font size, color (RGB), and opacity
    - Stroke/outline support with configurable color and width
  - **Image/SVG options:**
    - Scale control for sizing
    - Opacity/transparency adjustment
    - Automatic RGBA handling for transparency
  - **CLI usage:**

    ```bash
    # Text watermark with stroke
    color-tools image --file photo.jpg --watermark \
      --watermark-text "© 2025 My Brand" \
      --watermark-position bottom-right \
      --watermark-font-file Roboto-Bold.ttf \
      --watermark-font-size 32 \
      --watermark-color 255,255,255 \
      --watermark-stroke-color 0,0,0 \
      --watermark-stroke-width 2 \
      --watermark-opacity 0.7
    
    # Image watermark
    color-tools image --file photo.jpg --watermark \
      --watermark-image logo.png \
      --watermark-position top-left \
      --watermark-scale 0.2 \
      --watermark-opacity 0.6
    
    # SVG watermark
    color-tools image --file photo.jpg --watermark \
      --watermark-svg logo.svg \
      --watermark-position center \
      --watermark-scale 1.5 \
      --watermark-opacity 0.5
    ```

  - **Python API:**

    ```python
    from color_tools.image import add_text_watermark, add_image_watermark, add_svg_watermark
    from PIL import Image
    
    img = Image.open("photo.jpg")
    
    # Text with outline
    watermarked = add_text_watermark(
        img,
        text="© 2025",
        font_file="Roboto-Bold.ttf",
        font_size=36,
        color=(255, 255, 255),
        stroke_color=(0, 0, 0),
        stroke_width=2,
        position="bottom-right",
        opacity=0.8
    )
    
    # Image logo
    watermarked = add_image_watermark(
        img,
        watermark_path="logo.png",
        position="top-left",
        scale=0.3,
        opacity=0.7
    )
    
    # SVG logo (requires cairosvg)
    watermarked = add_svg_watermark(
        img,
        svg_path="logo.svg",
        position="center",
        opacity=0.6
    )
    ```

  - **Font directory:** Created `color_tools/image/fonts/` for custom fonts
    - Place .ttf or .otf files here for easy access
    - Reference by filename only: `--font-file MyFont.ttf`
    - Or use full paths for fonts elsewhere
    - See `color_tools/image/fonts/README.md` for details
  - **Dependencies:** Added `cairosvg>=2.7.0` to `requirements-image.txt` for SVG support
    - **Windows users:** If SVG watermarks fail after installing `[image]` extras, install the GTK runtime for Cairo C libraries
    - Download from: <https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases>
    - This provides the necessary Cairo/cairocffi dependencies for SVG rendering
  - **Comprehensive tests:** Added `tests/test_watermark.py` with 30+ test cases

### Changed

- **Internal CLI refactoring - Complete reorganization** - Extracted all CLI logic into dedicated package
  - Created `cli_commands/` package containing all CLI-specific code:
    - `handlers/` - Individual command handler modules (7 files):
      - `color.py` (165 lines) - Color search and query logic
      - `filament.py` (172 lines) - Filament search and filtering logic
      - `convert.py` (126 lines) - Color space conversion and gamut checking
      - `name.py` (57 lines) - Color name generation
      - `validate.py` (55 lines) - Color name/hex validation
      - `cvd.py` (75 lines) - Color vision deficiency simulation/correction
      - `image.py` (290 lines) - Image processing operations (HueForge, CVD, quantize, watermark)
    - `utils.py` (162 lines) - Validation and parsing utilities shared by handlers
    - `reporting.py` (300 lines) - User data diagnostics, override reporting, and verification logic
  - Reduced `cli.py` from 1776 lines to 706 lines (60.2% reduction, 1070 lines extracted)
  - **Benefits:**
    - All CLI logic now in one cohesive `cli_commands/` package
    - Each command handler is independent and testable
    - Shared utilities consolidated in one place
    - Verification/diagnostic code separated from main flow
    - Clear separation between CLI and library code
    - Consistent handler structure across all commands
  - No user-facing changes - purely internal code organization
  - All 522 tests passing with no regressions

### Fixed

## [5.5.0] - 2024-12-24

### Added

- **Four new retro palettes** - Added classic computer palettes for nostalgic conversions
  - **Apple II** (6 colors): Black, Red, Purple, Green, Cyan, Light Gray
  - **Macintosh** (8 colors): 8 grayscale shades from classic Mac
  - **Game Boy Color** (14 colors): Extended Game Boy palette with color variations
  - **Tandy 16** (16 colors): Full Tandy RGB/CGA-compatible 16-color palette
  - All palettes work with `--quantize-palette` image command
  - Example: `color-tools image --file photo.jpg --quantize-palette apple2`
  - Total retro palettes available: 19 (now 20 with pico8 added in v6.0.0)

### Changed

- **Palette quantization performance optimization** - Dramatically improved conversion speed for high-color images
  - **Before:** Slow conversions taking multiple seconds for large images
  - **After:** ~0.95 seconds for 1015×1015 image with 245k unique colors (nearly instant, comparable to web-based tools)
  - **Optimizations:**
    - Pixel sampling: Max 10k samples for k-means clustering (not all pixels)
    - k-means++ initialization: Better centroid selection than random
    - Reduced iterations: 5 instead of 10 (converges quickly with smart initialization)
    - Vectorized numpy operations: Eliminated Python loops, pure array math
    - RGB space k-means: Avoided expensive LAB conversions during clustering
    - Vectorized final assignment: All pixels assigned in one operation
  - **Impact:** Professional-grade speed with maintained visual quality

### Fixed

- **Palette quantization color collapse and detail loss** - Fixed critical bugs in retro palette conversions
  - **Problem 1:** 4-color images collapsed to 2 colors when mapped to 4-color palettes (CGA4, Gameboy)
  - **Problem 2:** High-color images lost significant detail, mapping most pixels to black/white extremes
  - **Root cause:** Per-pixel nearest-color matching without intelligent color reduction
  - **Solution:** Hybrid approach using k-means quantization + collision-free palette mapping
    - **High-color images** (unique colors > palette size): Use k-means clustering to reduce to palette_size representative colors, preserving image structure and detail
    - **Low-color images** (unique colors ≤ palette size): Direct 1:1 mapping with L-value sorting
    - Collision-free mapping ensures all palette colors are utilized
    - Color map dictionary provides O(1) pixel lookups
  - **Impact:** Retro palette conversions now preserve visual detail comparable to professional tools
  - **Examples:**
    - gb-megaman-title.png (4 colors) → CGA4: All 4 colors preserved (was 2)
    - purple-dragon.jpg (245k colors) → Gameboy: Detail preserved across all 4 shades (was mostly black/white)

## [5.4.0] - 2024-12-23

### Added

- **HueForge filament data import** - Imported 328 new filaments from HueForge dataset
  - **20 NEW manufacturers added:**
    - 3D Jake (3 filaments)
    - Atomic (2 filaments)
    - ERYONE (10 filaments)
    - Elegoo (12 filaments)
    - Fillamentum (3 filaments)
    - Flashforge (3 filaments)
    - Hatchbox (22 filaments)
    - IIID Max (37 filaments)
    - Inland (31 filaments)
    - Matterhacker (1 filament)
    - Mika3D (17 filaments)
    - Numakers (22 filaments)
    - Overture (18 filaments)
    - Protopasta (48 filaments)
    - Repkord (12 filaments)
    - Sunlu (13 filaments)
    - ...and 4 more
  - **4 existing manufacturers expanded:**
    - Bambu Lab (+1 filament)
    - Paramount 3D (+23 filaments)
    - Prusament (+19 filaments)
    - eSun (+31 filaments)
  - **Total filaments:** 913 (was 585, added 328)
  - Import tool: `tooling/import_hueforge_data.py` with dry-run preview, duplicate detection, and conflict handling
  - Filtered out 32 entries with null hex codes
  - Deduplicated entries with identical IDs

## [5.3.0] - 2025-12-23

### Added

- **Unit tests for data class string representations** - Added 5 comprehensive tests verifying `__str__()` behavior:
  - `test_color_record_str` - ColorRecord formatting
  - `test_filament_record_str` - FilamentRecord with/without finish
  - `test_validation_record_str` - ColorValidationRecord match/mismatch cases
  - `test_color_cluster_str` - ColorCluster pixel count display
  - `test_color_change_str` - ColorChange layer assignment
  - All tests verify both `str()` and `repr()` outputs
  - Total test count: 446 tests (all passing)

### Changed

- **String representation of data classes** - All data classes now have concise, user-friendly `__str__()` output for better readability when printing or logging. The `repr()` output remains unchanged for debugging purposes.
  - **ColorRecord**: `str(color)` now returns `"coral (#FF7F50)"` instead of full dataclass repr
  - **FilamentRecord**: `str(filament)` now returns `"Bambu Lab PLA Matte - Jet Black (#333333)"`
  - **ColorValidationRecord**: Shows match status, confidence, and Delta E at a glance
  - **ColorCluster**: Shows RGB color and pixel count
  - **ColorChange**: Shows HueForge layer assignment with Delta E
  - **Migration**: If you were parsing `str(record)` output (not recommended), use dataclass properties instead: `record.name`, `record.hex`, `record.rgb`, etc.
  - **Why this is minor version**: String representation is presentation layer, not API contract. The documented API (dataclass fields and properties) remains unchanged. Anyone parsing auto-generated repr was relying on undocumented implementation detail.

## [5.2.0] - 2025-12-23

### Added

- **Validation Module Exported in Public API** - The `validation` module is now fully accessible via main package imports:
  - ✅ `from color_tools import validate_color` - Validate color name/hex pairings with fuzzy matching and Delta E
  - ✅ `from color_tools import ColorValidationRecord` - Data class containing validation results
  - Previously required awkward: `from color_tools.validation import ...`
  - Now follows "batteries included" principle for public API

- **Validation CLI Command** - New `validate` command for validating color name/hex pairings:
  - `color-tools validate --name "light blue" --hex "#ADD8E6"` - Check if name matches hex
  - `--threshold` - Adjust Delta E threshold for strictness (default: 20.0)
  - `--json-output` - Get results in JSON format for scripting
  - Exit code 0 for match, 1 for no match (useful in scripts)
  - Shows fuzzy matching confidence, Delta E distance, and suggestions

- **Enhanced Data Class Documentation** - All 5 data classes now have comprehensive Sphinx autodoc:
  - `ColorRecord` - Detailed attribute descriptions with ranges and examples
  - `FilamentRecord` - Dual-color handling documentation and property explanations
  - `ColorValidationRecord` - Complete validation result field documentation
  - `ColorCluster` - Image cluster attributes with usage examples
  - `ColorChange` - Luminance redistribution field documentation
  - Single source of truth: docstrings auto-generate API documentation

- **Data Classes Quick Reference** - Added comprehensive quick reference table to Usage.md:
  - All 5 data classes with purpose, key fields, and API links
  - Value range notes for RGB, LAB, LCH, HSL
  - Installation notes for optional dependencies
  - Direct links to full Sphinx documentation

- **Export Library Examples** - Added comprehensive library usage examples to Usage.md:
  - `export_filaments()` examples with filtering (AutoForge CSV, generic CSV, JSON)
  - `export_colors()` examples
  - Code examples showing real-world export workflows
  - Complements existing CLI documentation

### Changed

- **Enhanced Package Docstring** - Main `__init__.py` docstring now includes:
  - Color validation example showing `validate_color()` usage
  - Improved image processing examples with `.save()` calls
  - Better organization of Quick Start, Validation, and Image sections
  - All examples now show complete workflows

- **Improved Sphinx Index** - Added Data Classes section to API documentation:
  - Highlights all 5 immutable dataclasses
  - Links to quick reference in Usage.md
  - Notes about comprehensive docstrings and examples

### Documentation

- Created `docs/other/DOCUMENTATION_GAPS.md` - Comprehensive analysis of documentation coverage:
  - Coverage summary table for all modules
  - Identified and resolved critical gaps (validation export)
  - Documented design decisions (image module import pattern)
  - Checklist for future feature additions

## [5.1.1] - 2025-12-23

### Fixed

- **Sphinx Documentation** - Updated API documentation to include all modules:
  - Added missing modules: `color_deficiency`, `export`, `matrices`
  - Fixed version number in Sphinx configuration (was 3.5.0, now 5.1.1)
  - Added links to comprehensive usage guides (CLI, Installation, FAQ, etc.)
  - Added CLI commands overview with links to detailed documentation

## [5.1.0] - 2025-12-23

### Added

- **Export System (v1.0)** - Export filaments and colors to external formats:
  - **AutoForge CSV export** - Export filaments for AutoForge library import
  - **Generic CSV export** - All fields exported to CSV for any tool
  - **JSON export** - Raw data export for backup/restore operations
  - **CLI integration** - New `--export`, `--output`, `--list-export-formats` flags
  - **Auto-generated filenames** - Timestamped filenames prevent overwrites (`filaments_autoforge_20251223_143022.csv`)
  - **Merged data exports** - Automatically includes user overrides (user-filaments.json, user-colors.json)
  - **Filter integration** - Combine with existing `--maker`, `--type`, `--finish` filters for targeted exports
  - **Library API** - `export_filaments()`, `export_colors()`, `list_export_formats()` functions
  - **Examples:**

    ```bash
    # Export Bambu Lab Basic/Matte filaments to AutoForge format
    python -m color_tools filament --maker "Bambu Lab" --finish Basic Matte --export autoforge
    
    # Export all CSS colors to JSON with custom filename
    python -m color_tools color --export json --output my_colors.json
    
    # List available export formats
    python -m color_tools filament --list-export-formats
    ```

  - **Full test coverage** - 18 unit tests covering all formats and features
  - **See `docs/other/IMPORT_EXPORT_SYSTEM.md` for design details and future plans**

- **Crayola Crayon Colors Palette** - New built-in palette with 120 classic Crayola crayon colors:
  - Load with `load_palette('crayola')` in Python
  - Includes iconic colors: Burnt Orange, Sunset Orange, Purple Heart, Screamin' Green, etc.
  - Full color space conversions (RGB, HSL, LAB, LCH) computed from source data
  - Generation script available at `tooling/generate_crayola_palette.py`
  - Documentation at `tooling/CRAYOLA_PALETTE.md`

### Changed

### Fixed

## [5.0.0] - 2025-12-22

### Added

- **Custom User Palettes** - Full support for user-created retro palettes:
  - Create custom palettes in `data/user/palettes/user-*.json`
  - Automatic discovery and CLI integration (`--palette list`, `--palette user-mycustom`)
  - Full image processing support (`quantize_image_to_palette` with user palettes)
  - Comprehensive error handling with helpful guidance
  - 10 new test cases covering all user palette scenarios

### Changed

- **BREAKING: User Palette Naming** - User palettes now **require** `user-` prefix for security and clarity:
  - User palette files **must** be named `user-*.json` (e.g., `user-cyberpunk.json`)
  - Access via `--palette user-cyberpunk` (not just `cyberpunk`)
  - Core palettes are protected from accidental override
  - Clear separation between built-in and user palettes
  - Enhanced error messages guide users to correct naming
- **Enhanced Palette Loading** - `load_palette()` function updated with user palette support:
  - Automatic detection of user vs core palettes based on name prefix
  - No more silent overriding of core palettes
  - Improved error messages with available palette listing
- **Updated Documentation** - FAQ and CLI help updated to reflect `user-` prefix requirement

### Migration Guide

If you have existing user palettes without `user-` prefix:

```bash
# Before: mycustom.json → --palette mycustom
# After:  user-mycustom.json → --palette user-mycustom

# Rename your palette files:
mv data/user/palettes/mycustom.json data/user/palettes/user-mycustom.json

# Update your commands:
color-tools color --palette user-mycustom --nearest --value 255 0 0
```

## [4.0.0] - 2025-12-22

### Added

- **Comprehensive FAQ Section** - Added detailed User Customization section to FAQ.md with 8 common questions covering all user override scenarios, file formats, conflict resolution, and troubleshooting
- **User Data Hash Verification** - New hash file support for user data integrity:
  - Generate `.sha256` hash files for user data with `--generate-user-hashes`
  - Verify user data integrity with `--verify-user-data`
  - Automatic hash checking when `.sha256` files exist alongside user data
  - Enhanced `--verify-all` to include both core and user data verification
- **Enhanced Documentation** - Comprehensive user override examples, troubleshooting guides, and best practices

### Changed

- **🚨 BREAKING: User Data Directory Structure** - User override files moved to organized subdirectory structure:
  - **Old locations** (no longer supported):
    - `data/user-colors.json` → `data/user/colors.json`
    - `data/user-filaments.json` → `data/user/filaments.json`
    - `data/user-synonyms.json` → `data/user/synonyms.json`
  - **New structure**: All user files now go in `data/user/` subdirectory
  - **Rationale**: Cleaner separation of core vs user data, better organization, easier to manage and document
  - **Migration**: Users must manually move their files to the new locations - no automatic migration provided

### Removed

- **🚨 BREAKING: Legacy User File Support** - No longer supports user override files in the root `data/` directory. All user files must be in `data/user/` subdirectory

### Developer Notes

- This is a major version bump due to breaking changes in user data file locations
- The new directory structure provides better organization and clearer separation of concerns
- Hash verification adds data integrity protection for user customizations

## [3.8.1] - 2025-12-22

### Fixed

- **Documentation** - Updated CHANGELOG.md to properly document the 3.8.0 release with comprehensive user override system features

## [3.8.0] - 2025-12-22

### Added

- **Comprehensive User Override System** - Complete user file override capabilities with full priority-based conflict resolution:
  - **Priority-Based Override Logic** - User files now consistently override core files across all lookup methods (`find_by_name()`, `find_by_rgb()`, `nearest_color()`, `nearest_filament()`)
  - **Enhanced FilamentPalette Override Support** - Added complete RGB override support for filaments with `_should_prefer_source()` logic ensuring user filaments are prioritized in `find_by_rgb()` results
  - **Comprehensive Synonym Override System** - User synonym files now completely replace (not extend) core synonyms for existing makers, with full logging and transparency
  - **Advanced Override Detection and Reporting** - New `get_override_info()` methods on Palette and FilamentPalette classes provide detailed override analysis including name conflicts, RGB conflicts, and synonym replacements
  - **CLI Override Integration** - Enhanced `--check-overrides` functionality now reports filament and synonym overrides in addition to color overrides
- **Filament database update** - Added missing Bambu Lab Matte Charcoal filament to complete the product line
- **Extensive Test Coverage** - Added comprehensive test suite (`test_user_overrides.py`) with 18 test classes covering all override scenarios, conflict detection, and integration testing

### Changed

- **Color value updates to resolve RGB duplication** - Modified cyan and magenta to use more accurate printer/subtractive color values:
  - **Cyan**: Changed from `#00FFFF` to `#00B7EB` (RGB: 0, 183, 235) - now represents true printer cyan instead of electric cyan
  - **Magenta**: Changed from `#FF00FF` to `#FF0090` (RGB: 255, 0, 144) - now represents true printer magenta
  - **Rationale**: The old values for cyan and magenta were identical to aqua (`#00FFFF`) and fuchsia (`#FF00FF`), causing RGB dictionary lookup collisions where only one color name would be findable by its RGB value
  - **Aqua and Fuchsia**: Retained their CSS-standard values as the canonical web colors
  - **Impact**: All four colors now have unique RGB coordinates, fixing palette RGB lookups and improving color matching accuracy
- **Enhanced Palette Constructor Logic** - Modified Palette and FilamentPalette constructors to use priority-based indexing where user records override core records consistently across all data structures

### Fixed

- **Complete RGB Lookup Consistency** - Resolved all remaining inconsistencies where different lookup methods could return different sources for identical RGB values
- **Filament RGB Priority Issues** - Fixed cases where `find_by_rgb()` and `nearest_filament()` could return core filaments when user filaments with identical RGB values existed

### Improved

- **Hash update tooling enhancements** - Significant improvements to `tooling/update_hashes.py`:
  - **Rich text output** - Added colored terminal output using Rich library for better readability (section headers, hash values, errors, warnings, and success messages all color-coded)
  - **New granular flags** - Added `--filaments-only` and `--palettes-only` options to regenerate specific hash categories without recomputing everything
  - **Eliminated code duplication** - Removed duplicate palette file mapping, now using single `PALETTE_FILES` constant as source of truth
  - **Uses ColorConstants methods** - Script now imports and uses `ColorConstants._compute_hash()` and `ColorConstants._compute_matrices_hash()` instead of duplicating hash logic, ensuring consistency with the main codebase
  - **Simplified architecture** - Removed conditional Rich fallback code; Rich is now a hard requirement for the script

## [3.7.0] - 2025-12-22

### Added

- **User Override System** - Comprehensive user file override capabilities with complete transparency:
  - **Source Tracking** - Added `source` field to ColorRecord and FilamentRecord dataclasses to track JSON filename origin (colors.json, filaments.json, user-colors.json, user-filaments.json)
  - **Automatic Override Detection** - User files (user-colors.json, user-filaments.json) automatically override core files when conflicts occur by name or RGB values, with logging warnings to inform users
  - **CLI Override Reporting** - New `--check-overrides` global flag displays detailed reports of user overrides, showing which colors/filaments come from user files vs core files
  - **Source Display in Output** - All CLI color and filament commands now show source filename in brackets (e.g., "red [from colors.json]", "Custom Blue [from user-colors.json]")
  - **Consistent Override Behavior** - Modified distance comparison logic in nearest neighbor searches to prefer user sources when distances are equal, ensuring `find_by_rgb()` and `nearest_color()` return consistent results

### Fixed

- **RGB Dictionary Lookup Consistency** - Resolved issue where `find_by_rgb()` and `nearest_color()` could return different results for the same RGB query when both user and core files contained colors with identical RGB values

### Changed

- **Enhanced CLI Help** - Updated CLI help text and examples to include `--check-overrides` flag usage and documentation

## [3.6.2] - 2025-12-03

### Fixed

- **Distribution cleanup** - Removed test files from PyPI packages:
  - **Excluded tests directory** - Test files are no longer included in source distributions (sdist) or wheels uploaded to PyPI
  - **Added MANIFEST.in** - Explicit control over which files are included in distributions
  - **Cleaner package installs** - End users now get only the essential package code and data files, reducing download size and eliminating development artifacts

## [3.6.1] - 2025-12-03

### Fixed

- **Package build optimization** - Eliminated setuptools warnings and cleaned up distribution:
  - **Removed importable data packages** - Data directories (`color_tools.data` and `color_tools.data.palettes`) are no longer treated as importable Python packages, eliminating setuptools warnings about package discovery ambiguity
  - **Explicit data configuration** - Switched to explicit `package-data` configuration with `include-package-data = false` for precise control over included files
  - **Build artifact cleanup** - Removed unnecessary `__init__.py` files from data directories and cleaned up empty `MANIFEST.in` file
  - **Zero-warning builds** - Package now builds cleanly without any setuptools warnings while maintaining full functionality
  - **Maintained data access** - All JSON data files (colors, filaments, palettes) remain accessible through the proper API without architectural changes

## [3.6.0] - 2025-12-03

### Added

- **Comprehensive API Documentation** - Professional Sphinx-based documentation system:
  - **Full API reference** - Complete documentation for all public functions and classes with parameter descriptions and examples
  - **Module examples** - Added practical usage examples to distance.py, conversions.py, and palette.py module docstrings
  - **Autosummary integration** - Automatic generation of module pages with cross-references and search functionality
  - **Read the Docs theme** - Professional styling with color science themed custom CSS
  - **Build automation** - PowerShell script for easy documentation regeneration (`docs/build-docs.ps1`)

### Changed

- **Updated license format** - Changed to SPDX license identifier (`MIT`) in `pyproject.toml` to eliminate PyPI warnings and improve machine readability

### Fixed

- **API Export Cleanup** - Improved public API consistency and maintainability:
  - **Added missing export** - `hue_diff_deg` function now properly exported in main `__all__` list
  - **Private helper functions** - Made internal conversion helpers private: `srgb_to_linear` → `_srgb_to_linear`, `linear_to_srgb` → `_linear_to_srgb`, `rgb_to_rawhsl` → `_rgb_to_rawhsl`  
  - **Complete image exports** - Added missing image transformation functions (`transform_image`, `simulate_cvd_image`, `correct_cvd_image`, `quantize_image_to_palette`) to `color_tools.image.__all__`
  - **Type safety** - Fixed CLI type annotation issues with tuple handling for better type checking

## [3.5.0] - 2025-12-01

### Added

- **Enhanced Hash Update Tooling** - Completely automated hash integrity management system:
  - **Automatic hash update script** - `python tooling/update_hashes.py --autoupdate` now updates all hash values in one command with confirmation prompts
  - **Two-step automation** - Updates individual hash values first, then generates and updates final ColorConstants hash automatically
  - **Safety features** - Requires explicit user confirmation before modifying any files, with ability to cancel at any time
  - **Comprehensive verification** - Includes debugging output showing which constants were updated and proper subprocess-based hash calculation to avoid module caching
  - **JSON array compacting** - `tooling/compact_color_arrays.py` script reformats JSON files for better readability, saving ~97KB space
  - **Complete documentation** - New `docs/Hash_Update_Guide.md` with manual and automatic workflows

  ```bash
  # Complete automated hash update workflow
  python tooling/update_hashes.py --autoupdate
  
  # Manual mode for review
  python tooling/update_hashes.py
  
  # Final step only (after manual updates)
  python tooling/update_hashes.py --constants-only
  ```

- **Multiple Result Support** - Both color and filament commands now support finding multiple nearest matches:
  - **`--count N` argument** - Returns top N closest matches (default: 1, max: 50) for both colors and filaments
  - **Enhanced output format** - Numbered list with distances and full details for easy comparison
  - **Backward compatibility** - Single result behavior preserved when `--count` is omitted or equals 1
  - **Consistent interface** - Same parameter works for both `color` and `filament` commands

  ```bash
  # Find top 5 CSS colors closest to purple
  python -m color_tools color --nearest --hex 8040C0 --count 5
  
  # Find top 3 filaments for custom blue, including alternatives
  python -m color_tools filament --nearest --hex 2121ff --count 3
  ```

- **Wildcard Filter Support** - Filament searches now support ignoring specific filters using `*` wildcard:
  - **`*` wildcard syntax** - Use `*` as special value to disable individual filters completely  
  - **Flexible filtering** - Ignore maker (`--maker "*"`), type (`--type "*"`), or finish (`--finish "*"`) constraints individually
  - **Mixed filtering** - Combine wildcard and specific filters (e.g., `--maker "*" --type PLA` searches all makers but only PLA)
  - **Complete bypass** - Use all wildcards to search entire filament database without restrictions
  - **Exploration friendly** - Perfect for discovering alternatives when preferred brand is unavailable

  ```bash
  # Search all makers for closest blue filament
  python -m color_tools filament --nearest --hex 2121ff --maker "*"
  
  # Find top 3 PLA filaments from any maker, any finish
  python -m color_tools filament --nearest --hex FF4500 --count 3 --maker "*" --finish "*"
  
  # Search all types but only from Bambu Lab
  python -m color_tools filament --nearest --hex 00FF00 --type "*" --maker "Bambu Lab"
  ```

- **Universal Hex Color Support** - Complete hex color input support across all CLI commands for improved real-world usability:
  - **`--hex` argument** - Added to `color`, `filament`, `name`, `cvd`, and `convert` commands as convenient alternative to `--value`
  - **Enhanced format support** - Accepts 6-digit hex (`#FF5733`, `FF5733`) and 3-digit shortcuts (`#24c`, `24c`) using existing robust `hex_to_rgb()` function  
  - **Smart defaults** - When using `--hex`, automatically implies RGB color space (no need to specify `--from rgb` in convert command)
  - **Mutual exclusivity validation** - Prevents conflicting `--hex` and `--value` usage with clear error messages
  - **DRY implementation** - Leverages existing `conversions.hex_to_rgb()` function to avoid code duplication
  - **LAB/LCH validation** - Added bounds checking with helpful error messages for LAB/LCH input values
  - **Examples across help** - Updated CLI help and examples to showcase hex usage patterns

### Added

- **Unified Image Transformation System** - Complete image processing architecture leveraging all existing color_tools infrastructure:
  - **`transform_image(image_path, transform_func, preserve_alpha=True, output_path=None)`** - Universal function for applying color transformations to entire images
  - **`simulate_cvd_image(image_path, deficiency_type, output_path=None)`** - Simulate color vision deficiency (protanopia, deuteranopia, tritanopia) for entire images using scientifically-validated matrices
  - **`correct_cvd_image(image_path, deficiency_type, output_path=None)`** - Apply CVD correction to improve discriminability for colorblind viewers using Daltonization algorithm  
  - **`quantize_image_to_palette(image_path, palette_name, metric='de2000', dither=False, output_path=None)`** - Convert images to retro palettes (CGA, EGA, VGA, Game Boy, Web Safe) with all 6 distance metrics and optional Floyd-Steinberg dithering
  - **Infrastructure Integration** - All functions reuse existing color deficiency matrices, palette system, and distance metrics
  - **Comprehensive format support** - RGB, RGBA, grayscale, palette mode images with alpha preservation
  - **Performance optimized** - Numpy-based processing with memory efficiency for large images

  ```python
  from color_tools.image import simulate_cvd_image, quantize_image_to_palette
  
  # Test accessibility - see how deuteranopes view your chart
  sim_image = simulate_cvd_image("infographic.png", "deuteranopia") 
  sim_image.save("colorblind_view.png")
  
  # Create retro CGA-style artwork with dithering
  retro = quantize_image_to_palette("photo.jpg", "cga4", dither=True)
  retro.save("retro_cga.png")
  
  # Convert to Game Boy aesthetic using perceptually accurate CIEDE2000
  gameboy = quantize_image_to_palette("artwork.png", "gameboy", metric="de2000")
  gameboy.save("gameboy_style.png")
  ```

- **Complete documentation** for the transformation system in `image/README.md` with usage examples, supported palettes, distance metrics, and architecture details
- **Comprehensive CLI support** - Full command-line interface for all image transformations:
  - `python -m color_tools image --list-palettes` - List all available retro palettes including custom additions
  - `python -m color_tools image --cvd-simulate TYPE --file image.jpg` - Simulate colorblindness (protanopia, deuteranopia, tritanopia)
  - `python -m color_tools image --cvd-correct TYPE --file image.jpg` - Apply CVD correction for improved discriminability
  - `python -m color_tools image --quantize-palette NAME --file image.jpg` - Convert to retro palette with 6 distance metrics and optional dithering
  - Dynamic palette discovery automatically supports new JSON palettes in data/palettes/
  - Smart output naming with optional `--output` parameter for custom paths
  - Comprehensive error handling and operation validation

## [3.4.0] - 2025-11-28

### Added

- **General-purpose image analysis functions** in `image/basic.py` module:
  - `count_unique_colors(image_path)` - Count total unique RGB colors in an image using numpy
  - `get_color_histogram(image_path)` - Get histogram mapping RGB colors to pixel counts
  - `get_dominant_color(image_path)` - Get the most common color in an image
  - All functions work with any image format (PNG, JPEG, GIF, etc.)
  - Efficient numpy-based implementation for large images
  - Clean Python types returned (int tuples, not numpy types)

  ```python
  from color_tools.image import count_unique_colors, get_dominant_color
  
  # Count colors
  total = count_unique_colors("photo.jpg")
  print(f"Found {total} unique colors")
  
  # Get dominant color and match to CSS color
  from color_tools import Palette
  dominant = get_dominant_color("photo.jpg")
  palette = Palette.load_default()
  nearest, distance = palette.nearest_color(dominant)
  print(f"Dominant color matches CSS '{nearest.name}'")
  ```

- **Image quality analysis functions** in `image/basic.py` module:
  - `analyze_brightness(image_path)` - Analyze image brightness with dark/normal/bright assessment
  - `analyze_contrast(image_path)` - Analyze image contrast using standard deviation with low/normal assessment
  - `analyze_noise_level(image_path)` - Estimate noise level using scikit-image with clean/noisy assessment
  - `analyze_dynamic_range(image_path)` - Analyze dynamic range and provide gamma correction suggestions
  - All functions return structured dictionaries with raw values and human-readable assessments
  - Based on proven thresholds from image processing applications

  ```python
  from color_tools.image import analyze_brightness, analyze_contrast, analyze_noise_level
  
  # Analyze image quality
  brightness = analyze_brightness("photo.jpg")
  print(f"Brightness: {brightness['mean_brightness']:.1f} ({brightness['assessment']})")
  
  contrast = analyze_contrast("photo.jpg") 
  print(f"Contrast: {contrast['contrast_std']:.1f} ({contrast['assessment']})")
  
  noise = analyze_noise_level("photo.jpg")
  print(f"Noise: {noise['noise_sigma']:.2f} ({noise['assessment']})")
  ```

- **Image module architecture improvements**:
  - Separated general-purpose functions (`basic.py`) from HueForge-specific tools (`analysis.py`)
  - Clear separation of concerns following project architectural principles
  - Updated module docstrings to document both categories of functions
- **numpy dependency**: Added to `[image]` extra and `requirements-image.txt`
  - Required for efficient color counting and histogram operations
  - Minimum version: numpy>=1.24.0
- **scikit-image dependency**: Added to `[image]` extra and `requirements-image.txt`
  - Required for advanced noise analysis using `restoration.estimate_sigma()`
  - Minimum version: scikit-image>=0.20.0
  - Graceful fallback if not available

### Changed

- **Simplified palette architecture** - Reverted to clean, simple JSON array format for better maintainability:
  - **Removed metadata complexity** - Eliminated unnecessary metadata fields that created technical debt
  - **Focused on fixed palettes** - Removed problematic dynamic palette systems (Genesis, TurboGrafx-16) that don't map to fixed color quantization
  - **Retained working palettes** - Kept all functional fixed palettes: CGA, EGA, VGA, Game Boy variants, Commodore 64, NES, SMS, VirtualBoy, Web Safe
  - **Maintained compatibility** - No breaking changes to palette loading or color matching APIs
  - **Performance optimized** - Simpler format improves loading speed and reduces memory usage

- **Enhanced error handling** - Improved validation and error messages for multiple result parameters
- **Updated CLI help** - Added examples and clarifications for new `--count` and wildcard features
- **Image extra now includes numpy and scikit-image**: `pip install color-match-tools[image]` now installs Pillow, numpy, and scikit-image
- **Image module documentation**: Updated `image/__init__.py` to show examples of both general and HueForge-specific functions

## [3.3.0] - 2025-11-10

### Added

- **Intelligent color naming system** (`naming.py` module)
  - `generate_color_name(rgb, palette_colors, near_threshold)` function generates descriptive color names
  - Three-tier naming strategy:
    1. Exact CSS color matches (e.g., "red", "blue", "papayawhip")
    2. Near CSS matches with Delta E < 5 (e.g., "near darkgray")
    3. Generated descriptive names based on HSL properties
  - **Lightness modifiers** (5 levels): very light, light, medium, dark, very dark
  - **Saturation modifiers** (6 levels):
    - pale (light colors, S<35%), muted (dark colors, S<35%)
    - dull (35% ≤ S < 50%)
    - (no modifier for medium saturation 50-70%)
    - bright (70% ≤ S < 85%)
    - deep (85% ≤ S < 95%)
    - vivid (S ≥ 95% - maximum saturation)
  - **Hue boundary transitions** ("-ish" variants):
    - Colors within ±8° of major hue boundaries get descriptive variants
    - Examples: "reddish orange", "orangeish yellow", "yellowish green", "blueish purple"
    - Only applied to colors with S ≥ 40% for meaningful descriptions
  - **Special case colors**:
    - Brown family: beige (light), tan (medium light), brown (darker)
    - Gold: desaturated yellow with moderate saturation (30-50%)
    - Pink: light reds with saturation
    - Olive: dark muted yellow-green
    - Navy: very dark blue
    - Maroon: very dark red
    - Teal: cyan-green range
    - Lime: bright yellow-green
  - Returns tuple of (name, match_type) where match_type is "exact", "near", or "generated"
  - Collision avoidance: Falls back to generic hue names if generated name conflicts with CSS
  - Exported as public API function for standalone use
  - **New CLI command**: `name --value R G B` generates descriptive names from RGB values
    - Examples: `name --value 255 128 64` → "light vivid orangeish red"
    - `--show-type` flag shows match type (exact/near/generated)
    - `--threshold` sets Delta E threshold for near matches (default: 5.0)

- **Improved palette color names**: All 6 palette files renamed with intelligent descriptive names
  - 110 colors improved across CGA, EGA, VGA, and Web palettes
  - Examples: "very light vivid greenish teal", "medium dull gold", "dark deep teal"
  - More variety and precision than generic numbering (e.g., "VGA 042" → "light vivid orange")

- **Comprehensive test suite for naming**: 53 new unit tests in `tests/test_naming.py`
  - Tests for lightness modifiers (5 levels)
  - Tests for saturation modifiers (6 levels including dull and deep)
  - Tests for "-ish" hue boundary transitions (8 boundaries)
  - Tests for special case colors (brown family, gold, olive, navy, maroon, teal, lime, pink)
  - Tests for complete name generation with collision avoidance
  - All 211 tests passing (158 existing + 53 new)

- **Unique filament IDs**: All filament records now include a unique `id` field
  - Generated from maker-type-finish-color using semantic slugification
  - IDs are stable, human-readable identifiers (e.g., "bambu-lab-pla-silk-plus-red")
  - Special character handling: `+` converted to `-plus` for URL-safe slugs
  - Zero ID collisions across entire database (584 unique IDs)
  - `id` field positioned as first field in FilamentRecord for clarity

- **Alternative filament names**: New optional `other_names` field for filament records
  - Supports regional variations (e.g., US vs EU names)
  - Tracks historical names when manufacturers rebrand products
  - Handles marketing variations and common misspellings
  - Field is optional - only populated when alternatives exist
  - Format: array of strings (e.g., `["Classic Red", "Premium PLA Red (EU)"]`)

- **Palette file integrity protection**: Added SHA-256 hash verification for all 6 palette files
  - CGA (4-color and 16-color), EGA (16-color and 64-color), VGA (256-color), Web (216-color)
  - `--verify-data` now checks all 9 core files (3 data + 6 palettes)
  - Updated CLI verification message to mention palettes

### Changed

- **Database restructuring and data corrections** (reduced from 588 to 584 filaments)
  - Removed 6 exact duplicate groups from database
  - **Polymaker data corrected**: 213 → 198 entries (-15)
    - Fixed incorrectly imported filament types (now includes specialized types like PC-ABS, PA6-CF20, LW-PLA, PC-PBT, CoPA)
    - Re-extracted from source PDF with improved parsing
    - Eliminated duplicate entries with wrong type labels
  - **Panchroma data corrected**: 143 → 154 entries (+11)
    - Fixed dual-color hex format from comma-separated to dash-separated (e.g., `#ABC, #DEF` → `#ABC-#DEF`)
    - Re-extracted from source PDF with improved parsing
    - Added missing filament colors
    - Fixed color name spacing issues in parentheses
  - **Bambu Lab expansion**: Added 38 new filament colors
    - 14 PETG HF colors (Yellow, Orange, Green, Red, Blue, Black, White, Cream, Lime Green, Forest Green, Lake Blue, Peanut Brown, Gray, Dark Gray)
    - 6 PETG-CF colors (Brick Red, Violet Purple, Indigo Blue, Malachite Green, Black, Titan Gray)
    - 10 PLA Translucent colors (Teal, Light Jade, Blue, Mellow Yellow, Purple, Cherry Pink, Orange, Ice Blue, Red, Lavender)
    - 8 PETG Translucent colors (Translucent Gray, Light Blue, Olive, Brown, Teal, Orange, Purple, Pink)

### Technical

- Updated `FilamentRecord` dataclass to include `id` as first field and optional `other_names` field
- Regenerated filaments.json integrity hash after data corrections and field additions
- Created PDF extraction tooling with improved parsing for Polymaker and Panchroma data sources
- Enhanced slug generation with collision detection and special character handling
- Added comprehensive database integrity tests (158 total tests, up from 142)
- **Enhanced data integrity protection**: Added SHA-256 hash verification for all 6 palette files (CGA4, CGA16, EGA16, EGA64, VGA, Web)
  - Palette files now protected against tampering alongside core data files
  - `--verify-all` flag now validates 9 core files total (3 data + 6 palettes)

## [3.2.1] - 2025-11-09

### Fixed

- Fixed README.md displaying correct version on PyPI package page
- Fixed changelog link to use full GitHub URL (relative links don't work on PyPI)

## [3.2.0] - 2025-11-09

### Added

- **3-character hex code support**: `hex_to_rgb()` now accepts shorthand hex format
  - Supports `#RGB` format (e.g., `#F00` → `#FF0000`, `#24c` → `#2244cc`)
  - Works with or without `#` prefix (e.g., `F00` or `#F00`)
  - Automatic expansion to 6-character format for processing
  - Fully integrated with validation, CLI, and all color operations

- **Hybrid fuzzy matching fallback** for validation module when fuzzywuzzy not installed
  - Pure Python implementation using Levenshtein distance algorithm
  - Three-strategy matching approach:
    1. Exact match after normalization (100% confidence)
    2. Substring matching (90-95% confidence based on coverage)
    3. Levenshtein distance calculation (variable confidence)
  - No external dependencies required for color name validation
  - Optional `fuzzywuzzy` package still recommended for best results

### Improved

- **Enhanced RGB parsing error handling**: Better validation and error messages
  - Added explicit type coercion for RGB values to catch non-numeric data
  - Improved error messages in `_parse_color_records()` helper function
  - Better handling of malformed color data in JSON files

## [3.1.0] - 2025-11-09

### Added

- **Custom palette support**: Load and use retro/classic color palettes
  - New `load_palette()` function to load named palettes
  - Six built-in palettes: `cga4`, `cga16`, `ega16`, `ega64`, `vga`, `web`
  - CGA 4-color: Classic gaming palette (Palette 1, high intensity)
  - CGA 16-color: Full RGBI palette
  - EGA 16-color: Standard/default EGA palette
  - EGA 64-color: Full 6-bit RGB palette
  - VGA 256-color: Classic Mode 13h palette
  - Web Safe: 216-color web-safe palette (6×6×6 RGB cube)
  - CLI support: `--palette <name>` flag for `color` command
  - All palettes work with existing distance metrics (de2000, de94, etc.)
  - Perfect for retro graphics, pixel art, and color quantization projects

- **Palette generation tooling**:
  - New `tooling/generate_palettes.py` script
  - Uses `color_tools` library to compute accurate LAB/LCH/HSL values
  - Pre-computes all color space conversions for fast loading
  - Palettes stored in `color_tools/data/palettes/` directory

- **Comprehensive unit tests for custom palettes**:
  - Tests for all 6 built-in palettes (cga4, cga16, ega16, ega64, vga, web)
  - Error handling tests for invalid palette names
  - Malformed JSON detection tests
  - Edge case coverage for empty names, case sensitivity, etc.

### Improved

- **Enhanced error handling in palette loading**:
  - `load_palette()` now provides helpful error messages listing available palettes
  - Better validation of palette JSON structure with specific error messages
  - Added `_parse_color_records()` helper function to avoid code duplication
  - Improved error messages include file names and problematic data indices
  - JSON decode errors are caught and re-raised with context

### Examples

```python
# Library usage
from color_tools import load_palette

cga = load_palette('cga4')
color, distance = cga.nearest_color((128, 64, 200), space='rgb')
print(f"{color.name}: {color.hex}")  # Light Magenta: #ff55ff
```

```bash
# CLI usage
python -m color_tools color --palette cga4 --nearest --value 128 64 200
python -m color_tools color --palette ega16 --nearest --value 255 0 0 --space rgb
```

## [3.0.0] - 2025-11-09

### Changed - BREAKING

- **Package restructuring**: Reorganized project into proper Python package structure
  - All Python modules moved to nested `color_tools/color_tools/` directory
  - Data files moved to `color_tools/color_tools/data/`
  - Import paths remain `from color_tools import ...` (no change for users)
  - CLI usage unchanged: `python -m color_tools` works the same way
- **Added pyproject.toml**: Modern Python packaging with full metadata
  - Package now installable with `pip install -e .` for development
  - Defines `color-tools` console script entry point
  - Declares Python 3.10+ requirement explicitly
  - No external dependencies (pure stdlib)

### Added

- Created `pyproject.toml` for modern Python packaging standards
- Package can now be installed and used as a proper Python library
- Console script `color-tools` available after installation

### Notes

This is a major version bump due to package restructuring. While the public API and CLI remain unchanged, the internal file structure has been reorganized. If you were importing modules directly from the file system (not recommended), you'll need to update those references.

## [2.1.1] - 2025-11-09

### Fixed

- Fixed type hint errors in `constants.py` by adding proper imports for type checking
- Added `from __future__ import annotations` for better type hint support
- Removed string quotes from `Path` type hints using `TYPE_CHECKING` conditional import

## [2.1.0] - 2025-11-09

### Added

- **Data file integrity verification** with SHA-256 hashes
  - Core data files (colors.json, filaments.json, maker_synonyms.json) are now protected with SHA-256 hashes
  - New `--verify-data` flag to verify data file integrity
  - New `--verify-all` flag to verify both constants and data files
  - `ColorConstants.verify_data_file()` and `verify_all_data_files()` methods
- **User data extension system** for custom colors, filaments, and synonyms
  - `data/user-colors.json` - Add custom CSS colors (optional)
  - `data/user-filaments.json` - Add custom filaments (optional)
  - `data/user-synonyms.json` - Add or extend maker synonyms (optional)
  - User files automatically loaded and merged with core data
  - User files are not verified (user-managed, full flexibility)
- Documentation for user data files and integrity verification

### Changed

- `load_colors()` now loads and merges user-colors.json if present
- `load_filaments()` now loads and merges user-filaments.json if present
- `load_maker_synonyms()` now loads and merges user-synonyms.json if present
- Updated ColorConstants hash to include new data file hash constants

## [2.0.1] - 2025-11-09

### Fixed

- `--json` argument now properly validates that the provided path is a directory
- Clear error messages when `--json` points to a file or non-existent path
- Enforces that `--json` must be a directory containing all three JSON data files

### Changed

- Updated help text to clarify `--json` requires a directory, not a file

## [2.0.0] - 2025-11-09

### Breaking Changes

- **Removed backwards compatibility** with old `color_tools.json` format
- Data files must now be split into three separate JSON files:
  - `colors.json` - CSS color database (array format)
  - `filaments.json` - 3D printing filament database (array format)
  - `maker_synonyms.json` - Maker name synonym mappings
- Old combined format `{"colors": [...], "filaments": [...]}` is no longer supported
- Migration tool available in `tooling/split_json.py` for converting old format

### Added

- **Maker synonym support** for flexible filament searches
  - Search for "Bambu" automatically finds "Bambu Lab" filaments
  - Search for "BLL" or "Paramount" uses synonym expansion
  - Synonyms defined in `data/maker_synonyms.json`
- `--version` flag to CLI to display version number
- `load_maker_synonyms()` function in public API
- `_expand_maker_names()` method in `FilamentPalette` class
- Support for `--json` argument to accept directory or specific file path

### Changed

- Imported 58 new Paramount 3D filaments from API data
- Reorganized project structure:
  - Created `docs/` folder for documentation files
  - Created `tests/` folder for test scripts
  - Created `tooling/` folder for utility scripts
- Updated all documentation for split file format
- `find_by_maker()` and `filter()` methods now support synonym expansion

### Fixed

- Eliminated duplicate hex parsing code by using `hex_to_rgb()` utility in `FilamentRecord.rgb`

## [1.0.0] - 2025-11-08

### Initial Release

- Initial stable release
- Complete CSS color database with 140+ named colors
- 3D printing filament database with 490+ filaments
- Multiple color space conversions (RGB, HSL, LAB, LCH, XYZ)
- Delta E distance metrics (CIE76, CIE94, CIEDE2000, CMC)
- Gamut checking for sRGB color space
- Thread-safe configuration for dual-color filament handling
- Command-line interface with three main commands:
  - `color` - Search and query CSS colors
  - `filament` - Search and query 3D printing filaments
  - `convert` - Convert between color spaces
- SHA-256 hash verification for color science constants
- Comprehensive documentation and examples

### Technical Details

- Python 3.10+ required (uses union type syntax `X | Y` and modern type hints)
- No external dependencies (standard library only)
- Portable package structure using relative imports
- Immutable dataclasses for color and filament records
