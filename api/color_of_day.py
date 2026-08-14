"""
Vercel serverless function: Color of the Day

Returns an SVG image showing today's color, deterministically selected from
the color_tools CSS color database using the current date as a seed.
The same date always produces the same color - no state required.
"""

from __future__ import annotations

import hashlib
from datetime import date
from http.server import BaseHTTPRequestHandler


def _today_index(count: int) -> int:
    """Deterministically map today's date to an index in [0, count)."""
    today = date.today().isoformat()
    hash_val = int(hashlib.sha256(today.encode()).hexdigest(), 16)
    return hash_val % count


def _build_svg(color) -> str:
    bg = color.hex if color.hex.startswith("#") else f"#{color.hex}"
    name = color.name.replace("-", " ").title()
    hex_upper = bg.upper()
    r, g, b = color.rgb
    try:
        today = date.today().strftime("%B %-d, %Y")
    except ValueError:
        today = date.today().strftime("%B %d, %Y").replace(" 0", " ")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="520" height="90" role="img" aria-label="Color of the Day: {name}">
  <title>Color of the Day: {name}</title>
  <rect width="520" height="90" rx="10" fill="#0d1117"/>
  <rect x="0" y="0" width="90" height="90" rx="10" fill="{bg}"/>
  <rect x="82" y="0" width="16" height="90" fill="{bg}"/>
  <text x="116" y="22" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        font-size="11" fill="#8b949e" letter-spacing="0.08em">COLOR OF THE DAY · {today}</text>
  <text x="116" y="52" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
        font-size="24" font-weight="700" fill="#ffffff">{name}</text>
  <text x="116" y="72" font-family="'SF Mono','Fira Code','Consolas',monospace"
        font-size="13" fill="#8b949e">{hex_upper} · rgb({r}, {g}, {b})</text>
</svg>"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        from color_tools.palette import Palette

        palette = Palette.load_default()
        colors = sorted(palette.records, key=lambda c: c.name)
        color = colors[_today_index(len(colors))]
        svg = _build_svg(color)

        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=3600, s-maxage=3600")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(svg.encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002
        pass
