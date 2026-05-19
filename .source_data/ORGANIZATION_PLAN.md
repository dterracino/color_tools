# `.source_data/` Organization Plan

## The Problem

There is no reliable way to know, just by looking at a file here, whether its data has been
consumed into the live databases (`color_tools/data/filaments.json` or `colors.json`).
The only way to determine integration status is to open the live data file and compare —
which requires judgment for each source.

This document tracks what we know, and what the plan is for cleaning this up.

---

## Proposed Folder Structure

```
.source_data/
├── ORGANIZATION_PLAN.md      ← this file
├── raw/                      ← original source files, untouched (PDFs, TXTs, unprocessed JSONs)
├── processed/                ← cleaned & formatted data, ready to review/merge
│   └── (currently: import/)  ← rename import/ to processed/
├── filamentcolors.xyz/       ← external API snapshots (keep separate, has its own structure)
└── _status.json              ← manifest tracking integration status of every source
```

The `raw/` and `processed/` split answers: *"Has any work been done on this source?"*
The `_status.json` manifest answers: *"Has the work actually made it into the live DB?"*

---

## `_status.json` Manifest Format

Each source entry tracks:

```json
[
  {
    "source_file": "raw/Prusa Filaments.pdf",
    "maker": "Prusament",
    "data_type": "filaments",
    "status": "integrated",
    "integrated_date": "2025-10-13",
    "processed_file": "processed/prusament.json",
    "record_count": 79,
    "notes": "Extracted via prusament_filaments.json. TD values present."
  }
]
```

**Status values:**
- `raw` — source file exists, no processing done
- `processed` — cleaned file exists in `processed/`, not yet merged into live DB
- `integrated` — data is confirmed present in the live DB
- `partial` — some records integrated, others not (e.g. a maker with new colorways added later)
- `superseded` — source was replaced by a newer/better source; do not integrate

---

## Current Known State

### Retro Palettes — all `integrated` ✅

All palette source files have corresponding entries in `color_tools/data/palettes/`.
These files are provenance records only — no action needed.

| Source File | Live File |
|-------------|-----------|
| `apple-ii-retro-palette.json` | `data/palettes/apple2.json` |
| `crayola_crayon_colors.json` | `data/palettes/crayola.json` |
| `ega-palette.txt` | `data/palettes/ega16.json`, `ega64.json` |
| `gameboy-color-retro-palette.json` | `data/palettes/gameboy-color.json` |
| `macintosh-retro-palette.json` | `data/palettes/macintosh.json` |
| `sega-master-system-retro-palette.json` | `data/palettes/sms.json` |
| `tandy16-retro-palette.json` | `data/palettes/tandy16.json` |
| `vga-palette.csv` | `data/palettes/vga.json` |

### Filament Makers — `integrated` ✅ (22 makers in live DB)

3D Jake, Atomic, Bambu Lab, Elegoo, ERYONE, eSun, Fillamentum, Flashforge, Hatchbox,
IIID Max, Inland, Matterhacker, Mika3D, Numakers, Overture, Panchroma, Paramount 3D,
Polymaker, Protopasta, Prusament, Repkord, Sunlu

Source files for these makers (PDFs, TXTs, raw JSONs) are provenance only.

### Filament Makers — `processed` 🔶 (17 makers in `import/`, not yet merged)

These have cleaned JSON files in `import/` but have **not** been verified as present
in `filaments.json`. Each one needs a manual check before merging.

3D-Fuel, 3DE, Copymaster 3D, Creality, Duramic 3D, FilaCube, Filament PM, Formfutura,
Fremover/GST3D, GreenGate3D, Longer, Plast-Spaw, PrintBed, Printed Solid, R3D,
TeqStone PETG, Zyltech

### filamentcolors.xyz Data — `raw` 🔴 (needs review)

The `filamentcolors.xyz/import_data/` folder contains:

- `existing_makers_missing_filaments.json` — additions for makers **already in the live DB**
  (new colorways, new product lines). Needs diff against live filaments.json.
- `new_maker_*.json` — 16 makers not yet in the live DB at all:
  Amolen, Anycubic, CC3D, Cookiecad, Geeetech, Giantarm, Jayo, Kexcelled, Kingroon,
  Qidi Tech, Reprapper, SainSmart, Tecbears, Tinmorry, VOXELPLA, Ziro

---

## Recommended Next Steps

1. **Rename `import/` → `processed/`** to match the folder structure above
2. **Move all raw source files** (PDFs, TXTs, original JSONs) into `raw/`
3. **Create `_status.json`** starting with what we know:
   - Mark all palette sources as `integrated`
   - Mark the 22 live makers' source files as `integrated`
   - Mark the 17 `processed/` makers as `processed`
   - Mark filamentcolors.xyz entries as `raw`
4. **Work through the 17 `processed/` makers** — open each against `filaments.json`,
   confirm whether it's already in there, update status
5. **Decide on filamentcolors.xyz data** — is this a periodic sync source,
   or a one-time import to review manually?
