# Intellivision Palette Source and Representation

This document records the source, ordering, and intended meaning of the
built-in `intellivision` palette.

## Hardware color model

The Intellivision uses the General Instrument AY-3-8900 Standard Television
Interface Chip, commonly called the STIC. It provides a fixed 16-color palette
through analog television output rather than modern digital RGB.

The RGB values selected here are a vivid CRT-style representation intended for
image conversion. They are not presented as exact output from every console,
television standard, RF modulator, CRT, capture device, or emulator.

## Color order

The records follow STIC hardware color codes 0 through 15:

| Code | Name | Hex |
| ---: | --- | --- |
| 0 | Black | `#0C0005` |
| 1 | Blue | `#002DFF` |
| 2 | Red | `#FF3E00` |
| 3 | Tan | `#C9D464` |
| 4 | Dark green | `#00780F` |
| 5 | Green | `#00A720` |
| 6 | Yellow | `#FAEA27` |
| 7 | White | `#FFFCFF` |
| 8 | Gray | `#A7A8A8` |
| 9 | Cyan | `#5ACBFF` |
| 10 | Orange | `#FFA600` |
| 11 | Brown | `#3C5800` |
| 12 | Magenta | `#FF3276` |
| 13 | Light blue | `#BD95FF` |
| 14 | Yellow-green | `#6CCD30` |
| 15 | Purple | `#C81A7D` |

The selected RGB set appears as the Intellivision preset in the
[OSSC Pro palette collection](https://junkerhq.net/xrgb/index.php/OSSC_Pro) and
as a visually grouped
[Lospec palette](https://lospec.com/palette-list/intellivision). The values are
stored here in hardware order using the code mapping documented by the
[STIC digitizer project](https://github-wiki-see.page/m/c0pperdragon/LumaCode/wiki/STICdigitizer-%28for-Intellivision%29).
That digitizer mapping uses pure black for code 0; this palette intentionally
retains the selected preset's near-black `#0C0005` to preserve its analog-style
appearance.

Technical details about the display modes and color-code restrictions are
available in the
[Intellivision STIC documentation](https://wiki.intellivision.us/index.php/STIC).

## Reproduction

The ordered source table is stored as `_INTELLIVISION` in
`tooling/generate_additional_retro_palettes.py`. The generator derives hex,
HSL, LAB, and LCH values through the production Color Tools conversions.

Protected file hashes and final palette counts are intentionally updated only
after the complete release palette batch has been finalized.
