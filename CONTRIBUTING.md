# Contributing to color-match-tools

Thank you for your interest in contributing! This document covers everything you need
to know to get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Adding to the Filament Database](#adding-to-the-filament-database)
- [Hash Integrity](#hash-integrity)

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating,
you are expected to uphold it.

## How to Contribute

### Reporting Bugs

- Search [existing issues](https://github.com/dterracino/color_tools/issues) first
- Use the **Bug Report** issue template
- Include your Python version, OS, and `color-match-tools` version
- Provide a minimal reproducible example

### Suggesting Features

- Search [existing issues](https://github.com/dterracino/color_tools/issues) for
  similar requests
- Use the **Feature Request** issue template
- Explain the use case — what problem does it solve?

### Contributing Code

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes (see development setup below)
4. Add or update tests
5. Update `CHANGELOG.md` under `[Unreleased]`
6. Open a pull request

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Git

The repository's `.python-version` selects Python 3.12 for tools such as pyenv
and uv. It is a development default, not an upper bound on supported runtimes.

### Steps

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/color_tools.git
cd color_tools

# Create and activate virtual environment
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

# Install dev dependencies
pip install -r requirements-dev.txt

# Install optional extras if needed
pip install -e ".[image]"
pip install -e ".[interactive]"
```

### Verify Everything Works

```bash
python -m color_tools --verify-all
python -m unittest discover tests
```

## Running Tests

```bash
# Run all tests
python -m unittest discover tests

# Run a specific test file
python -m unittest tests.test_conversions

# Run a specific test case
python -m unittest tests.test_conversions.TestRGBConversions.test_rgb_to_lab
```

All tests must pass before submitting a pull request. CI runs the suite on
Python 3.12, 3.13, and 3.14, and checks strict repository typing on Python 3.12.
Use the repository virtual environment, including the documentation and demo
dependencies, to reproduce that typing check:

```bash
python -m pip install -r requirements-dev.txt
python -m pip install pytest "pygame>=2.5.0" "moderngl>=5.10.0"
pyright --project pyrightconfig.json --warnings
```

## Code Style

- **Python 3.12+** syntax; do not require features from newer Python releases
- **PEP 8** style conventions
- **Type hints** on all function signatures
- **Docstrings** on all public functions and classes
- Use `from __future__ import annotations` for forward references
- No external dependencies in core code (pure stdlib only)
- Optional extras may introduce dependencies declared in `pyproject.toml`

### Module Responsibilities

Each module has a single responsibility — don't cross boundaries:

| Module | Responsibility |
| ------ | -------------- |
| `conversions.py` | Color space transformations only |
| `distance.py` | Distance metrics only |
| `palette.py` | CSS color database and search |
| `filament_palette.py` | Filament database and search |
| `constants.py` | Immutable constants only |
| `cli.py` | User interface only (orchestrates, never implements logic) |

### Changelog

**Every change must be documented in `CHANGELOG.md` under `[Unreleased]`**, no matter
how small. Use the appropriate category: `Added`, `Changed`, `Deprecated`, `Removed`,
`Fixed`, or `Security`.

## Submitting Changes

### Pull Request Checklist

Before opening a PR, confirm:

- [ ] All tests pass: `python -m unittest discover tests`
- [ ] No Pyright/type errors (check Problems panel in VS Code)
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] New features have tests
- [ ] Docstrings added/updated for public API changes
- [ ] Hash constants updated if core data was modified (see below)

### Commit Messages

Use clear, descriptive commit messages. A brief summary line is sufficient for most changes.

## Adding to the Filament Database

Filament data contributions are especially welcome. You can report a missing
filament, correct an existing color, or supply a missing or corrected
transmission distance (TD).

### No-code submissions

Use the
[Filament Data Submission form](https://github.com/dterracino/color_tools/issues/new?template=filament_data.yml).
You do not need to fork the repository, edit JSON, generate an ID, or update a
hash. A maintainer will review the information and handle the protected data
file. Corrections are just as valuable as new records.

Please provide as much of the following as you know:

| Field | What to provide |
| --- | --- |
| Maker | The manufacturer or brand shown for the filament |
| Type | The material or formulation, such as `PLA`, `PLA+`, or `ASA-CF` |
| Finish | An appearance such as `Matte`, `Silk`, or `Rock`, if applicable |
| Color | The manufacturer's color or product name |
| Hex | An explicit color value, or ordered values for a multi-color filament |
| TD | A published, community-provided, or measured value, if available |
| Reference | A product page, color chart, measurement photo, or other useful context |

Do not guess a hex or TD value merely to fill a field. For multi-color
filaments, preserve the source order and submit values as
`#RRGGBB-#RRGGBB` (with additional components when applicable). Product lines
that describe a material or formulation belong in **Type**; appearance belongs
in **Finish**.

### What transmission distance means

Transmission distance describes how readily light passes through a filament,
expressed as a distance in millimeters. A lower TD represents a more opaque
filament; a higher TD represents a filament that transmits light through a
greater thickness. TD is not a percentage and is not normalized to 0.0–1.0.

HueForge uses a filament's color and TD to model how its appearance changes as
printed layers accumulate over other colors. An inaccurate TD can make a
preview change color at the wrong thickness, while an accurate value helps
HueForge choose layer transitions that better reproduce the intended image.

The library keeps TD values when they are available, whether they originated
with a manufacturer, the community, or a direct measurement. It does not store
per-record provenance or certify a TD value's origin. References submitted in
an issue help maintainers review the contribution; they are not added to the
filament record as provenance metadata.

### Pull requests for filament data

Code contributors may update `color_tools/data/filaments.json` directly. The
database uses this format:

```json
{
  "id": "manufacturer-pla-matte-color-name",
  "maker": "Manufacturer Name",
  "type": "PLA",
  "finish": "Matte",
  "color": "Color Name",
  "hex": "#RRGGBB",
  "td_value": 0.5,
  "other_names": null
}
```

For a multi-color filament, put every ordered component in `hex`, for example
`"#FF0000-#0000FF"`. Use `null` when finish, TD, or alternate names are not
known. Preserve the existing `id` when correcting a record; IDs are stable
references and must not change with display text or color corrections.

After modifying `filaments.json`, regenerate the protected data hashes as
described in [Hash Integrity](#hash-integrity), run the database and full test
suites, and update `CHANGELOG.md`.

For large manufacturer imports, keep extraction, review, normalization, and
application separate. Importers must default to a dry run and require an
explicit option before modifying the database. They should report additions,
corrections, unchanged records, and conflicts, and a second run must be
idempotent.

## Hash Integrity

Core data files and color science constants are protected by SHA-256 hashes. If you
modify any of the following, you must regenerate the corresponding hash in `constants.py`:

- `color_tools/data/colors.json`
- `color_tools/data/filaments.json`
- `color_tools/data/maker_synonyms.json`
- Any file under `color_tools/data/palettes/`
- Constants in `constants.py`
- Matrices in `matrices.py`

Refer to the [Hash Update Guide](https://github.com/dterracino/color_tools/blob/main/docs/other/Hash_Update_Guide.md)
for step-by-step instructions.

Verify integrity at any time:

```bash
python -m color_tools --verify-all
```

## Questions?

See [SUPPORT.md](SUPPORT.md) for where to get help.
