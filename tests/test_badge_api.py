"""Tests for the public Vercel badge endpoints in the root ``api`` folder."""

from __future__ import annotations

import hashlib
import io
import unittest
from datetime import date
from typing import cast
from unittest.mock import patch

from api import color_of_day, filament_of_day
from color_tools.filament_palette import FilamentPalette, FilamentRecord
from color_tools.palette import ColorRecord, Palette


class _ResponseProbe:
    """Capture the observable output of a serverless request handler."""

    def __init__(self) -> None:
        self.status: int | None = None
        self.headers: list[tuple[str, str]] = []
        self.wfile = io.BytesIO()

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, name: str, value: str) -> None:
        self.headers.append((name, value))

    def end_headers(self) -> None:
        pass


class _FixedDate:
    """Provide a stable date for badge output tests."""

    @classmethod
    def today(cls) -> date:
        return date(2026, 10, 6)


class _FallbackDate:
    """Exercise the portable date-format fallback used on Windows."""

    @classmethod
    def today(cls) -> _FallbackDate:
        return cls()

    def isoformat(self) -> str:
        return "2026-10-06"

    def strftime(self, format_string: str) -> str:
        if "%-d" in format_string:
            raise ValueError("Unsupported format directive")
        return "October 06, 2026"


class TestColorOfDayApi(unittest.TestCase):
    """Verify deterministic selection, SVG output, and HTTP response details."""

    def setUp(self) -> None:
        self.color = ColorRecord.from_rgb((17, 34, 51), name="deep-blue")

    def test_today_index_is_stable_and_bounded(self) -> None:
        with patch.object(color_of_day, "date", _FixedDate):
            result = color_of_day._today_index(17)

        expected = int(
            hashlib.sha256(b"2026-10-06").hexdigest(),
            16,
        ) % 17
        self.assertEqual(result, expected)

    def test_svg_contains_color_and_portable_date(self) -> None:
        with patch.object(color_of_day, "date", _FallbackDate):
            svg = color_of_day._build_svg(self.color)

        self.assertIn("Color of the Day: Deep Blue", svg)
        self.assertIn('fill="#112233"', svg)
        self.assertIn("#112233 · rgb(17, 34, 51)", svg)
        self.assertIn("October 6, 2026", svg)

    def test_get_returns_svg_with_cache_and_security_headers(self) -> None:
        probe = _ResponseProbe()
        palette = Palette([self.color])
        with (
            patch.object(Palette, "load_default", return_value=palette),
            patch.object(color_of_day, "_today_index", return_value=0),
            patch.object(color_of_day, "date", _FixedDate),
        ):
            color_of_day.handler.do_GET(
                cast(color_of_day.handler, probe)
            )

        self.assertEqual(probe.status, 200)
        self.assertIn(
            ("Content-Type", "image/svg+xml; charset=utf-8"),
            probe.headers,
        )
        self.assertIn(
            ("Cache-Control", "public, max-age=3600, s-maxage=3600"),
            probe.headers,
        )
        self.assertIn(("X-Content-Type-Options", "nosniff"), probe.headers)
        self.assertIn(b"Color of the Day: Deep Blue", probe.wfile.getvalue())

    def test_request_logging_is_suppressed(self) -> None:
        color_of_day.handler.log_message(
            cast(color_of_day.handler, _ResponseProbe()),
            "%s",
            "ignored",
        )


class TestFilamentOfDayApi(unittest.TestCase):
    """Verify deterministic filament badge selection and HTTP output."""

    def setUp(self) -> None:
        self.filament = FilamentRecord(
            id="maker-pla-matte-red",
            maker="Maker",
            type="PLA",
            finish="Matte",
            color="Deep Red",
            hex="#AA1122",
        )

    def test_today_index_is_stable_and_namespaced(self) -> None:
        with patch.object(filament_of_day, "date", _FixedDate):
            result = filament_of_day._today_index(17)

        expected = int(
            hashlib.sha256(b"filament:2026-10-06").hexdigest(),
            16,
        ) % 17
        self.assertEqual(result, expected)

    def test_svg_contains_filament_details_and_portable_date(self) -> None:
        with patch.object(filament_of_day, "date", _FallbackDate):
            svg = filament_of_day._build_svg(self.filament)

        self.assertIn("Filament of the Day: Deep Red by Maker", svg)
        self.assertIn('fill="#AA1122"', svg)
        self.assertIn("Maker · PLA · Matte", svg)
        self.assertIn("#AA1122 · rgb(170, 17, 34)", svg)
        self.assertIn("October 6, 2026", svg)

    def test_svg_omits_separator_when_finish_is_missing(self) -> None:
        filament = FilamentRecord(
            id="maker-petg-blue",
            maker="Maker",
            type="PETG",
            finish=None,
            color="Blue",
            hex="#0000FF",
        )
        with patch.object(filament_of_day, "date", _FixedDate):
            svg = filament_of_day._build_svg(filament)

        self.assertIn("Maker · PETG</text>", svg)
        self.assertNotIn("Maker · PETG ·", svg)

    def test_get_returns_sorted_filament_badge(self) -> None:
        later = FilamentRecord(
            id="zeta-pla-blue",
            maker="Zeta",
            type="PLA",
            finish=None,
            color="Blue",
            hex="#0000FF",
        )
        probe = _ResponseProbe()
        palette = FilamentPalette([later, self.filament])
        with (
            patch.object(
                FilamentPalette,
                "load_default",
                return_value=palette,
            ),
            patch.object(filament_of_day, "_today_index", return_value=0),
            patch.object(filament_of_day, "date", _FixedDate),
        ):
            filament_of_day.handler.do_GET(
                cast(filament_of_day.handler, probe)
            )

        self.assertEqual(probe.status, 200)
        self.assertIn(
            ("Content-Type", "image/svg+xml; charset=utf-8"),
            probe.headers,
        )
        self.assertIn(
            ("Cache-Control", "public, max-age=3600, s-maxage=3600"),
            probe.headers,
        )
        self.assertIn(("X-Content-Type-Options", "nosniff"), probe.headers)
        self.assertIn(b"Deep Red", probe.wfile.getvalue())
        self.assertNotIn(b"Zeta", probe.wfile.getvalue())

    def test_request_logging_is_suppressed(self) -> None:
        filament_of_day.handler.log_message(
            cast(filament_of_day.handler, _ResponseProbe()),
            "%s",
            "ignored",
        )


if __name__ == "__main__":
    unittest.main()
