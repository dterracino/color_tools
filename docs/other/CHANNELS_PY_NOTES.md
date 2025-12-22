# Channel Extractor

```python
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

CHANNEL_NAMES = {
    "RGB": ["Red", "Green", "Blue"],
    "HSV": ["Hue", "Saturation", "Value"],
    "YCbCr": ["Y", "Cb", "Cr"],
    "CMYK": ["Cyan", "Magenta", "Yellow", "Black"],
    "LAB": ["L", "A", "B"]
}

def normalize_channel(channel):
    ch_min, ch_max = channel.min(), channel.max()
    if ch_max > ch_min:
        norm = (channel - ch_min) * (255.0 / (ch_max - ch_min))
    else:
        norm = channel.copy()
    return norm.astype(np.uint8)

def add_label(img, text):
    labeled = img.convert("RGB")
    draw = ImageDraw.Draw(labeled)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    draw.text((10, 10), text, fill=(255, 0, 0), font=font)
    return labeled

def add_legend(composite, names, suffix, layout):
    """Add a legend strip listing channel names in order."""
    w, h = composite.size
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    if layout == "horizontal":
        legend_height = 30
        new_img = Image.new("RGB", (w, h + legend_height), (255, 255, 255))
        new_img.paste(composite, (0, 0))
        draw = ImageDraw.Draw(new_img)
        step = w // len(names)
        for idx, name in enumerate(names):
            draw.text((idx * step + 10, h + 5), f"{name} ({suffix})", fill=(0, 0, 0), font=font)
    else:  # vertical layout
        legend_width = 150
        new_img = Image.new("RGB", (w + legend_width, h), (255, 255, 255))
        new_img.paste(composite, (0, 0))
        draw = ImageDraw.Draw(new_img)
        step = h // len(names)
        for idx, name in enumerate(names):
            draw.text((w + 10, idx * step + 10), f"{name} ({suffix})", fill=(0, 0, 0), font=font)
    return new_img

def extract_channels(image_path, mode="HSV", output_dir="channels_out",
                     save_raw=True, save_normalized=True, layout="horizontal",
                     compare_raw_normalized=False, add_legends=True):
    """
    Extract channels in a given color space, save raw/normalized versions with labels,
    and create composites. Layout can be 'horizontal' or 'vertical'.
    If compare_raw_normalized=True, builds a combined composite:
      - horizontal mode → raw above normalized
      - vertical mode   → raw beside normalized
    If add_legends=True, adds a legend strip with channel names.
    """
    img = Image.open(image_path)
    converted = img.convert(mode)
    arr = np.array(converted)

    os.makedirs(output_dir, exist_ok=True)
    names = CHANNEL_NAMES.get(mode, [f"Channel_{i}" for i in range(arr.shape[2])])

    raw_channels, norm_channels = [], []

    for i in range(arr.shape[2]):
        ch = arr[:, :, i]

        if save_raw:
            raw_img = Image.fromarray(ch)
            labeled_raw = add_label(raw_img, f"{names[i]} (raw)")
            labeled_raw.save(os.path.join(output_dir, f"{mode}_{names[i]}_raw.png"))
            raw_channels.append(labeled_raw)

        if save_normalized:
            norm = normalize_channel(ch)
            norm_img = Image.fromarray(norm)
            labeled_norm = add_label(norm_img, f"{names[i]} (normalized)")
            labeled_norm.save(os.path.join(output_dir, f"{mode}_{names[i]}_normalized.png"))
            norm_channels.append(labeled_norm)

    def make_composite(ch_list, suffix):
        if not ch_list:
            return None
        width, height = ch_list[0].size
        if layout == "horizontal":
            composite = Image.new("RGB", (width * len(ch_list), height))
            for idx, ch_img in enumerate(ch_list):
                composite.paste(ch_img, (idx * width, 0))
        else:  # vertical layout
            composite = Image.new("RGB", (width, height * len(ch_list)))
            for idx, ch_img in enumerate(ch_list):
                composite.paste(ch_img, (0, idx * height))
        if add_legends:
            composite = add_legend(composite, names, suffix, layout)
        composite.save(os.path.join(output_dir, f"{mode}_channels_composite_{suffix}_{layout}.png"))
        return composite

    raw_comp = make_composite(raw_channels, "raw") if save_raw else None
    norm_comp = make_composite(norm_channels, "normalized") if save_normalized else None

    if compare_raw_normalized and raw_comp and norm_comp:
        w, h = raw_comp.size
        if layout == "horizontal":
            combined = Image.new("RGB", (w, h * 2))
            combined.paste(raw_comp, (0, 0))
            combined.paste(norm_comp, (0, h))
        else:  # vertical layout
            combined = Image.new("RGB", (w * 2, h))
            combined.paste(raw_comp, (0, 0))
            combined.paste(norm_comp, (w, 0))
        combined.save(os.path.join(output_dir, f"{mode}_channels_composite_compare.png"))

    print(f"Saved {len(names)} {mode} channels with labels and legends (raw={save_raw}, normalized={save_normalized}, layout={layout}, compare={compare_raw_normalized}) to {output_dir}")


# Example usage:
extract_channels("your_image.jpg", mode="HSV", save_raw=True, save_normalized=True,
                 layout="horizontal", compare_raw_normalized=True, add_legends=True)

extract_channels("your_image.jpg", mode="CMYK", save_raw=True, save_normalized=True,
                 layout="vertical", compare_raw_normalized=True, add_legends=True)

```
