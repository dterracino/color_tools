#!/usr/bin/env python3
"""Interactive image/video preview for the shaders in ``demos/shaders``.

Shaders are discovered automatically and use the contract in ``demos/README.md``.
The LUT shader accepts named color_tools palettes or custom palette strips.
"""

from __future__ import annotations

import argparse
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from shader_demo_layout import fit_integer_viewport, fit_viewport, initial_window_size

try:
    import cv2
    import moderngl
    import numpy as np
    import pygame
    from numpy.typing import NDArray
    from PIL import Image
except ImportError as exc:
    print(f"Missing demo dependency: {exc.name}")
    print("Run: python -m pip install -r demos/requirements.txt")
    raise SystemExit(1) from exc

try:
    from color_tools import load_palette
except ImportError as exc:
    print("color_tools is required. Run: python -m pip install -e .")
    raise SystemExit(1) from exc


RGBFrame = NDArray[np.uint8]
UniformValue = int | float | tuple[float, float]
VertexArrayFactory = Callable[
    [moderngl.Program, list[tuple[moderngl.Buffer, str, str, str]]],
    moderngl.VertexArray,
]


class _VertexArrayContext(Protocol):
    """Typed view of the ModernGL context method missing from its stub."""

    vertex_array: VertexArrayFactory


DEMO_DIR = Path(__file__).resolve().parent
SHADER_DIR = DEMO_DIR / "shaders"
VERTEX_SHADER_PATH = SHADER_DIR / "quad.vert"
VIDEO_SUFFIXES = frozenset({".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".m4v"})

_SHADER_DEFAULTS: dict[str, tuple[str, float]] = {
    "nes": ("NES", 4.0),
    "gameboy": ("Game Boy", 4.0),
    "cga16": ("CGA 16", 3.0),
    "pico8": ("PICO-8", 3.0),
    "palette_lut": ("Palette LUT", 3.0),
}
_PREFERRED_SHADER_ORDER = tuple(_SHADER_DEFAULTS)


@dataclass(frozen=True, slots=True)
class ShaderDefinition:
    """A discovered fragment shader and its presentation defaults."""

    name: str
    path: Path
    label: str
    default_pixelate: float


@dataclass(slots=True)
class ProgramResources:
    """ModernGL resources that must be replaced and released together."""

    program: moderngl.Program
    vertex_array: moderngl.VertexArray
    vertex_buffer: moderngl.Buffer

    def release(self) -> None:
        """Release the program and its associated quad geometry."""
        self.vertex_array.release()
        self.vertex_buffer.release()
        self.program.release()


def discover_shaders(directory: Path = SHADER_DIR) -> tuple[ShaderDefinition, ...]:
    """Discover every fragment shader, retaining stable shortcuts for known shaders."""
    paths = {path.stem: path for path in directory.glob("*.frag")}
    preferred = [name for name in _PREFERRED_SHADER_ORDER if name in paths]
    names = preferred + sorted(set(paths).difference(preferred))
    definitions: list[ShaderDefinition] = []
    for name in names:
        label, default_pixelate = _SHADER_DEFAULTS.get(
            name,
            (name.replace("_", " ").replace("-", " ").title(), 1.0),
        )
        definitions.append(ShaderDefinition(name, paths[name], label, default_pixelate))
    return tuple(definitions)


def _read_shader(path: Path) -> str:
    """Read UTF-8 GLSL source."""
    return path.read_text(encoding="utf-8")


def _create_program_resources(
    ctx: moderngl.Context,
    shader: ShaderDefinition,
) -> ProgramResources:
    """Compile a shader and create its fullscreen quad resources."""
    program = ctx.program(
        vertex_shader=_read_shader(VERTEX_SHADER_PATH),
        fragment_shader=_read_shader(shader.path),
    )
    if "u_texture" not in program:
        program.release()
        raise ValueError(f"{shader.path.name} must declare uniform sampler2D u_texture")

    vertices = np.array(
        [
            -1.0, -1.0, 0.0, 0.0,
            1.0, -1.0, 1.0, 0.0,
            1.0, 1.0, 1.0, 1.0,
            -1.0, -1.0, 0.0, 0.0,
            1.0, 1.0, 1.0, 1.0,
            -1.0, 1.0, 0.0, 1.0,
        ],
        dtype=np.float32,
    )
    vertex_buffer = ctx.buffer(vertices.tobytes())
    create_vertex_array = cast(_VertexArrayContext, ctx).vertex_array
    vertex_array = create_vertex_array(
        program,
        [(vertex_buffer, "2f 2f", "in_position", "in_texcoord")],
    )
    return ProgramResources(program, vertex_array, vertex_buffer)


def _set_uniform(program: moderngl.Program, name: str, value: UniformValue) -> None:
    """Set an optional uniform when the active shader declares it."""
    member = program.get(name, None)
    if isinstance(member, moderngl.Uniform):
        member.value = value


def _make_rgb_texture(ctx: moderngl.Context, frame: RGBFrame) -> moderngl.Texture:
    """Upload one RGB frame using OpenGL's bottom-left row order."""
    height, width = frame.shape[:2]
    flipped = np.ascontiguousarray(np.flipud(frame))
    texture = ctx.texture((int(width), int(height)), 3, flipped.tobytes())
    texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
    texture.repeat_x = False
    texture.repeat_y = False
    return texture


def _load_image(path: Path) -> RGBFrame:
    """Decode a still image as an RGB uint8 frame."""
    with Image.open(path) as image:
        return np.array(image.convert("RGB"), dtype=np.uint8, copy=True)


def _load_lut_colors(palette_name: str, lut_path: Path | None) -> RGBFrame:
    """Load palette colors from color_tools or the first row of a custom image."""
    if lut_path is None:
        palette = load_palette(palette_name)
        colors = np.asarray([record.rgb for record in palette.records], dtype=np.uint8)
    else:
        with Image.open(lut_path) as image:
            pixels = np.asarray(image.convert("RGB"), dtype=np.uint8)
        colors = pixels[0] if pixels.ndim == 3 else pixels
    if colors.ndim != 2 or colors.shape[1] != 3 or colors.shape[0] == 0:
        raise ValueError("Palette LUT must contain at least one RGB color")
    return np.ascontiguousarray(colors, dtype=np.uint8)


def _make_lut_texture(
    ctx: moderngl.Context,
    palette_name: str,
    lut_path: Path | None,
) -> tuple[moderngl.Texture, int]:
    """Create a one-row palette texture for LUT-driven shaders."""
    colors = _load_lut_colors(palette_name, lut_path)
    size = int(colors.shape[0])
    texture = ctx.texture((size, 1), 3, colors.tobytes())
    texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
    texture.repeat_x = False
    texture.repeat_y = False
    return texture, size


class VideoReader:
    """Time an OpenCV video stream and expose RGB frames."""

    def __init__(self, path: Path) -> None:
        self._capture = cv2.VideoCapture(str(path))
        if not self._capture.isOpened():
            raise FileNotFoundError(f"Cannot open video: {path}")
        measured_fps = float(self._capture.get(cv2.CAP_PROP_FPS))
        self.fps = measured_fps if math.isfinite(measured_fps) and measured_fps > 0 else 30.0
        self._paused = False
        self._next_frame_time = time.monotonic()

    def next_frame(self, *, force: bool = False) -> RGBFrame | None:
        """Return a newly decoded frame when it is due, otherwise return ``None``."""
        now = time.monotonic()
        if self._paused or (not force and now < self._next_frame_time):
            return None
        read_ok, bgr = self._capture.read()
        if not read_ok:
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            read_ok, bgr = self._capture.read()
        if not read_ok:
            return None
        self._next_frame_time = now + (1.0 / self.fps)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        return np.asarray(rgb, dtype=np.uint8)

    def toggle_pause(self) -> None:
        """Toggle playback and resume without trying to catch up."""
        self._paused = not self._paused
        self._next_frame_time = time.monotonic()

    @property
    def paused(self) -> bool:
        """Return whether playback is paused."""
        return self._paused

    def release(self) -> None:
        """Release the OpenCV capture."""
        self._capture.release()


def _open_source(path: Path) -> tuple[RGBFrame, VideoReader | None]:
    """Open an image or video and return its first frame."""
    if path.suffix.casefold() not in VIDEO_SUFFIXES:
        try:
            return _load_image(path), None
        except (OSError, ValueError):
            pass
    video = VideoReader(path)
    frame = video.next_frame(force=True)
    if frame is None:
        video.release()
        raise ValueError(f"Could not decode an image or video frame from {path}")
    return frame, video


def run(
    source_path: Path,
    shader_name: str,
    pixelate: float,
    dither: float,
    window_scale: float,
    *,
    lut_palette: str,
    lut_path: Path | None,
    naive: bool = False,
) -> None:
    """Open an image or video and run the interactive shader preview."""
    shaders = discover_shaders()
    shader_by_name = {shader.name: shader for shader in shaders}
    frame, video = _open_source(source_path)
    if naive:
        if video is not None:
            video.release()
            raise ValueError("--naive supports static images only")
        from naive_nes_processor import process_naive_nes

        frame = process_naive_nes(frame, dither).frame
        current_shader = shader_by_name["passthrough"]
    else:
        current_shader = shader_by_name[shader_name]
    window_width, window_height = initial_window_size(window_scale, naive_nes=naive)
    source_height, source_width = (int(value) for value in frame.shape[:2])
    layout_viewport = fit_integer_viewport if naive else fit_viewport
    viewport = layout_viewport((window_width, window_height), (source_width, source_height))

    pygame.init()
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, 1)
    pygame.display.set_mode(
        (window_width, window_height),
        pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE,
    )
    clock = pygame.time.Clock()

    ctx = moderngl.create_context()
    source_texture = _make_rgb_texture(ctx, frame)
    source_texture.use(0)
    lut_texture, lut_size = _make_lut_texture(ctx, lut_palette, lut_path)
    lut_texture.use(1)
    resources = _create_program_resources(ctx, current_shader)
    pixelate_value = 1.0 if naive else (
        pixelate if pixelate > 0 else current_shader.default_pixelate)
    dither_value = dither
    started_at = time.monotonic()
    frame_number = 0

    def set_uniforms() -> None:
        program = resources.program
        _set_uniform(program, "u_texture", 0)
        _set_uniform(program, "u_palette", 1)
        _set_uniform(program, "u_palette_size", lut_size)
        _set_uniform(program, "u_pixelate", pixelate_value)
        _set_uniform(program, "u_dither", dither_value)
        _set_uniform(program, "u_resolution", (float(viewport[2]), float(viewport[3])))
        _set_uniform(program, "u_source_resolution", (float(source_width), float(source_height)))

    def update_title() -> None:
        paused = " [PAUSED]" if video is not None and video.paused else ""
        mode = "Naive NES – " if naive else "Palette Shader – "
        pygame.display.set_caption(
            f"{mode}{current_shader.label}  "
            f"pixelate={pixelate_value:.0f}  dither={dither_value:.1f}{paused}"
        )

    def replace_shader(next_shader: ShaderDefinition, *, reset_pixelate: bool) -> None:
        nonlocal current_shader, resources, pixelate_value
        replacement = _create_program_resources(ctx, next_shader)
        previous = resources
        resources = replacement
        current_shader = next_shader
        if reset_pixelate:
            pixelate_value = next_shader.default_pixelate
        source_texture.use(0)
        lut_texture.use(1)
        set_uniforms()
        update_title()
        previous.release()
        print(f"Shader: {next_shader.label} ({next_shader.path.name})")

    set_uniforms()
    update_title()
    print(f"Loaded {'video' if video is not None else 'image'}: {source_path}")
    print(f"LUT palette: {lut_path if lut_path is not None else lut_palette} ({lut_size} colors)")
    print("\nDiscovered shaders:")
    for index, shader in enumerate(shaders, 1):
        shortcut = str(index) if index <= 9 else "-"
        print(f"  {shortcut:>2}  {shader.name:20s} {shader.path.name}")
    print("\nKeys: 1-9 shader, +/- pixel size, D dither, R reload, S screenshot,")
    print("      Space pause video, Q/Esc quit\n")

    running = True
    screenshot_count = 0
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type in (pygame.VIDEORESIZE, pygame.WINDOWRESIZED):
                    window_width, window_height = pygame.display.get_window_size()
                    viewport = layout_viewport(
                        (window_width, window_height),
                        (source_width, source_height),
                    )
                    set_uniforms()
                elif event.type == pygame.KEYDOWN:
                    key = int(event.key)
                    if key in (pygame.K_q, pygame.K_ESCAPE):
                        running = False
                    elif event.unicode in "123456789":
                        shader_index = int(event.unicode) - 1
                        if shader_index < len(shaders):
                            try:
                                replace_shader(shaders[shader_index], reset_pixelate=True)
                            except (moderngl.Error, OSError, ValueError) as exc:
                                print(f"Shader switch failed: {exc}")
                    elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        pixelate_value = min(pixelate_value + 1.0, 32.0)
                        set_uniforms()
                        update_title()
                    elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        pixelate_value = max(pixelate_value - 1.0, 1.0)
                        set_uniforms()
                        update_title()
                    elif key == pygame.K_d:
                        if naive:
                            print("Naive dither is fixed during CPU preprocessing; restart with --dither")
                        else:
                            dither_value = 0.0 if dither_value > 0 else 1.0
                            set_uniforms()
                            update_title()
                    elif key == pygame.K_r:
                        try:
                            replace_shader(current_shader, reset_pixelate=False)
                        except (moderngl.Error, OSError, ValueError) as exc:
                            print(f"Shader reload failed; keeping current shader: {exc}")
                    elif key == pygame.K_s:
                        screenshot_count += 1
                        name = "naive_nes" if naive else current_shader.name
                        output = DEMO_DIR / f"screenshot_{name}_{screenshot_count:03d}.png"
                        raw = ctx.screen.read(components=3)
                        image = Image.frombytes("RGB", (window_width, window_height), raw)
                        image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(output)
                        print(f"Screenshot saved: {output}")
                    elif key == pygame.K_SPACE and video is not None:
                        video.toggle_pause()
                        update_title()

            if video is not None:
                next_frame = video.next_frame()
                if next_frame is not None:
                    flipped = np.ascontiguousarray(np.flipud(next_frame))
                    source_texture.write(flipped.tobytes())

            _set_uniform(resources.program, "u_time", time.monotonic() - started_at)
            _set_uniform(resources.program, "u_frame", frame_number)
            ctx.viewport = viewport
            ctx.clear(0.0, 0.0, 0.0)
            resources.vertex_array.render(moderngl.TRIANGLES)
            pygame.display.flip()
            frame_number += 1
            clock.tick(60)
    finally:
        if video is not None:
            video.release()
        resources.release()
        lut_texture.release()
        source_texture.release()
        pygame.quit()


def _build_parser(shaders: tuple[ShaderDefinition, ...]) -> argparse.ArgumentParser:
    """Build the command-line parser from the discovered shader catalog."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, help="Image or video file to preview")
    parser.add_argument(
        "--shader", "--palette", dest="shader", choices=[shader.name for shader in shaders],
        default="nes" if any(shader.name == "nes" for shader in shaders) else shaders[0].name,
        help="Starting fragment shader; --palette is retained as an alias",
    )
    parser.add_argument("--pixelate", type=float, default=0.0, help="Pixel-block size; 0 uses shader default")
    parser.add_argument("--dither", type=float, default=0.0, help="Ordered-dither strength from 0.0 to 1.0")
    parser.add_argument("--scale", type=float, default=1.0, help="Window scale factor")
    parser.add_argument("--lut-palette", default="nes", metavar="NAME", help="color_tools palette for LUT shaders")
    parser.add_argument("--lut", type=Path, metavar="IMAGE", help="Custom horizontal palette strip for LUT shaders")
    parser.add_argument("--list-shaders", action="store_true", help="List discovered fragment shaders and exit")
    parser.add_argument(
        "--naive", action="store_true",
        help="CPU-process a static image into a naive 256x240 NES baseline")
    return parser


def main() -> None:
    """Parse arguments and start the demo."""
    shaders = discover_shaders()
    if not shaders:
        raise SystemExit(f"No .frag shaders found in {SHADER_DIR}")
    parser = _build_parser(shaders)
    args = parser.parse_args()
    if bool(args.list_shaders):
        for shader in shaders:
            print(f"{shader.name:20s} {shader.path.name}")
        return

    source = cast(Path | None, args.source)
    if source is None:
        parser.error("source is required unless --list-shaders is used")
    if not source.is_file():
        parser.error(f"source file not found: {source}")
    naive = bool(args.naive)
    if naive and source.suffix.casefold() in VIDEO_SUFFIXES:
        parser.error("--naive supports static images only")
    lut_path = cast(Path | None, args.lut)
    if lut_path is not None and not lut_path.is_file():
        parser.error(f"LUT image not found: {lut_path}")
    pixelate = float(args.pixelate)
    dither = float(args.dither)
    scale = float(args.scale)
    if pixelate < 0:
        parser.error("--pixelate must be zero or greater")
    if not 0.0 <= dither <= 1.0:
        parser.error("--dither must be between 0.0 and 1.0")
    if not math.isfinite(scale) or scale <= 0:
        parser.error("--scale must be a positive finite number")

    run(
        source,
        str(args.shader),
        pixelate,
        dither,
        scale,
        lut_palette=str(args.lut_palette),
        lut_path=lut_path,
        naive=naive,
    )


if __name__ == "__main__":
    main()
