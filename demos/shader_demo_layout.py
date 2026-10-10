"""Window and viewport layout helpers for the palette shader demo."""

from __future__ import annotations


NES_FRAME_SIZE = (256, 240)
NES_PIXEL_ASPECT = 5.0 / 4.0


def initial_window_size(scale: float, *, naive_nes: bool) -> tuple[int, int]:
    """Return a bounded 4:3 initial window size."""
    base_width = 1280 if naive_nes else 960
    width = min(1920, max(320, int(base_width * scale)))
    return width, width * 3 // 4


def fit_viewport(
    window_size: tuple[int, int],
    source_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    """Center the complete source in the window without stretching it."""
    window_width, window_height = window_size
    source_width, source_height = source_size
    scale = min(window_width / source_width, window_height / source_height)
    width = max(1, round(source_width * scale))
    height = max(1, round(source_height * scale))
    return (window_width - width) // 2, (window_height - height) // 2, width, height


def fit_integer_viewport(
    window_size: tuple[int, int],
    source_size: tuple[int, int] = NES_FRAME_SIZE,
    *,
    pixel_aspect: float = NES_PIXEL_ASPECT,
) -> tuple[int, int, int, int]:
    """Center an integer-scaled viewport with a close NES pixel aspect ratio."""
    window_width, window_height = window_size
    source_width, source_height = source_size
    max_scale_x = max(1, window_width // source_width)
    max_scale_y = max(1, window_height // source_height)
    candidates = (
        (scale_x, scale_y)
        for scale_x in range(1, max_scale_x + 1)
        for scale_y in range(1, max_scale_y + 1)
    )
    scale_x, scale_y = min(
        candidates,
        key=lambda pair: (
            abs((pair[0] / pair[1]) - pixel_aspect),
            -(pair[0] * pair[1]),
        ),
    )
    width = source_width * scale_x
    height = source_height * scale_y
    return (window_width - width) // 2, (window_height - height) // 2, width, height
