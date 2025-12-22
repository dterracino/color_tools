# Palette System Architecture

To support dynamic generation, static presets, and image extraction, we will treat "Palette Generation" as a modular system with three distinct input strategies.

## 1. The Core Object: `Palette`

Regardless of where the colors come from, the output is always the same.

* **Structure:** A standard list of Color objects (Hex/RGB).
* **Metadata:** Name, Origin (e.g., "Generated from Red", "Xmas Preset 1", "Extracted: Deep Mood").

---

## 2. The Three Strategies (Sources)

### A. Procedural Generators (The "Math") 🧮

* **Input:** 1 Base Color + 1 Harmony Config (e.g., "Complementary").
* **Logic:** Uses the "Color Wheel Offsets" and "Variations" (Tints/Shades).
* **Use Case:** "I have a brand color #FF0000, give me a Triadic palette for it."
* **Implementation:** `HarmonyGenerator(base_color, config_name)`

### B. Static Presets (The "Library") 📚

* **Input:** Theme Key (e.g., "holiday_xmas", "retro_vaporwave").
* **Logic:** Lookups in a predefined JSON/Dictionary structure.
* **Use Case:** "Show me 10 cool Christmas palettes."
* **Implementation:** `PresetLibrary.get('christmas')`

### C. Extractors (The "Analysis") 📷

* **Input:** Image File / URL + **Mood** (Filter).
* **Logic:**
    1. **Quantize:** Cluster pixels to find significant colors (e.g., K-Means).
    2. **Filter (Moods):** Select the final palette based on HSL properties.
* **Mood Definitions:**
  * **None (Default):** Pure statistical dominance.
  * **Colorful:** High saturation, distinct hues.
  * **Bright:** High Lightness (>0.5) & High Saturation.
  * **Muted:** Low Saturation (<0.4), Mid-range Lightness.
  * **Deep:** High Saturation (>0.6), Low Lightness (<0.4).
  * **Dark:** Low Lightness (<0.3).
* **Use Case:** "Make a 'Dark' and moody palette from this sunset photo."
* **Implementation:** `ImageExtractor.extract(image_path, mood='dark', count=5)`
* **Example:** <https://color.adobe.com/create/image>

---

## 3. The Unified Interface (The "Manager")

We will build a main `PaletteManager` class that acts as the traffic controller.

```python
# Pseudo-code usage
manager = PaletteManager()

# 1. Math
my_palette = manager.generate(base="#FF0055", type="split_complementary")

# 2. Presets
xmas_palettes = manager.get_presets(tag="christmas")

# 3. Image with Mood
# Returns a Palette object optimized for "Deep" colors
photo_palette = manager.extract_from_image("sunset.jpg", mood="deep")
