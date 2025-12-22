# Color Tools Documentation

This directory contains the Sphinx-based documentation for the Color Tools library.

## 📚 Documentation Structure

```
docs/
├── sphinx/              # Sphinx source files
│   ├── conf.py         # Sphinx configuration
│   ├── index.rst       # Main documentation page
│   ├── _static/        # Static files (CSS, images, .nojekyll)
│   └── _templates/     # Custom templates
├── build-docs.ps1      # PowerShell build script (Windows)
└── requirements.txt    # Documentation build dependencies
```

## 🌐 Published Documentation

The documentation is automatically published to GitHub Pages:
**https://dterracino.github.io/color_tools/**

## 🔨 Building Documentation Locally

### Prerequisites

Install documentation dependencies:

```bash
# Install with docs extra
pip install -e ".[docs]"

# Or install requirements directly
pip install -r docs/requirements.txt
```

### Build Commands

**Linux/Mac:**
```bash
cd docs/sphinx
python -m sphinx -b html . _build/html
```

**Windows (PowerShell):**
```powershell
.\docs\build-docs.ps1 -Clean -Open
```

The built documentation will be in `docs/sphinx/_build/html/index.html`.

## 🚀 Automatic Deployment

Documentation is automatically built and deployed via GitHub Actions:

### Triggers
- **Push to main branch**: Deploys latest docs
- **Version tags (v*.*.*)**: Deploys docs for new releases
- **Manual trigger**: Via GitHub Actions UI

### Workflow File
See `.github/workflows/docs.yml`

### Deployment Process
1. Checkout repository
2. Set up Python 3.11
3. Install package with `[docs]` extras
4. Build Sphinx HTML documentation
5. Deploy to `gh-pages` branch
6. GitHub Pages serves from `gh-pages` branch

## 📝 Editing Documentation

### API Documentation
API documentation is auto-generated from docstrings in the source code:
- Edit docstrings in `color_tools/*.py` files
- Follow Google-style or NumPy-style docstring format
- Rebuild docs to see changes

### Content Pages
- Main page: `docs/sphinx/index.rst`
- Add new pages as `.rst` or `.md` files in `docs/sphinx/`
- Reference new pages in `index.rst` toctree

### Styling
- Theme: `sphinx_rtd_theme` (Read the Docs)
- Custom CSS: `docs/sphinx/_static/custom.css`
- Configuration: `docs/sphinx/conf.py`

## 🔧 Configuration

### Sphinx Extensions
- `sphinx.ext.autodoc` - Auto-generate API docs from docstrings
- `sphinx.ext.autosummary` - Create summary tables
- `sphinx.ext.napoleon` - Google/NumPy docstring support
- `sphinx_autodoc_typehints` - Type hint rendering
- `myst_parser` - Markdown support

### Version Management
The version number in `conf.py` should match `pyproject.toml` and `color_tools/__init__.py`.

## 🐛 Troubleshooting

### Build Errors
```bash
# Clean build directory
rm -rf docs/sphinx/_build

# Rebuild with verbose output
cd docs/sphinx
python -m sphinx -b html . _build/html -v
```

### Import Errors
Ensure the package is installed in development mode:
```bash
pip install -e .
```

### GitHub Pages Not Updating
- Check GitHub Actions workflow status
- Verify `gh-pages` branch exists
- Check repository Settings → Pages → Source is set to `gh-pages` branch

## 📖 Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [Read the Docs Theme](https://sphinx-rtd-theme.readthedocs.io/)
- [MyST Parser (Markdown)](https://myst-parser.readthedocs.io/)
- [Napoleon (Docstrings)](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
