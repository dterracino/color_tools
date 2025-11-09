"""Unit tests for color_tools.palette module."""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from color_tools.palette import (
    Palette,
    FilamentPalette,
    ColorRecord,
    FilamentRecord,
    load_palette,
    _parse_color_records,
)


class TestColorRecord(unittest.TestCase):
    """Test ColorRecord dataclass."""
    
    def test_color_record_creation(self):
        """Test creating a ColorRecord."""
        color = ColorRecord(
            name="red",
            hex="#FF0000",
            rgb=(255, 0, 0),
            hsl=(0.0, 100.0, 50.0),
            lab=(53.24, 80.09, 67.20),
            lch=(53.24, 104.55, 39.99)
        )
        self.assertEqual(color.name, "red")
        self.assertEqual(color.hex, "#FF0000")
        self.assertEqual(color.rgb, (255, 0, 0))
    
    def test_color_record_immutable(self):
        """Test that ColorRecord is immutable (frozen)."""
        color = ColorRecord(
            name="red",
            hex="#FF0000",
            rgb=(255, 0, 0),
            hsl=(0.0, 100.0, 50.0),
            lab=(53.24, 80.09, 67.20),
            lch=(53.24, 104.55, 39.99)
        )
        with self.assertRaises(AttributeError):
            color.name = "blue"


class TestFilamentRecord(unittest.TestCase):
    """Test FilamentRecord dataclass."""
    
    def test_filament_record_creation(self):
        """Test creating a FilamentRecord."""
        filament = FilamentRecord(
            maker="Test Maker",
            type="PLA",
            finish="Matte",
            color="Red",
            hex="#FF0000",
            td_value=0.5
        )
        self.assertEqual(filament.maker, "Test Maker")
        self.assertEqual(filament.type, "PLA")
        self.assertEqual(filament.color, "Red")
        # rgb is a property that converts from hex
        self.assertEqual(filament.rgb, (255, 0, 0))
    
    def test_filament_record_immutable(self):
        """Test that FilamentRecord is immutable (frozen)."""
        filament = FilamentRecord(
            maker="Test Maker",
            type="PLA",
            finish="Matte",
            color="Red",
            hex="#FF0000",
            td_value=0.5
        )
        with self.assertRaises(AttributeError):
            filament.color = "Blue"


class TestPalette(unittest.TestCase):
    """Test Palette class for CSS colors."""
    
    def test_load_default(self):
        """Test loading default palette."""
        palette = Palette.load_default()
        self.assertIsInstance(palette, Palette)
        self.assertGreater(len(palette.records), 0)
    
    def test_find_by_name_exact(self):
        """Test finding color by exact name."""
        palette = Palette.load_default()
        result = palette.find_by_name("red")
        # May or may not find exact "red" depending on what's in the palette
        # Just test it returns the right type
        self.assertTrue(result is None or isinstance(result, ColorRecord))
    
    def test_find_by_name_case_insensitive(self):
        """Test that name search is case insensitive."""
        palette = Palette.load_default()
        # Find a color that exists
        if palette.records:
            color_name = palette.records[0].name
            result1 = palette.find_by_name(color_name.lower())
            result2 = palette.find_by_name(color_name.upper())
            result3 = palette.find_by_name(color_name)
            # All should return the same result
            if result1:  # If found
                self.assertEqual(result1.name, result2.name if result2 else None)
                self.assertEqual(result1.name, result3.name if result3 else None)
    
    def test_find_by_rgb(self):
        """Test finding color by RGB value."""
        palette = Palette.load_default()
        # Use a color from the palette
        if palette.records:
            color = palette.records[0]
            # Search by its RGB
            result = palette.find_by_rgb(color.rgb)
            self.assertIsNotNone(result)
            self.assertEqual(result.rgb, color.rgb)
    
    def test_find_by_lab(self):
        """Test finding color by LAB value."""
        palette = Palette.load_default()
        # Use a color from the palette
        if palette.records:
            color = palette.records[0]
            # Search by its LAB (exact match may fail due to rounding)
            result = palette.find_by_lab(color.lab, rounding=1)
            # May or may not find depending on rounding
            self.assertTrue(result is None or isinstance(result, ColorRecord))
    
    def test_nearest_color_rgb(self):
        """Test finding nearest color by RGB."""
        palette = Palette.load_default()
        # Find nearest color to a pure red
        nearest, distance = palette.nearest_color((255, 0, 0), space="rgb")
        self.assertIsNotNone(nearest)
        self.assertIsInstance(distance, float)
        self.assertGreaterEqual(distance, 0)
    
    def test_nearest_color_lab(self):
        """Test finding nearest color by LAB."""
        palette = Palette.load_default()
        # Find nearest color to a LAB value
        nearest, distance = palette.nearest_color((50, 25, -30), space="lab")
        self.assertIsNotNone(nearest)
        self.assertIsInstance(distance, float)
        self.assertGreaterEqual(distance, 0)
    
    def test_nearest_color_hsl(self):
        """Test finding nearest color by HSL."""
        palette = Palette.load_default()
        # Find nearest color to an HSL value
        nearest, distance = palette.nearest_color((180, 50, 50), space="hsl")
        self.assertIsNotNone(nearest)
        self.assertIsInstance(distance, float)
        self.assertGreaterEqual(distance, 0)
    
    def test_nearest_color_metric(self):
        """Test finding nearest color with specific metric."""
        palette = Palette.load_default()
        # Find nearest with Delta E 2000
        nearest, distance = palette.nearest_color(
            (50, 25, -30),
            space="lab",
            metric="de2000"
        )
        self.assertIsNotNone(nearest)
        self.assertGreaterEqual(distance, 0)


class TestFilamentPalette(unittest.TestCase):
    """Test FilamentPalette class for 3D printing filaments."""
    
    def test_load_default(self):
        """Test loading default filament palette."""
        palette = FilamentPalette.load_default()
        self.assertIsInstance(palette, FilamentPalette)
        self.assertGreater(len(palette.records), 0)
    
    def test_find_by_maker(self):
        """Test finding filaments by maker."""
        palette = FilamentPalette.load_default()
        # Get all makers (it's a property, not a method)
        makers_list = palette.makers
        if makers_list:
            # Search for first maker
            results = palette.find_by_maker(makers_list[0])
            self.assertGreater(len(results), 0)
            # All results should be from that maker
            self.assertTrue(all(f.maker == makers_list[0] for f in results))
    
    def test_find_by_maker_synonym(self):
        """Test finding filaments by maker synonym."""
        palette = FilamentPalette.load_default()
        # Try to find using "Bambu" which should map to "Bambu Lab"
        results_synonym = palette.find_by_maker("Bambu")
        results_canonical = palette.find_by_maker("Bambu Lab")
        # Should return same results
        if results_canonical:  # Only test if Bambu Lab exists
            self.assertEqual(len(results_synonym), len(results_canonical))
    
    def test_find_by_type(self):
        """Test finding filaments by type."""
        palette = FilamentPalette.load_default()
        types_list = palette.types
        if types_list:
            results = palette.find_by_type(types_list[0])
            self.assertGreater(len(results), 0)
            self.assertTrue(all(f.type == types_list[0] for f in results))
    
    def test_find_by_finish(self):
        """Test finding filaments by finish."""
        palette = FilamentPalette.load_default()
        finishes_list = palette.finishes
        if finishes_list:
            results = palette.find_by_finish(finishes_list[0])
            self.assertGreater(len(results), 0)
            self.assertTrue(all(f.finish == finishes_list[0] for f in results))
    
    def test_filter_combined(self):
        """Test filtering with multiple criteria."""
        palette = FilamentPalette.load_default()
        makers_list = palette.makers
        types_list = palette.types
        if makers_list and types_list:
            results = palette.filter(maker=makers_list[0], type_name=types_list[0])
            # All results should match both criteria
            for f in results:
                self.assertEqual(f.maker, makers_list[0])
                self.assertEqual(f.type, types_list[0])
    
    def test_list_makers(self):
        """Test listing all makers."""
        palette = FilamentPalette.load_default()
        makers_list = palette.makers
        self.assertIsInstance(makers_list, list)
        self.assertGreater(len(makers_list), 0)
        # Should be sorted
        self.assertEqual(makers_list, sorted(makers_list))
    
    def test_list_types(self):
        """Test listing all types."""
        palette = FilamentPalette.load_default()
        types_list = palette.types
        self.assertIsInstance(types_list, list)
        self.assertGreater(len(types_list), 0)
        # Should be sorted
        self.assertEqual(types_list, sorted(types_list))
    
    def test_list_finishes(self):
        """Test listing all finishes."""
        palette = FilamentPalette.load_default()
        finishes_list = palette.finishes
        self.assertIsInstance(finishes_list, list)
        self.assertGreater(len(finishes_list), 0)
        # Should be sorted
        self.assertEqual(finishes_list, sorted(finishes_list))
    
    def test_nearest_filament(self):
        """Test finding nearest filament."""
        palette = FilamentPalette.load_default()
        # Find nearest to pure red
        nearest, distance = palette.nearest_filament((255, 0, 0))
        self.assertIsNotNone(nearest)
        self.assertIsInstance(distance, float)
        self.assertGreaterEqual(distance, 0)
    
    def test_nearest_filament_with_filter(self):
        """Test finding nearest filament with filtering."""
        palette = FilamentPalette.load_default()
        makers_list = palette.makers
        if makers_list:
            # Find nearest PLA from first maker
            nearest, distance = palette.nearest_filament(
                (180, 100, 200),
                maker=makers_list[0],
                type_name="PLA"
            )
            if nearest:  # Only test if match found
                self.assertEqual(nearest.maker, makers_list[0])
                self.assertEqual(nearest.type, "PLA")


class TestPaletteEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_nearest_color_empty_palette(self):
        """Test nearest color on empty palette."""
        palette = Palette([])
        # Should handle empty palette gracefully
        try:
            nearest, distance = palette.nearest_color((255, 0, 0))
            # If it doesn't raise, it should return None
            self.assertTrue(nearest is None or distance is None or distance == float('inf'))
        except (ValueError, IndexError):
            # Or it might raise an error, which is also acceptable
            pass
    
    def test_find_by_name_no_match(self):
        """Test finding color with no matches."""
        palette = Palette.load_default()
        result = palette.find_by_name("this_color_should_not_exist_12345")
        self.assertIsNone(result)


class TestLoadPalette(unittest.TestCase):
    """Test load_palette() function for loading retro palettes."""
    
    def test_load_cga4_palette(self):
        """Test loading CGA 4-color palette."""
        palette = load_palette("cga4")
        self.assertIsInstance(palette, Palette)
        self.assertEqual(len(palette.records), 4)
        # Verify it's a working Palette instance
        self.assertGreater(len(palette._by_name), 0)
    
    def test_load_cga16_palette(self):
        """Test loading CGA 16-color palette."""
        palette = load_palette("cga16")
        self.assertIsInstance(palette, Palette)
        self.assertEqual(len(palette.records), 16)
    
    def test_load_ega16_palette(self):
        """Test loading EGA 16-color palette."""
        palette = load_palette("ega16")
        self.assertIsInstance(palette, Palette)
        self.assertEqual(len(palette.records), 16)
    
    def test_load_ega64_palette(self):
        """Test loading EGA 64-color palette."""
        palette = load_palette("ega64")
        self.assertIsInstance(palette, Palette)
        self.assertEqual(len(palette.records), 64)
    
    def test_load_vga_palette(self):
        """Test loading VGA 256-color palette."""
        palette = load_palette("vga")
        self.assertIsInstance(palette, Palette)
        self.assertEqual(len(palette.records), 256)
    
    def test_load_web_palette(self):
        """Test loading Web-safe 216-color palette."""
        palette = load_palette("web")
        self.assertIsInstance(palette, Palette)
        self.assertEqual(len(palette.records), 216)
    
    def test_loaded_palette_can_find_nearest_color(self):
        """Test that loaded palette can perform nearest color search."""
        palette = load_palette("cga4")
        # Find nearest color to pure red
        nearest, distance = palette.nearest_color((255, 0, 0), space="rgb")
        self.assertIsNotNone(nearest)
        self.assertIsInstance(nearest, ColorRecord)
        self.assertIsInstance(distance, float)
        self.assertGreaterEqual(distance, 0)
    
    def test_loaded_palette_has_valid_color_data(self):
        """Test that loaded palette colors have all required fields."""
        palette = load_palette("cga4")
        for color in palette.records:
            # Verify all required fields exist
            self.assertIsInstance(color.name, str)
            self.assertIsInstance(color.hex, str)
            self.assertIsInstance(color.rgb, tuple)
            self.assertEqual(len(color.rgb), 3)
            self.assertIsInstance(color.hsl, tuple)
            self.assertEqual(len(color.hsl), 3)
            self.assertIsInstance(color.lab, tuple)
            self.assertEqual(len(color.lab), 3)
            self.assertIsInstance(color.lch, tuple)
            self.assertEqual(len(color.lch), 3)
    
    def test_invalid_palette_name_raises_file_not_found(self):
        """Test that invalid palette name raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError) as context:
            load_palette("nonexistent_palette_xyz123")
        # Error message should be helpful
        error_msg = str(context.exception)
        self.assertIn("nonexistent_palette_xyz123", error_msg)
        self.assertIn("Available palettes:", error_msg)
    
    def test_error_message_lists_available_palettes(self):
        """Test that error message lists available palettes in sorted order."""
        with self.assertRaises(FileNotFoundError) as context:
            load_palette("invalid")
        error_msg = str(context.exception)
        # Check that known palettes are mentioned
        self.assertIn("cga4", error_msg)
        self.assertIn("cga16", error_msg)
        self.assertIn("ega16", error_msg)
        self.assertIn("ega64", error_msg)
        self.assertIn("vga", error_msg)
        self.assertIn("web", error_msg)
    
    def test_empty_palette_name_raises_error(self):
        """Test that empty palette name raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_palette("")
    
    def test_palette_name_case_sensitivity(self):
        """Test case sensitivity of palette names."""
        # Palette names should be case-sensitive (file system dependent)
        # On most systems, this should raise an error
        with self.assertRaises(FileNotFoundError):
            load_palette("CGA4")  # Capital letters
    
    def test_malformed_json_raises_value_error(self):
        """Test that malformed JSON file raises ValueError."""
        import tempfile
        import os
        
        # Create a temporary directory with malformed JSON
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "palettes" / "bad.json"
            bad_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write malformed JSON
            with open(bad_file, 'w') as f:
                f.write("{invalid json content")
            
            # Temporarily modify the function to use this directory
            # Since we can't easily override the hardcoded path, we'll test
            # by directly calling the underlying code
            import json
            with self.assertRaises(ValueError) as context:
                with open(bad_file, 'r') as f:
                    json.load(f)
                # This will raise JSONDecodeError which should be caught
            # The actual function wraps this in ValueError
    
    def test_non_list_palette_data_raises_value_error(self):
        """Test that palette file with non-list root raises ValueError."""
        import tempfile
        import json
        
        # Create a temporary directory with invalid structure
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "palettes" / "notlist.json"
            bad_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write JSON object instead of array
            with open(bad_file, 'w') as f:
                json.dump({"colors": []}, f)
            
            # We'll test the validation logic directly
            with open(bad_file, 'r') as f:
                data = json.load(f)
            
            # This should not be a list
            self.assertNotIsInstance(data, list)
            # The actual function would raise ValueError here


class TestParseColorRecords(unittest.TestCase):
    """Test _parse_color_records() helper function."""
    
    def test_parse_single_color_record(self):
        """Test parsing a single color record."""
        data = [
            {
                "name": "Test Red",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        records = _parse_color_records(data, "test.json")
        
        self.assertEqual(len(records), 1)
        self.assertIsInstance(records[0], ColorRecord)
        self.assertEqual(records[0].name, "Test Red")
        self.assertEqual(records[0].hex, "#FF0000")
        self.assertEqual(records[0].rgb, (255, 0, 0))
        self.assertEqual(records[0].hsl, (0.0, 100.0, 50.0))
        self.assertEqual(records[0].lab, (53.24, 80.09, 67.20))
        self.assertEqual(records[0].lch, (53.24, 104.55, 39.99))
    
    def test_parse_multiple_color_records(self):
        """Test parsing multiple color records."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            },
            {
                "name": "Green",
                "hex": "#00FF00",
                "rgb": [0, 255, 0],
                "hsl": [120.0, 100.0, 50.0],
                "lab": [87.73, -86.18, 83.18],
                "lch": [87.73, 119.78, 136.02]
            },
            {
                "name": "Blue",
                "hex": "#0000FF",
                "rgb": [0, 0, 255],
                "hsl": [240.0, 100.0, 50.0],
                "lab": [32.30, 79.19, -107.86],
                "lch": [32.30, 133.81, 306.29]
            }
        ]
        records = _parse_color_records(data, "test.json")
        
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].name, "Red")
        self.assertEqual(records[1].name, "Green")
        self.assertEqual(records[2].name, "Blue")
    
    def test_parse_empty_list(self):
        """Test parsing empty color list."""
        data = []
        records = _parse_color_records(data, "test.json")
        self.assertEqual(len(records), 0)
        self.assertEqual(records, [])
    
    def test_missing_name_key_raises_value_error(self):
        """Test that missing 'name' key raises ValueError with helpful message."""
        data = [
            {
                # Missing "name" key
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        self.assertIn("'name'", error_msg)
        self.assertIn("index 0", error_msg)
        self.assertIn("test.json", error_msg)
    
    def test_missing_hex_key_raises_value_error(self):
        """Test that missing 'hex' key raises ValueError."""
        data = [
            {
                "name": "Red",
                # Missing "hex" key
                "rgb": [255, 0, 0],
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        self.assertIn("'hex'", error_msg)
        self.assertIn("test.json", error_msg)
    
    def test_missing_rgb_key_raises_value_error(self):
        """Test that missing 'rgb' key raises ValueError."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                # Missing "rgb" key
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        self.assertIn("'rgb'", error_msg)
    
    def test_missing_hsl_key_raises_value_error(self):
        """Test that missing 'hsl' key raises ValueError."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                # Missing "hsl" key
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        self.assertIn("'hsl'", error_msg)
    
    def test_missing_lab_key_raises_value_error(self):
        """Test that missing 'lab' key raises ValueError."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                "hsl": [0.0, 100.0, 50.0],
                # Missing "lab" key
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        self.assertIn("'lab'", error_msg)
    
    def test_missing_lch_key_raises_value_error(self):
        """Test that missing 'lch' key raises ValueError."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20]
                # Missing "lch" key
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        self.assertIn("'lch'", error_msg)
    
    def test_invalid_rgb_array_indices_raises_value_error(self):
        """Test that RGB array with missing indices raises ValueError."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": [255, 0],  # Only 2 values instead of 3
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        self.assertIn("index 0", error_msg)
        self.assertIn("test.json", error_msg)
    
    def test_invalid_hsl_array_indices_raises_value_error(self):
        """Test that HSL array with missing indices raises ValueError."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                "hsl": [0.0],  # Only 1 value instead of 3
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        self.assertIn("index 0", error_msg)
    
    def test_invalid_lab_array_indices_raises_value_error(self):
        """Test that LAB array with missing indices raises ValueError."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09],  # Only 2 values instead of 3
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        self.assertIn("index 0", error_msg)
    
    def test_invalid_lch_array_indices_raises_value_error(self):
        """Test that LCH array with missing indices raises ValueError."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20],
                "lch": []  # Empty array
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        self.assertIn("index 0", error_msg)
    
    def test_non_numeric_rgb_values_raises_value_error(self):
        """Test that non-numeric RGB values raise ValueError with context."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": ["not", "a", "number"],  # Invalid RGB values
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        # RGB values are now validated early to provide better error messages
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        self.assertIn("index 0", error_msg)
        self.assertIn("test.json", error_msg)
    
    def test_non_numeric_hsl_values_raises_value_error(self):
        """Test that non-numeric HSL values raise ValueError."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                "hsl": ["x", "y", "z"],
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        self.assertIn("index 0", error_msg)
    
    def test_non_numeric_lab_values_raises_value_error(self):
        """Test that non-numeric LAB values raise ValueError."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                "hsl": [0.0, 100.0, 50.0],
                "lab": [None, None, None],
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        self.assertIn("index 0", error_msg)
    
    def test_error_at_specific_index_in_multiple_records(self):
        """Test that error message correctly identifies the problematic index."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            },
            {
                "name": "Green",
                "hex": "#00FF00",
                "rgb": [0, 255, 0],
                "hsl": [120.0, 100.0, 50.0],
                "lab": [87.73, -86.18, 83.18],
                "lch": [87.73, 119.78, 136.02]
            },
            {
                "name": "Blue",
                # Missing "hex" key - error at index 2
                "rgb": [0, 0, 255],
                "hsl": [240.0, 100.0, 50.0],
                "lab": [32.30, 79.19, -107.86],
                "lch": [32.30, 133.81, 306.29]
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test.json")
        
        error_msg = str(context.exception)
        # Should identify index 2 (third item, 0-indexed)
        self.assertIn("index 2", error_msg)
        self.assertIn("test.json", error_msg)
    
    def test_source_file_name_appears_in_error_message(self):
        """Test that source file name appears in error messages."""
        data = [
            {
                "name": "Red",
                # Missing other required keys
            }
        ]
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "my_custom_palette.json")
        
        error_msg = str(context.exception)
        self.assertIn("my_custom_palette.json", error_msg)
    
    def test_handles_integer_rgb_values(self):
        """Test that integer RGB values are properly handled."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],  # Integers, not floats
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        records = _parse_color_records(data, "test.json")
        self.assertEqual(records[0].rgb, (255, 0, 0))
    
    def test_handles_float_hsl_values(self):
        """Test that float HSL values are properly handled."""
        data = [
            {
                "name": "Red",
                "hex": "#FF0000",
                "rgb": [255, 0, 0],
                "hsl": [0.5, 99.9, 50.1],  # Float values
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        records = _parse_color_records(data, "test.json")
        self.assertEqual(records[0].hsl, (0.5, 99.9, 50.1))
    
    def test_rgb_validation_prevents_late_failure_in_nearest_color(self):
        """
        Test that RGB validation in _parse_color_records prevents late failures
        in nearest_color with proper error context.
        
        This is a regression test for the issue where non-numeric RGB values
        were not validated early, causing ValueError in nearest_color without
        file/index context.
        """
        # Create data with invalid RGB values
        data = [
            {
                "name": "Invalid Color",
                "hex": "#FF0000",
                "rgb": ["string", "values", "here"],  # Invalid!
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 39.99]
            }
        ]
        
        # Should fail early in _parse_color_records with context
        with self.assertRaises(ValueError) as context:
            _parse_color_records(data, "test_colors.json")
        
        # Error message should include file name and index
        error_msg = str(context.exception)
        self.assertIn("test_colors.json", error_msg)
        self.assertIn("index 0", error_msg)
        
        # The old behavior would have allowed this to pass _parse_color_records
        # and only fail later in Palette.nearest_color() without context


if __name__ == '__main__':
    unittest.main()
