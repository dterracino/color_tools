# Future Palette Schema and Rendering Profile Design

## Status

- Created: 2026-10-13.
- Status: design direction and discussion record; richer profile elements are
  not yet approved for implementation.
- Near-term objective: migrate the existing bundled indexed palettes to a
  stable, versioned document envelope during the 7.0.0 breaking release.
- Future objective: support palette references, generated bit-depth color
  domains, display profiles, color-processing styles, and renderer
  postprocessing without another root-level file-format change.

The example files currently under `color_tools/data/palettes/new/` are design
experiments. Their differences are intentional explorations, not competing
formats that must remain compatible. This document captures the common model
to refine before those future elements are implemented.

## Why introduce the envelope now

The current bundled palette files are arrays of color records at the JSON root.
That representation is sufficient for explicit indexed palettes, but it has no
place for palette identity, generated color domains, shared palette references,
display geometry, color-processing constraints, or renderer effects.

The 7.0.0 release is an appropriate point to make the one required root-level
breaking change. Existing colors can be nested under a palette definition now,
while optional capabilities can be added later without restructuring every
file again.

The public `load_palette()` behavior should remain focused on returning a
usable palette. The bundled package-data format may change even when the normal
library API remains source compatible. Direct consumers of bundled JSON files
must be treated as affected by the 7.0.0 schema change.

## Proposed near-term indexed schema

Use `schema_version`, not `format_version`, to identify the document schema.
The initial value should be the integer `1` rather than a semantic-version
string. Optional additions do not require a new schema version; incompatible
changes do.

```json
{
  "schema_version": 1,
  "metadata": {
    "id": "vic-20",
    "name": "Commodore VIC-20",
    "description": "An 8-bit home computer released by Commodore.",
    "release_year": 1980
  },
  "palette": {
    "type": "indexed",
    "colors": [
      {
        "name": "black",
        "hex": "#000000",
        "rgb": [0, 0, 0],
        "hsl": [0.0, 0.0, 0.0],
        "lab": [0.0, 0.0, 0.0],
        "lch": [0.0, 0.0, 0.0]
      }
    ]
  }
}
```

The near-term migration should introduce only the stable envelope needed by
the current files:

- `schema_version`
- `metadata`
- `palette.type` with the value `indexed`
- `palette.colors` containing the existing ordered color records

The richer sections described below should not be populated across the current
files until their contracts have been reviewed and approved.

## Document responsibilities

The eventual document represents a selectable system style or rendering
profile containing a palette component. A simple artistic palette may contain
only metadata and a palette definition. A system profile may additionally
describe display geometry, color-processing behavior, and postprocessing.

The major sections have distinct responsibilities:

1. `metadata` identifies and describes the definition.
2. `palette` defines the available color domain.
3. `color_style` controls mapping into that domain.
4. `display_profile` controls logical geometry and presentation scaling.
5. `postprocess` describes optional display-simulation effects.

These responsibilities should remain separate even when one renderer consumes
all of them.

## Metadata

Metadata should describe the definition rather than encode rendering behavior.
Initial fields include:

- `id`: stable machine-readable identity
- `name`: human-readable name
- `description`: concise description of the represented system or subject, not
  its rendering characteristics
- `release_year`: optional historical year
- future source, attribution, or descriptive tags if a concrete need arises

Rendering characteristics such as master-palette size, simultaneous-color
limits, resolution, and display behavior should use future structured fields
with defined semantics. The shared presentation-style purpose of the bundled
system palettes belongs in library documentation rather than repeated metadata
in every file. A generic `notes` field is not part of the initial schema and
can be added later if a concrete need remains after the structured fields are
designed.

The canonical relationship among file stem, metadata ID, and reference name
must be decided. Initially keeping the metadata ID equal to the file stem is
simple and avoids ambiguous lookup behavior.

The existing exporter-oriented `PaletteMetadata` model should not
automatically become this document metadata model. Export metadata currently
serves interchange formats and includes concerns such as author, column count,
and tags. System identity and rendering-profile information have a different
ownership boundary.

## Palette definition variants

`palette` should be a discriminated object. The `type` field determines which
other fields are valid. Each field should retain one JSON type rather than
changing meaning between variants.

### Indexed palette

An indexed palette stores an explicit ordered array of color records.

```json
{
  "palette": {
    "type": "indexed",
    "colors": []
  }
}
```

For this variant, `colors` must always be an array. `color_count` should not be
stored because it is derived from the array length and could drift out of sync.
Likewise, `master_palette_size` should be omitted unless a future contract
defines a meaningful distinction between the stored entries and a larger
hardware color domain.

### Referenced palette

Reference palettes are a future revision and are deliberately excluded from
the initial schema implementation. The first migration will keep colors
materialized in each indexed system palette, including the separate TI-99/4A,
ColecoVision, SG-1000, and MSX1 files that currently share TMS9918-derived
colors. It will not add a shared `tms9918.json` definition.

Deferring references keeps the initial loader focused on one palette variant
and avoids prematurely defining reference lookup, identity, error handling,
cycle detection, hash ownership, packaging behavior, and interactions with
custom or user palettes. The duplication is small and intentional until those
contracts are designed.

A reference profile obtains its color domain from another named palette while
providing its own display and processing rules.

```json
{
  "palette": {
    "type": "reference",
    "reference": "ega16"
  }
}
```

This is appropriate for Sierra AGI. AGI is primarily a presentation style: it
uses EGA16 colors but supplies its own working resolution, horizontal pixel
expansion, dithering defaults, and optional display effects.

The reference field should use the same stable name accepted by palette
loading, such as `ega16` or an explicitly supported user-palette name. It
should not overload `colors` with a string value.

Reference semantics should be narrow:

> A palette reference imports only the referenced palette definition. It does
> not inherit the target document's metadata, display profile, color style, or
> postprocessing.

A reference may ultimately resolve to an indexed or generated palette. The
resolver must reject missing targets and cycles. Whether multi-level reference
chains should be permitted remains an implementation decision; cycle detection
is required if they are.

### Generated bit-depth palette

A bit-depth definition describes a color domain mathematically instead of
listing every value. This allows systems with thousands of possible colors to
remain compact.

```json
{
  "palette": {
    "type": "bit_depth",
    "channels": {
      "red": 5,
      "green": 6,
      "blue": 5
    },
    "encoding": "unorm"
  }
}
```

Named channel fields are clearer than an array whose RGB ordering must be
remembered. The total bit depth and possible color count are derived from the
channel widths and should not need duplicate stored values.

The contract still needs to define:

- supported channel names and ordering
- whether alpha can be represented
- encoded versus linear-light channel interpretation
- how reduced-bit channel values expand to 8-bit or floating-point RGB
- whether nonuniform or lookup-based channel encodings are needed
- how generated colors receive names, if names are needed at all

SNES-style 5:5:5 and RGB 5:6:5 are related examples but should not be assumed
to have identical output or display-transfer semantics merely because both can
be represented by channel widths.

## Runtime representation of generated palettes

The current `Palette` model materializes every `ColorRecord`, creates several
indexes, and performs nearest-color searches across the record list. That is
appropriate for small and medium indexed palettes.

It is not necessarily appropriate for generated color domains. A 5:6:5 domain
contains 65,536 colors; eagerly creating and indexing 65,536 full records would
consume unnecessary memory, and a linear nearest-color search would ignore the
simple mathematical quantization available from the channel definition.

Future implementation should therefore consider a separate implicit or
generated-palette runtime model that:

- quantizes channels mathematically
- creates records only when a result must be returned
- exposes useful palette-size information without enumeration
- avoids pretending that every generated color has an authored name
- presents a compatible consumer-facing operation where practical

The bundled file schema can support `bit_depth` before the exact runtime class
hierarchy is chosen, but the loader must reject unsupported types clearly until
their behavior is implemented.

## Display profile

`display_profile` describes logical image geometry and how logical pixels are
presented. Potential fields include:

- working or logical resolution
- display or output resolution
- intended display aspect ratio
- pixel aspect ratio
- explicit pixel expansion
- scaling or resampling defaults
- region or video-standard variants when PAL and NTSC differ

These fields need precise definitions. Many systems support multiple video
modes and resolutions, so a single value cannot always be described as the
system's universal native resolution. Application preferences such as a
default window-fitting policy should be distinguished from hardware or content
geometry.

`display_profile` is optional. A general-purpose palette such as an artistic
palette or web-safe colors should not require invented display information.

## Color style

`color_style` describes how source colors are prepared and mapped into the
palette domain. Potential responsibilities include:

- simultaneous-color restrictions
- palette-selection restrictions
- dithering method and strength
- contrast or saturation adjustments
- transfer-function or gamma interpretation
- system-specific tile, sprite, layer, or scanline color rules

Simple values such as `simultaneous_color_limit` may be inadequate for hardware
whose limits operate per tile, sprite, layer, scanline, or palette bank. The
schema should not flatten those constraints prematurely.

Color-style values should normally be renderer defaults that a caller may
override, not immutable claims that every image must use the same dithering or
adjustment strength.

## Postprocessing

`postprocess` describes optional effects applied after the logical image has
been palette-mapped and presented at its intended pixel geometry. Potential
effects include:

- scanlines
- CRT softness
- phosphor masks
- bloom
- composite-video artifacts
- display persistence or ghosting

An ordered `effects` array is useful because effect order can change the
result. Each effect should use a discriminating `type` and validate only the
parameters defined for that type.

These are simulation choices, not intrinsic RGB palette values. They should be
optional and overridable by the renderer.

## Rendering pipeline semantics

The schema must define when each section applies. The proposed conceptual
pipeline is:

```text
source image
-> logical resolution and layout
-> color-style processing and palette mapping
-> pixel expansion, aspect correction, and scaling
-> ordered postprocessing effects
-> final image
```

This order prevents ambiguity. Dithering generally operates before logical
pixels are expanded, while scanlines and CRT softness generally operate after
the logical image has been scaled for presentation.

The exact placement of contrast, saturation, transfer functions, and
system-specific restrictions remains to be standardized.

## Example reference-based AGI profile

The following example illustrates the intended separation. It is not yet a
final approved schema for every nested field.

```json
{
  "schema_version": 1,
  "metadata": {
    "id": "sierra-agi",
    "name": "Sierra AGI",
    "description": "Low-resolution Sierra AGI presentation style."
  },
  "palette": {
    "type": "reference",
    "reference": "ega16"
  },
  "display_profile": {
    "working_resolution": [160, 200],
    "display_resolution": [320, 200],
    "display_aspect_ratio": [4, 3],
    "pixel_expansion": [2, 1],
    "scale_filter": "nearest"
  },
  "color_style": {
    "simultaneous_color_limit": 16,
    "dither": {
      "method": "ordered_bayer",
      "strength": 0.35
    }
  },
  "postprocess": {
    "effects": [
      {
        "type": "scanlines",
        "strength": 0.18
      },
      {
        "type": "crt_softness",
        "strength": 0.12
      }
    ]
  }
}
```

## Compatibility and migration boundaries

The near-term indexed-envelope migration affects more than `load_palette()`.
Before implementation is considered complete, audit and update:

- the bundled palette loader and its structural validation
- CLI palette discovery and color counts
- all built-in palette generators
- maintenance scripts that iterate root-level arrays
- tests that directly inspect palette JSON
- documentation for built-in and user palette files
- package-data and installed-wheel checks
- data-integrity registrations and hashes

The generic JSON exporter is an interchange format and does not have to become
identical to the bundled authoritative palette-document schema.

The lightweight user-palette format may remain a root array of `name` and
`hex` records for compatibility. Bundled palette definitions and simple user
palettes already have different validation and storage requirements. Whether
users should also be allowed to author the richer versioned document is a
separate public-contract decision.

Loaders should reject unknown required structures and unsupported palette
types with specific errors. They should tolerate future optional top-level
sections when those sections are irrelevant to the requested operation.

## Proposed implementation sequence

### Current 7.0.0 work

1. Approve the minimal indexed document envelope.
2. Add focused typed parsing for `schema_version`, `metadata`, and the indexed
   palette definition.
3. Preserve the existing public result of `load_palette()`.
4. Support only materialized `indexed` palette definitions in this revision;
   do not implement reference resolution or add `tms9918.json`.
5. Decide whether legacy root arrays remain accepted for bundled/custom core
   paths, user palettes, or both.
6. Update every bundled palette generator to emit the new envelope.
7. Migrate every current bundled indexed palette consistently.
8. Update direct JSON consumers, tests, documentation, and hashes.
9. Validate source-tree and installed-wheel behavior.

### Future revision discussion

1. Finalize stable metadata identity and reference resolution.
2. Finalize the `reference` palette contract.
3. Finalize bit-depth channel encoding and runtime quantization.
4. Standardize display-profile terminology and mode/region handling.
5. Standardize color-style constraints and stage ordering.
6. Define the postprocess effect registry and override behavior.
7. Decide whether a public `PaletteProfile` or `RenderProfile` model should
   accompany the existing materialized `Palette` class.
8. Implement a renderer only after the schema and processing contracts are
   approved.

## Open decisions

- Is `metadata.id` required, and must it match the filename?
- Do references resolve by file stem, metadata ID, or a namespaced identifier?
- Are user-palette references supported?
- Are reference chains allowed?
- Which metadata fields are required versus optional?
- How are multiple hardware video modes represented?
- How are PAL, NTSC, and regional variants represented?
- Which display fields describe hardware, and which describe renderer policy?
- What is the exact order of color adjustments, dithering, restriction, and
  quantization?
- How should complex per-tile, per-layer, per-sprite, or per-scanline color
  limits be expressed?
- Which postprocess effects are standardized, and can external renderers ignore
  unsupported optional effects?
- How are bit-depth values expanded and interpreted with respect to transfer
  functions?
- Should generated palettes share the `Palette` API or use a distinct runtime
  abstraction?
- Should richer versioned documents be supported for user-authored palettes?

Until these decisions are approved, the experimental files remain references
for discussion rather than authoritative schemas.
