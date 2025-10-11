# In your Python script or REPL
from color_tools import rgb_to_lab, delta_e_2000, Palette

# Convert a color
lab = rgb_to_lab((255, 128, 64))
print(f"LAB: {lab}")

# Load the palette
palette = Palette.load_default()
print(f"Loaded {len(palette.records)} colors!")

# Find nearest color
nearest, distance = palette.nearest_color(lab)
print(f"Nearest: {nearest.name} (ΔE={distance:.2f})")