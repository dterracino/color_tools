Color Tools API Reference
=========================

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

Core API Reference
------------------

All Modules
~~~~~~~~~~~

.. autosummary::
   :toctree: api
   :template: module.rst
   
   color_tools.conversions
   color_tools.distance
   color_tools.palette
   color_tools.gamut
   color_tools.validation
   color_tools.naming
   color_tools.config
   color_tools.constants
   color_tools.image

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`