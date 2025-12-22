# 📚 Documentation Quick Reference

## 🔗 URLs

- **Live Documentation:** https://dterracino.github.io/color_tools/
- **Repository:** https://github.com/dterracino/color_tools
- **PyPI Package:** https://pypi.org/project/color-match-tools/

## ⚙️ Quick Commands

### Build Documentation Locally
```bash
# Install dependencies
pip install -e ".[docs]"

# Build docs
cd docs/sphinx
python -m sphinx -b html . _build/html

# Open in browser
open _build/html/index.html  # macOS
```

### Clean Build
```bash
# Remove old build
rm -rf docs/sphinx/_build

# Rebuild
cd docs/sphinx
python -m sphinx -b html . _build/html
```

### Manual Deployment Trigger
1. Go to GitHub Actions tab
2. Select "Build and Deploy Documentation" workflow
3. Click "Run workflow"
4. Select branch and click "Run workflow"

## 📋 Setup Checklist (First Time)

- [ ] Merge this PR to main
- [ ] Go to Settings → Pages
- [ ] Set Source: `gh-pages` branch, `/` folder
- [ ] Click Save
- [ ] Wait 1-2 minutes
- [ ] Visit https://dterracino.github.io/color_tools/
- [ ] ✅ Done!

## 🔄 Automatic Deployment Triggers

| Event | When | Docs Update |
|-------|------|-------------|
| Push to main | After commit to main branch | Within 2-3 minutes |
| Version tag | After `git tag v*.*.*` and push | Within 2-3 minutes |
| Manual | Via GitHub Actions UI | Within 2-3 minutes |

## 📖 Documentation Files

| File | Purpose |
|------|---------|
| `docs/GITHUB_PAGES_SETUP.md` | One-time setup instructions |
| `docs/DEPLOYMENT_WORKFLOW.md` | Technical workflow diagram |
| `docs/DEPLOYMENT_OPTIONS.md` | Platform comparison (GH Pages vs Vercel) |
| `docs/README.md` | General documentation guide |
| `.github/workflows/docs.yml` | Deployment automation |

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Docs not updating | Check Actions tab for failures |
| 404 error | Verify gh-pages branch exists and has content |
| Build fails | Check workflow logs, verify dependencies |
| Styling issues | Clear browser cache, check custom.css |

## 🔍 Check Status

```bash
# Check if gh-pages branch exists
git ls-remote --heads origin gh-pages

# View workflow status
# Go to: https://github.com/dterracino/color_tools/actions
```

## 📞 Need Help?

1. Check the detailed guides in `docs/` directory
2. Review GitHub Actions logs
3. Open an issue in the repository

---

**Last Updated:** 2024-12-22
**Workflow Version:** 1.0
**Documentation Platform:** GitHub Pages
