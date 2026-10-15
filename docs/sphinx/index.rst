Color Tools API Reference
=========================

**Version:** |release|

Welcome to the Color Tools API documentation! This library provides comprehensive color science tools for accurate color space conversions, perceptual color distance metrics, and color matching.

🎨 **Three Ways to Use Color Tools:**

1. **As a library:** ``from color_tools import rgb_to_lab``
2. **As a CLI tool:** ``python -m color_tools color --name coral``  
3. **As installed command:** ``color-tools filament --list-makers`` (needs pip install)

Quick Start
-----------

.. code-block:: python

   from color_tools import rgb_to_lab, delta_e_2000, Palette
   
   # Convert RGB to LAB
   lab = rgb_to_lab((255, 128, 64))
   
   # Find nearest CSS color
   palette = Palette.load_default()
   nearest, distance = palette.nearest_color(lab)
   print(f"Nearest color: {nearest.name}")

Documentation
-------------

For comprehensive guides and CLI usage:

* `📖 Usage Guide <https://github.com/dterracino/color_tools/blob/main/docs/Usage.md>`_ - Library and CLI usage examples
* `⚙️ Installation <https://github.com/dterracino/color_tools/blob/main/docs/Installation.md>`_ - Installation instructions
* `🎨 Customization <https://github.com/dterracino/color_tools/blob/main/docs/Customization.md>`_ - User overrides and custom palettes
* `❓ FAQ <https://github.com/dterracino/color_tools/blob/main/docs/FAQ.md>`_ - Frequently asked questions
* `📋 Quick Reference <https://github.com/dterracino/color_tools/blob/main/docs/QUICK_REFERENCE.md>`_ - Command cheat sheet
* `🔧 Troubleshooting <https://github.com/dterracino/color_tools/blob/main/docs/Troubleshooting.md>`_ - Common issues and solutions

CLI Commands
~~~~~~~~~~~~

The CLI provides eight commands:

* **color** - Search CSS colors by name or find nearest color
* **harmony** - Generate styled LCH color harmonies
* **filament** - Search 3D printing filaments with filtering (maker, type, finish)
* **convert** - Convert between color spaces and check gamut
* **name** - Generate descriptive names for RGB colors
* **validate** - Validate if hex codes match color names (fuzzy matching + Delta E)
  
  * *Optional:* Install ``[fuzzy]`` extra for improved fuzzy matching: ``pip install color-match-tools[fuzzy]``
  
* **cvd** - Color vision deficiency simulation and correction
* **image** - Image color analysis and manipulation
  
  * *Requires:* Install ``[image]`` extra: ``pip install color-match-tools[image]``

See the `Usage Guide <https://github.com/dterracino/color_tools/blob/main/docs/Usage.md>`__ for detailed CLI examples.

Selected Data Models
~~~~~~~~~~~~~~~~~~~~

The library uses typed dataclasses and models to represent colors, filaments,
export configuration, and results. Record and result types are immutable where
their contracts require it; export metadata and option objects remain mutable.

* **ColorRecord** - CSS colors with precomputed values in all color spaces
* **FilamentRecord** - 3D printing filaments retaining source RGB components and an effective color
* **FilamentFilterCriteria** - Reusable maker, type, finish, color, and TD filters
* **HarmonyColor / HarmonyResult** - Ideal and displayable LCH harmony results
* **ColorValidationRecord** - Color name/hex validation results with fuzzy matching
* **PaletteMetadata / PaletteExportData** - Palette-level export metadata and ordered colors
* **HexExportOptions / HueForgeExportOptions** - Typed per-export behavior
* **ColorCluster** - Image color clusters from k-means analysis *(requires [image] extra)*
* **ColorChange** - Luminance redistribution results for HueForge *(requires [image] extra)*

The module pages below are the authoritative class and function inventory.
See the `Usage Guide <https://github.com/dterracino/color_tools/blob/main/docs/Usage.md#selected-data-models-and-export-options>`__ for a quick reference table.

Core API Reference
------------------

Public Package API
~~~~~~~~~~~~~~~~~~

The package root contains the supported convenience imports intended for most
library users. The owning module pages below provide the detailed API grouped
by responsibility.

Color Science
~~~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.conversions
   color_tools.distance
   color_tools.gamut
   color_tools.harmony
   color_tools.constants
   color_tools.matrices
   color_tools.config

Color Input Contracts
~~~~~~~~~~~~~~~~~~~~~

The public helpers below share one canonical implementation. RGB validation
requires exactly three built-in integer channels in 0-255. Hex parsing accepts
RGB/RGBA short and long forms; alpha is validated and discarded.

.. autofunction:: color_tools.conversions.validate_rgb

.. autofunction:: color_tools.conversions.parse_hex_colors

.. autofunction:: color_tools.conversions.normalize_hex

The implementation module is also documented for maintainers:

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools._color_utils

Dependency-Free PNG Writing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

``from color_tools.png_writer import SimplePNGWriter`` writes sRGB-tagged
8-bit RGB solid, block, gradient, and equal-width swatch images without Pillow
or NumPy. It is part of the base package, not ``color_tools.image``.

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.png_writer

Color & Filament Data
~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.palette
   color_tools.filament_palette
   color_tools.filament_filter_criteria
   color_tools.filament_collections
   color_tools.naming
   color_tools.validation
   color_tools.color_deficiency

Export System
~~~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.export
   color_tools.exporters
   color_tools.exporters.base
   color_tools.exporters.export_options_base
   color_tools.exporters.palette_export_data
   color_tools.exporters.palette_metadata
   color_tools.exporters.registry
   color_tools.exporters.ase_exporter
   color_tools.exporters.aseprite_exporter
   color_tools.exporters.autoforge_exporter
   color_tools.exporters.css_exporter
   color_tools.exporters.csv_exporter
   color_tools.exporters.glsl_exporter
   color_tools.exporters.gpl_exporter
   color_tools.exporters.hex_exporter
   color_tools.exporters.hueforge_exporter
   color_tools.exporters.jascpal_exporter
   color_tools.exporters.json_exporter
   color_tools.exporters.kpl_exporter
   color_tools.exporters.lospec_exporter
   color_tools.exporters.paintnet_exporter
   color_tools.exporters.palette_lut_exporter
   color_tools.exporters.python_exporter
   color_tools.exporters.riffpal_exporter
   color_tools.exporters.scribus_exporter
   color_tools.exporters.sketchpalette_exporter
   color_tools.exporters.soc_exporter
   color_tools.exporters.swatch_image_exporter

Import System
~~~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.importers
   color_tools.importers.base
   color_tools.importers.registry
   color_tools.importers.gpl_importer
   color_tools.importers.hex_importer
   color_tools.importers.jascpal_importer
   color_tools.importers.riffpal_importer

Image Processing *(requires* ``[image]`` *extra)*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.image
   color_tools.image.analysis
   color_tools.image.basic
   color_tools.image.blend
   color_tools.image.conversion
   color_tools.image.dominance
   color_tools.image.watermark

Command Line Interface
~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.cli
   color_tools.cli_commands
   color_tools.cli_commands.utils
   color_tools.cli_commands.reporting
   color_tools.cli_commands.handlers
   color_tools.cli_commands.handlers.color
   color_tools.cli_commands.handlers.convert
   color_tools.cli_commands.handlers.cvd
   color_tools.cli_commands.handlers.harmony
   color_tools.cli_commands.handlers.filament
   color_tools.cli_commands.handlers.image
   color_tools.cli_commands.handlers.name
   color_tools.cli_commands.handlers.validate

Logging *(optional* ``[logging]`` *extra for colorized output)*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.logging_config

Interactive Terminal Features *(requires* ``[interactive]`` *extra)*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.interactive_manager
   color_tools.interactive_wizard

Desktop Filament Manager *(requires* ``[gui]`` *extra)*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.filament_manager_gui
   color_tools.filament_export_dialog

Model Context Protocol *(requires* ``[mcp]`` *extra)*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.mcp
   color_tools.mcp.models
   color_tools.mcp.server

.. automodule:: color_tools
   :no-members:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
