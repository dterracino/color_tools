# Palette Shader Demo

Real-time image and video preview for the GLSL shaders in `demos/shaders`,
built with pygame and ModernGL. The demo discovers fragment shaders at startup,
so adding a compatible `.frag` file does not require changing Python code.

The system-specific shaders contain fixed palettes. The generic `palette_lut`
shader can use any palette shipped by `color_tools`, or a custom palette-strip
image, without recompiling GLSL.

## Quick start

```bash
python -m pip install -r demos/requirements.txt

# Still image with a system-specific shader
python demos/palette_shader_demo.py photo.jpg --shader nes

# CPU-generated naive NES baseline for comparison
python demos/palette_shader_demo.py photo.jpg --naive --dither 0.75

# Video with another fixed shader
python demos/palette_shader_demo.py gameplay.mp4 --shader gameboy --pixelate 4

# Any color_tools palette through the generic LUT shader
python demos/palette_shader_demo.py photo.jpg --shader palette_lut --lut-palette ega16

# A custom horizontal palette strip
python demos/palette_shader_demo.py photo.jpg --shader palette_lut --lut my_palette.png

# Show every discovered shader
python demos/palette_shader_demo.py --list-shaders
```

`--palette` remains an alias for `--shader` for compatibility with older
commands.

## Options

```text
python demos/palette_shader_demo.py SOURCE [options]

--shader NAME        Starting fragment shader (default: nes)
--palette NAME       Backward-compatible alias for --shader
--pixelate FLOAT     Pixel-block size; 0 uses the shader default, 1 disables it
--dither FLOAT       Ordered-dither strength from 0.0 to 1.0
--scale FLOAT        Initial window scale factor
--lut-palette NAME   Named color_tools palette for LUT shaders (default: nes)
--lut IMAGE          Custom horizontal palette strip for LUT shaders
--list-shaders       List discovered fragment shaders and exit
--naive              CPU-process a static image into a naive NES baseline
```

Pillow decodes still images. OpenCV decodes video and provides the source frame
rate. Playback loops at the end of the video. The demo is a preview tool: it can
save the displayed frame as a screenshot, but it does not encode processed
video or preserve source audio.

The initial window is a 4:3 presentation surface and can be freely resized.
Source media retains its aspect ratio and is centered with black letterboxing
when it does not match the window.

## Naive NES baseline

`--naive` is available for static images. It provides a deterministic baseline
that does not depend on a fragment shader's sampling behavior:

1. Center-crop the source to a 4:3 composition.
2. Resample once into an exact 256×240 framebuffer.
3. Median-cut the source framebuffer into 25 representative color bins.
4. Convert the source bins and NES master palette from RGB to CIELAB.
5. Use CIEDE2000 to build a source-informed palette of at most 25 NES colors.
6. For every NES texel, find the two nearest allowed colors and use a
   grid-aligned 4×4 Bayer threshold to select strictly between those colors.
7. Present the completed frame through `passthrough.frag` without additional
   quantization.

The `--dither` value controls the two-candidate mixing strength; zero selects
only the nearest color. Naive preprocessing reports each stage and its final
palette counts using Rich. Press `S` to save the displayed baseline.

The naive viewport uses integer horizontal and vertical texel scales. At the
default 1280×960 window, each NES texel is exactly 5×4 display pixels, providing
4:3 presentation without uneven rows, skipped columns, or fractional shearing.
Smaller resized windows select the closest integer pixel shape and letterbox
the result.

This baseline deliberately does not invent per-tile palettes. A credible
16×16 attribute mode needs one shared backdrop and four coherent scene-wide
subpalettes; independently choosing colors for every tile recreates visible
checkerboard discontinuities. Video is rejected because stable palette choices
across frames require a separate temporal design.

## Keyboard shortcuts

| Key | Action |
| ----- | -------- |
| `1`–`9` | Select the corresponding discovered shader |
| `+` / `-` | Increase / decrease pixel-block size |
| `D` | Toggle ordered dithering |
| `R` | Hot-reload the active shader |
| `S` | Save a screenshot to `demos/` |
| `Space` | Pause / resume video |
| `Q` / `Esc` | Quit |

Shader switches and reloads are transactional: a compile failure is reported
without discarding the shader that is already working.

## Included shaders

| Name | Description |
| ------ | ------------- |
| `nes` | NES 54-color global nearest-color conversion |
| `gameboy` | Original Game Boy DMG four-shade conversion |
| `cga16` | IBM CGA 16-color RGBI conversion |
| `pico8` | PICO-8 16-color conversion |
| `palette_lut` | Generic nearest-color conversion using a palette texture |
| `passthrough` | Unmodified display of CPU-processed baseline frames |

The fixed shaders approximate each platform's colors and coarse resolution;
they do not enforce original hardware tile, sprite, per-cell palette, signal,
or scanout restrictions.

## Adding a shader

Place a `.frag` file in `demos/shaders`. Its filename stem becomes its CLI name.
Every shader must target GLSL 3.3, work with `quad.vert`, declare
`sampler2D u_texture`, and write `fragColor`.

The demo sets these uniforms when the shader declares them and ignores them
otherwise:

| Uniform | Type | Value |
| --------- | ------ | ------- |
| `u_texture` | `sampler2D` | Source image/video on texture unit 0 |
| `u_palette` | `sampler2D` | Palette strip on texture unit 1 |
| `u_palette_size` | `int` | Number of colors in the palette strip |
| `u_pixelate` | `float` | Current pixel-block size |
| `u_dither` | `float` | Current dither strength |
| `u_resolution` | `vec2` | Output viewport size in pixels |
| `u_source_resolution` | `vec2` | Source texture size in pixels |
| `u_time` | `float` | Seconds since preview startup |
| `u_frame` | `int` | Rendered frame number |

A shader with additional required uniforms needs a corresponding application
control or a default encoded in the shader. Unknown shaders use a display label
derived from their filename and a default pixel-block size of 1.

## Palette texture generator

The demo builds its LUT in memory. `generate_palette_textures.py` is a thin
batch wrapper around the registered `palette_lut` exporter when another
application needs canonical N×1 palette textures on disk. By default it exports
every bundled palette:

```bash
python demos/generate_palette_textures.py --list
python demos/generate_palette_textures.py
python demos/generate_palette_textures.py --palette nes gameboy --glsl
```

Generated PNG files are written to `demos/palette_textures/`. `--glsl` also
writes a `.glsl` array through the registered GLSL exporter; the utility does
not duplicate either serialization implementation.

## Dependencies

The demo dependencies are separate from the main library and listed in
`demos/requirements.txt`:

| Package | Purpose |
| --------- | --------- |
| `pygame` | Window, input, and OpenGL context |
| `moderngl` | OpenGL 3.3 resource and draw API |
| `numpy` | Frame and texture data |
| `Pillow` | Still-image decoding and screenshots |
| `opencv-python` | Video decoding |
| `color-match-tools` | Palette catalog and loading |
| `rich` | Naive preprocessing progress and result reporting |
