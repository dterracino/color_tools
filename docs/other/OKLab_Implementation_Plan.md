# Oklab and OkLCh Implementation Plan

**Status**: Reviewed and ready for implementation  
**Last updated**: August 11, 2026  
**Target version**: TBD

## Current State

Oklab and OkLCh are not currently implemented. A repository-wide review found no
conversion functions, distance metrics, command-line support, MCP contracts, or tests
outside this planning document.

The implementation must integrate with the existing conversion, gamut, palette,
filament, CLI, interactive, and MCP architecture without changing existing color data
formats or CIELAB behavior.

## Goals

- Add accurate sRGB, Oklab, and OkLCh conversions.
- Preserve floating-point precision and extended-sRGB values during intermediate
  conversions.
- Add the standard Delta E OK color-difference metric.
- Support Oklab and OkLCh through the public Python API, CLI, interactive wizard, and
  MCP server.
- Add dedicated sRGB gamut checks and mapping for Oklab and OkLCh.
- Preserve compatibility with existing core and user palette data.
- Verify behavior against current W3C and Bjorn Ottosson reference values.

## Non-Goals

- Do not apply CIE94, CIEDE2000, CMC, or HyAB to Oklab coordinates. Those formulas
  contain corrections and scaling specific to CIELAB.
- Do not add required `oklab` or `oklch` fields to JSON data files.
- Do not replace existing CIELAB/LCH matching or gamut behavior by default.
- Do not implement CSS color-string parsing, alpha interpolation, or every CSS gamut
  mapping algorithm as part of the initial feature.
- Do not claim that Oklab is universally more accurate than CIEDE2000 for every
  color-matching workload.

## Coordinate Conventions

- Oklab uses `(L, a, b)`.
- OkLCh uses `(L, C, h)`.
- `L` uses the native range from `0.0` to `1.0`.
- `h` is expressed in degrees and normalized to `[0, 360)` when present.
- `a`, `b`, and `C` are theoretically unbounded. Values around `+/-0.5` and `0.5`
  are practical reference ranges, not validation limits.
- OkLCh chroma is non-negative.
- A converted OkLCh hue is `math.nan` when `C <= 0.000004`, matching the CSS Color
  Level 4 powerless-hue threshold.
- Oklab uses a D65 white point.

## Mathematical Requirements

### Conversion Matrices

Use a single internally consistent set of high-precision matrices. Prefer the current
W3C 64-bit Oklab matrices for XYZ D65 interoperability. Direct linear-sRGB matrices
from the updated 2021 Ottosson implementation may be used for optimized sRGB paths if
tests prove they agree with the XYZ path within the documented tolerance.

Store immutable matrix constants in `color_tools/constants.py` following the existing
constant conventions. Adding uppercase constants requires regeneration of
`ColorConstants._EXPECTED_HASH`.

### Signed Cube Root

The Oklab forward transform must use a real signed cube root:

```python
def _signed_cbrt(value: float) -> float:
    return math.copysign(abs(value) ** (1.0 / 3.0), value)
```

Do not use `value ** (1 / 3)`. Negative LMS values can occur for extended or
out-of-gamut colors, and Python may return a complex number for that expression.

### Extended sRGB

Internal transfer functions must preserve values below `0.0` and above `1.0`.
The nonlinear branch must operate on the absolute value and restore the sign. This is
required for correct conversion and gamut detection of out-of-gamut colors.

Public APIs that explicitly return display RGB may continue to return rounded integer
channels for compatibility. Conversion routing and gamut checks must use a separate
floating-point path before any clipping or rounding.

### Rectangular and Cylindrical Conversion

Convert Oklab to OkLCh with:

$$
C = \sqrt{a^2 + b^2}, \qquad h = \operatorname{atan2}(b, a)
$$

Convert OkLCh to Oklab with:

$$
a = C\cos(h), \qquad b = C\sin(h)
$$

If an incoming hue is `math.nan`, treat it as missing and produce `a = b = 0.0`.
Reject negative chroma through the library's normal validation policy rather than
silently changing it.

### Delta E OK

Expose the standard raw Oklab Euclidean distance as `delta_e_ok()`:

$$
\Delta E_{OK} =
\sqrt{(L_1-L_2)^2 + (a_1-a_2)^2 + (b_1-b_2)^2}
$$

One just-noticeable difference is approximately `0.02` on this scale. Do not multiply
the result by `100`.

Do not implement an OkLCh distance by combining hue degrees directly with lightness
and chroma. If a cylindrical helper is useful, it must be mathematically equivalent to
Cartesian Oklab distance:

$$
\sqrt{\Delta L^2 + C_1^2 + C_2^2 - 2C_1C_2\cos(\Delta h)}
$$

The preferred initial API is only `delta_e_ok()`, avoiding two names for the same
metric.

The current CSS specification also describes Delta E OK2 and Delta E OKr2. They may be
added in a later, separately reviewed change. If added now, they require their own
names, documentation, reference tests, and matching metric options; they must not
change the definition of `delta_e_ok()`.

## Implementation Surfaces

### 1. Constants and Conversion Core

Update:

- `color_tools/constants.py`
- `color_tools/conversions.py`
- `color_tools/validation.py` if shared validation is appropriate

Add public functions with complete type hints and docstrings:

```python
def rgb_to_oklab(rgb: tuple[int, int, int]) -> tuple[float, float, float]: ...
def oklab_to_rgb(
    oklab: tuple[float, float, float],
    clamp: bool = True,
) -> tuple[int, int, int]: ...
def oklab_to_oklch(
    oklab: tuple[float, float, float],
) -> tuple[float, float, float]: ...
def oklch_to_oklab(
    oklch: tuple[float, float, float],
) -> tuple[float, float, float]: ...
```

Also add private float-preserving helpers for conversion routing and gamut checks.
Their exact names should follow nearby conversion helpers, but they must return
unrounded, unclamped sRGB channels.

Where conversions between Oklab and existing non-RGB spaces are needed, route through
a float-preserving D65 XYZ representation. Do not route through integer RGB.

### 2. Distance Metrics

Update `color_tools/distance.py` with `delta_e_ok()` and export it publicly.

Keep all existing CIELAB metric signatures and documentation CIELAB-specific. Add
`delta_e_ok` as an explicit metric choice wherever callers currently select among
`de76`, `de94`, `de2000`, `cmc`, and `hyab`.

Matching code must convert both operands to Oklab when this metric is selected. It
must not pass Oklab tuples into existing Delta E functions.

### 3. Public API

Update `color_tools/__init__.py` to export:

- `rgb_to_oklab`
- `oklab_to_rgb`
- `oklab_to_oklch`
- `oklch_to_oklab`
- `delta_e_ok`

Include the new functions in the module documentation and preserve all existing
exports.

### 4. Data Model and Persistence

Keep RGB or hex as the stored source of truth:

- Do not modify `colors.json`, `filaments.json`, palette JSON files, or user data
  schemas.
- Do not add required fields to `ColorRecord` or `FilamentRecord`.
- Derive Oklab and OkLCh from each record's existing RGB value when requested.
- If repeated matching shows a measurable performance problem, add a private lazy
  cache or index in a later optimization backed by profiling.

This avoids data duplication, hash churn, stale derived values, larger package data,
and backward-compatibility failures for user palettes.

### 5. Palette and Filament Matching

Update `color_tools/palette.py`, `color_tools/filament_palette.py`, and shared palette
utilities as needed so `delta_e_ok` can be selected explicitly.

Requirements:

- Existing default metrics remain unchanged.
- Filters, maker synonyms, dual-color handling, and owned-filament behavior remain
  unchanged.
- Matching outputs identify the selected metric consistently.
- Tests compare actual nearest-match ordering for representative colors, not only
  direct distance values.

### 6. CLI and Interactive Wizard

Update:

- `color_tools/cli.py`
- `color_tools/cli_commands/handlers/convert.py`
- related CLI reporting and validation helpers
- `color_tools/interactive_wizard.py`

Add `oklab` and `oklch` to source and target choices. Update component counts, labels,
help text, validation, text output, and JSON output.

Refactor or extend the centralized conversion router so all supported source/target
combinations work without integer-RGB quantization. Adding isolated `if` branches only
for direct Oklab-to-RGB conversion is insufficient.

Add `delta_e_ok` to matching metric choices without changing the current default.

### 7. Gamut Support

Update `color_tools/gamut.py` with dedicated or generalized APIs for:

- Testing whether Oklab or OkLCh coordinates are inside sRGB.
- Mapping an out-of-gamut OkLCh color by reducing chroma while preserving lightness
  and hue.
- Returning a mapped color in a clearly documented coordinate space.

Gamut detection must inspect unrounded, unclamped floating-point sRGB channels.

The first implementation may use constant-lightness, constant-hue binary chroma
reduction. CSS local-MINDE, EdgeSeeker, and ray-trace mapping are out of scope unless
explicitly selected. Do not silently replace the existing CIELAB/LCH gamut mapper.

### 8. Harmony Integration

Review `color_tools/harmony.py` after core support is complete. Existing harmony
generation must continue to use CIE LCH unless an explicit Oklab/OkLCh mode is added.

If an OkLCh mode is included:

- Keep the existing mode backward compatible.
- Use OkLCh-appropriate lightness and chroma ranges.
- Use the new OkLCh gamut mapper.
- Define achromatic behavior using the OkLCh epsilon rather than the CIE LCH
  threshold.

### 9. MCP Integration

Update:

- `color_tools/mcp/models.py`
- `color_tools/mcp/server.py`
- `color_tools/mcp/README.md`

Requirements:

- Extend the closed `ColorSpace` type with `oklab` and `oklch`.
- Extend coordinate and conversion outputs with typed Oklab and OkLCh values.
- Add `delta_e_ok` to the supported distance metrics and comparison output.
- Preserve array-free tool input schemas; continue using scalar components.
- Keep structured outputs typed and backward compatible where practical.
- Test both in-memory client transport and spawned stdio transport.

### 10. Exporters

Review universal CSV and JSON exporters. Add Oklab/OkLCh columns only when the
exporter's compatibility contract permits additive fields and tests confirm stable
ordering. Format-specific palette exporters should remain unchanged unless their
formats explicitly support these spaces.

Do not alter persisted source data merely to expose derived export fields.

## Test Plan

Create `tests/test_oklab.py` for core math and add focused integration tests to the
existing CLI, palette, filament, gamut, and MCP test modules.

### Reference and Conversion Tests

- Verify high-precision W3C or Ottosson reference vectors for black, white, primaries,
  secondaries, neutrals, and representative mixed colors.
- Verify RGB to Oklab to RGB round trips within one integer channel after final public
  rounding.
- Verify Oklab to OkLCh to Oklab round trips at floating-point tolerance.
- Verify the signed cube root with negative LMS components.
- Verify extended-sRGB values survive intermediate conversion without clipping.
- Verify neutral OkLCh hue becomes `math.nan` at the specified epsilon.
- Verify `math.nan` hue converts back to an achromatic Oklab value.
- Verify hue normalization around `0` and `360` degrees.
- Verify invalid tuples, non-finite values, and negative chroma follow existing error
  conventions.

Use more precision than three-decimal examples when testing matrix correctness. Avoid
asserting values copied from rounded prose examples as exact ground truth.

### Distance Tests

- Identity, symmetry, and non-negativity for `delta_e_ok`.
- Published or independently calculated reference pairs.
- A known `0.02` distance-scale example.
- Cartesian and cylindrical-equivalent calculations agree.
- Existing CIELAB metrics remain unchanged.

### Gamut Tests

- Clearly in-gamut and out-of-gamut Oklab/OkLCh colors.
- Values only slightly outside sRGB, ensuring rounding cannot hide the violation.
- Mapping preserves lightness and hue within tolerance while reducing chroma.
- Mapping returns an in-gamut result.
- Black, white, neutral, and extreme-lightness behavior.

### Integration Tests

- Every CLI source/target combination involving Oklab or OkLCh.
- CLI text and JSON output.
- Interactive wizard choices and validation.
- Named-color and filament matching with `delta_e_ok`.
- MCP structured models, in-memory transport, and stdio transport.
- Public imports from `color_tools`.
- Existing data files load unchanged.

## Documentation

Update after behavior and names are finalized:

- `README.md`
- `docs/API.md`
- `docs/Usage.md`
- `docs/QUICK_REFERENCE.md`
- relevant module documentation
- `color_tools/mcp/README.md`
- `CHANGELOG.md` under `Unreleased`

Document the `0.0` to `1.0` lightness scale, `math.nan` neutral hue, Delta E OK scale,
gamut behavior, and the difference between Oklab and CIELAB metrics.

Examples must be generated from the finished implementation rather than copied from
this plan.

## Integrity and Validation

If uppercase constants are added, regenerate and update the constants hash:

```powershell
& '.\.venv\Scripts\python.exe' -c "from color_tools.constants import ColorConstants; print(ColorConstants._compute_hash())"
```

Core data files should not change under this plan. If a later approved change modifies
protected data, use the repository tool so CRLF normalization matches runtime checks:

```powershell
& '.\.venv\Scripts\python.exe' tooling/update_hashes.py --autoupdate
```

Final validation must include:

```powershell
& '.\.venv\Scripts\python.exe' -m unittest discover tests
& '.\.venv\Scripts\python.exe' -m color_tools --verify-all
```

Also run Pyright/Pylance diagnostics and verify the CLI, library import, interactive
wizard, and MCP transports.

## Implementation Sequence

### Phase 1: Core Math

- [ ] Add high-precision matrices and signed cube-root support.
- [ ] Add float-preserving extended-sRGB helpers.
- [ ] Implement Oklab and OkLCh conversions.
- [ ] Implement `delta_e_ok`.
- [ ] Add core reference, edge-case, and round-trip tests.
- [ ] Regenerate and verify the constants hash.
- [ ] Export the new public API.

### Phase 2: Conversion and Gamut Integration

- [ ] Extend centralized conversion routing without RGB quantization.
- [ ] Add Oklab/OkLCh sRGB gamut checking.
- [ ] Add constant-hue OkLCh chroma-reduction mapping.
- [ ] Add focused gamut and cross-space tests.

### Phase 3: User Interfaces and Matching

- [ ] Add CLI conversion and metric choices.
- [ ] Add interactive wizard definitions.
- [ ] Add named-color and filament matching support.
- [ ] Extend MCP models, tools, and both transport test paths.
- [ ] Review optional exporter and harmony integration.

### Phase 4: Documentation and Release Preparation

- [ ] Update user and API documentation.
- [ ] Add the feature to `CHANGELOG.md` under `Unreleased`.
- [ ] Run the full test suite and integrity verification.
- [ ] Resolve all Pyright/Pylance diagnostics.
- [ ] Decide the semantic version only after final scope is known.

## Acceptance Criteria

- Reference conversions agree with current W3C/Ottosson values at documented
  tolerances.
- Intermediate conversions preserve extended and floating-point values.
- `delta_e_ok` implements raw Oklab Euclidean distance and uses the `0.0` to `1.0`
  lightness scale.
- Existing CIELAB metrics and defaults are unchanged.
- Existing core and user JSON files load without migration.
- CLI, wizard, palette, filament, and MCP integrations are tested.
- Oklab/OkLCh gamut checks do not depend on rounded integer RGB.
- Constants and data integrity verification pass.
- The full test suite and type checking pass with no new errors.

## References

- [Bjorn Ottosson: A perceptual color space for image processing](https://bottosson.github.io/posts/oklab/)
- [CSS Color Module Level 4: Oklab and OkLCh](https://www.w3.org/TR/css-color-4/#ok-lab)
- [CSS Color Module Level 4: Sample conversion code](https://www.w3.org/TR/css-color-4/#color-conversion-code)
- [CSS Color Module Level 4: Delta E OK](https://www.w3.org/TR/css-color-4/#color-difference-OK)
- [CSS Color Module Level 4: Gamut mapping](https://www.w3.org/TR/css-color-4/#gamut-mapping)

## Resolved Decisions

1. Use native Oklab lightness in the `0.0` to `1.0` range.
2. Use `delta_e_ok` as the initial Oklab distance metric.
3. Keep CIELAB-specific Delta E formulas restricted to CIELAB.
4. Derive Oklab and OkLCh from RGB instead of changing JSON schemas.
5. Preserve floating-point and extended-sRGB values internally.
6. Represent powerless converted OkLCh hue as `math.nan`.
7. Keep existing matching, harmony, and gamut defaults backward compatible.

## Remaining Scope Decisions

1. Include Delta E OK2 and Delta E OKr2 now, or defer them to a later feature.
2. Include an explicit OkLCh harmony mode in the initial release, or only prepare the
   integration boundary.
3. Add derived Oklab/OkLCh columns to universal CSV and JSON exports, or leave
   exporters unchanged initially.
4. Implement basic binary chroma reduction only, or include CSS local-MINDE in the
   initial gamut work.
