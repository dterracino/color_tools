# Installation

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Usage →](https://github.com/dterracino/color_tools/blob/main/docs/Usage.md)

---

## Requirements

**Python 3.10+** is required.

## Install from PyPI (Recommended)

**Base package (zero dependencies):**

```bash
pip install color-match-tools
```

**With enhanced fuzzy matching:**

```bash
pip install color-match-tools[fuzzy]
```

Adds fuzzywuzzy for better color name validation (validation module has built-in fallback).

**With image processing support:**

```bash
pip install color-match-tools[image]
```

Adds Pillow for image transformations (CVD simulation/correction, palette quantization), color analysis, k-means clustering, and Hueforge optimization.

**With all optional features:**

```bash
pip install color-match-tools[all]
```

Installs everything: fuzzy matching + image processing.

All variants install the `color-tools` command globally in your terminal.

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
- All optional dependencies (fuzzy matching, image processing)
- Development tools (coverage, pyright, build, twine)

**Minimal development setup (base only):**

```bash
pip install -r requirements.txt
pip install -e .
```

## Dependencies

The core module uses **only Python standard library** - **zero external dependencies** required!

**Optional dependencies:**

- `[fuzzy]`: fuzzywuzzy >= 0.18.0 for enhanced fuzzy color name matching (validation module has built-in fallback)
- `[image]`: Pillow >= 10.0.0 for image processing features
- `[all]`: All of the above (fuzzy + image)

**Requirements files (for development/manual installation):**

- `requirements.txt`: Base package (currently empty - zero dependencies)
- `requirements-fuzzy.txt`: Base + fuzzywuzzy dependencies
- `requirements-image.txt`: Base + Pillow
- `requirements-dev.txt`: All of above + development tools (coverage, pyright, build, twine)

The validation module works without fuzzywuzzy using a built-in Levenshtein distance implementation. Install fuzzywuzzy for better fuzzy matching performance:

```bash
pip install color-match-tools[fuzzy]  # OR
pip install fuzzywuzzy
```

**Note:** If `fuzzywuzzy` is not installed, the validation module automatically falls back to a built-in hybrid fuzzy matcher using exact/substring/Levenshtein matching. This provides good results without external dependencies, though `fuzzywuzzy` is recommended for optimal matching accuracy.

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

See [Hash_Update_Guide.md](https://github.com/dterracino/color_tools/blob/main/docs/Hash_Update_Guide.md) for detailed workflows and troubleshooting.

---

[← Back to README](https://github.com/dterracino/color_tools/blob/main/README.md) | [Usage →](https://github.com/dterracino/color_tools/blob/main/docs/Usage.md)
