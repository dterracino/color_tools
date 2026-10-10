"""CPU baseline for converting a static image into a naive NES-like frame."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from color_tools import delta_e_2000_array, load_palette, rgb_to_lab_array
from numpy.typing import NDArray
from PIL import Image
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn


RGBFrame = NDArray[np.uint8]
FloatArray = NDArray[np.float64]
IndexArray = NDArray[np.intp]
NES_FRAME_SIZE = (256, 240)
_SOURCE_COLOR_LIMIT = 25
_BAYER_4X4 = np.asarray(
    (
        (0, 8, 2, 10),
        (12, 4, 14, 6),
        (3, 11, 1, 9),
        (15, 7, 13, 5),
    ),
    dtype=np.float64,
)


@dataclass(frozen=True, slots=True)
class NaiveNesResult:
    """Processed framebuffer and palette-reduction statistics."""

    frame: RGBFrame
    source_color_count: int
    allowed_color_count: int
    nes_color_count: int


def _crop_and_resize(frame: RGBFrame) -> RGBFrame:
    """Center-crop to 4:3 display composition and resample to 256×240."""
    source_height, source_width = frame.shape[:2]
    target_aspect = 4.0 / 3.0
    source_aspect = source_width / source_height
    if source_aspect > target_aspect:
        crop_width = round(source_height * target_aspect)
        left = (source_width - crop_width) // 2
        box = (left, 0, left + crop_width, source_height)
    else:
        crop_height = round(source_width / target_aspect)
        top = (source_height - crop_height) // 2
        box = (0, top, source_width, top + crop_height)

    image = Image.fromarray(frame)
    resized = image.crop(box).resize(NES_FRAME_SIZE, Image.Resampling.LANCZOS)
    return np.array(resized, dtype=np.uint8, copy=True)


def _representative_colors(frame: RGBFrame) -> RGBFrame:
    """Use median-cut bin quantization to find representative source colors."""
    image = Image.fromarray(frame)
    quantized = image.quantize(
        colors=_SOURCE_COLOR_LIMIT,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    quantized_rgb = np.asarray(quantized.convert("RGB"), dtype=np.uint8)
    colors, counts = np.unique(
        np.reshape(quantized_rgb, (-1, 3)),
        axis=0,
        return_counts=True,
    )
    return np.asarray(colors[np.argsort(-counts)], dtype=np.uint8)


def _allowed_nes_colors(source_colors: RGBFrame) -> tuple[RGBFrame, FloatArray]:
    """Map representative source colors into the NES palette with CIEDE2000."""
    nes_rgb = np.asarray(
        [record.rgb for record in load_palette("nes").records],
        dtype=np.uint8,
    )
    source_lab = rgb_to_lab_array(source_colors)
    nes_lab = rgb_to_lab_array(nes_rgb)
    distances = delta_e_2000_array(source_lab[:, np.newaxis, :], nes_lab[np.newaxis, :, :])
    ranked = np.argsort(distances, axis=1)
    selected: list[int] = []
    for rank in range(ranked.shape[1]):
        for source_index in range(ranked.shape[0]):
            nes_index = int(ranked[source_index, rank])
            if nes_index not in selected:
                selected.append(nes_index)
                if len(selected) == _SOURCE_COLOR_LIMIT:
                    break
        if len(selected) == _SOURCE_COLOR_LIMIT:
            break
    unique_indices = np.asarray(selected, dtype=np.intp)
    return nes_rgb[unique_indices], nes_lab[unique_indices]


def _nearest_two(image_lab: FloatArray, palette_lab: FloatArray) -> tuple[IndexArray, IndexArray]:
    """Return the two nearest allowed palette entries for every framebuffer pixel."""
    distances = delta_e_2000_array(
        image_lab[:, :, np.newaxis, :],
        palette_lab[np.newaxis, np.newaxis, :, :],
    )
    if palette_lab.shape[0] == 1:
        only = np.zeros(image_lab.shape[:2], dtype=np.intp)
        return only, only
    pair = np.argpartition(distances, kth=1, axis=2)[:, :, :2]
    pair_distances = np.take_along_axis(distances, pair, axis=2)
    ordered = np.argsort(pair_distances, axis=2)
    pair = np.take_along_axis(pair, ordered, axis=2)
    return np.asarray(pair[:, :, 0], dtype=np.intp), np.asarray(pair[:, :, 1], dtype=np.intp)


def _ordered_dither(
    image_lab: FloatArray,
    palette_rgb: RGBFrame,
    palette_lab: FloatArray,
    strength: float,
) -> RGBFrame:
    """Alternate strictly between the two nearest allowed colors on the NES grid."""
    nearest, second = _nearest_two(image_lab, palette_lab)
    if strength <= 0.0 or palette_lab.shape[0] == 1:
        return np.asarray(palette_rgb[nearest], dtype=np.uint8)

    first_lab = palette_lab[nearest]
    second_lab = palette_lab[second]
    direction = second_lab - first_lab
    denominator = np.sum(direction * direction, axis=2)
    numerator = np.sum((image_lab - first_lab) * direction, axis=2)
    mix = np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator),
        where=denominator > 0.0,
    )
    mix = np.minimum(np.maximum(mix, 0.0), 1.0) * strength
    threshold = np.tile((_BAYER_4X4 + 0.5) / 16.0, (60, 64))
    selected = np.where(threshold < mix, second, nearest)
    return np.asarray(palette_rgb[selected], dtype=np.uint8)


def process_naive_nes(
    frame: RGBFrame,
    dither_strength: float,
    *,
    console: Console | None = None,
) -> NaiveNesResult:
    """Build a deterministic 256×240 naive NES baseline from a static RGB frame."""
    output = console or Console()
    progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        console=output,
    )
    with progress:
        task = progress.add_task("[cyan]Mapping source into the 256x240 framebuffer", total=5)
        resized = _crop_and_resize(frame)
        progress.advance(task)
        progress.console.print("[green]OK[/green] Mapped source into an exact 256x240 framebuffer")
        progress.update(task, description="[cyan]Bin-quantizing source palette to 25 colors")
        source_colors = _representative_colors(resized)
        progress.advance(task)
        progress.console.print(f"[green]OK[/green] Selected {len(source_colors)} median-cut source bins")
        progress.update(task, description="[cyan]Converting RGB palettes to CIELAB")
        image_lab = rgb_to_lab_array(resized)
        progress.advance(task)
        progress.console.print("[green]OK[/green] Converted framebuffer RGB values to CIELAB")
        progress.update(task, description="[cyan]Mapping source bins into the NES LAB palette")
        palette_rgb, palette_lab = _allowed_nes_colors(source_colors)
        progress.advance(task)
        progress.console.print(
            f"[green]OK[/green] Built a {len(palette_rgb)}-color NES candidate palette"
        )
        progress.update(task, description="[cyan]Applying two-candidate grid-aligned dithering")
        result = _ordered_dither(image_lab, palette_rgb, palette_lab, dither_strength)
        progress.advance(task)
        progress.console.print("[green]OK[/green] Applied grid-aligned two-candidate dithering")

    unique_output = np.unique(np.reshape(result, (-1, 3)), axis=0)
    output.print(
        "[green]Naive NES baseline complete:[/green] "
        f"256x240, {len(source_colors)} source bins, "
        f"{len(palette_rgb)} allowed / {len(unique_output)} used NES colors, "
        f"dither={dither_strength:.2f}"
    )
    return NaiveNesResult(
        frame=np.ascontiguousarray(result, dtype=np.uint8),
        source_color_count=len(source_colors),
        allowed_color_count=len(palette_rgb),
        nes_color_count=len(unique_output),
    )
