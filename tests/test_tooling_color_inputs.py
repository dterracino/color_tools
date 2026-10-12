"""Color-input regressions for source-data adapters without PDF dependencies."""

from __future__ import annotations

from collections.abc import Callable
import io
import json
from pathlib import Path
from runpy import run_path
import tempfile
from types import ModuleType
from typing import cast
import unittest
from unittest.mock import MagicMock, mock_open, patch


_ROOT = Path(__file__).resolve().parents[1]
_Records = list[dict[str, object]]
_BambuParser = Callable[[Path, str, str, str | None], _Records]
_PDFParser = Callable[[Path], _Records]


class TestToolingColorInputs(unittest.TestCase):
    """Source adapters must validate whole color fields, not valid substrings."""

    def test_crayola_source_colors_use_canonical_validation(self) -> None:
        process = cast(
            Callable[[], _Records],
            run_path(str(_ROOT / "tooling" / "generate_crayola_palette.py"))[
                "process_crayola_colors"
            ],
        )
        data: dict[str, object] = {"name": "probe", "rgb": [17, 34, 51], "hex": "#1230"}
        with patch("builtins.open", mock_open(read_data=json.dumps([data]))):
            self.assertEqual(process()[0]["hex"], "#112233")
        for rgb in ([True, 2, 3], [1.0, 2, 3], [-1, 2, 3], [256, 2, 3], [1, 2]):
            data["rgb"] = rgb
            with self.subTest(rgb=rgb), patch(
                "builtins.open", mock_open(read_data=json.dumps([data])),
            ), self.assertRaises(ValueError):
                process()
        data["rgb"] = [17, 34, 51]
        data["hex"] = "#12GG34"
        with patch(
            "builtins.open", mock_open(read_data=json.dumps([data])),
        ), self.assertRaises(ValueError):
            process()

    def test_bambu_both_source_formats_use_compound_parser(self) -> None:
        parser = cast(
            _BambuParser,
            run_path(str(_ROOT / "tooling" / "import_bambu_new.py"))["parse_bambu_file"],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bambu.txt"
            for template in ("Header\nProbe\tHex:{hex}\n", "Header\nProbe\nHex:{hex}\n"):
                for value, expected in (
                    ("aabbcc", "#AABBCC"),
                    ("#1230", "#112233"),
                    ("#f00 / 0f0f;00f", "#FF0000-#00FF00-#0000FF"),
                ):
                    with self.subTest(template=template, value=value):
                        path.write_text(template.format(hex=value), encoding="utf-8")
                        records = parser(path, "Bambu Lab", "PLA", None)
                        self.assertEqual(len(records), 1)
                        self.assertEqual(records[0]["hex"], expected)
                for value in ("#12GG34", "##AABBCC", "#AABBCCjunk", "#f00,,00f"):
                    with self.subTest(template=template, invalid=value):
                        path.write_text(template.format(hex=value), encoding="utf-8")
                        with self.assertRaisesRegex(ValueError, "Probe.*bambu.txt"):
                            parser(path, "Bambu Lab", "PLA", None)

    def test_pdf_color_fields_use_compound_parser(self) -> None:
        for script, function, product in (
            ("extract_panchroma.py", "extract_panchroma_filaments", "Panchroma PLA"),
            ("extract_polymaker.py", "parse_polymaker_pdf", "PolyLite PLA"),
        ):
            page = MagicMock()
            pdf = MagicMock()
            pdf.pages = [page]
            pdf_open = MagicMock()
            pdf_open.return_value.__enter__.return_value = pdf
            module = ModuleType("pdfplumber")
            setattr(module, "open", pdf_open)
            with patch.dict("sys.modules", {"pdfplumber": module}):
                parser = cast(
                    _PDFParser,
                    run_path(str(_ROOT / "tooling" / script))[function],
                )
                for value, expected in (
                    ("aabbcc, #ddeeff", "#AABBCC-#DDEEFF"),
                    ("#1230 / 0f0;00f", "#112233-#00FF00-#0000FF"),
                    ("#f00,\n#00f", "#FF0000-#0000FF"),
                ):
                    page.extract_tables.return_value = [[
                        ["SKU", "Product Name", "Color Name", "HEX Code"],
                        ["probe", product, "Probe", value],
                    ]]
                    with self.subTest(script=script, value=value), patch(
                        "sys.stdout", new_callable=io.StringIO,
                    ):
                        records = parser(Path("probe.pdf"))
                        self.assertEqual(len(records), 1)
                        self.assertEqual(records[0]["hex"], expected)
                for value in ("#12GG34", "##AABBCC", "#AABBCCjunk", "#f00,,00f"):
                    page.extract_tables.return_value = [[
                        ["SKU", "Product Name", "Color Name", "HEX Code"],
                        ["probe", product, "Probe", value],
                    ]]
                    with self.subTest(script=script, invalid=value), patch(
                        "sys.stdout", new_callable=io.StringIO,
                    ), self.assertRaisesRegex(ValueError, "Probe.*page 1"):
                        parser(Path("probe.pdf"))
