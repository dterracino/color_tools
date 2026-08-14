# Filament Inventory App — Project Summary

*Status: planning complete, no code written yet. One open design decision flagged below.*

## Goal

A personal iOS app for tracking owned 3D-printing filament, matching colors (via camera or
manual entry) against your filament database, and locating spools around the house — all built
on top of the existing `color_tools` Python library.

## Scope

- Single user, one phone, no multi-device sync
- No weight/percentage-remaining tracking (too much manual upkeep for personal use)
- Flat location labels (e.g. "Bonus Room Shelf 1") — no nested Room → Shelf hierarchy

## Core Features

1. **Color matching** — camera photo *or* manual hex/color-picker entry, matched against the
   filament database using `color_tools`' existing Delta E logic (CIEDE2000 etc.)
2. **Camera calibration** — a reference card (3-patch white/gray/black, and/or a 24-patch
   ColorChecker-style card) is included in the shot to correct for lighting/white-balance
   before sampling the filament color
3. **Spool code scanning** — barcode/QR scan to identify a spool; logs the code as an ID and
   attempts to look up known filament info. No existing code database — built up over time
   by scanning your own spools.
4. **Inventory tracking** — one record per physical spool (not just "do I own this color").
   Quantity is *derived* from scan-in / scan-out, never manually typed.
5. **Location tracking** — flat, typeable-or-dropdown location per spool. Powers the killer
   feature: scan/enter a color → see matching filaments → see where they are in the house.
6. **Manual filament entry** — color name, hex code, and other filament properties as needed.

## Architecture

### Split rationale

`color_tools` stays a general-purpose, reusable color-science library. Anything specific to
*this* app (spool records, locations, HTTP, the phone UI) lives outside it. Calibration and
scanning are color/image science, so they belong in `color_tools`; "where is my stuff"
inventory is app-domain data.

### `color_tools` additions (new code, in the existing repo)

Follows the existing subpackage pattern in `color_tools/image/` (which already contains
`analysis.py`, `basic.py`, `blend.py`, etc.) and the dataclass style used by `ColorCluster` /
`ColorChange`.

- **`color_tools/image/calibration.py`**
  `detect_reference_card()` / `extract_patches()` — pure image processing (uses the
  already-installed `opencv-contrib-python`). Takes a raw photo + card type (3-patch or
  24-patch), returns a dataclass with sampled-vs-expected patch colors and the sampled
  filament region. No color-matching logic here — image in, structured patch data out.

- **`color_tools/image/color_correction.py`**
  Takes the calibration dataclass, computes the correction (per-channel gain/offset for the
  3-patch card; a fuller correction matrix for the 24-patch card), returns a corrected color.
  Usable standalone, independent of calibration.py's image step.

- **`color_tools/image/codes.py`**
  QR/barcode detection via OpenCV's built-in `QRCodeDetector` and `barcode.BarcodeDetector`
  (already covered by the existing `opencv-contrib-python` dependency — no new dependency
  needed).

- **Composing function** (exact location TBD once we look at `filament_palette.py` directly)
  Something like `match_filament_from_calibrated_image()` that chains
  extract → correct → `FilamentPalette.nearest_filament()`. Each underlying step stays
  independently callable — calibration alone, correction alone, or the full chain.

### ⚠️ Open decision — where does spool-level inventory live?

Today, `filament_palette.py` tracks *ownership by filament ID only*
(`owned-filaments.json`, plus `FilamentPalette.add_owned()` / `.remove_owned()` /
`.list_owned()` / `.save_owned()` and a CLI TUI manager). There's no quantity, code, or
location field.

Two ways forward:

1. **Extend `color_tools` itself** — grow the owned-filament model into per-spool records
   (code, location, date added) inside the library.
2. **Keep `color_tools` ID-only** — spool records (code, location) live in the app's own
   database and simply *reference* a `color_tools` filament ID.

Leaning toward **option 2** for SoC reasons (keeps `color_tools` reusable for anyone who
doesn't care about personal shelving), but this needs a deliberate decision before coding
starts.

### API service

The repo's existing `api/` folder was a narrow, stateless Vercel deployment (two serverless
functions generating "color of the day" / "filament of the day" README badges, installing
`color-match-tools` from PyPI at deploy time, no database, no auth). **Not a fit** for this
project — it's been moved to `badges/`, freeing `api/` for the real service.

**New `api/`:** a proper FastAPI app —

- `main.py`
- `routers/matching.py`, `routers/inventory.py`, `routers/scanning.py`
- `schemas.py` (Pydantic models)
- own `requirements.txt`, importing `color-match-tools` as a normal pip dependency (not
  vendoring local source, unlike the old badge functions)
- SQLite for spool/location inventory data (if option 2 above is chosen)

**Hosting:** a home server (e.g. Raspberry Pi), reachable via Tailscale (free, private VPN —
no port forwarding, no public exposure). Fits a single-user tool with no cost and no
multi-device requirement.

### App

- **Framework:** Expo / React Native — camera capture, barcode/QR scanning, inventory UI
- **Dev/test loop:** Expo Go on your own phone (no Mac required, live reload via QR code)
- **Build/release path:** EAS Build (Expo's cloud build service) → TestFlight (internal
  testing, near-instant, no Apple review wait) — still requires a $99/year Apple Developer
  account, but no Mac ownership needed anywhere in the pipeline

## Explicitly out of scope

- Weight / percentage-remaining tracking per spool
- Nested location hierarchy (Room → Shelf)
- Multi-device sync / multi-user support
- Full print-industry color certification accuracy (gray-card/ColorChecker correction is
  "good enough to shortlist," not lab-instrument precision)

## Next steps before coding starts

1. Decide the open spool-inventory-location question above
2. Look at `filament_palette.py` and `color_tools/image/` contents directly to place the new
   composing function precisely
3. Confirm API folder structure and naming
