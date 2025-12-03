# Configuration file for the Sphinx documentation builder.
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# -- Path setup --------------------------------------------------------------
# Add the parent directory to sys.path to import color_tools
sys.path.insert(0, os.path.abspath('../../'))

# Ensure the package can be imported
try:
    import color_tools
    print(f"Successfully imported color_tools v{color_tools.__version__}")
except ImportError as e:
    print(f"Failed to import color_tools: {e}")
    raise

# -- Project information -----------------------------------------------------
project = 'Color Tools'
copyright = '2024, David Terracino'
author = 'David Terracino'
release = '3.5.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',           # Auto-generate docs from docstrings
    'sphinx.ext.autosummary',       # Auto-generate summary tables
    'sphinx.ext.viewcode',          # Add source code links
    'sphinx.ext.napoleon',          # Support for Google/NumPy docstring styles
    'sphinx.ext.intersphinx',       # Link to other projects' docs
    'sphinx.ext.todo',              # Support for TODO notes
    'sphinx.ext.coverage',          # Coverage checker
    'sphinx_autodoc_typehints',     # Better type hint rendering
    'myst_parser',                  # Markdown support
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'  # Read the Docs theme

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------

# Napoleon settings for docstring parsing
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Autosummary settings  
autosummary_generate = True
autosummary_generate_overwrite = True
autosummary_mock_imports = []

# Intersphinx mapping for cross-references
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'pillow': ('https://pillow.readthedocs.io/en/stable/', None),
}

# Type hints configuration
typehints_fully_qualified = False
always_document_param_types = True

# MyST parser configuration (for Markdown files)
myst_enable_extensions = [
    "deflist",
    "fieldlist", 
    "html_admonition",
    "html_image",
    "colon_fence",
    "smartquotes",
    "replacements",
    "linkify",
    "substitution",
    "tasklist",
]

# Source file suffixes
source_suffix = {
    '.rst': None,
    '.md': 'myst_parser',
}

# Custom CSS for better color science documentation
html_css_files = [
    'custom.css',
]