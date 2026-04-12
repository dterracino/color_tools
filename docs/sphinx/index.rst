Color Tools API Reference
=========================

**Version:** |release|

Welcome to the Color Tools API documentation! This library provides comprehensive color science tools for accurate color space conversions, perceptual color distance metrics, and color matching.

🎨 **Three Ways to Use Color Tools:**

1. **As a library:** ``from color_tools import rgb_to_lab``
2. **As a CLI tool:** ``python -m color_tools color --name coral``  
3. **As installed command:** ``color_tools filament --list-makers`` (needs pip install)

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

The CLI provides six main commands:

* **color** - Search CSS colors by name or find nearest color
* **filament** - Search 3D printing filaments with filtering (maker, type, finish)
* **convert** - Convert between color spaces and check gamut
* **name** - Generate descriptive names for RGB colors
* **validate** - Validate if hex codes match color names (fuzzy matching + Delta E)
  
  * *Optional:* Install ``[fuzzy]`` extra for improved fuzzy matching: ``pip install color-match-tools[fuzzy]``
  
* **cvd** - Color vision deficiency simulation and correction
* **image** - Image color analysis and manipulation
  
  * *Requires:* Install ``[image]`` extra: ``pip install color-match-tools[image]``

See the `Usage Guide <https://github.com/dterracino/color_tools/blob/main/docs/Usage.md>`_ for detailed CLI examples.

Data Classes
~~~~~~~~~~~~

The library uses immutable dataclasses (frozen) to represent colors, filaments, and results:

* **ColorRecord** - CSS colors with precomputed values in all color spaces
* **FilamentRecord** - 3D printing filaments with intelligent dual-color handling
* **ColorValidationRecord** - Color name/hex validation results with fuzzy matching
* **ColorCluster** - Image color clusters from k-means analysis *(requires [image] extra)*
* **ColorChange** - Luminance redistribution results for HueForge *(requires [image] extra)*

All data classes have comprehensive docstrings with attribute descriptions and examples.
See the `Usage Guide <https://github.com/dterracino/color_tools/blob/main/docs/Usage.md#data-classes-quick-reference>`_ for a quick reference table.

Core API Reference
------------------

Color Science
~~~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.conversions
   color_tools.distance
   color_tools.gamut
   color_tools.constants
   color_tools.matrices
   color_tools.config

Color & Filament Data
~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.palette
   color_tools.filament_palette
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
   color_tools.exporters.csv_exporter
   color_tools.exporters.json_exporter
   color_tools.exporters.gpl_exporter
   color_tools.exporters.hex_exporter
   color_tools.exporters.jascpal_exporter
   color_tools.exporters.autoforge_exporter
   color_tools.exporters.lospec_exporter
   color_tools.exporters.paintnet_exporter

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
   color_tools.cli_commands.handlers.filament
   color_tools.cli_commands.handlers.image
   color_tools.cli_commands.handlers.name
   color_tools.cli_commands.handlers.validate

Optional Features
~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst

   color_tools.interactive_manager

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`