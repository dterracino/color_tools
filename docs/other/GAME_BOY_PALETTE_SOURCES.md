# Game Boy Palette Sources and Representation Decisions

This document records the origin and intended meaning of the built-in Game Boy
palettes. It exists because monochrome Game Boy hardware does not define an RGB
palette that can be copied directly into a modern image.

## Hardware color model

The original Game Boy family stores two bits per pixel. Palette registers map
those values to four ordered LCD intensities. Nintendo's programming manual
describes those four grayscale outputs, but it does not assign sRGB values to
them. The visible color comes from the physical LCD, its contrast setting,
lighting, viewing angle, and the console model.

Consequently, the RGB values below are documented modern representations. They
must not be described as official Nintendo RGB palettes.

## Current built-in palettes

Every palette is stored from darkest to lightest.

### `gameboy`

This is the fixed authoring palette used by GB Studio for monochrome artwork.
It is retained under the short, established name because it is useful for asset
creation and was already part of the public Color Tools palette set.

| Shade | Hex |
| --- | --- |
| Darkest | `#071821` |
| Dark | `#306850` |
| Light | `#86C06C` |
| Lightest | `#E0F8CF` |

Source: [GB Studio palette documentation](https://www.gbstudio.dev/docs/assets/palettes/)

### `gameboy-dmg`

This uses the first four entries of SameBoy's `GB_PALETTE_DMG` table to
approximate the original DMG-01 LCD. SameBoy's fifth entry represents the LCD
when it is off, not an addressable pixel intensity, so it is omitted.

| Shade | Hex |
| --- | --- |
| Darkest | `#081810` |
| Dark | `#396139` |
| Light | `#84A563` |
| Lightest | `#C6DE8C` |

### `gameboy-pocket`

This is an intentionally neutral representation of the Game Boy Pocket's four
monochrome intensities. It uses evenly spaced sRGB values and matches SameBoy's
`GB_PALETTE_GREY` table. It represents grayscale data cleanly rather than
attempting to reproduce a particular Pocket LCD under particular lighting.

| Shade | Hex |
| --- | --- |
| Darkest | `#000000` |
| Dark | `#555555` |
| Light | `#AAAAAA` |
| Lightest | `#FFFFFF` |

### `gameboy-light`

This uses the first four entries of SameBoy's `GB_PALETTE_GBL` table to
approximate the Game Boy Light with its backlight enabled. Its separate LCD-off
entry is omitted.

| Shade | Hex |
| --- | --- |
| Darkest | `#0A1C15` |
| Dark | `#357862` |
| Light | `#56B495` |
| Lightest | `#7FE2C3` |

Source for the DMG, neutral-gray, and Light tables:
[SameBoy `Core/display.c`](https://github.com/LIJI32/SameBoy/blob/master/Core/display.c)

## Retired palette files

The repository previously contained four additional names whose origins were
not recorded when they were added:

- `gameboy_dmg` used `#294139`, `#39594A`, `#5A7942`, and `#7B8210`.
- `gameboy_gbl` used `#004F3A`, `#00694A`, `#009A70`, and `#00B582`.
- `gameboy_mgb` used `#181818`, `#4A5138`, `#8C926B`, and `#C5CAA4`.
- `gameboy-color` combined 14 colors from an unattributed local JSON array.

Git history shows that the three underscore-named model palettes were added
together in commit `0ae285a` on November 29, 2025. The commit did not identify a
source. Their exact values can be found in later community palette collections,
but that does not establish where this repository obtained them.

The 14-color `gameboy-color` file was generated from
`.source_data/gameboy-color-retro-palette.json` in commit `ca37824` on December
24, 2025. Neither the source array nor the commit records its origin. It was not
a Game Boy Color hardware palette: Game Boy Color software selects colors from
a 32,768-color, 15-bit RGB space rather than using one fixed 14-color set.

These four files were retired for the 7.0.0 breaking release. The three model
names were replaced by descriptive hyphenated names with explicit sources, and
the unsupported 14-color collection was removed rather than relabeled without
provenance.

## Reproduction

The RGB source tables are explicit in
`tooling/generate_additional_retro_palettes.py`. The generator derives hex, HSL,
LAB, and LCH values with the production Color Tools conversions. Protected file
hashes are intentionally updated only after the complete release palette batch
has been finalized.

## Primary technical reference

- [Game Boy Programming Manual](https://files.nekoblog.org/uploads/pdf/39999184-GameBoy-Programming-Manual.pdf)
  documents the DMG/MGB grayscale palette registers and the separate 15-bit
  color system used by Game Boy Color.
