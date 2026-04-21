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

- Python 3.10 or higher
- Git

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

All tests must pass before submitting a pull request.

## Code Style

- **Python 3.10+** syntax (union types with `|`, modern type hints)
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

The filament database (`color_tools/data/filaments.json`) uses a specific format:

```json
{
  "maker": "Manufacturer Name",
  "type": "PLA",
  "finish": "Matte",
  "color": "Color Name",
  "hex": "#RRGGBB",
  "td_value": 0.5
}
```

After modifying `filaments.json`, you **must** regenerate the data file hashes.
See [Hash Integrity](#hash-integrity) below.

For guidance on sourcing accurate hex values, see the existing entries as a reference —
values should match the manufacturer's published color as closely as possible.

## Hash Integrity

Core data files and color science constants are protected by SHA-256 hashes. If you
modify any of the following, you must regenerate the corresponding hash in `constants.py`:

- `color_tools/data/colors.json`
- `color_tools/data/filaments.json`
- `color_tools/data/maker_synonyms.json`
- Any file under `color_tools/data/palettes/`
- Constants in `constants.py`
- Matrices in `matrices.py`

Refer to the [Hash Update Guide](https://github.com/dterracino/color_tools/blob/main/docs/Hash_Update_Guide.md)
for step-by-step instructions.

Verify integrity at any time:

```bash
python -m color_tools --verify-all
```

## Questions?

See [SUPPORT.md](SUPPORT.md) for where to get help.
