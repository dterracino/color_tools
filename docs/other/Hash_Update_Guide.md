# Hash integrity system update guide

Color Tools uses SHA-256 hashes to detect accidental changes to protected
bundled data, system palettes, color-science constants, and color-vision
transformation matrices. User data uses optional sidecar hashes under the user
data directory.

## Generated integrity manifest

Expected hashes for bundled project data are stored in the private generated
module `color_tools/_integrity_hashes.py`. It contains only declarative values:

- `CORE_DATA_HASHES` for `colors.json`, `filaments.json`, and
  `maker_synonyms.json`.
- `SYSTEM_PALETTE_HASHES` for every JSON file in
  `color_tools/data/palettes`.
- `MATRICES_EXPECTED_HASH` for the supported color-vision matrices.
- `COLOR_CONSTANTS_EXPECTED_HASH` for the uppercase values owned by
  `ColorConstants`.

Do not edit the manifest manually. Hash regeneration does not edit
`constants.py`.

All file hashing normalizes CRLF line endings to LF before calculating SHA-256,
so normal Windows line-ending conversion does not invalidate protected JSON
files.

## Inspect hashes without writing

From the repository root:

```powershell
.\.venv\Scripts\python.exe tooling/update_hashes.py
```

The default mode discovers the current system palettes, calculates every
protected hash, displays the proposed manifest values, and makes no changes.

Narrow read-only reports are also available:

```powershell
.\.venv\Scripts\python.exe tooling/update_hashes.py --filaments-only
.\.venv\Scripts\python.exe tooling/update_hashes.py --palettes-only
.\.venv\Scripts\python.exe tooling/update_hashes.py --constants-only
```

## Regenerate bundled hashes

Use automatic update mode after intentionally changing protected data,
palettes, constants, or matrices:

```powershell
.\.venv\Scripts\python.exe tooling/update_hashes.py --autoupdate
```

The tool:

1. Calculates every protected hash.
2. Validates that all three core data files and at least one system palette are
   present.
3. Discovers every `*.json` file in the system palette directory; there is no
   second hand-maintained palette list.
4. Displays all proposed values.
5. Requires explicit confirmation.
6. Renders the complete manifest deterministically.
7. Atomically replaces only `color_tools/_integrity_hashes.py`.

Cancellation leaves every file unchanged. Repeating regeneration without
source changes produces byte-for-byte identical manifest contents.

After regeneration, run:

```powershell
.\.venv\Scripts\python.exe -m color_tools --verify-all
```

The checked-in tests also verify that the manifest contains exactly the bundled
system palette files and that every value is a lowercase 64-character SHA-256
digest.

## When regeneration is required

Regenerate the manifest after intentionally changing any of the following:

- `color_tools/data/colors.json`
- `color_tools/data/filaments.json`
- `color_tools/data/maker_synonyms.json`
- Any `color_tools/data/palettes/*.json` file
- Uppercase constants owned by `ColorConstants`
- Protected transformation matrices in `color_tools/matrices.py`

Adding or removing a system palette requires no updater registry edit. Palette
registration is the generated `SYSTEM_PALETTE_HASHES` mapping itself.

## User data sidecars

User files are not added to the generated project manifest. Users can create
optional `.sha256` sidecars with the public CLI:

```powershell
.\.venv\Scripts\python.exe -m color_tools --generate-user-hashes
```

For a custom data directory:

```powershell
.\.venv\Scripts\python.exe -m color_tools --json PATH --generate-user-hashes
```

This processes existing user color, filament, and synonym files plus active
`user-*.json` palettes. Copyable example palettes are excluded. A user file
without a sidecar remains usable and is treated as unverified.

Verify user sidecars with:

```powershell
.\.venv\Scripts\python.exe -m color_tools --verify-user-data
```

## Troubleshooting

If bundled verification fails after an intentional change, rerun the updater
and confirm the manifest replacement. If a newly added palette is absent, make
sure it uses the `.json` suffix and is located directly in
`color_tools/data/palettes`.

If regeneration fails, no success-shaped partial manifest is written. Correct
the reported missing file or invalid digest, rerun the tool, then run
`--verify-all` before committing.
