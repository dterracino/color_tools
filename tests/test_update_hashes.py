"""Tests for deterministic integrity-manifest regeneration."""

from __future__ import annotations

from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from color_tools._integrity_hashes import (
    COLOR_CONSTANTS_EXPECTED_HASH,
    CORE_DATA_HASHES,
    MATRICES_EXPECTED_HASH,
    SYSTEM_PALETTE_HASHES,
)
from tooling.update_hashes import (
    DATA_DIRECTORY,
    MANIFEST_PATH,
    IntegrityManifest,
    collect_integrity_manifest,
    render_integrity_manifest,
    write_integrity_manifest,
)


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class TestIntegrityManifestGeneration(unittest.TestCase):
    """Protect the generated manifest's completeness and stable format."""

    def test_checked_in_manifest_matches_current_sources(self) -> None:
        """Every checked-in digest equals a fresh calculation."""
        generated = collect_integrity_manifest()
        self.assertEqual(generated.core_data_hashes, CORE_DATA_HASHES)
        self.assertEqual(generated.system_palette_hashes, SYSTEM_PALETTE_HASHES)
        self.assertEqual(generated.matrices_expected_hash, MATRICES_EXPECTED_HASH)
        self.assertEqual(
            generated.color_constants_expected_hash,
            COLOR_CONSTANTS_EXPECTED_HASH,
        )

    def test_manifest_registers_exactly_the_system_palette_files(self) -> None:
        """Palette discovery has neither missing nor stale manifest entries."""
        palette_files = {
            path.name
            for path in (DATA_DIRECTORY / "palettes").glob("*.json")
        }
        self.assertEqual(set(SYSTEM_PALETTE_HASHES), palette_files)

    def test_all_manifest_values_are_lowercase_sha256_digests(self) -> None:
        """Generated values use one canonical digest representation."""
        all_hashes = (
            *CORE_DATA_HASHES.values(),
            *SYSTEM_PALETTE_HASHES.values(),
            MATRICES_EXPECTED_HASH,
            COLOR_CONSTANTS_EXPECTED_HASH,
        )
        for hash_value in all_hashes:
            with self.subTest(hash_value=hash_value):
                self.assertRegex(hash_value, _SHA256_PATTERN)

    def test_checked_in_module_uses_deterministic_rendering(self) -> None:
        """A no-change regeneration produces byte-for-byte identical text."""
        generated = collect_integrity_manifest()
        self.assertEqual(
            MANIFEST_PATH.read_text(encoding="utf-8"),
            render_integrity_manifest(generated),
        )

    def test_atomic_writer_is_idempotent_and_does_not_touch_constants(self) -> None:
        """Repeated writes affect only the selected generated manifest."""
        generated = collect_integrity_manifest()
        constants_path = MANIFEST_PATH.with_name("constants.py")
        constants_before = constants_path.read_bytes()
        with TemporaryDirectory() as directory:
            output_path = Path(directory) / "_integrity_hashes.py"
            self.assertEqual(
                write_integrity_manifest(generated, output_path),
                output_path,
            )
            first = output_path.read_bytes()
            write_integrity_manifest(generated, output_path)
            second = output_path.read_bytes()
            leftovers = list(output_path.parent.glob(".*.tmp"))

        self.assertEqual(first, second)
        self.assertEqual(constants_path.read_bytes(), constants_before)
        self.assertEqual(leftovers, [])

    def test_collection_requires_core_files_and_palettes(self) -> None:
        """Incomplete data trees cannot produce a success-shaped manifest."""
        with TemporaryDirectory() as directory:
            data_directory = Path(directory)
            with self.assertRaisesRegex(FileNotFoundError, "colors.json"):
                collect_integrity_manifest(data_directory=data_directory)

            for filename in CORE_DATA_HASHES:
                (data_directory / filename).write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(FileNotFoundError, "No system palette"):
                collect_integrity_manifest(data_directory=data_directory)

    def test_renderer_sorts_mapping_keys(self) -> None:
        """Rendering order is independent of dictionary insertion order."""
        digest_a = "a" * 64
        digest_b = "b" * 64
        manifest = IntegrityManifest(
            core_data_hashes={
                "maker_synonyms.json": digest_b,
                "colors.json": digest_a,
                "filaments.json": digest_b,
            },
            system_palette_hashes={"z.json": digest_b, "a.json": digest_a},
            matrices_expected_hash=digest_a,
            color_constants_expected_hash=digest_b,
        )
        rendered = render_integrity_manifest(manifest)
        self.assertLess(rendered.index('"a.json"'), rendered.index('"z.json"'))
        self.assertLess(
            rendered.index('"colors.json"'),
            rendered.index('"maker_synonyms.json"'),
        )
