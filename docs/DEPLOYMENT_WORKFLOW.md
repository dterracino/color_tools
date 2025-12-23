# Documentation Deployment Workflow

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Trigger Events                              │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Push to main │  │ Version tag  │  │   Manual     │         │
│  │    branch    │  │  (v*.*.*)    │  │   trigger    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                  │                  │
│         └─────────────────┴──────────────────┘                  │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              GitHub Actions Workflow (docs.yml)                 │
│                                                                 │
│  Step 1: Checkout code                                         │
│  ├─ actions/checkout@v4                                        │
│  └─ Fetch all history                                          │
│                                                                 │
│  Step 2: Set up Python                                         │
│  ├─ actions/setup-python@v5                                    │
│  ├─ Python 3.11                                                │
│  └─ pip cache enabled                                          │
│                                                                 │
│  Step 3: Install dependencies                                  │
│  ├─ pip install --upgrade pip                                  │
│  └─ pip install -e ".[docs]"                                   │
│                                                                 │
│  Step 4: Build Sphinx documentation                            │
│  ├─ cd docs/sphinx                                             │
│  ├─ python -m sphinx -b html . _build/html                     │
│  └─ Output: HTML files + .nojekyll                             │
│                                                                 │
│  Step 5: Deploy to GitHub Pages                                │
│  ├─ peaceiris/actions-gh-pages@v3                              │
│  ├─ Source: docs/sphinx/_build/html                            │
│  ├─ Target: gh-pages branch (root)                             │
│  └─ Force orphan commit                                        │
│                                                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    gh-pages Branch                              │
│                                                                 │
│  ├─ .nojekyll                    ← Prevents Jekyll processing  │
│  ├─ index.html                   ← Main documentation page     │
│  ├─ api/                         ← API reference               │
│  ├─ _static/                     ← CSS, JS, images             │
│  ├─ _modules/                    ← Source code links           │
│  └─ ...                          ← Other generated files       │
│                                                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Pages                                │
│                                                                 │
│  🌐 https://dterracino.github.io/color_tools/                  │
│                                                                 │
│  Serves content from gh-pages branch                           │
│  Updates within 1-2 minutes after workflow completes           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Timeline

```
Event (push/tag) → Workflow starts (0-5 sec)
                 ↓
              Build docs (30-60 sec)
                 ↓
              Deploy to gh-pages (5-10 sec)
                 ↓
              GitHub Pages update (60-120 sec)
                 ↓
              Docs live! ✅
```

Total time: ~2-3 minutes from push to live docs

## Branch Strategy

```
main branch
  ├─ source code
  ├─ docs/sphinx/*.rst (source)
  └─ .github/workflows/docs.yml (automation)
         │
         │ [workflow builds & deploys]
         ▼
gh-pages branch (auto-managed)
  └─ HTML output only (never manually edited)
```

## File Flow

```
Source Files (in main)           Built Files (in gh-pages)
─────────────────────            ────────────────────────
docs/sphinx/
  ├─ conf.py                  →  Configuration (not deployed)
  ├─ index.rst                →  index.html
  ├─ _static/                 →  _static/
  │  ├─ custom.css            →    custom.css
  │  └─ .nojekyll             →  .nojekyll (root)
  └─ _templates/              →  (not deployed)

color_tools/
  ├─ __init__.py              →  api/color_tools.html
  ├─ conversions.py           →  api/color_tools.conversions.html
  ├─ distance.py              →  api/color_tools.distance.html
  └─ ...                      →  ...
```

## Security & Permissions

The workflow uses `GITHUB_TOKEN` (automatically provided) with:
- `contents: write` - Required to push to gh-pages branch
- No additional secrets needed
- Safe for public repositories
