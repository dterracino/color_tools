# GitHub Pages Setup Guide

This guide explains how to enable GitHub Pages for the Color Tools documentation after merging the documentation deployment PR.

## 📋 Prerequisites

- The documentation deployment workflow has been merged to `main`
- You have admin access to the repository

## 🚀 One-Time Setup Steps

### 1. Enable GitHub Pages

After merging the PR, the docs workflow will run and create a `gh-pages` branch. Then:

1. Go to your repository on GitHub
2. Click **Settings** (top navigation)
3. Click **Pages** (left sidebar, under "Code and automation")
4. Under **Source**, select:
   - **Branch**: `gh-pages`
   - **Folder**: `/ (root)`
5. Click **Save**

### 2. Wait for Deployment

- GitHub Pages will deploy automatically (takes 1-2 minutes)
- Check the deployment status in the **Actions** tab
- Look for the "pages-build-deployment" workflow

### 3. Verify Documentation is Live

Once deployed, visit:
**https://dterracino.github.io/color_tools/**

You should see the Color Tools API documentation homepage.

## 🔄 How It Works

### Automatic Deployment Triggers

The documentation is automatically rebuilt and deployed on:

1. **Push to main branch** - Updates docs with latest changes
2. **Version tags (v*.*.*)** - Updates docs for new releases
3. **Manual trigger** - Via GitHub Actions UI (workflow_dispatch)

### Workflow Process

1. Checkout code
2. Set up Python 3.11
3. Install package with `[docs]` extras
4. Build Sphinx documentation
5. Deploy to `gh-pages` branch
6. GitHub Pages serves from `gh-pages` branch

### Files and Locations

- **Workflow**: `.github/workflows/docs.yml`
- **Sphinx config**: `docs/sphinx/conf.py`
- **Source files**: `docs/sphinx/index.rst` + auto-generated API docs
- **Build output**: `docs/sphinx/_build/html/` (local, not committed)
- **Deployment branch**: `gh-pages` (auto-created, managed by workflow)

## 🛠️ Troubleshooting

### Documentation not updating?

1. Check the **Actions** tab for workflow failures
2. Review the docs workflow logs
3. Ensure the `gh-pages` branch exists
4. Verify GitHub Pages source is set to `gh-pages` branch

### 404 errors on documentation site?

1. Check that `.nojekyll` file exists in the gh-pages branch root
2. Verify Sphinx build completed successfully in workflow logs
3. Wait 1-2 minutes after workflow completes for Pages to update

### Need to rebuild docs manually?

1. Go to **Actions** tab
2. Select **Build and Deploy Documentation** workflow
3. Click **Run workflow** dropdown
4. Click **Run workflow** button

## 📝 Updating Documentation

### Update API Documentation

Edit docstrings in source code (`color_tools/*.py`), then:
- Push to main → docs update automatically
- Or create a tag → docs update with release

### Update Content Pages

Edit `docs/sphinx/index.rst` or add new `.rst`/`.md` files, then push to main.

### Local Preview

Build docs locally before pushing:

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Build docs
cd docs/sphinx
python -m sphinx -b html . _build/html

# Open in browser
open _build/html/index.html  # Mac
xdg-open _build/html/index.html  # Linux
start _build/html/index.html  # Windows
```

## 🎯 Next Steps

After enabling GitHub Pages:

1. ✅ Verify docs are live at https://dterracino.github.io/color_tools/
2. ✅ Test navigation and API reference pages
3. ✅ Share the documentation link with users
4. 📝 Consider adding more content to `docs/sphinx/index.rst`
5. 🔗 Update PyPI listing to include docs link (already in pyproject.toml)

## 📚 Resources

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [peaceiris/actions-gh-pages](https://github.com/peaceiris/actions-gh-pages)

## ❓ Questions?

If you encounter issues or have questions about the documentation deployment, please open an issue in the repository.
