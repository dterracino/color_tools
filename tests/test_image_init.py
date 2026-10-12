"""Tests for the lazy public API in :mod:`color_tools.image`."""

from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
import unittest

import color_tools.image as image


class TestImageExports(unittest.TestCase):
    """The runtime and static public export declarations must stay aligned."""

    def test_all_matches_export_table(self) -> None:
        self.assertEqual(image.__all__, ["IMAGE_AVAILABLE", *image._EXPORTS])

    def test_type_checking_imports_match_export_table(self) -> None:
        source_path = Path(image.__file__)
        module = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_names: set[str] = set()

        for node in module.body:
            if not (
                isinstance(node, ast.If)
                and isinstance(node.test, ast.Name)
                and node.test.id == "TYPE_CHECKING"
            ):
                continue
            for statement in node.body:
                if isinstance(statement, ast.ImportFrom):
                    imported_names.update(
                        alias.asname or alias.name for alias in statement.names
                    )

        self.assertEqual(imported_names, set(image._EXPORTS))

    def test_watermark_exports_are_complete(self) -> None:
        self.assertTrue(
            {
                "add_text_watermark",
                "add_image_watermark",
                "add_svg_watermark",
            }.issubset(image._EXPORTS)
        )

    def test_png_writer_is_not_an_image_export(self) -> None:
        self.assertNotIn("SimplePNGWriter", image._EXPORTS)
        self.assertNotIn("SimplePNGWriter", image.__all__)
        self.assertFalse(hasattr(image, "SimplePNGWriter"))

    def test_dir_includes_lazy_exports(self) -> None:
        self.assertTrue(set(image.__all__).issubset(dir(image)))


class TestLazyRuntime(unittest.TestCase):
    """Fresh interpreters verify import and dependency behavior in isolation."""

    @staticmethod
    def _run(code: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
            timeout=30,
            check=False,
        )

    def test_package_import_does_not_load_optional_dependencies(self) -> None:
        result = self._run(
            """
import sys
import color_tools.image as image

for name in ("PIL", "numpy", "skimage", "pillow_heif", "cairosvg", "cv2", "sklearn"):
    assert name not in sys.modules, name
assert not any(name.startswith("color_tools.image.") for name in sys.modules)
assert isinstance(image.IMAGE_AVAILABLE, bool)
"""
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_access_loads_only_the_owning_submodule_and_caches_value(self) -> None:
        result = self._run(
            """
import sys
import color_tools.image as image

first = image.add_text_watermark
second = image.add_text_watermark
assert first is second
assert first.__module__ == "color_tools.image.watermark"
assert "color_tools.image.watermark" in sys.modules
for name in ("numpy", "skimage", "cv2", "sklearn"):
    assert name not in sys.modules, name
"""
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_pillow_error_is_precise_and_chained(self) -> None:
        result = self._run(
            """
import sys
sys.modules["PIL"] = None

import color_tools.image as image
assert image.IMAGE_AVAILABLE is False

try:
    image.add_text_watermark
except ImportError as exc:
    assert "Pillow" in str(exc)
    assert "add_text_watermark" in str(exc)
    assert exc.__cause__ is not None
    assert getattr(exc.__cause__, "name", None) == "PIL"
else:
    raise AssertionError("missing Pillow did not raise ImportError")
"""
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_opencv_does_not_disable_watermark_exports(self) -> None:
        result = self._run(
            """
import sys
sys.modules["cv2"] = None

import color_tools.image as image
assert image.add_text_watermark.__module__ == "color_tools.image.watermark"

try:
    image.DominantColor
except ImportError as exc:
    assert "OpenCV" in str(exc)
    assert "DominantColor" in str(exc)
    assert exc.__cause__ is not None
    assert getattr(exc.__cause__, "name", None) == "cv2"
else:
    raise AssertionError("missing OpenCV did not raise ImportError")
"""
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unexpected_import_error_propagates_unchanged(self) -> None:
        result = self._run(
            """
import color_tools.image as image

failure = ImportError("internal failure", name="color_tools.internal_bug")

def fail_import(name, package):
    raise failure

image.import_module = fail_import
try:
    image.convert_image
except ImportError as exc:
    assert exc is failure
    assert exc.__cause__ is None
else:
    raise AssertionError("unexpected ImportError was hidden")
"""
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_dependencies_do_not_create_fake_exports(self) -> None:
        result = self._run(
            """
import sys
sys.modules["PIL"] = None
sys.modules["numpy"] = None

import color_tools.image as image
assert image.ColorCluster.__module__ == "color_tools.image.analysis"
assert image.ColorChange.__module__ == "color_tools.image.analysis"
assert image.BLEND_MODES
assert image.BLEND_MODES["multiply"].__module__ == "color_tools.image.blend"
"""
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unknown_attribute_raises_attribute_error(self) -> None:
        result = self._run(
            """
import color_tools.image as image
assert not hasattr(image, "no_such_name")
try:
    image.no_such_name
except AttributeError:
    pass
else:
    raise AssertionError("unknown name did not raise AttributeError")
"""
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
