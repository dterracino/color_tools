# Palette Shader Demo

Real-time retro-palette conversion demo built with **pygame** and **moderngl**.

Load any image or video and watch it rendered as if it came from a classic
gaming system — NES, Game Boy, IBM CGA, or PICO-8 — entirely on the GPU via
a GLSL fragment shader.

---

## Quick start

```bash
# 1. Install dependencies (only for this demo — does not touch the main library)
pip install -r demos/requirements.txt

# 2. Run with an image
python demos/palette_shader_demo.py my_photo.jpg --palette nes

# 3. Run with a video
python demos/palette_shader_demo.py gameplay.mp4 --palette gameboy --pixelate 4
```

---

## Usage

```
python palette_shader_demo.py SOURCE [options]

positional arguments:
  SOURCE              Image or video file (.jpg, .png, .mp4, .avi, …)

options:
  --palette {nes,gameboy,cga16,pico8}
                      Starting palette (default: nes)
  --pixelate FLOAT    Pixel-block size; 0 = use palette default, 1 = off
  --dither FLOAT      Bayer 4×4 dither strength: 0.0 (off) to 1.0 (full)
  --scale FLOAT       Window scale factor (default: 1.0)
```

### Examples

```bash
# NES palette, default pixel-block size (4×4)
python demos/palette_shader_demo.py photo.jpg --palette nes

# Game Boy green tones, strong dither
python demos/palette_shader_demo.py photo.png --palette gameboy --dither 0.8

# CGA 16-colour, no pixelation, light dither
python demos/palette_shader_demo.py video.mp4 --palette cga16 --pixelate 1 --dither 0.4

# PICO-8, 3×3 blocks, no dither
python demos/palette_shader_demo.py trailer.mp4 --palette pico8 --pixelate 3
```

---

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `1` | NES palette |
| `2` | Game Boy (DMG) palette |
| `3` | CGA 16-colour palette |
| `4` | PICO-8 palette |
| `+` / `-` | Increase / decrease pixel-block size |
| `D` | Toggle Bayer dither on/off |
| `R` | Hot-reload shaders from disk |
| `S` | Save screenshot to `demos/` |
| `Space` | Pause / resume video |
| `Q` / `Esc` | Quit |

---

## Supported palettes

| Name | Colours | System |
|------|--------:|--------|
| `nes` | 54 | Nintendo Entertainment System (NTSC master palette) |
| `gameboy` | 4 | Original Game Boy DMG (green LCD) |
| `cga16` | 16 | IBM CGA full palette |
| `pico8` | 16 | PICO-8 fantasy console |

More palettes are available in `color_tools/data/palettes/` (see
`generate_palette_textures.py --list`).  Adding a new palette requires:

1. A `.frag` file in `demos/shaders/` following the same pattern as the
   existing shaders.
2. An entry in the `PALETTES` dict at the top of `palette_shader_demo.py`.

---

## Shaders

All shaders live in `demos/shaders/`.  They are self-contained and can be
copied directly into any other moderngl / OpenGL project.

| File | Description |
|------|-------------|
| `quad.vert` | Fullscreen-quad vertex shader (shared by all effects) |
| `nes.frag` | NES 54-colour palette quantisation + optional Bayer dither |
| `gameboy.frag` | Game Boy DMG 4-shade greyscale + optional Bayer dither |
| `cga16.frag` | CGA 16-colour palette + optional Bayer dither |
| `pico8.frag` | PICO-8 16-colour palette + optional Bayer dither |

### Shader uniforms (all palette shaders)

| Uniform | Type | Default | Description |
|---------|------|---------|-------------|
| `u_texture` | `sampler2D` | — | Source image / video frame |
| `u_pixelate` | `float` | 4.0 | Pixel-block size (1 = disabled) |
| `u_dither` | `float` | 0.0 | Bayer 4×4 dither strength (0–1) |

### Using a shader in another project

```python
import moderngl, numpy as np

ctx = moderngl.create_context()

vert = open("shaders/quad.vert").read()
frag = open("shaders/nes.frag").read()      # swap for any palette shader
prog = ctx.program(vertex_shader=vert, fragment_shader=frag)

# Bind your texture, set uniforms, render a fullscreen quad
prog["u_texture"]  = 0
prog["u_pixelate"] = 4.0
prog["u_dither"]   = 0.0
```

---

## Palette texture generator

`generate_palette_textures.py` bakes every palette JSON file into a 1×N PNG
strip that can be used as a GPU palette texture instead of a hard-coded array:

```bash
# Generate PNG strips for all common palettes
python demos/generate_palette_textures.py

# List all available palettes
python demos/generate_palette_textures.py --list

# Generate a specific palette and print its GLSL snippet
python demos/generate_palette_textures.py --palette nes --glsl
```

Output files are written to `demos/palette_textures/`.

---

## Where should shaders live in the library?

When the shader collection matures, a natural home in the `color_tools`
package would be:

```
color_tools/
  shaders/
    palette/
      nes.frag
      gameboy.frag
      cga16.frag
      pico8.frag
      ...
    common/
      quad.vert
      palette_lookup.glsl   # shared GLSL include / snippet
    README.md
```

This keeps the GLSL shaders alongside the palette JSON data they are derived
from and allows them to be installed with the package via a `MANIFEST.in`
glob.  Users could then import a shader path with:

```python
from importlib.resources import files
shader_path = files("color_tools.shaders.palette") / "nes.frag"
```

For now, all shaders live in `demos/shaders/` as requested.

---

## Dependencies

All listed in `demos/requirements.txt` — separate from the main library:

| Package | Purpose |
|---------|---------|
| `pygame` | Window, event loop, OpenGL context creation |
| `moderngl` | Pythonic OpenGL 3.3 wrapper |
| `numpy` | Fast array operations for texture data |
| `Pillow` | Image loading and screenshot saving |
| `opencv-python` | Video decoding (optional — required only for video files) |
