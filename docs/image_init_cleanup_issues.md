# color_tools `image/__init__.py`: cleanup issues

October 12, 2026

## Scope and verdict

`image/__init__.py` works, but it repeats one name list in four places and can hide real import errors behind a misleading message. This document lists every issue found so each can be fixed on its own.

Reviewed: `image/__init__.py` (the full file) and `image/watermark.py`. Nothing was executed against the real package, so every finding comes from reading the code.

## Issues in `image/__init__.py`

### 1. The same name list lives in four places

- **What:** every public name is listed in the `TYPE_CHECKING` block, the `try` block, the fallback stubs, and `__all__`.
- **Why it matters:** one new function means four edits. A missed stub only fails on machines without Pillow, so tests on a dev machine will not catch it.
- **Fix:** one table mapping each name to its submodule, driving the imports and `__all__`.

### 2. `except ImportError` is too broad

- **What:** any ImportError raised inside those submodules lands in the same handler: a typo, a circular import, a missing numpy, a bug in your own code.
- **Why it matters:** every case reports "Image processing requires Pillow", which sends people to reinstall a package that was never the problem.
- **Fix:** check the exception's `name` attribute. Fall back only when the missing module is a known optional dependency (`PIL`, `numpy`). Re-raise everything else, and name the module that is actually missing.

### 3. The fallback placeholders fail silently

- **What:** without Pillow, `BLEND_MODES` becomes an empty dict, and `ColorCluster`, `ColorChange`, `DominantColor` and `DominanceAnalysis` become empty classes. Only the functions raise.
- **Why it matters:** `if mode in BLEND_MODES` quietly returns False. The fake classes can be instantiated and subclassed with no error. `from color_tools.image import *` imports all of them without complaint.
- **Fix:** raise a clear ImportError when any of these names is accessed. No stubs, no fake classes.

### 4. Importing the package is eager and heavy

- **What:** `import color_tools.image` imports every submodule, and with them Pillow and numpy, even when the caller only wants `SimplePNGWriter`.
- **Why it matters:** the "no Pillow required" claim is true for correctness but not for import cost.
- **Fix:** load names on first access (see Recommended approach).

### 5. `IMAGE_AVAILABLE` is tied to every import succeeding

- **What:** the flag is True only if all submodules import cleanly. One broken module sets it to False for the whole package, including functions that work.
- **Why it matters:** the flag answers "is a bug present?" when callers read it as "is Pillow installed?"
- **Fix:** compute it with `importlib.util.find_spec("PIL")`, which checks for the package without importing it.

### 6. Minor

- `SimplePNGWriter` is imported after the guard, below the code that uses the names above it. It belongs in the same name table as everything else.
- The fallback error message names only Pillow. Numpy is also required, so say which module is missing.

## Docstring problems in `image/__init__.py`

The module docstring's examples do not match the code beneath them.

- [ ] The import line names `add_watermark`, which does not exist. The example then calls `add_text_watermark`, which that import never brought in.
- [ ] The watermark example passes a file path (`"photo.jpg"`) and an `output_path` argument. The real `add_text_watermark` takes a PIL `Image`, has no `output_path`, and returns a new `Image`, not a `PosixPath`.
- [ ] `convert_image("photo.webp", ...)` shows no result while the next line shows `PosixPath('photo.webp')`. Pick one style.
- [ ] "Requires Pillow" leaves out numpy. Name everything the `[image]` extra pulls in.
- [ ] The examples read files that will not exist, so any doctest run over this module would fail. Mark them `# doctest: +SKIP` or run them as plain code blocks.

## Related findings in `watermark.py`

The import structure is mostly right: Pillow at the top of the module, and `cairosvg` imported inside `add_svg_watermark` so a missing cairosvg does not disable text and image watermarks. Two import fixes remain, then some smaller items.

### Imports

- [ ] **`import cairosvg` can raise `OSError`.** cairosvg needs the native Cairo library. When that is missing, common on Windows, the failure is an `OSError`, which the `except ImportError` does not catch. Catch both, and mention the native library in the message.
- [ ] **The re-raise drops its cause.** Use `raise ImportError(...) from exc` so the original error stays visible.
- [ ] **Check the install hint.** The message says `pip install color-match-tools[image]`. Confirm cairosvg is part of that extra.

### Other

| Where | Problem | Fix |
| --- | --- | --- |
| Docstring example | `result.save("watermarked.jpg")` fails: the function returns RGBA and Pillow cannot write RGBA as JPEG | Convert to RGB first, or save as PNG in the example |
| All three `add_*` functions | RGBA conversion, alpha scaling and overlay/paste/composite are repeated | One `_apply_opacity` helper and one `_composite_at` helper |
| `_load_font` | Final fallback calls `ImageFont.load_default()` in a `try`, then calls it again in the `except` | Single call; drop the dead branch |
| `_load_font` | `raise ValueError(...)` inside `except` loses the original error | Add `from e` |
| `add_svg_watermark` | `assert png_data is not None` is stripped under `python -O` | Explicit `if ... raise` |
| `_calculate_position` | An unknown position string gives a bare `KeyError` | Check the value and list the valid positions in the error |
| `opacity`, `scale` | Not range-checked; a `scale` of 0 or less gives a zero-size image | Validate: `0 <= opacity <= 1`, `scale > 0` |

## Recommended approach: lazy loading with a module `__getattr__`

PEP 562 lets a package load names on first access. It fixes issues 1, 3, 4 and 5 together, and gives issue 2 a natural home.

1. **One name table.** A single mapping from each public name to its submodule. `__all__` is derived from it, so there is one list to maintain.
2. **Load on access.** A module-level `__getattr__` imports the owning submodule the first time a name is used, then stores the result in the module namespace so it runs once per name.
3. **Precise errors.** If the import fails because a known optional dependency is missing (`PIL`, `numpy`), raise one ImportError that names the missing package and the install command, chained with `from exc`. Any other ImportError propagates unchanged.
4. **Honest availability flag.** `IMAGE_AVAILABLE` comes from `importlib.util.find_spec("PIL")`, which checks without importing.
5. **Tooling support.** Define `__dir__` so tab completion works, and keep the `TYPE_CHECKING` block so type checkers and IDEs still see real signatures.
6. **Drift guard.** Add a test asserting that the `TYPE_CHECKING` names, the name table and `__all__` agree. That replaces the four-way duplication with one enforced source.

`SimplePNGWriter` stays in the same table. It then costs only standard-library import time.

### Trade-offs

- Tools that probe attributes (`inspect.getmembers`, doctest collection, Sphinx autodoc, `from color_tools.image import *`) trigger the lazy imports. Without Pillow they would see an ImportError. `hasattr` and `getattr` with a default only swallow `AttributeError`.
- Mitigation: raise `AttributeError` for names not in the table, and ImportError only for known names whose dependency is missing.

## Suggested order of work and tests

Small, independent fixes first, the structural refactor next, and the cleanup of working code last, once tests protect it.

1. `watermark.py` import fixes: catch `OSError` from cairosvg and chain with `from exc`.
2. Docstring corrections in `__init__.py`.
3. Lazy-loading refactor (issues 1 to 5) together with the drift-guard test.
4. `watermark.py` DRY cleanup and the smaller validation items.

### Tests to add

- [ ] With Pillow blocked (for example `sys.modules["PIL"] = None`, or a virtualenv without it), `import color_tools.image` succeeds and `SimplePNGWriter` works.
- [ ] In that same setup, using `add_text_watermark` raises an ImportError that names `PIL`.
- [ ] A submodule with a deliberate internal ImportError is reported as itself, not as "requires Pillow".
- [ ] `BLEND_MODES` and the data classes raise without Pillow instead of returning an empty dict or a fake class.
- [ ] `IMAGE_AVAILABLE` matches whether Pillow is installed.
- [ ] After touching only `SimplePNGWriter`, `"PIL" not in sys.modules` (proves loading is lazy).
- [ ] `hasattr(color_tools.image, "no_such_name")` is False.
- [ ] The name table, `__all__` and the `TYPE_CHECKING` names agree.
