"""
Vercel serverless function: Filament of the Day

Returns an SVG image showing today's filament, deterministically selected from
the color_tools filament database using the current date as a seed.
The same date always produces the same filament — no state required.
"""

from __future__ import annotations

import hashlib
from datetime import date
from http.server import BaseHTTPRequestHandler


def _today_index(count: int) -> int:
    """Deterministically map today's date to an index in [0, count)."""
    # Use a different salt than color_of_day so the two don't cycle together
    today = f"filament:{date.today().isoformat()}"
    hash_val = int(hashlib.sha256(today.encode()).hexdigest(), 16)
    return hash_val % count


def _foreground(hex_color: str) -> str:
    """Return #000000 or #ffffff depending on background luminance."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#000000" if luminance > 0.5 else "#ffffff"


def _build_svg(filament) -> str:
    bg = filament.hex if filament.hex.startswith("#") else f"#{filament.hex}"
    r, g, b = filament.rgb
    hex_upper = bg.upper()
    maker = filament.maker
    material = filament.type
    finish = f" · {filament.finish}" if filament.finish else ""
    color_name = filament.color
    try:
        today = date.today().strftime("%B %-d, %Y")
    except ValueError:
        # Windows doesn't support %-d
        today = date.today().strftime("%B %d, %Y").replace(" 0", " ")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="520" height="90" role="img" aria-label="Filament of the Day: {color_name} by {maker}">
  <title>Filament of the Day: {color_name} by {maker}</title>
  <!-- background -->
  <rect width="520" height="90" rx="10" fill="#0d1117"/>
  <!-- color swatch -->
  <rect x="0" y="0" width="90" height="90" rx="10" fill="{bg}"/>
  <rect x="82" y="0" width="16" height="90" fill="{bg}"/>
  <!-- label -->
  <text x="116" y="22" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        font-size="11" fill="#8b949e" letter-spacing="0.08em">FILAMENT OF THE DAY · {today}</text>
  <!-- color name -->
  <text x="116" y="50" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        font-size="22" font-weight="700" fill="#ffffff">{color_name}</text>
  <!-- maker + material + hex -->
  <text x="116" y="68" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        font-size="12" fill="#8b949e">{maker} · {material}{finish}</text>
  <text x="116" y="82" font-family="'SF Mono','Fira Code','Consolas',monospace"
        font-size="11" fill="#6e7681">{hex_upper} · rgb({r}, {g}, {b})</text>
</svg>"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        from color_tools.filament_palette import FilamentPalette

        fp = FilamentPalette.load_default()
        filaments = sorted(fp.filaments, key=lambda f: (f.maker, f.type, f.color))
        filament = filaments[_today_index(len(filaments))]
        svg = _build_svg(filament)

        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=3600, s-maxage=3600")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(svg.encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002
        pass  # suppress default access log noise
