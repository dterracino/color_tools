# TMS9918 System Palette Source and Representation

This document records why four built-in system palettes share one RGB table and
what those RGB values represent.

## User-facing system palettes

The following palette files intentionally contain the same 15 colors:

- `ti-99-4a`
- `colecovision`
- `sg-1000`
- `msx1`

Users normally select a palette by the system they want to evoke, not by the
video-display processor inside that system. Separate files make those systems
independently discoverable and leave room for a future system-specific change
without renaming another public palette.

## Representation boundary

The TMS9918 family defines color output through luminance and color-difference
levels rather than modern sRGB values. The values below reconstruct RGB from
the Texas Instruments output levels and apply a gamma 1.6 CRT-style transform.
They are intended to give image conversion a recognizable, saturated period
look on a modern display.

These files are not claims of electrically exact output from every console,
television standard, RF modulator, CRT, capture device, or emulator. Their
purpose is consistent image stylization using a documented representation.

## Shared color table

The order follows hardware color codes 1 through 15.

| Code | Name | Hex |
| ---: | --- | --- |
| 1 | Black | `#000000` |
| 2 | Medium green | `#0AAD1E` |
| 3 | Light green | `#34C84C` |
| 4 | Dark blue | `#2B2DE3` |
| 5 | Light blue | `#514BFB` |
| 6 | Dark red | `#BD2925` |
| 7 | Cyan | `#1EE2EF` |
| 8 | Medium red | `#FB2C2B` |
| 9 | Light red | `#FF5F4C` |
| 10 | Dark yellow | `#BDA22B` |
| 11 | Light yellow | `#D7B454` |
| 12 | Dark green | `#0A8C18` |
| 13 | Magenta | `#AF329A` |
| 14 | Gray | `#B2B2B2` |
| 15 | White | `#FFFFFF` |

Hardware color code 0 is omitted. It represents transparency or backdrop
behavior depending on where it is used; it is not a separate visible RGB color
that an image quantizer can select.

## Source and reproduction

The primary hardware source is the
[Texas Instruments TMS9918A, TMS9928A, and TMS9929A Video Display Processors Data Manual](https://www.bitsavers.org/components/ti/TMS9900/TMS9918A_TMS9928A_TMS9929A_Video_Display_Processors_Data_Manual_Nov82.pdf),
particularly Table 2-3, Color Assignments.

The shared source table is stored once as `_TMS9918_CRT` in
`tooling/generate_additional_retro_palettes.py`. The generator writes four
system-named JSON files and derives their hex, HSL, LAB, and LCH fields through
the production Color Tools conversions.

MSX2 is intentionally excluded from this shared table. Its V9938 video
processor provides programmable 9-bit RGB colors and requires a separate source
table and representation decision.

Protected file hashes and final palette counts are updated only after the
complete release palette batch has been finalized.
