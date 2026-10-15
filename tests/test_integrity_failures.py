"""Failure-contract tests for core and user data integrity helpers."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from color_tools.constants import ColorConstants


class TestCoreDataIntegrityFailures(unittest.TestCase):
    """Exercise missing and modified core-data verification paths."""

    def test_verify_data_file_returns_false_for_missing_file(self) -> None:
        """A missing protected file cannot pass integrity verification."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            self.assertFalse(ColorConstants.verify_data_file(path, "0" * 64))

    def test_verify_data_file_normalizes_windows_line_endings(self) -> None:
        """Equivalent LF and CRLF text has the same protected-data hash."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            path.write_bytes(b"first\r\nsecond\r\n")
            expected = ColorConstants.generate_user_data_hash(path)
            path.write_bytes(b"first\nsecond\n")
            self.assertTrue(ColorConstants.verify_data_file(path, expected))

    def test_verify_all_data_files_accumulates_every_failure(self) -> None:
        """Core databases and palettes report all failures in one pass."""
        with TemporaryDirectory() as directory:
            data_dir = Path(directory)
            with patch.object(
                ColorConstants,
                "_registered_palette_hashes",
                return_value=(("test-system.json", "a" * 64),),
            ):
                valid, errors = ColorConstants.verify_all_data_files(data_dir)

        self.assertFalse(valid)
        self.assertEqual(len(errors), 4)
        self.assertTrue(any("colors.json integrity check FAILED" in error for error in errors))
        self.assertTrue(any("filaments.json integrity check FAILED" in error for error in errors))
        self.assertTrue(
            any("maker_synonyms.json integrity check FAILED" in error for error in errors)
        )
        self.assertTrue(
            any("test-system.json integrity check FAILED" in error for error in errors)
        )

    def test_verify_all_data_files_reports_only_modified_file(self) -> None:
        """A single hash mismatch does not create unrelated failures."""
        with TemporaryDirectory() as directory:
            data_dir = Path(directory)

            def verify(path: Path, _expected_hash: str) -> bool:
                return path.name != "filaments.json"

            with (
                patch.object(ColorConstants, "verify_data_file", side_effect=verify),
                patch.object(ColorConstants, "_registered_palette_hashes", return_value=()),
            ):
                valid, errors = ColorConstants.verify_all_data_files(data_dir)

        self.assertFalse(valid)
        self.assertEqual(errors, [
            f"filaments.json integrity check FAILED: {data_dir / 'filaments.json'}"
        ])


class TestUserDataIntegrityFailures(unittest.TestCase):
    """Exercise user hash creation and verification boundaries."""

    def test_generate_hash_rejects_missing_file(self) -> None:
        """Hash generation identifies the missing user file."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            with self.assertRaisesRegex(FileNotFoundError, "missing.json"):
                ColorConstants.generate_user_data_hash(path)

    def test_save_hash_rejects_missing_file(self) -> None:
        """Saving a sidecar cannot create one for a missing data file."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            with self.assertRaisesRegex(FileNotFoundError, "missing.json"):
                ColorConstants.save_user_data_hash(path)

    def test_save_supplied_hash_does_not_recalculate(self) -> None:
        """A caller-supplied digest is written exactly as supplied."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "user-colors.json"
            path.write_text("[]", encoding="utf-8")
            supplied = "f" * 64
            with patch.object(
                ColorConstants,
                "generate_user_data_hash",
                side_effect=AssertionError("hash should not be recalculated"),
            ):
                sidecar = ColorConstants.save_user_data_hash(path, supplied)

            self.assertEqual(
                sidecar.read_text(encoding="utf-8"),
                f"{supplied}  {path.name}\n",
            )

    def test_verify_missing_user_file(self) -> None:
        """Direct user-file verification reports a missing input."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            valid, error = ColorConstants.verify_user_data_file(path)
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertIn("User data file not found", error or "")

    def test_verify_without_sidecar_is_an_unverified_success(self) -> None:
        """User files remain optional to hash for backward compatibility."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "user-colors.json"
            path.write_text("[]", encoding="utf-8")
            self.assertEqual(
                ColorConstants.verify_user_data_file(path),
                (True, None),
            )

    def test_verify_empty_and_malformed_sidecars_fail(self) -> None:
        """Empty and non-digest sidecars cannot validate a user file."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "user-colors.json"
            path.write_text("[]", encoding="utf-8")
            sidecar = path.with_suffix(".json.sha256")
            for contents in ("", "not-a-sha256  user-colors.json\n"):
                with self.subTest(contents=contents):
                    sidecar.write_text(contents, encoding="utf-8")
                    valid, error = ColorConstants.verify_user_data_file(path)
                    self.assertFalse(valid)
                    self.assertIsNotNone(error)
                    self.assertIn("Hash mismatch", error or "")

    def test_verify_hash_mismatch_reports_expected_and_actual_prefixes(self) -> None:
        """Mismatch output remains useful without printing complete digests."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "user-colors.json"
            path.write_text("[]", encoding="utf-8")
            path.with_suffix(".json.sha256").write_text(
                f"{'0' * 64}  {path.name}\n",
                encoding="utf-8",
            )
            actual = ColorConstants.generate_user_data_hash(path)
            valid, error = ColorConstants.verify_user_data_file(path)

        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertIn("expected 00000000", error or "")
        self.assertIn(f"got {actual[:8]}", error or "")

    def test_verify_unreadable_sidecar_returns_focused_error(self) -> None:
        """Filesystem errors are returned rather than escaping verification."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "user-colors.json"
            path.write_text("[]", encoding="utf-8")
            path.with_suffix(".json.sha256").write_text("digest", encoding="utf-8")
            with patch.object(Path, "read_text", side_effect=OSError("access denied")):
                valid, error = ColorConstants.verify_user_data_file(path)

        self.assertFalse(valid)
        self.assertEqual(error, "Error verifying user-colors.json: access denied")

    def test_verify_all_user_data_missing_directory_is_success(self) -> None:
        """An installation without user customization has nothing to verify."""
        with TemporaryDirectory() as directory:
            self.assertEqual(
                ColorConstants.verify_all_user_data(Path(directory) / "missing"),
                (True, []),
            )

    def test_verify_all_user_data_accumulates_data_and_palette_errors(self) -> None:
        """Active user databases and palettes participate in one result."""
        with TemporaryDirectory() as directory:
            data_dir = Path(directory)
            user_dir = data_dir / "user"
            palette_dir = user_dir / "palettes"
            palette_dir.mkdir(parents=True)
            color_file = user_dir / "user-colors.json"
            palette_file = palette_dir / "user-test.json"
            example_file = palette_dir / "user-palette.example.json"
            for path in (color_file, palette_file, example_file):
                path.write_text("[]", encoding="utf-8")
                ColorConstants.save_user_data_hash(path)
                path.write_text("changed", encoding="utf-8")

            valid, errors = ColorConstants.verify_all_user_data(data_dir)

        self.assertFalse(valid)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("user-colors.json" in error for error in errors))
        self.assertTrue(any("user-test.json" in error for error in errors))
        self.assertFalse(any("example" in error for error in errors))
