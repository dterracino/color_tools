import json
import math
import colorsys

def srgb_to_linear(x):
    """
    Converts an sRGB value (0-1) to linear RGB.
    Applies gamma correction.
    """
    if x <= 0.04045:
        return x / 12.92
    else:
        return ((x + 0.055) / 1.055) ** 2.4

def rgb_to_xyz(r, g, b):
    """
    Converts sRGB (0-255) to CIE XYZ (D65).
    """
    # Normalize and convert to linear
    rn = srgb_to_linear(r / 255.0)
    gn = srgb_to_linear(g / 255.0)
    bn = srgb_to_linear(b / 255.0)

    # sRGB to XYZ Matrix (D65)
    x = rn * 0.4124564 + gn * 0.3575761 + bn * 0.1804375
    y = rn * 0.2126729 + gn * 0.7151522 + bn * 0.0721750
    z = rn * 0.0193339 + gn * 0.1191920 + bn * 0.9503041

    # Scale XYZ for LAB calculation (Reference White Y=100)
    return x * 100.0, y * 100.0, z * 100.0

def xyz_to_lab(x, y, z):
    """
    Converts CIE XYZ to CIE L*a*b*.
    Reference White: D65 (X=95.047, Y=100.000, Z=108.883)
    """
    ref_x = 95.047
    ref_y = 100.000
    ref_z = 108.883

    x /= ref_x
    y /= ref_y
    z /= ref_z

    def func(t):
        if t > 0.008856:
            return t ** (1/3)
        else:
            return (7.787 * t) + (16 / 116)

    fx = func(x)
    fy = func(y)
    fz = func(z)

    l_val = (116 * fy) - 16
    a_val = 500 * (fx - fy)
    b_val = 200 * (fy - fz)

    return round(l_val, 1), round(a_val, 1), round(b_val, 1)

def lab_to_lch(l, a, b):
    """
    Converts CIE L*a*b* to CIE L*C*h.
    """
    c = math.sqrt(a**2 + b**2)
    h = math.degrees(math.atan2(b, a))
    
    if h < 0:
        h += 360

    return round(l, 1), round(c, 1), round(h, 1)

def rgb_to_hsl(r, g, b):
    """
    Converts RGB (0-255) to HSL (0-360, 0-100, 0-100).
    """
    # colorsys uses 0-1 inputs
    h, l, s = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
    
    return round(h * 360, 1), round(s * 100, 1), round(l * 100, 1)

def generate_palette():
    """
    Generates the full TurboGrafx-16 palette in the requested JSON format.
    """
    levels = [0, 36, 72, 108, 144, 180, 216, 252]
    palette_data = []
    
    index = 0
    for r in levels:
        for g in levels:
            for b in levels:
                # 1. Hex
                hex_val = f"#{r:02X}{g:02X}{b:02X}"
                
                # 2. RGB
                rgb_val = [r, g, b]
                
                # 3. HSL
                hsl_val = list(rgb_to_hsl(r, g, b))
                
                # 4. LAB
                x, y, z = rgb_to_xyz(r, g, b)
                lab_val = list(xyz_to_lab(x, y, z))
                
                # 5. LCH
                lch_val = list(lab_to_lch(*lab_val))
                
                # Construct Object
                color_obj = {
                    "name": f"tg16_{index:03d}", # e.g. tg16_000, tg16_001
                    "hex": hex_val,
                    "rgb": rgb_val,
                    "hsl": hsl_val,
                    "lab": lab_val,
                    "lch": lch_val
                }
                
                palette_data.append(color_obj)
                index += 1
                
    return palette_data

if __name__ == "__main__":
    full_palette = generate_palette()
    
    # Save to file
    filename = "tg16_complete_palette.json"
    with open(filename, "w") as f:
        json.dump(full_palette, f, indent=2)
        
    print(f"Successfully generated {len(full_palette)} colors into '{filename}'.")