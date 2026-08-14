# Future Feature Concept: Algorithmic UI Theme Generator

## Overview

A future extension to `color_tools` could generate a complete semantic UI theme from a single user-supplied base color.

The goal is not simply to create a traditional harmony palette. Instead, the base color would seed an algorithm that derives a coherent set of colors for real interface roles such as backgrounds, surfaces, text, borders, controls, selections, status colors, and interaction states.

The generated theme would use the existing palette model and could then be exported through any compatible exporter.

```text
Base color
    ↓
Harmony generation
    ↓
Theme recipe evaluation
    ↓
Semantic UI color tokens
    ↓
PaletteExportData
    ↓
Python / CSS / SCSS / JSON / Tailwind / Swatch Image / etc.
```

## Declarative Theme Recipes

Each UI role would be defined by a repeatable formula or transformation chain rather than by hard-coded color values.

Conceptually:

```text
background =
    base
    → tetradic[3]
    → reduce_chroma
    → darken

surface =
    background
    → lighten

primary =
    base

primary_hover =
    primary
    → lighten

primary_active =
    primary
    → darken

accent =
    base
    → split_complementary[1]

text_primary =
    background
    → contrasting_foreground
```

The exact syntax is intentionally deferred. The important idea is that each semantic color derives from the base color, a harmony color, or another semantic token.

This makes the theme algorithm inspectable, testable, tunable, and potentially serializable.

## Theme Recipes as Data

Theme definitions should ideally behave like data rather than being permanently embedded in procedural code.

That would allow multiple theme families to use the same evaluation engine:

```text
dark_ui
light_ui
muted_ui
pastel_ui
warm_ui
cool_ui
high_contrast_ui
```

A future implementation could also allow custom user-defined recipes.

The conceptual separation is:

```text
Color operations
      ↓
Harmony generation
      ↓
Theme recipe
      ↓
Theme evaluation
      ↓
PaletteExportData
```

Exporting remains a separate concern.

## Dependency Graph

Not every UI role should derive independently from the base color. Many should derive from other semantic roles.

```text
base
 │
 ├── primary
 │    ├── primary_hover
 │    ├── primary_active
 │    ├── primary_disabled
 │    └── primary_subtle
 │
 ├── harmony branch
 │    ├── secondary
 │    └── accent
 │
 └── neutralized harmony branch
      └── background
           ├── surface
           │    ├── surface_alt
           │    └── surface_elevated
           ├── border
           └── text hierarchy
```

This keeps related states coherent. For example, `primary_hover` should clearly relate to `primary`, rather than being independently generated from the seed.

## Perceptual Color Operations

UI theme generation should prefer perceptual color operations over naïve RGB arithmetic.

Useful conceptual operations include:

```text
shift_lightness(...)
shift_chroma(...)
rotate_hue(...)
desaturate(...)
ensure_contrast(...)
contrast_foreground(...)
```

LAB/LCh-based manipulation is a natural fit because `color_tools` already works with perceptual color spaces.

## Harmony Generation

Color harmonies provide candidate hues for major theme roles.

Potential harmony families include:

```text
analogous
complementary
split-complementary
triadic
tetradic
```

A likely general model is:

```text
primary   ← base
secondary ← analogous or tetradic branch
accent    ← complementary or split-complementary branch
```

Harmony generation should guide the theme, but it should not dictate every color.

## Semantic Colors

Status colors such as success, warning, error, and information have established visual meaning.

A mathematically valid harmony can still produce a poor semantic result. For that reason, semantic colors should be influenced by the theme while remaining constrained to recognizable hue families.

Suggested roles:

```text
success
warning
error
info
```

Each could also produce:

```text
<status>_surface
<status>_text
```

For example:

```text
error
error_surface
error_text
```

## Contrast Validation

A harmonious palette is not automatically a usable interface palette.

Important foreground/background relationships should be checked and adjusted as part of theme evaluation.

Examples:

```text
text_primary      against background
text_primary      against surface
text_on_primary   against primary
selection_text    against selection
error_text        against error_surface
tooltip_text      against tooltip_background
```

Contrast correction belongs in theme generation, not in the exporter.

# Semantic UI Token Inventory

The C# `KnownColor` system-color list is useful as a reference inventory, but much of its vocabulary reflects older desktop/windowing APIs. A modern generator should cover the same concepts through reusable semantic tokens.

## Core Surfaces

```text
background
surface
surface_alt
surface_elevated
surface_sunken
overlay
```

Specialized surfaces may derive from these:

```text
menu_background
tooltip_background
dialog_background
input_background
```

## Text

```text
text_primary
text_secondary
text_muted
text_disabled
text_inverse

text_on_primary
text_on_secondary
text_on_accent
```

These generalize older concepts such as WindowText, ControlText, MenuText, GrayText, HighlightText, and caption text.

## Borders and Separators

```text
border
border_subtle
border_strong
border_focus
border_disabled
separator
```

These cover the conceptual space represented by ActiveBorder, InactiveBorder, WindowFrame, and older 3-D control highlight/shadow colors.

## Primary Interaction

```text
primary
primary_hover
primary_active
primary_disabled
primary_subtle
text_on_primary
```

The base color would normally become `primary`.

## Secondary Interaction

```text
secondary
secondary_hover
secondary_active
text_on_secondary
```

The secondary color would generally come from a harmony branch.

## Accent

```text
accent
accent_hover
accent_active
text_on_accent
```

Accent should normally provide stronger visual separation from the primary than the secondary does.

## Selection, Hover, and Focus

```text
selection
selection_text
hover
focus
focus_ring
```

These modernize concepts such as Highlight, HighlightText, and HotTrack.

## Controls and Inputs

General controls:

```text
control
control_hover
control_active
control_disabled
```

Inputs:

```text
input_background
input_border
input_border_focus
input_text
input_placeholder
```

Specific widgets such as checkboxes, radio buttons, and toggles may not need unique colors. They can consume these semantic tokens.

A core design principle is:

> Generate reusable design tokens, not a separate arbitrary color for every widget.

## Semantic Status Colors

```text
success
success_surface
success_text

warning
warning_surface
warning_text

error
error_surface
error_text

info
info_surface
info_text
```

## Scrollbars

```text
scrollbar_track
scrollbar_thumb
scrollbar_thumb_hover
scrollbar_thumb_active
```

## Window Chrome

For desktop-oriented applications:

```text
titlebar
titlebar_text
titlebar_inactive
titlebar_inactive_text
window_border
```

These cover the concepts represented by ActiveCaption, ActiveCaptionText, InactiveCaption, InactiveCaptionText, ActiveBorder, and InactiveBorder.

# Primitive vs. Derived Tokens

A major design goal should be to avoid independently generating every semantic token.

A possible primitive set:

```text
background
surface
surface_alt

primary
secondary
accent

text_primary
text_secondary
text_muted

border

success
warning
error
info
```

Other tokens can then be derived or aliased:

```text
menu_background      = surface_elevated
tooltip_background   = surface_elevated
dialog_background    = surface_elevated

input_background     = surface
window_border        = border

scrollbar_track      = surface_sunken
scrollbar_thumb      = border_strong

selection            = primary_subtle
focus_ring           = primary
```

This reduces arbitrary color generation and makes themes more internally consistent.

# Light and Dark Theme Modes

Theme mode should be an explicit generation input:

```text
light
dark
```

The same seed color should produce very different neutral and surface ramps depending on mode.

Primary, secondary, and accent hues can remain related across modes while their lightness and chroma are adjusted for usability.

# Potential Future API Shape

The exact API is intentionally deferred, but conceptually:

```text
theme = generate_ui_theme(
    base_color,
    theme_recipe,
    mode,
)
```

The result should be ordinary:

```text
PaletteExportData
```

Each generated `ColorRecord.name` would contain the semantic token name.

Example:

```text
background
surface
surface_alt
primary
primary_hover
primary_active
secondary
accent
text_primary
text_secondary
text_muted
border
success
warning
error
info
```

# Export Possibilities

Once generated as `PaletteExportData`, the same theme could be exported to:

```text
Python source
CSS variables
SCSS variables/maps
JSON
Tailwind configuration
JavaScript / TypeScript
Swatch image
ASE
GPL
GLSL
```

This is one of the main benefits of keeping theme generation independent from serialization.

# Design Principles

1. Semantic roles rather than arbitrary harmony positions.
2. Recipes rather than hard-coded values.
3. Dependencies between related tokens.
4. Perceptual color manipulation.
5. Harmony as guidance, not absolute law.
6. Contrast as part of generation.
7. Semantic status colors retain recognizable meaning.
8. Reusable design tokens rather than one color per widget.
9. Theme generation remains separate from exporting.
10. Theme recipes should eventually be extensible.

# Open Questions

Before implementation, the following should be finalized:

- Final semantic UI token inventory.
- Primitive versus derived tokens.
- Exact dependency graph.
- Default harmony strategy for each recipe.
- Perceptual color space used for transformations.
- Contrast targets and correction algorithm.
- Rules for semantic status hue constraints.
- Light/dark surface-ramp generation.
- Whether recipes are Python objects, declarative data, or both.
- Whether aliases remain separate palette entries or are resolved before export.
- Representation of custom user-defined recipes.
- Additional theme modes such as muted, pastel, warm, cool, and high contrast.

# Summary

The proposed UI theme generator would transform a single base color into a coherent semantic interface palette.

Its defining feature would be a declarative theme-recipe system where colors are derived through harmony selection, perceptual transformations, semantic dependencies, and contrast constraints.

The output remains ordinary `PaletteExportData`, allowing the theme generator to immediately benefit from the full importer/exporter ecosystem.

This would make a natural future extension to `color_tools`: the library would not only analyze and convert palettes, but also algorithmically construct reusable design systems from a single seed color.
