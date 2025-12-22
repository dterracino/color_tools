#!/usr/bin/env python3

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from color_tools.palette import load_palette, Palette
from color_tools.cli import _get_available_palettes


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
                "rgb": [0, 0, 255], 
                "hsl": [240.0, 100.0, 50.0],
                "lab": [32.30, 79.19, -107.86],
                "lch": [32.30, 133.81, 306.3]
            }
        ]
        
        # User override palette (same name as core)
        self.user_override_data = [
            {
                "name": "OverrideRed",
                "hex": "#FF6600", 
                "rgb": [255, 102, 0],
                "hsl": [24.0, 100.0, 50.0],
                "lab": [65.43, 54.01, 70.50],
                "lch": [65.43, 89.16, 52.5]
            }
        ]
        
        # Write core palette
        core_file = self.test_data_dir / "palettes" / "test_core.json"
        with open(core_file, 'w', encoding='utf-8') as f:
            json.dump(self.core_palette_data, f, indent=2)
        
        # Write user palette  
        user_file = self.test_data_dir / "user" / "palettes" / "user-test_user.json"
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_palette_data, f, indent=2)
            
        # Write user override (different from core palette due to user- prefix)
        override_file = self.test_data_dir / "user" / "palettes" / "user-test_override.json"
        with open(override_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_override_data, f, indent=2)
            
        # Write non-prefixed file (should be ignored)
        ignored_file = self.test_data_dir / "user" / "palettes" / "ignored_palette.json"
        with open(ignored_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_palette_data, f, indent=2)
    
    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
    
    def test_get_available_palettes(self):
        """Test _get_available_palettes function."""
        available = _get_available_palettes(self.test_data_dir)
        
        # Should include both core and user palettes
        self.assertIn("test_core", available)
        self.assertIn("user-test_user", available)
        self.assertIn("user-test_override", available)
        
        # Should NOT include non-prefixed user palettes
        self.assertNotIn("ignored_palette", available)
    
    def test_load_core_palette(self):
        """Test loading core palette (user palettes don't override)."""
        palette = load_palette("test_core", self.test_data_dir)
        
        # Should load core palette (user doesn't override without user- prefix)
        self.assertEqual(len(palette.records), 1)
        self.assertEqual(palette.records[0].name, "CoreRed")
        self.assertEqual(palette.records[0].hex, "#FF0000")
    
    def test_load_user_palette(self):
        """Test loading user palette with user- prefix."""
        palette = load_palette("user-test_user", self.test_data_dir)
        
        # Should load user palette
        self.assertEqual(len(palette.records), 1)
        self.assertEqual(palette.records[0].name, "UserBlue")
        self.assertEqual(palette.records[0].hex, "#0000FF")
    
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
        self.assertIn("Expected array of colors", error_msg)
    
    def test_empty_directories(self):
        """Test behavior with empty palette directories."""
        # Create empty directories
        empty_dir = Path(self.temp_dir.name) / "empty"
        (empty_dir / "palettes").mkdir(parents=True)
        (empty_dir / "user" / "palettes").mkdir(parents=True)
        
        available = _get_available_palettes(empty_dir)
        self.assertEqual(available, [])
    
    def test_missing_directories(self):
        """Test behavior with missing palette directories."""
        # Use non-existent directory
        missing_dir = Path(self.temp_dir.name) / "missing"
        
        available = _get_available_palettes(missing_dir)
        self.assertEqual(available, [])


if __name__ == '__main__':
    unittest.main()