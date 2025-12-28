# Custom Fonts for Watermarking

This directory contains custom TrueType (.ttf) and OpenType (.otf) fonts that can be used for text watermarks.

## Included Fonts (Recommended)

We recommend including these open-source fonts for general use:

### Sans-Serif (Clean & Modern)

- **Roboto-Regular.ttf** - Google's flagship font, extremely readable
- **Roboto-Bold.ttf** - Bold weight for emphasis
- **OpenSans-Regular.ttf** - Professional, widely used
- **OpenSans-Bold.ttf** - Bold weight

### Monospace (Technical)

- **RobotoMono-Regular.ttf** - Great for copyright symbols, technical marks

### Display (Branding)

- **Montserrat-Bold.ttf** - Geometric, eye-catching for logos

All recommended fonts are under the **SIL Open Font License** (free for commercial use).

## Using Custom Fonts

### From This Directory

Place your .ttf or .otf files here and reference them by filename:

```bash
color-tools image --file input.jpg --watermark \
  --watermark-text "© 2025 My Brand" \
  --watermark-font-file Roboto-Bold.ttf \
  --watermark-font-size 36
```

### From Custom Path

You can also specify a full or relative path to any font file:

```bash
color-tools image --file input.jpg --watermark \
  --watermark-text "My Watermark" \
  --watermark-font-file ~/my-fonts/CustomFont.ttf \
  --watermark-font-size 24
```

### Using System Fonts

Alternatively, use installed system fonts by name:

```bash
color-tools image --file input.jpg --watermark \
  --watermark-text "© 2025" \
  --watermark-font-name "Arial" \
  --watermark-font-size 32
```

## Adding Your Own Fonts

1. Download a .ttf or .otf font file
2. Copy it to this directory
3. Use `--watermark-font-file filename.ttf` in your watermark commands

## Font License Compliance

When adding fonts to this directory **for redistribution with the package**:

- **Ensure the font license permits redistribution** - Most open-source fonts (OFL, Apache, MIT) allow this
- **Document the license** - Add font name, license type, and source URL to this README
- **Respect attribution requirements** - Some licenses require attribution in documentation

**For personal use:** You can use any font you legally own (purchased, licensed, or free) by placing it in this directory or specifying its path with `--watermark-font-file`. Just don't commit proprietary/purchased fonts to the repository.

**Note:** Including individual license files (OFL.txt, LICENSE.txt) alongside each font is optional. Google Fonts use the same filename for all fonts, which would cause conflicts. Instead, document licenses here or in a master LICENSE file.

## Font Sources

Great sources for open-source fonts:

- [Google Fonts](https://fonts.google.com/) - All fonts under open licenses
- [Font Squirrel](https://www.fontsquirrel.com/) - Commercial-use free fonts
- [The League of Moveable Type](https://www.theleagueofmoveabletype.com/) - Open-source type foundry

## Technical Notes

- Supported formats: .ttf (TrueType), .otf (OpenType)
- Font files are loaded via Pillow's ImageFont module
- If a font cannot be found, the system will fall back to Pillow's default font
