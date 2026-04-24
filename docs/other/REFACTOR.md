# Refactoring Review — `color_tools` Main Module

> **Date:** 2026-04-24  
> **Scope:** `color_tools/` package  
> **Focus:** Orphan code, SoC violations, DRY violations, code smells, quick wins, architecture

---

## Summary Table

| # | Category | Item | Effort | Benefit | API Impact |
|---|----------|------|--------|---------|------------|
| B1 | **Bug** | `"last"` dual-color mode silently broken | Low | High | Patch fix — no break |
| B2 | **Bug** | `palette.colors` used in ~8 docstrings but doesn't exist | Low | High | Additive (new property) |
| O1 | **Orphan** | `EXPORT_FORMATS` imported but unused in `export.py` | Trivial | Low | None |
| O2 | **Orphan** | `get_override_info()` on both palette classes | Low | Medium | Remove (internal use only) |
| O3 | **Orphan** | Duplicate block in `determine_base_hue` | Trivial | Low | None |
| D1 | **DRY** | Metric-resolution logic duplicated 4× | Medium | High | None |
| D2 | **DRY** | `nearest_color` / `nearest_colors` are near-duplicates | Medium | High | None |
| D3 | **DRY** | Data-path resolution pattern duplicated 4× | Low | Medium | None |
| D4 | **DRY** | `hsl_to_rgb` manually re-implements `colorsys.hls_to_rgb` | Low | Medium | None |
| D5 | **DRY** | Wildcard filter handling duplicated in filament nearest methods | Trivial | Low | None |
| S1 | **SoC** | Module-level palette load in `validation.py` | Low | High | None |
| S2 | **SoC** | `naming.py` loads `Palette.load_default()` on every call | Low | High | None |
| S3 | **SoC** | `FilamentRecord.__post_init__` reaches into global config | Medium | Medium | Possible breaking change |
| S4 | **SoC** | `get_override_info` loads a JSON file inside a class method | Low | Medium | None |
| S5 | **SoC** | `reporting.py` wires up a `ListHandler` to capture log messages | Low | Medium | None |
| C1 | **Smell** | Bare `except:` in 4 locations | Low | High | None |
| C2 | **Smell** | `object.__setattr__` on a frozen dataclass | Medium | Medium | None |
| C3 | **Smell** | `XYZ_SCALE_FACTOR` overloaded to mean `100.0` in non-XYZ code | Low | Medium | None |
| C4 | **Smell** | Inline `from pathlib import Path` inside function bodies | Trivial | Low | None |
| C5 | **Smell** | `from pathlib import Path` duplicated in `logging_config.py` | Trivial | Low | None |
| A1 | **Arch** | Extract `_resolve_metric()` helper into `_palette_utils.py` | Medium | High | None |
| A2 | **Arch** | Extract `_resolve_data_path()` helper | Low | Medium | None |
| A3 | **Arch** | Make `_palette` in `validation.py` lazily initialized | Low | Medium | None |
| A4 | **Arch** | Accept optional `palette=` argument in `naming.py` | Low | Medium | Additive |

---

## Bugs (Found During Review)

### B1 — `"last"` dual-color mode is silently broken
**Files:** `config.py`, `filament_palette.py`  
**Effort:** Low | **Benefit:** High | **API Impact:** Patch fix, no breaking change

`config.py:set_dual_color_mode` validates against `("first", "last", "mix")` and documents
`"last"` as "Use the second color." However, `FilamentRecord.__post_init__` only checks
`mode == "second"` — it never checks `mode == "last"`. As a result, setting
`set_dual_color_mode("last")` silently falls through to the `else` branch and uses the
*first* color. The mode `"last"` is accepted, stored, but completely ignored.

**Fix:** Change the `if mode == "second"` guard in `filament_palette.py` to
`if mode in ("second", "last")`, or rename the constant used throughout to `"last"` for
consistency (preferred, since `"second"` is undocumented in the public API).

---

### B2 — `palette.colors` used in ~8 docstring examples but the attribute doesn't exist
**Files:** `palette.py`, `export.py`, `exporters/*.py`  
**Effort:** Low | **Benefit:** High | **API Impact:** Additive (new `colors` property)

The `Palette` class exposes `self.records`, but virtually every docstring example in
`palette.py`, `export.py`, and several exporters calls `palette.colors` (e.g.,
`export_colors_csv(palette.colors)`). Two test scripts in `/tools/` also use
`palette.colors`. All of these would raise `AttributeError` at runtime.

Similarly, `FilamentPalette` exposes `self.records`; its `export.py` example calls
`palette.filaments`, which also doesn't exist.

**Fix:** Add `@property` aliases to both classes:
```python
# In Palette
@property
def colors(self) -> List[ColorRecord]:
    """Alias for records — more intuitive name for CSS color data."""
    return self.records

# In FilamentPalette
@property
def filaments(self) -> List[FilamentRecord]:
    """Alias for records — more intuitive name for filament data."""
    return self.records
```
This is a pure addition, does not break anything, and makes the documented API actually
work.

---

## 1. Orphan Code

### O1 — `EXPORT_FORMATS` imported but unused in `export.py`
**File:** `export.py` (line 36)  
**Effort:** Trivial | **Benefit:** Low | **API Impact:** None

```python
from color_tools.exporters import (
    get_exporter,
    list_export_formats as _list_export_formats,
    EXPORT_FORMATS,   # ← imported but never referenced in this file
)
```
`EXPORT_FORMATS` is imported but no code in `export.py` actually references it. It is
likely a leftover from when `export.py` contained its own format dictionary.

**Fix:** Remove the `EXPORT_FORMATS` line from the import. No other impact.

---

### O2 — `get_override_info()` on both palette classes appears unused
**Files:** `palette.py` (line 615), `filament_palette.py` (line 876)  
**Effort:** Low | **Benefit:** Medium | **API Impact:** Internal — safe to remove or mark private

Both `Palette.get_override_info()` and `FilamentPalette.get_override_info()` build
complex diagnostic dictionaries about user-vs-core data conflicts. The information they
produce is already logged to the `logging` system at load time (in `load_colors()` and
`load_filaments()`), making these methods largely redundant.

Neither method appears to be called from any CLI handler, any exporter, or any test. The
`FilamentPalette` version also has an embedded `json.load()` call (see **S4**) and a
bare `except: pass` (see **C1**), making it a maintenance liability.

**Fix options:**
1. Remove both methods entirely.
2. Rename to `_get_override_info()` (private) to signal they are diagnostic/testing aids.

---

### O3 — Duplicated 5-line block in `determine_base_hue`
**File:** `naming.py` (lines 139–150)  
**Effort:** Trivial | **Benefit:** Low | **API Impact:** None

Lines 139–144 and lines 145–150 are byte-for-byte identical — the same call to
`get_hue_with_ish` with the same guard block and the same `pass` comment. This is a
copy-paste leftover from an incomplete edit.

```python
# Lines 139–144 (first copy)
ish_variant = get_hue_with_ish(h, s)
if ish_variant:
    pass  # Will check special cases below
# Lines 145–150 (second copy — identical)
ish_variant = get_hue_with_ish(h, s)
if ish_variant:
    pass  # Will check special cases below
```

**Fix:** Delete one of the two identical blocks. The function is pure so this is safe.

---

## 2. DRY Violations

### D1 — Metric-resolution logic duplicated across 4 methods ⭐ Major
**Files:** `palette.py` (nearest_color, nearest_colors), `filament_palette.py`
(nearest_filament, nearest_filaments)  
**Effort:** Medium | **Benefit:** High | **API Impact:** None

The same `metric_l` → `distance_fn` mapping block appears in all four nearest-neighbor
methods. Any new metric (e.g., HyAB was presumably added this way) must be added in four
places. The filament methods also handle `"euclidean"` differently from the palette methods
(wrapping in a lambda), introducing subtle divergence.

```python
# This block or a close variant appears 4 times:
metric_l = metric.lower()
if metric_l in ("de2000", "ciede2000"):
    fn = delta_e_2000
elif metric_l in ("de94", "cie94"):
    fn = delta_e_94
elif metric_l in ("de76", "cie76", "euclidean"):
    fn = delta_e_76
elif metric_l in ("cmc", "decmc"):
    fn = ...
elif metric_l == "hyab":
    fn = delta_e_hyab
else:
    raise ValueError(...)
```

**Fix:** Extract a `_resolve_lab_metric(metric, cmc_l, cmc_c)` function into
`_palette_utils.py` that returns a `Callable[[tuple, tuple], float]`. All four methods
then reduce to a single call. See **A1** for details.

---

### D2 — `nearest_color` / `nearest_colors` are near-duplicates in `Palette`
**File:** `palette.py`  
**Effort:** Medium | **Benefit:** High | **API Impact:** None

`nearest_color` and `nearest_colors` share an almost identical body: same space
dispatching, same metric resolution, same loop. The only differences are that
`nearest_color` tracks a single best and `nearest_colors` builds a list. Both methods
are ~90 lines each.

Same duplication exists between `nearest_filament` / `nearest_filaments` in
`filament_palette.py`.

**Fix:** Have `nearest_color` delegate to `nearest_colors(count=1)` and return
`result[0]`. This is idiomatic and eliminates ~90 lines of duplicated code. The same
refactoring applies to the filament variants.

---

### D3 — Data-path resolution pattern repeated in all four `load_*` functions
**Files:** `palette.py` (`load_colors`), `filament_palette.py` (`load_filaments`,
`load_maker_synonyms`, `load_owned_filaments`)  
**Effort:** Low | **Benefit:** Medium | **API Impact:** None

All four loader functions contain the same path-resolution boilerplate:

```python
if json_path is None:
    data_dir = Path(__file__).parent / "data"
    json_path = data_dir / SOME_FILENAME
else:
    json_path = Path(json_path)
    if json_path.is_dir():
        data_dir = json_path
        json_path = json_path / SOME_FILENAME
    else:
        data_dir = json_path.parent
```

**Fix:** Extract `_resolve_data_path(json_path, filename) -> tuple[Path, Path]` into
`_palette_utils.py` returning `(data_dir, resolved_file_path)`. Each loader becomes two
lines. See **A2** for the proposed signature.

---

### D4 — `hsl_to_rgb` manually re-implements `colorsys.hls_to_rgb`
**File:** `conversions.py` (lines 407–455)  
**Effort:** Low | **Benefit:** Medium | **API Impact:** None

The forward direction `rgb_to_hsl` uses `_rgb_to_rawhsl` which internally calls
`colorsys.rgb_to_hls`. The reverse `hsl_to_rgb` does not use colorsys — it
reimplements the entire algorithm manually, including an inner `hue_to_rgb` closure.

Python's `colorsys.hls_to_rgb(h, l, s)` (note argument order) does the same thing
correctly, with the stdlib already tested and maintained.

**Fix:**
```python
def hsl_to_rgb(hsl: Tuple[float, float, float]) -> Tuple[int, int, int]:
    h, s, l = hsl
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
    return (
        max(0, min(255, int(round(r * 255)))),
        max(0, min(255, int(round(g * 255)))),
        max(0, min(255, int(round(b * 255)))),
    )
```
This eliminates ~40 lines and removes a custom inner function. Risk is low since
`colorsys` is already imported.

---

### D5 — Wildcard-filter handling duplicated in `nearest_filament` / `nearest_filaments`
**File:** `filament_palette.py` (lines 728–731 and 818–821)  
**Effort:** Trivial | **Benefit:** Low | **API Impact:** None

Both methods contain identical wildcard handling:
```python
maker_filter = None if maker == "*" else maker
type_filter  = None if type_name == "*" else type_name
finish_filter = None if finish == "*" else finish
```
Fixing **D2** above (delegating `nearest_filament` to `nearest_filaments`) would
eliminate this automatically.

---

## 3. Separation of Concerns (SoC) Violations

### S1 — Module-level palette load in `validation.py` ⭐ Major
**File:** `validation.py` (lines 27–28)  
**Effort:** Low | **Benefit:** High | **API Impact:** None

```python
# At module level — runs at import time!
_palette = Palette.load_default()
_color_names = [r.name for r in _palette.records]
```

This means:
- Importing `validation` anywhere immediately reads and parses `colors.json`.
- Any import-time failure (missing file, bad data) shows as a confusing `ImportError`.
- Tests that mock the palette have to intercept the import before the module loads.
- Every module that imports `from color_tools import validate_color` pays this I/O cost.

**Fix:** Lazy initialization with `functools.lru_cache` or a module-level `None` sentinel:
```python
_palette: Optional[Palette] = None
_color_names: Optional[list[str]] = None

def _ensure_palette_loaded() -> None:
    global _palette, _color_names
    if _palette is None:
        _palette = Palette.load_default()
        _color_names = [r.name for r in _palette.records]
```
Call `_ensure_palette_loaded()` at the top of `validate_color()`. Zero API change.

---

### S2 — `naming.py` loads `Palette.load_default()` on every call
**File:** `naming.py` (line 357 in `generate_color_name`, line 295 in
`is_unique_near_claim`)  
**Effort:** Low | **Benefit:** High | **API Impact:** Additive (optional `palette=` param)

Both `generate_color_name` and `is_unique_near_claim` call `Palette.load_default()`
directly, which reads and parses `colors.json` each time. When processing a palette of
1,000 filaments (image quantization), this results in 1,000 JSON loads.

This also tightly couples the naming module to the file system and the default palette,
making it impossible to generate names against a custom palette without subclassing.

**Fix:** Accept an optional `palette` argument with a lazy default:
```python
def generate_color_name(
    rgb: tuple[int, int, int],
    palette_colors: list[tuple[int, int, int]] | None = None,
    near_threshold: float = 5.0,
    palette: Palette | None = None,   # NEW
) -> tuple[str, MatchType]:
    if palette is None:
        palette = Palette.load_default()
    ...
```
Callers who want performance can pass a pre-loaded palette. Existing callers are unaffected.

---

### S3 — `FilamentRecord.__post_init__` reaches into global config
**File:** `filament_palette.py` (line 82)  
**Effort:** Medium | **Benefit:** Medium | **API Impact:** Potentially breaking if changed

```python
def __post_init__(self) -> None:
    mode = get_dual_color_mode()   # ← calls global config!
```

A frozen data-record dataclass should not have side effects that depend on mutable global
state. This means:
- Two `FilamentRecord` instances constructed with the same arguments at different points
  in time (before/after `set_dual_color_mode`) can have different `rgb` and `lab` values.
- Thread-local config changes after record construction have no effect (the value is baked
  in at construction time), which can be surprising.
- Records cannot be safely used as dict keys or in sets without this being a latent bug.

The fundamental tension is that `FilamentRecord` computes derived properties (`rgb`, `lab`)
at construction time from a global setting. This is a genuine design conflict.

**Options (least to most breaking):**
1. **Quick win:** Document this clearly and add a note in `set_dual_color_mode` that it
   must be called before any `FilamentRecord` is constructed. (Low effort, zero API change.)
2. **Better:** Add a `@classmethod FilamentRecord.from_dict(data, mode="first")` factory
   that accepts `mode` explicitly, and have `_parse_filament_records` pass the mode
   through. The existing constructor becomes implementation detail.
3. **Full fix:** Store both `rgb1`/`lab1` and `rgb2`/`lab2` on the record; resolve which
   to use at search time (inside `FilamentPalette`). This removes the global dependency
   from the record entirely.

---

### S4 — `FilamentPalette.get_override_info()` loads a JSON file inside a class method
**File:** `filament_palette.py` (lines 925–947)  
**Effort:** Low | **Benefit:** Medium | **API Impact:** Affects only `get_override_info` return value

```python
core_file = Path(__file__).parent / "data" / "maker_synonyms.json"
with open(core_file, 'r') as f:
    core_synonyms = json.load(f)
```

A palette class method should not be directly opening data files to compare state. This
breaks the single responsibility principle and makes the method fragile (it re-reads the
file every call, uses a hardcoded path, and silently ignores any errors via `except: pass`).

**Fix:** If `get_override_info` is kept (see **O2**), pass the comparison data as an
argument, or remove the synonym comparison section (since synonym overrides are already
logged at `load_maker_synonyms()` time).

---

### S5 — `reporting.py` uses a `ListHandler` as an ad-hoc message bus
**File:** `cli_commands/reporting.py` (lines 29–36)  
**Effort:** Low | **Benefit:** Medium | **API Impact:** None (internal CLI code)

`show_override_report` attaches a temporary `ListHandler` to the `color_tools.palette`
logger to intercept and collect log messages in order to display them as a report. This
is using the logging system as an inter-process communication bus rather than its intended
purpose.

The root cause is that `load_colors` and `load_filaments` don't return override information
directly — they log it. The data is communicated to the CLI via a side channel (the logger).

**Fix:** Have `load_colors` and `load_filaments` return a `(records, overrides)` tuple, or
a dataclass like `LoadResult`. `show_override_report` can then display the overrides
directly without the `ListHandler` hack. The log calls can remain for normal library use.

---

## 4. Code Smells

### C1 — Bare `except:` in 4 locations ⭐ High Priority
**Files:** `gamut.py` (line 71), `filament_palette.py` (lines 764, 853, 945)  
**Effort:** Low | **Benefit:** High | **API Impact:** None

Bare `except:` catches **everything** including `SystemExit`, `KeyboardInterrupt`,
`MemoryError`, and `RecursionError`. This can swallow crashes and make programs impossible
to interrupt.

```python
# gamut.py — is_in_srgb_gamut
try:
    rgb = lab_to_rgb(lab, clamp=False)
    ...
except:          # ← should be: except (ValueError, OverflowError, ArithmeticError)
    return False

# filament_palette.py — nearest_filament and nearest_filaments
try:
    d = distance_fn(target_lab, rec.lab)
    ...
except:          # ← should be: except (ValueError, ZeroDivisionError, OverflowError)
    continue

# filament_palette.py — get_override_info
try:
    ...
except:          # ← most egregious: silently ignores all errors including coding mistakes
    pass
```

**Fix:** Replace all bare `except:` with the specific exception types that can actually
occur (typically `(ValueError, ArithmeticError, OverflowError)`).

---

### C2 — `object.__setattr__` abused to bypass frozen dataclass immutability
**File:** `filament_palette.py` (lines 100, 101, 115, 116)  
**Effort:** Medium | **Benefit:** Medium | **API Impact:** None

`FilamentRecord` is declared `@dataclass(frozen=True)` but then mutates itself in
`__post_init__` using `object.__setattr__`:

```python
object.__setattr__(self, 'rgb', mixed_rgb)
object.__setattr__(self, 'lab', rgb_to_lab(mixed_rgb))
```

This pattern exists because `rgb` and `lab` are declared as `field(init=False)` (derived
fields computed in post-init), and frozen dataclasses don't allow normal assignment in
`__post_init__`. The use of `object.__setattr__` is the standard workaround for this
specific pattern, but it signals a design mismatch: a "frozen" record that initializes
computed fields is an awkward combination.

**Fix (quick):** No immediate change needed — the pattern works correctly and is a known
Python idiom. However, a `# noqa` / explanatory comment would reduce future confusion.

**Fix (proper):** Store `hex`, `hex2`, and `td_value` as inputs; compute `rgb` and `lab`
as `@property` accessors that read from `hex` at access time. The record stays truly
immutable. This ties into **S3**: if `rgb`/`lab` are properties, dual-color mode can be
applied at access time rather than construction time.

---

### C3 — `XYZ_SCALE_FACTOR = 100.0` overloaded across unrelated color spaces
**File:** `constants.py`, `conversions.py`  
**Effort:** Low | **Benefit:** Medium | **API Impact:** None (internal constant)

`ColorConstants.XYZ_SCALE_FACTOR` (= 100.0) is named for its original purpose (XYZ
values are scaled 0–100). However, it is also used as a "percent scale" constant in
CMY/CMYK conversions (`c = (1.0 - r/RGB_MAX) * XYZ_SCALE_FACTOR`) and HSL conversions
(`s * XYZ_SCALE_FACTOR`). These are semantically different uses of the same number.

This means:
- Code that reads `v * XYZ_SCALE_FACTOR` in a CMY function requires the reader to know
  that XYZ_SCALE_FACTOR happens to be 100.0, not that this is an XYZ operation.
- If XYZ ever used a different scale, all percent conversions would break.

**Fix:** Add `PERCENT_SCALE: float = 100.0` to `ColorConstants` and replace uses in
CMY/CMYK/HSL code with `PERCENT_SCALE`. The value is identical; the name becomes
self-documenting. Note: this requires regenerating the constants hash.

---

### C4 — `from pathlib import Path` inside function body
**File:** `palette.py` (line 127 in `_parse_color_records`)  
**Effort:** Trivial | **Benefit:** Low | **API Impact:** None

```python
def _parse_color_records(data: list, source_file: str = "JSON data") -> List[ColorRecord]:
    ...
    from pathlib import Path   # ← inline import inside a helper function
    source_filename = Path(source_file).name ...
```

`Path` is already imported at the top of `palette.py`. This is a redundant inline import
that adds confusion. Possibly a leftover from an earlier version before the top-level import
was added.

**Fix:** Remove the inline import from `_parse_color_records`. Same applies to similar
inline imports in `constants.py` (`verify_data_file`, `verify_all_data_files`).

---

### C5 — `from pathlib import Path` duplicated in `logging_config.py`
**File:** `logging_config.py` (line 45 and inside `setup_logging`)  
**Effort:** Trivial | **Benefit:** Low | **API Impact:** None

`Path` is imported at the module level and also redundantly imported inside `setup_logging`.
Remove the inline import.

---

## 5. Architecture Suggestions

### A1 — Extract `_resolve_lab_metric()` helper (solves D1)
**File:** `_palette_utils.py`  
**Effort:** Medium | **Benefit:** High | **API Impact:** None

Add a factory function that maps a metric name string to a callable:

```python
from typing import Callable
from color_tools.distance import (
    delta_e_2000, delta_e_94, delta_e_76, delta_e_cmc, delta_e_hyab, euclidean
)
from color_tools.constants import ColorConstants

def _resolve_lab_metric(
    metric: str,
    cmc_l: float = ColorConstants.CMC_L_DEFAULT,
    cmc_c: float = ColorConstants.CMC_C_DEFAULT,
) -> Callable[[tuple, tuple], float]:
    """
    Resolve a metric name string to a distance function.
    
    Centralizes all metric aliasing in one place so that new metrics only
    need to be added here, not in each palette's nearest-neighbor methods.
    """
    m = metric.lower()
    if m in ("de2000", "ciede2000"):
        return delta_e_2000
    elif m in ("de94", "cie94"):
        return delta_e_94
    elif m in ("de76", "cie76", "euclidean"):
        return delta_e_76
    elif m in ("cmc", "decmc"):
        return lambda a, b: delta_e_cmc(a, b, l=cmc_l, c=cmc_c)
    elif m == "cmc21":
        return lambda a, b: delta_e_cmc(a, b, l=2.0, c=1.0)
    elif m == "cmc11":
        return lambda a, b: delta_e_cmc(a, b, l=1.0, c=1.0)
    elif m == "hyab":
        return delta_e_hyab
    else:
        raise ValueError("Unknown metric. Use 'euclidean'/'de76'/'de94'/'de2000'/'cmc'/'hyab'.")
```

All four nearest-neighbor methods then reduce to:
```python
distance_fn = _resolve_lab_metric(metric, cmc_l, cmc_c)
for rec in candidates:
    d = distance_fn(value, rec.lab)
    ...
```

This also fixes a subtle divergence: in `filament_palette.py`, `euclidean` is wrapped in
a lambda but in `palette.py` it falls through to `de76`. With a central resolver, this
inconsistency is normalized.

---

### A2 — Extract `_resolve_data_path()` helper (solves D3)
**File:** `_palette_utils.py`  
**Effort:** Low | **Benefit:** Medium | **API Impact:** None

```python
from pathlib import Path

def _resolve_data_path(
    json_path: "Path | str | None",
    filename: str,
) -> tuple[Path, Path]:
    """
    Resolve (data_dir, json_file_path) from a flexible path argument.
    
    Returns:
        (data_dir, json_file_path) where data_dir is the containing directory
        and json_file_path is the fully resolved path to the target file.
    """
    if json_path is None:
        data_dir = Path(__file__).parent.parent / "data"
        return data_dir, data_dir / filename
    p = Path(json_path)
    if p.is_dir():
        return p, p / filename
    return p.parent, p
```

All four loaders (`load_colors`, `load_filaments`, `load_maker_synonyms`,
`load_owned_filaments`) then start with:
```python
data_dir, json_path = _resolve_data_path(json_path, ColorConstants.COLORS_JSON_FILENAME)
```

---

### A3 — Make `_palette` in `validation.py` lazy (solves S1)
**File:** `validation.py`  
**Effort:** Low | **Benefit:** Medium | **API Impact:** None

The simplest safe fix uses a module-level sentinel and lazy initialization, avoiding the
import-time I/O penalty entirely. See **S1** for the fix pattern.

Alternatively, use `functools.lru_cache` on a helper function:
```python
@functools.lru_cache(maxsize=1)
def _get_default_palette() -> tuple[Palette, list[str]]:
    p = Palette.load_default()
    return p, [r.name for r in p.records]
```

---

### A4 — Accept optional `palette=` argument in `naming.py` (solves S2)
**File:** `naming.py`  
**Effort:** Low | **Benefit:** Medium | **API Impact:** Additive

For users processing hundreds or thousands of colors (e.g., image quantization output),
`generate_color_name` loading the full CSS palette on every call is expensive. An optional
`palette` parameter allows callers to pass a pre-loaded (or even custom) palette. This
pattern is already used by other functions in the codebase.

---

## Priority Recommendation

**Do first (low effort, clear value):**
- **B1** Fix `"last"` dual-color mode bug
- **B2** Add `colors` / `filaments` property aliases to palette classes
- **O3** Delete the duplicate block in `determine_base_hue`
- **O1** Remove unused `EXPORT_FORMATS` import in `export.py`
- **C1** Replace all bare `except:` with specific exception types
- **C4 / C5** Remove inline `from pathlib import Path` redundancies
- **S1** Make `_palette` in `validation.py` lazy

**Do next (medium effort, architectural payoff):**
- **D1 + A1** Extract `_resolve_lab_metric()` and simplify all nearest-neighbor methods
- **D2** Refactor `nearest_color` to delegate to `nearest_colors`
- **D3 + A2** Extract `_resolve_data_path()` and DRY the loaders
- **D4** Replace manual `hsl_to_rgb` with `colorsys.hls_to_rgb`
- **S2 + A4** Add optional `palette=` to `naming.py` functions; lazy-load

**Larger, optional (architectural, evaluate ROI):**
- **S3** Decouple `FilamentRecord` from global config
- **S4 / S5** Improve override diagnostics architecture
- **O2** Remove or privatize `get_override_info` methods
- **C3** Add `PERCENT_SCALE` constant (requires hash regeneration)

---

*Generated by code review — see `docs/other/REVIEW_INDEX.md` for related documents.*
