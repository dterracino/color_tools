#!/usr/bin/env python3
"""
Palette Shader Demo
===================
Real-time palette conversion demo using pygame + moderngl.

Loads an image or video and applies a retro-platform palette shader,
displaying the result in a live window.

Supported palettes
------------------
  nes       Nintendo Entertainment System (54 colours)
  gameboy   Original Game Boy DMG (4 shades of green)
  cga16     IBM CGA 16-colour palette
  pico8     PICO-8 fantasy console (16 colours)

Usage
-----
  python palette_shader_demo.py image.png --palette nes
  python palette_shader_demo.py video.mp4 --palette gameboy --pixelate 4
  python palette_shader_demo.py image.jpg --palette cga16 --dither 0.8
  python palette_shader_demo.py image.jpg --palette pico8 --pixelate 3 --dither 0.5

Keyboard shortcuts
------------------
  1-4       Switch palette  (1=NES, 2=Game Boy, 3=CGA16, 4=PICO-8)
  +/-       Increase/decrease pixel-block size
  D         Toggle dither on/off
  R         Reload shaders from disk (hot-reload)
  S         Save screenshot  (palette_screenshot.png)
  Space     Pause / resume video
  Q / Esc   Quit
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

# Third-party imports
try:
    import pygame
except ImportError:
    print("pygame is required.  Run:  pip install -r requirements.txt")
    sys.exit(1)

try:
    import moderngl
except ImportError:
    print("moderngl is required.  Run:  pip install -r requirements.txt")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("numpy is required.  Run:  pip install -r requirements.txt")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Pillow is required.  Run:  pip install -r requirements.txt")
    sys.exit(1)

# Optional: opencv for video
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DEMO_DIR   = Path(__file__).parent
SHADER_DIR = DEMO_DIR / "shaders"

PALETTES = {
    "nes":     {"frag": "nes.frag",     "default_pixelate": 4.0, "label": "NES"},
    "gameboy": {"frag": "gameboy.frag", "default_pixelate": 4.0, "label": "Game Boy"},
    "cga16":   {"frag": "cga16.frag",   "default_pixelate": 3.0, "label": "CGA 16"},
    "pico8":   {"frag": "pico8.frag",   "default_pixelate": 3.0, "label": "PICO-8"},
}
PALETTE_KEYS = list(PALETTES.keys())


# ---------------------------------------------------------------------------
# Shader helpers
# ---------------------------------------------------------------------------

def _read_shader(path: Path) -> str:
    """Read a GLSL shader file and return its source."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def build_program(ctx: moderngl.Context, palette: str) -> moderngl.Program:
    """Compile and link a shader program for the given palette."""
    vert_src = _read_shader(SHADER_DIR / "quad.vert")
    frag_src = _read_shader(SHADER_DIR / PALETTES[palette]["frag"])
    return ctx.program(vertex_shader=vert_src, fragment_shader=frag_src)


# ---------------------------------------------------------------------------
# Texture helpers
# ---------------------------------------------------------------------------

def make_texture(ctx: moderngl.Context, rgb_array: np.ndarray) -> moderngl.Texture:
    """
    Create a moderngl texture from a numpy uint8 array of shape (H, W, 3).
    The texture is flipped vertically because OpenGL's origin is bottom-left.
    """
    h, w = rgb_array.shape[:2]
    # OpenGL expects image data from the bottom row upward
    flipped = np.ascontiguousarray(np.flipud(rgb_array))
    tex = ctx.texture((w, h), 3, flipped.tobytes())
    tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    tex.repeat_x = False
    tex.repeat_y = False
    return tex


def load_image(path: Path) -> np.ndarray:
    """Load an image file and return an RGB numpy uint8 array (H, W, 3)."""
    img = Image.open(path).convert("RGB")
    return np.array(img, dtype=np.uint8)


# ---------------------------------------------------------------------------
# Fullscreen-quad VAO
# ---------------------------------------------------------------------------

def make_quad_vao(ctx: moderngl.Context, program: moderngl.Program) -> moderngl.VertexArray:
    """
    Create a fullscreen quad (two triangles) covering clip-space [-1, 1].
    Vertex layout: position (x,y), texcoord (u,v) — 4 floats per vertex.
    """
    # Two triangles forming a quad that covers the entire screen
    vertices = np.array([
        # x,     y,    u,    v
        -1.0, -1.0,  0.0,  0.0,
         1.0, -1.0,  1.0,  0.0,
         1.0,  1.0,  1.0,  1.0,
        -1.0, -1.0,  0.0,  0.0,
         1.0,  1.0,  1.0,  1.0,
        -1.0,  1.0,  0.0,  1.0,
    ], dtype=np.float32)

    vbo = ctx.buffer(vertices.tobytes())
    return ctx.vertex_array(program, [(vbo, "2f 2f", "in_position", "in_texcoord")])


# ---------------------------------------------------------------------------
# Video reader
# ---------------------------------------------------------------------------

class VideoReader:
    """Wraps an OpenCV VideoCapture, exposes frames as RGB numpy arrays."""

    def __init__(self, path: Path) -> None:
        if not HAS_CV2:
            raise RuntimeError(
                "opencv-python is required for video support.\n"
                "Run:  pip install -r requirements.txt"
            )
        self.cap = cv2.VideoCapture(str(path))
        if not self.cap.isOpened():
            raise FileNotFoundError(f"Cannot open video: {path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._paused = False
        self._last_frame: Optional[np.ndarray] = None
        self._next_frame_time = time.monotonic()

    def next_frame(self) -> Optional[np.ndarray]:
        """Return the next frame (RGB uint8), or None if the stream ended."""
        now = time.monotonic()
        if self._paused:
            return self._last_frame
        if now < self._next_frame_time:
            return self._last_frame

        ret, bgr = self.cap.read()
        if not ret:
            # Loop back to beginning
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, bgr = self.cap.read()
            if not ret:
                return self._last_frame

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        self._last_frame = rgb
        self._next_frame_time = now + 1.0 / self.fps
        return rgb

    def toggle_pause(self) -> None:
        self._paused = not self._paused

    @property
    def paused(self) -> bool:
        return self._paused

    def release(self) -> None:
        self.cap.release()


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

def run(
    source_path: Path,
    palette: str,
    pixelate: float,
    dither: float,
    window_scale: float,
) -> None:
    """
    Open the source image/video, create the window, and run the render loop.
    """
    # ------------------------------------------------------------------
    # Detect source type
    # ------------------------------------------------------------------
    is_video = source_path.suffix.lower() in {
        ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv",
    }

    video: Optional[VideoReader] = None
    frame: Optional[np.ndarray] = None

    if is_video:
        print(f"Loading video: {source_path}")
        video = VideoReader(source_path)
        # Grab first frame to determine dimensions
        frame = video.next_frame()
        if frame is None:
            print("Error: could not read first frame from video.")
            sys.exit(1)
        src_h, src_w = frame.shape[:2]
    else:
        print(f"Loading image: {source_path}")
        frame = load_image(source_path)
        src_h, src_w = frame.shape[:2]

    # ------------------------------------------------------------------
    # Compute window dimensions (preserve aspect ratio)
    # ------------------------------------------------------------------
    win_w = int(src_w * window_scale)
    win_h = int(src_h * window_scale)
    # Clamp to reasonable screen size
    max_dim = 1024
    if win_w > max_dim or win_h > max_dim:
        scale = max_dim / max(win_w, win_h)
        win_w = int(win_w * scale)
        win_h = int(win_h * scale)

    # ------------------------------------------------------------------
    # pygame + moderngl setup
    # ------------------------------------------------------------------
    pygame.init()
    pygame.display.set_caption(f"Palette Demo – {PALETTES[palette]['label']}")

    # OpenGL 3.3 core context
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    pygame.display.gl_set_attribute(
        pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE
    )
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, 1)

    screen = pygame.display.set_mode((win_w, win_h), pygame.OPENGL | pygame.DOUBLEBUF)
    clock  = pygame.time.Clock()

    ctx = moderngl.create_context()

    # ------------------------------------------------------------------
    # Build shader program and geometry
    # ------------------------------------------------------------------
    current_palette  = palette
    pixelate_val     = pixelate if pixelate > 0 else PALETTES[palette]["default_pixelate"]
    dither_val       = dither

    program = build_program(ctx, current_palette)
    vao     = make_quad_vao(ctx, program)
    texture = make_texture(ctx, frame)
    texture.use(0)

    def set_uniforms() -> None:
        if "u_pixelate" in program:
            program["u_pixelate"].value = pixelate_val
        if "u_dither" in program:
            program["u_dither"].value = dither_val
        if "u_texture" in program:
            program["u_texture"].value = 0

    set_uniforms()

    def update_title() -> None:
        pal_label = PALETTES[current_palette]["label"]
        pix_str   = f"pixelate={pixelate_val:.0f}"
        dth_str   = f"dither={dither_val:.1f}"
        paused    = "  [PAUSED]" if (video and video.paused) else ""
        pygame.display.set_caption(
            f"Palette Demo – {pal_label}  {pix_str}  {dth_str}{paused}"
        )

    def switch_palette(new_palette: str) -> None:
        nonlocal current_palette, program, vao, pixelate_val
        current_palette = new_palette
        pixelate_val    = PALETTES[new_palette]["default_pixelate"]
        program.release()
        vao.release()
        program = build_program(ctx, current_palette)
        vao     = make_quad_vao(ctx, program)
        texture.use(0)
        set_uniforms()
        update_title()
        print(f"Switched to {PALETTES[new_palette]['label']} palette")

    def reload_shaders() -> None:
        """Hot-reload shaders from disk."""
        nonlocal program, vao
        try:
            program.release()
            vao.release()
            program = build_program(ctx, current_palette)
            vao     = make_quad_vao(ctx, program)
            texture.use(0)
            set_uniforms()
            print(f"Shaders reloaded for {PALETTES[current_palette]['label']}")
        except Exception as exc:
            print(f"Shader reload failed: {exc}")

    update_title()
    print("\nKeyboard shortcuts:")
    print("  1-4   Switch palette (1=NES, 2=Game Boy, 3=CGA16, 4=PICO-8)")
    print("  +/-   Increase/decrease pixel-block size")
    print("  D     Toggle dither")
    print("  R     Reload shaders from disk")
    print("  S     Save screenshot")
    print("  Space Pause/resume video")
    print("  Q/Esc Quit\n")

    # ------------------------------------------------------------------
    # Render loop
    # ------------------------------------------------------------------
    running = True
    screenshot_count = 0

    while running:
        # ---- events --------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                key = event.key

                # Quit
                if key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False

                # Switch palette (1-4)
                elif key == pygame.K_1:
                    switch_palette("nes")
                elif key == pygame.K_2:
                    switch_palette("gameboy")
                elif key == pygame.K_3:
                    switch_palette("cga16")
                elif key == pygame.K_4:
                    switch_palette("pico8")

                # Pixel-block size
                elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    pixelate_val = min(pixelate_val + 1.0, 32.0)
                    set_uniforms()
                    update_title()
                elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    pixelate_val = max(pixelate_val - 1.0, 1.0)
                    set_uniforms()
                    update_title()

                # Dither toggle
                elif key == pygame.K_d:
                    dither_val = 0.0 if dither_val > 0 else 1.0
                    set_uniforms()
                    update_title()

                # Reload shaders
                elif key == pygame.K_r:
                    reload_shaders()

                # Screenshot
                elif key == pygame.K_s:
                    screenshot_count += 1
                    fname = DEMO_DIR / f"screenshot_{current_palette}_{screenshot_count:03d}.png"
                    # Read back the framebuffer
                    raw = ctx.screen.read(components=3)
                    img = Image.frombytes("RGB", (win_w, win_h), raw)
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)
                    img.save(fname)
                    print(f"Screenshot saved: {fname}")

                # Pause/resume video
                elif key == pygame.K_SPACE:
                    if video:
                        video.toggle_pause()
                        update_title()

        # ---- video frame update ------------------------------------
        if video:
            new_frame = video.next_frame()
            if new_frame is not None and not video.paused:
                frame = new_frame
                # Update GPU texture in-place
                flipped = np.ascontiguousarray(np.flipud(frame))
                texture.write(flipped.tobytes())

        # ---- render ------------------------------------------------
        ctx.viewport = (0, 0, win_w, win_h)
        ctx.clear(0.0, 0.0, 0.0)
        vao.render(moderngl.TRIANGLES)
        pygame.display.flip()

        clock.tick(60)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    if video:
        video.release()
    texture.release()
    vao.release()
    program.release()
    pygame.quit()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retro palette shader demo (pygame + moderngl)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Image or video file to display",
    )
    parser.add_argument(
        "--palette",
        choices=list(PALETTES.keys()),
        default="nes",
        help="Starting palette (default: nes)",
    )
    parser.add_argument(
        "--pixelate",
        type=float,
        default=0.0,
        help="Pixel-block size (0 = use palette default, 1 = off)",
    )
    parser.add_argument(
        "--dither",
        type=float,
        default=0.0,
        help="Bayer dither strength: 0.0 (off) to 1.0 (full)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Window scale factor (default: 1.0)",
    )

    args = parser.parse_args()

    source = args.source
    if not source.exists():
        print(f"Error: file not found: {source}")
        sys.exit(1)

    run(
        source_path=source,
        palette=args.palette,
        pixelate=args.pixelate,
        dither=args.dither,
        window_scale=args.scale,
    )


if __name__ == "__main__":
    main()
