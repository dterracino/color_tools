# VIC-20 Palette Source and Representation

This document records the source, ordering, and intended meaning of the
built-in `vic-20` palette.

## Hardware color model

The VIC-20 uses the MOS Technology 6560 video interface chip in NTSC systems
and the 6561 in PAL systems. The VIC-I produces composite video rather than
modern digital RGB. Its appearance therefore varies with the chip revision,
video standard, display, signal path, capture method, and emulator settings.

The palette is a visually useful CRT-style interpretation for image conversion.
It is not presented as a universally exact measurement of VIC-20 output.

## Color order

The records follow VIC-I hardware color codes 0 through 15:

| Code | Name | Hex |
| ---: | --- | --- |
| 0 | Black | `#000000` |
| 1 | White | `#FFFFFF` |
| 2 | Red | `#772D26` |
| 3 | Cyan | `#85D4DC` |
| 4 | Purple | `#A85FB4` |
| 5 | Green | `#559E4A` |
| 6 | Blue | `#42348B` |
| 7 | Yellow | `#BDCC71` |
| 8 | Orange | `#A8734A` |
| 9 | Light orange | `#E9B287` |
| 10 | Pink | `#B66862` |
| 11 | Light cyan | `#C5FFFF` |
| 12 | Light purple | `#E99DF5` |
| 13 | Light green | `#92DF87` |
| 14 | Light blue | `#7E70CA` |
| 15 | Light yellow | `#FFFFB0` |

The selected RGB set is published by
[Lospec](https://lospec.com/palette-list/commodore-vic-20) in visually grouped
shade pairs. That presentation order is not the VIC-I register order. The
values above are remapped using the color-code names in the
[MOS 6560/6561 VIC-I documentation](https://www.vic-20.it/wp-content/uploads/2021/05/6561-6560.pdf).
The same hardware order and names are also used by
[VICE's VIC-20 palettes](https://github.com/VICE-Team/svn-mirror/tree/main/vice/data/VIC20).

## Reproduction

The ordered source table is stored as `_VIC20` in
`tooling/generate_additional_retro_palettes.py`. The generator derives hex,
HSL, LAB, and LCH values through the production Color Tools conversions.

Protected file hashes and final palette counts are intentionally updated only
after the complete release palette batch has been finalized.
