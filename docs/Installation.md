# Installation

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Usage →](https://github.com/dterracino/color_tools/blob/main/docs/Usage.md)

---

## Requirements

**Python 3.12+** is required for version 7.0.0 and newer. The CI test matrix
covers Python 3.12, 3.13, and 3.14.

For Python 3.10 or 3.11, use the previous release series:

```bash
pip install "color-match-tools<7"
```

## Install from PyPI (Recommended)

**Base package (zero dependencies):**

```bash
pip install color-match-tools
```

**With enhanced fuzzy matching:**

```bash
pip install color-match-tools[fuzzy]
```

Adds RapidFuzz for better color name validation (validation module has built-in fallback).

**With image processing support:**

```bash
pip install color-match-tools[image]
```

Adds Pillow, NumPy, scikit-image, scikit-learn, OpenCV, CairoSVG,
pillow-heif, and `swatch` for image conversion and transforms, color analysis,
palette quantization, HEIC/SVG support, and Adobe ASE export.

**With interactive filament library manager:**

```bash
pip install color-match-tools[interactive]
```

Adds prompt_toolkit for a beautiful TUI interface to manage your owned filament library with autocomplete, filtering, and multi-select.

**With the PySide6 desktop filament manager:**

```bash
pip install color-match-tools[gui]
```

Adds PySide6 for the desktop owned-filament manager, launched with
`color-tools filament --gui`. This extra is independent of `[interactive]`.

**With colorized console logging:**

```bash
pip install color-match-tools[logging]
```

Adds Rich for colorized, formatted console log output. Without this extra the logging system falls back to plain `StreamHandler` output automatically — no errors.

**With the Color Tools MCP server:**

```bash
pip install color-match-tools[mcp]
```

Adds the official MCP Python SDK and installs the `color-tools-mcp` server command for GitHub
Copilot and other MCP-compatible agents.

**With all optional features:**

```bash
pip install color-match-tools[all]
```

Installs all optional user-facing features: fuzzy matching, image processing,
terminal and desktop filament managers, logging, and MCP. Development and
documentation tools remain separate under `[dev]` and `[docs]`.

All variants install `color-tools` as the canonical command and `color_tools` as
a backward-compatible alias. Both commands invoke the same CLI as
`python -m color_tools`.

If an installed command reports a different version from `python -m color_tools`,
your shell is resolving an older launcher from another Python installation. See
the [troubleshooting guide](Troubleshooting.md#installed-command-runs-an-older-version).

## For Development

Clone this repository and install in development mode with all optional features:

```bash
git clone https://github.com/dterracino/color_tools.git
cd color_tools
pip install -r requirements-dev.txt
pip install -e .
```

This installs:

- Base package in "editable" mode (modify code while using it)
- All optional dependencies (fuzzy matching, image processing, terminal and desktop UIs, logging, and MCP)
- Development tools (pytest, pytest-cov, coverage, pyright, build, twine)

**Minimal development setup (base only):**

```bash
pip install -r requirements.txt
pip install -e .
```

## Dependencies

The core module uses **only Python standard library** - **zero external dependencies** required!

**Optional dependencies:**

- `[fuzzy]`: rapidfuzz >= 3.0.0 for enhanced fuzzy color name matching (validation module has built-in fallback)
- `[image]`: Pillow, NumPy, scikit-image, pillow-heif, CairoSVG, OpenCV,
  scikit-learn, and `swatch` for image processing and ASE export
- `[interactive]`: prompt_toolkit >= 3.0.0 for interactive filament library manager
- `[gui]`: PySide6 >= 6.6.0 for the desktop filament library manager
- `[logging]`: Rich >= 13.0.0 for colorized console log output (plain StreamHandler used as fallback)
- `[mcp]`: MCP >= 2.0.0 for typed agent tools over stdio
- `[all]`: All of the above (fuzzy + image + interactive + gui + logging + MCP)
- `[dev]`: pytest, pytest-cov, Coverage.py, Pyright, build, and Twine for
  development and release checks
- `[docs]`: Sphinx and documentation extensions for building the API reference

**Requirements files (for development/manual installation):**

- `requirements.txt`: Base package (currently empty - zero dependencies)
- `requirements-fuzzy.txt`: Base + RapidFuzz dependency
- `requirements-image.txt`: Base + the complete `[image]` extra
- `requirements-interactive.txt`: Base + prompt_toolkit
- `requirements-gui.txt`: Base + PySide6
- `requirements-mcp.txt`: Base + MCP SDK
- `requirements-dev.txt`: All user-facing extras plus development and documentation tools

The validation module works without RapidFuzz using a built-in Levenshtein distance implementation. Install RapidFuzz for better fuzzy matching performance:

```bash
pip install color-match-tools[fuzzy]  # OR
pip install rapidfuzz
```

**Note:** If `rapidfuzz` is not installed, the validation module automatically falls back to a built-in hybrid fuzzy matcher using exact/substring/Levenshtein matching. This provides good results without external dependencies, though `rapidfuzz` is recommended for optimal matching accuracy.

## Hash Update Tooling (Maintainers)

For project maintainers, automated tooling is available to manage data integrity hashes:

```bash
# Automated hash update after modifying data files
python tooling/update_hashes.py --autoupdate

# Manual mode for review and control
python tooling/update_hashes.py

# Update only ColorConstants hash (after manual changes)
python tooling/update_hashes.py --constants-only
```

The automated tooling provides:

- **Complete automation** - Updates all hash values with safety confirmations
- **Two-step process** - Updates individual hashes first, then ColorConstants hash
- **Debug output** - Shows exactly which constants were modified
- **Safety features** - Requires explicit confirmation before modifying files

**When to use hash tooling:**

- After modifying any JSON data files (`colors.json`, `filaments.json`, etc.)
- After updating palette files in `data/palettes/`
- After adding new constants to `ColorConstants` class
- After modifying transformation matrices in `matrices.py`

See [Troubleshooting: Data Integrity Verification](Troubleshooting.md#data-integrity-verification)
for verification behavior and recovery guidance.

---

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Usage →](https://github.com/dterracino/color_tools/blob/main/docs/Usage.md)
