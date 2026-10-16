#!/usr/bin/env python3

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from color_tools.palette import load_palette
from color_tools.cli_commands.reporting import get_available_palettes
from tests.palette_document_fixtures import palette_document


class TestUserPalettes(unittest.TestCase):
    """Test user palette functionality."""
    
    def setUp(self):
        """Set up test fixtures with temporary directory structure."""
        self.temp_dir = TemporaryDirectory()
        self.test_data_dir = Path(self.temp_dir.name)
        
        # Create directory structure
        (self.test_data_dir / "palettes").mkdir()
        (self.test_data_dir / "user" / "palettes").mkdir(parents=True)
        
        # Core palette
        self.core_palette_data = [
            {
                "name": "CoreRed",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 40.0]
            }
        ]
        
        # User palette  
        self.user_palette_data = [
            {
                "name": "UserBlue",
                "hex": "#0000FF",
            }
        ]
        
        # User override palette (same name as core)
        self.user_override_data = [
            {
                "name": "OverrideRed",
                "hex": "#FF6600", 
            }
        ]
        
        # Write core palette
        core_file = self.test_data_dir / "palettes" / "test_core.json"
        with open(core_file, 'w', encoding='utf-8') as f:
            json.dump(palette_document("test_core", self.core_palette_data), f, indent=2)

        core_example_file = self.test_data_dir / "palettes" / "test.example.json"
        with open(core_example_file, 'w', encoding='utf-8') as f:
            json.dump(palette_document("test.example", self.core_palette_data), f, indent=2)
        
        # Write user palette  
        user_file = self.test_data_dir / "user" / "palettes" / "user-test_user.json"
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(palette_document("user-test_user", self.user_palette_data), f, indent=2)
            
        # Write user override (different from core palette due to user- prefix)
        override_file = self.test_data_dir / "user" / "palettes" / "user-test_override.json"
        with open(override_file, 'w', encoding='utf-8') as f:
            json.dump(palette_document("user-test_override", self.user_override_data), f, indent=2)
            
        # Write non-prefixed file (should be ignored)
        ignored_file = self.test_data_dir / "user" / "palettes" / "ignored_palette.json"
        with open(ignored_file, 'w', encoding='utf-8') as f:
            json.dump(palette_document("ignored_palette", self.user_palette_data), f, indent=2)

        example_file = (
            self.test_data_dir / "user" / "palettes" / "user-palette.example.json"
        )
        with open(example_file, 'w', encoding='utf-8') as f:
            json.dump(palette_document("user-palette.example", self.user_palette_data), f, indent=2)
    
    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
    
    def test_get_available_palettes(self):
        """Test get_available_palettes function."""
        available = get_available_palettes(self.test_data_dir)
        
        # get_available_palettes now returns list of (name, color_count) tuples
        palette_names = [name for name, _ in available]
        
        # Should include both core and user palettes
        self.assertIn("test_core", palette_names)
        self.assertIn("user-test_user", palette_names)
        self.assertIn("user-test_override", palette_names)
        
        # Should NOT include non-prefixed user palettes
        self.assertNotIn("ignored_palette", palette_names)
        self.assertNotIn("user-palette.example", palette_names)
        self.assertNotIn("test.example", palette_names)
        
        # Verify color counts are present
        for _, color_count in available:
            self.assertIsInstance(color_count, int)
            # Color count should be >= 0 (or -1 for error)
    
    def test_load_core_palette(self):
        """Test loading core palette (user palettes don't override)."""
        palette = load_palette("test_core", self.test_data_dir)
        
        # Should load core palette (user doesn't override without user- prefix)
        self.assertEqual(len(palette.records), 1)
        self.assertEqual(palette.records[0].name, "CoreRed")
        self.assertEqual(palette.records[0].hex, "#FF0000")
    
    def test_load_user_palette(self):
        """Load a name/hex-only palette and derive all other color spaces."""
        palette = load_palette("user-test_user", self.test_data_dir)
        
        self.assertEqual(len(palette.records), 1)
        record = palette.records[0]
        self.assertEqual(record.name, "UserBlue")
        self.assertEqual(record.hex, "#0000FF")
        self.assertEqual(record.rgb, (0, 0, 255))
        self.assertEqual(record.hsl, (240.0, 100.0, 50.0))
        self.assertAlmostEqual(record.lab[0], 32.29701093285073)
        self.assertAlmostEqual(record.lab[1], 79.18751984512221)
        self.assertAlmostEqual(record.lab[2], -107.8601617541481)
        self.assertAlmostEqual(record.lch[0], 32.29701093285073)
        self.assertAlmostEqual(record.lch[1], 133.80761485376166)
        self.assertAlmostEqual(record.lch[2], 306.2849380699878)

    def test_user_palette_rejects_supplied_derived_fields(self):
        """User palettes reject cached values instead of ignoring them."""
        palette_path = (
            self.test_data_dir / "user" / "palettes" / "user-test_user.json"
        )
        palette_path.write_text(
            json.dumps(palette_document("user-test_user", [{
                "name": "UserBlue",
                "hex": "#0000FF",
                "rgb": [1, 2, 3],
                "hsl": ["invalid"],
                "lab": None,
                "lch": {"stale": True},
            }])),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "accept only 'name' and 'hex'"):
            load_palette("user-test_user", self.test_data_dir)

    def test_user_palette_requires_name_and_hex(self):
        """User palette color entries require name and hex fields."""
        palette_path = (
            self.test_data_dir / "user" / "palettes" / "user-invalid-fields.json"
        )
        palette_path.write_text(
            json.dumps(palette_document(
                "user-invalid-fields",
                [{"name": "MissingHex"}],
            )),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "Missing or invalid 'hex'"):
            load_palette("user-invalid-fields", self.test_data_dir)

    def test_user_palette_rejects_invalid_hex(self):
        """Malformed hex input raises an indexed palette validation error."""
        palette_path = (
            self.test_data_dir / "user" / "palettes" / "user-invalid-hex.json"
        )
        palette_path.write_text(
            json.dumps(palette_document(
                "user-invalid-hex",
                [{"name": "Bad", "hex": "#nothex"}],
            )),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "Invalid color data at index 0"):
            load_palette("user-invalid-hex", self.test_data_dir)
    
    def test_user_palette_no_override(self):
        """Test that user palettes don't override core palettes (separate namespaces)."""
        # Load core palette
        core_palette = load_palette("test_core", self.test_data_dir)
        self.assertEqual(core_palette.records[0].name, "CoreRed")
        self.assertEqual(core_palette.records[0].hex, "#FF0000")
        
        # Load user palette with different name
        user_palette = load_palette("user-test_override", self.test_data_dir)
        self.assertEqual(user_palette.records[0].name, "OverrideRed")
        self.assertEqual(user_palette.records[0].hex, "#FF6600")
    
    def test_load_palette_not_found(self):
        """Test loading non-existent palette."""
        with self.assertRaises(FileNotFoundError) as cm:
            load_palette("nonexistent", self.test_data_dir)
        
        # Error message should list available palettes
        error_msg = str(cm.exception)
        self.assertIn("nonexistent", error_msg)
        self.assertIn("Available palettes", error_msg)
        self.assertIn("test_core", error_msg)
        self.assertIn("user-test_user", error_msg)
    
    def test_load_non_prefixed_user_palette_error(self):
        """Test helpful error when trying to load non-prefixed user palette."""
        with self.assertRaises(FileNotFoundError) as cm:
            load_palette("ignored_palette", self.test_data_dir)
        
        # Should provide helpful message about user- prefix requirement
        error_msg = str(cm.exception)
        self.assertIn("ignored_palette", error_msg)
        self.assertIn("must be named 'user-ignored_palette.json'", error_msg)
    
    def test_load_palette_invalid_json(self):
        """Test loading palette with invalid JSON."""
        invalid_file = self.test_data_dir / "user" / "palettes" / "user-invalid.json"
        with open(invalid_file, 'w', encoding='utf-8') as f:
            f.write("{ invalid json")
        
        with self.assertRaises(ValueError) as cm:
            load_palette("user-invalid", self.test_data_dir)
        
        error_msg = str(cm.exception)
        self.assertIn("Invalid JSON", error_msg)
    
    def test_load_palette_invalid_format(self):
        """Test loading palette with invalid format."""
        invalid_file = self.test_data_dir / "user" / "palettes" / "user-badformat.json"
        with open(invalid_file, 'w', encoding='utf-8') as f:
            json.dump({"not": "an array"}, f)
        
        with self.assertRaises(ValueError) as cm:
            load_palette("user-badformat", self.test_data_dir)
        
        error_msg = str(cm.exception)
        self.assertIn("schema_version", error_msg)
    
    def test_empty_directories(self):
        """Test behavior with empty palette directories."""
        # Create empty directories
        empty_dir = Path(self.temp_dir.name) / "empty"
        (empty_dir / "palettes").mkdir(parents=True)
        (empty_dir / "user" / "palettes").mkdir(parents=True)
        
        available = get_available_palettes(empty_dir)
        self.assertEqual(available, [])
    
    def test_missing_directories(self):
        """Test behavior with missing palette directories."""
        # Use non-existent directory
        missing_dir = Path(self.temp_dir.name) / "missing"
        
        available = get_available_palettes(missing_dir)
        self.assertEqual(available, [])


if __name__ == '__main__':
    unittest.main()
