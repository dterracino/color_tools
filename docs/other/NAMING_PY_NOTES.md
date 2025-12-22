# NAMING.PY COMPARISON CODE

It might make sense when naming a color to have both the looked up name and the generated name (or friendly name) in the ColorRecord object itself. So we instantiate a new ColorRecord with our hex code (or whatever), and we will get all the various color space values for that color, and the names. It would be better for the code to be encapsulated like that.

I don't think thre's any way right now for a ColorRecord to self-populate; and I'm not even sure if there's a function that takes an arbitrary color code and gives you back a ColorRecord, but I can certainly see the uses. We would have to discuss actual implementation.

```python
def describe_color(hue_deg, saturation, lightness):
    """
    Generate a descriptive color name from hue (0-360), saturation (0-1), and lightness (0-1),
    including:
      - Blended names like 'reddish orange' with dynamic thresholds
      - 'Pure' names like 'pure blue-green' when near exact midpoints
    """
    # --- Input validation ---
    if not all(isinstance(v, (int, float)) for v in (hue_deg, saturation, lightness)):
        raise ValueError("Hue, saturation, and lightness must be numeric.")
    if not (0 <= hue_deg <= 360):
        raise ValueError("Hue must be between 0 and 360 degrees.")
    if not (0 <= saturation <= 1):
        raise ValueError("Saturation must be between 0 and 1.")
    if not (0 <= lightness <= 1):
        raise ValueError("Lightness must be between 0 and 1.")

    # --- Base color mapping (boundaries in degrees) ---
    hue_ranges = [
        (0, "red"),
        (15, "orange"),
        (45, "yellow"),
        (75, "green"),
        (150, "cyan"),
        (210, "blue"),
        (270, "purple"),
        (300, "magenta"),
        (345, "red")  # wrap-around
    ]

    base_color = None
    for i, (boundary, color) in enumerate(hue_ranges):
        next_boundary, next_name = hue_ranges[(i + 1) % len(hue_ranges)]

        # Handle wrap-around segment (e.g., magenta → red)
        if boundary < next_boundary:
            in_segment = boundary <= hue_deg < next_boundary
            segment_width = next_boundary - boundary
        else:
            in_segment = hue_deg >= boundary or hue_deg < next_boundary
            segment_width = (360 - boundary) + next_boundary

        if in_segment:
            base_color = color
            # Dynamic blend threshold: 20% of segment width
            blend_threshold = segment_width * 0.2
            # Midpoint tolerance: ±2 degrees
            midpoint_tolerance = 2

            # Distance to next and previous boundaries
            dist_to_next = (next_boundary - hue_deg) % 360
            dist_to_prev = (hue_deg - boundary) % 360

            # Calculate midpoint between colors
            midpoint = (boundary + segment_width / 2) % 360
            dist_to_mid = min((hue_deg - midpoint) % 360, (midpoint - hue_deg) % 360)

            # Check for pure midpoint case
            if dist_to_mid <= midpoint_tolerance:
                base_color = f"pure {color}-{next_name}"
            elif dist_to_next < blend_threshold and dist_to_next != 0:
                base_color = f"{color}ish {next_name}"
            elif dist_to_prev < blend_threshold and dist_to_prev != 0:
                base_color = f"{next_name}ish {color}"
            break

    # --- Lightness-based adjective ---
    if lightness <= 0.15:
        light_adj = "very dark"
    elif lightness <= 0.35:
        light_adj = "dark"
    elif lightness <= 0.65:
        light_adj = ""
    elif lightness <= 0.85:
        light_adj = "light"
    else:
        light_adj = "very light"

    # --- Saturation-based adjective ---
    if saturation >= 0.8:
        sat_adj = "vivid"
    elif saturation >= 0.55:
        sat_adj = "bright"
    elif saturation >= 0.3:
        sat_adj = "muted"
    else:
        sat_adj = "pastel"

    # --- Combine adjectives ---
    adjectives = [light_adj, sat_adj]
    adjectives = [adj for adj in adjectives if adj]  # remove empty
    return " ".join(adjectives + [base_color])


# --- Example usage ---
if __name__ == "__main__":
    test_values = [
        (0, 1.0, 0.5),     # vivid red
        (14, 0.7, 0.6),    # bright reddish orange
        (22.5, 0.9, 0.5),  # vivid pure red-orange (midpoint)
        (40, 0.6, 0.8),    # light bright yellowish orange
        (120, 0.3, 0.4),   # dark muted green
        (145, 0.9, 0.5),   # vivid greenish cyan
        (180, 0.85, 0.5),  # vivid pure cyan-green (midpoint)
        (250, 0.1, 0.9),   # very light pastel blue
        (310, 0.85, 0.2)   # very dark vivid magenta
    ]

    for hue, sat, light in test_values:
        print(f"H={hue}, S={sat}, L={light} → {describe_color(hue, sat, light)}")
```
