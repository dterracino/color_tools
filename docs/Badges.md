# Vercel API — Color of the Day & Filament of the Day

> **Personal demo deployment — not a public API.**
> This endpoint is hosted for the README swatches only. It carries no SLA, no rate-limit policy,
> and may be taken down or changed at any time without notice. Do not build products against it.

## Overview

Two Vercel serverless functions serve daily SVG swatch images embedded in the README:

| Endpoint | Description |
| --- | --- |
| `GET /api/color_of_day` | SVG swatch for today's CSS color |
| `GET /api/filament_of_day` | SVG swatch for today's 3D printing filament |

Both endpoints are **stateless and deterministic** — the same date always returns the same color.
No database, no authentication, no side effects. The color is selected by hashing the ISO date
string with SHA-256 and taking `hash % count`.

## Architecture

```text
GitHub repo
  └── api/
       ├── color_of_day.py       ← Vercel serverless function
       ├── filament_of_day.py    ← Vercel serverless function
       └── requirements.txt      ← color-match-tools (installed at build time)
  └── vercel.json                ← Vercel project config
  └── .github/workflows/
       └── vercel.yml            ← Auto-deploy on push to main
```

The functions install `color-match-tools` from PyPI at deploy time — they do **not** use the
local `color_tools/` source tree. The `vercel.json` `excludeFiles` config strips all non-API
folders from the bundle to keep the deployment small.

## Re-deploying

### Prerequisites

- [Vercel CLI](https://vercel.com/docs/cli) installed: `npm i -g vercel`
- Logged in: `vercel login`
- GitHub secrets set on this repo:
  - `VERCEL_TOKEN` — personal access token from [vercel.com/account/tokens](https://vercel.com/account/tokens)
  - `VERCEL_ORG_ID` — team/org ID from Vercel project settings
  - `VERCEL_PROJECT_ID` — project ID from Vercel project settings

### Manual deploy (one-off)

```bash
# Preview deployment
vercel

# Production deployment
vercel --prod
```

### Automatic deploy via GitHub Actions

Push to `main` automatically triggers `.github/workflows/vercel.yml`, which:

1. Runs a preview deploy on any PR targeting `main`
2. Runs a production deploy on every push to `main`

No manual action needed for normal releases.

### First-time project setup (if starting fresh)

```bash
# Link repo to a new Vercel project
vercel link

# Deploy to production
vercel --prod
```

Then capture the project settings from `vercel.com/[team]/[project]/settings` and update
the GitHub secrets `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` accordingly.

## Smoke-testing the deployed endpoints

Run the test script to verify both endpoints are up and returning valid SVGs:

```bash
python tooling/test_api.py
```

Pass `--base-url` to test a preview deployment:

```bash
python tooling/test_api.py --base-url https://color-tools-git-my-branch-dterracino.vercel.app
```

## Configuration

`vercel.json` controls:

- **`maxDuration`** — function timeout in seconds (currently 15 s)
- **`excludeFiles`** — folders stripped from the bundle (tests, docs, tooling, etc.)
- **`headers`** — `Cache-Control` and security headers applied to all `/api/*` responses

## Updating the production URL

If the Vercel project is recreated and gets a new URL, update two places:

1. `README.md` — the two `[![...](https://...)](https://...)` badge lines
2. This file — the endpoint table above

Then run `python tooling/test_api.py --base-url <new-url>` to verify before committing.
