#!/usr/bin/env python3
"""
Test user override system for colors, filaments, and synonyms.

This module tests the comprehensive user override system that allows user files
to override core data with consistent behavior and transparency.
"""

import unittest
from pathlib import Path
import tempfile
import json
import os
import logging

from color_tools.palette import (
    Palette, FilamentPalette, ColorRecord, FilamentRecord,
    _parse_color_records, _parse_filament_records,
    load_colors, load_filaments, load_maker_synonyms
)


class TestUserOverrideSystem(unittest.TestCase):
    """Test the comprehensive user override system."""
    
    def setUp(self):
        """Set up test environment with temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Create core data files
        self._create_core_data()
        
        # Store original data directory for restoration
        self.original_data_dir = None
    
    def tearDown(self):
        """Clean up test environment."""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def _create_core_data(self):
        """Create core test data files."""
        # Core colors
        core_colors = [
            {
                "name": "red",
                "hex": "#FF0000", 
                "rgb": [255, 0, 0],
                "hsl": [0.0, 100.0, 50.0],
                "lab": [53.24, 80.09, 67.20],
                "lch": [53.24, 104.55, 40.0]
            },
            {
                "name": "blue",
                "hex": "#0000FF",
                "rgb": [0, 0, 255],
                "hsl": [240.0, 100.0, 50.0],
                "lab": [32.30, 79.19, -107.86],
                "lch": [32.30, 133.81, 306.3]
            }
        ]
        
        # Core filaments
        core_filaments = [
            {
                "maker": "Bambu Lab",
                "type": "PLA",
                "finish": "Matte",
                "color": "Red",
                "hex": "#FF0000"
            },
            {
                "maker": "Test Maker",
                "type": "PLA",
                "finish": "Glossy", 
                "color": "Blue",
                "hex": "#0000FF"
            }
        ]
        
        # Core synonyms
        core_synonyms = {
            "Bambu Lab": ["Bambu", "BLL"],
            "Test Maker": ["TM"]
        }
        
        # Write core files
        with open(self.data_dir / "colors.json", "w") as f:
            json.dump(core_colors, f, indent=2)
        
        with open(self.data_dir / "filaments.json", "w") as f:
            json.dump(core_filaments, f, indent=2)
            
        with open(self.data_dir / "maker_synonyms.json", "w") as f:
            json.dump(core_synonyms, f, indent=2)
    
    def _create_user_colors(self, colors_data):
        """Create user-colors.json file with given data."""
        with open(self.data_dir / "user-colors.json", "w") as f:
            json.dump(colors_data, f, indent=2)
    
    def _create_user_filaments(self, filaments_data):
        """Create user-filaments.json file with given data."""
        with open(self.data_dir / "user-filaments.json", "w") as f:
            json.dump(filaments_data, f, indent=2)
    
    def _create_user_synonyms(self, synonyms_data):
        """Create user-synonyms.json file with given data."""
        with open(self.data_dir / "user-synonyms.json", "w") as f:
            json.dump(synonyms_data, f, indent=2)
    
    def _load_with_custom_dir(self, loader_func):
        """Load data using custom directory."""
        return loader_func(json_path=str(self.data_dir))


class TestColorOverrides(TestUserOverrideSystem):
    """Test color override behavior."""
    
    def test_color_name_override(self):
        """Test that user colors override core colors by name."""
        # User color overrides core red with different RGB
        user_colors = [
            {
                "name": "red",  # Same name as core
                "hex": "#DC143C",  # Different color (crimson)
                "rgb": [220, 20, 60],
                "hsl": [348.0, 83.3, 47.1],
                "lab": [47.1, 70.8, 33.2],
                "lch": [47.1, 78.3, 25.1]
            }
        ]
        self._create_user_colors(user_colors)
        
        # Load palette with overrides
        colors = self._load_with_custom_dir(load_colors)
        palette = Palette(colors)
        
        # Name lookup should return user override
        red_color = palette.find_by_name("red")
        self.assertIsNotNone(red_color)
        assert red_color is not None  # Type assertion for Pylance
        self.assertEqual(red_color.source, "user-colors.json")
        self.assertEqual(red_color.hex, "#DC143C")
        self.assertEqual(red_color.rgb, (220, 20, 60))
        
        # Both RGB values should be accessible since they're different
        core_red_rgb = palette.find_by_rgb((255, 0, 0))
        self.assertIsNotNone(core_red_rgb)  # Core RGB still accessible
        assert core_red_rgb is not None  # Type assertion for Pylance
        self.assertEqual(core_red_rgb.source, "colors.json")
        
        # User RGB should be findable  
        user_red_rgb = palette.find_by_rgb((220, 20, 60))
        self.assertIsNotNone(user_red_rgb)
        assert user_red_rgb is not None  # Type assertion for Pylance
        self.assertEqual(user_red_rgb.name, "red")
        self.assertEqual(user_red_rgb.source, "user-colors.json")
    
    def test_color_rgb_override(self):
        """Test that user colors override core colors by RGB."""
        # User color uses same RGB as core blue but different name
        user_colors = [
            {
                "name": "my_blue",  # Different name
                "hex": "#0000FF",   # Same RGB as core blue
                "rgb": [0, 0, 255],
                "hsl": [240.0, 100.0, 50.0], 
                "lab": [32.30, 79.19, -107.86],
                "lch": [32.30, 133.81, 306.3]
            }
        ]
        self._create_user_colors(user_colors)
        
        colors = self._load_with_custom_dir(load_colors)
        palette = Palette(colors)
        
        # RGB lookup should return user override (user wins RGB conflicts)
        blue_rgb = palette.find_by_rgb((0, 0, 255))
        self.assertIsNotNone(blue_rgb)
        assert blue_rgb is not None  # Type assertion for Pylance
        self.assertEqual(blue_rgb.source, "user-colors.json")
        self.assertEqual(blue_rgb.name, "my_blue")
        
        # Both names should still be accessible since no name conflict
        core_blue = palette.find_by_name("blue")
        self.assertIsNotNone(core_blue)  # Core name still accessible
        assert core_blue is not None  # Type assertion for Pylance
        self.assertEqual(core_blue.source, "colors.json")
        
        user_blue = palette.find_by_name("my_blue")
        self.assertIsNotNone(user_blue)
        assert user_blue is not None  # Type assertion for Pylance
        self.assertEqual(user_blue.source, "user-colors.json")
    
    def test_color_addition_no_conflict(self):
        """Test that user colors can add new colors without conflicts."""
        user_colors = [
            {
                "name": "green",
                "hex": "#00FF00",
                "rgb": [0, 255, 0],
                "hsl": [120.0, 100.0, 50.0],
                "lab": [87.73, -86.18, 83.18],
                "lch": [87.73, 119.78, 136.0]
            }
        ]
        self._create_user_colors(user_colors)
        
        colors = self._load_with_custom_dir(load_colors)
        palette = Palette(colors)
        
        # Should find both core and user colors
        red = palette.find_by_name("red")
        blue = palette.find_by_name("blue") 
        green = palette.find_by_name("green")
        
        self.assertIsNotNone(red)
        assert red is not None  # Type assertion for Pylance
        self.assertEqual(red.source, "colors.json")
        
        self.assertIsNotNone(blue)
        assert blue is not None  # Type assertion for Pylance
        self.assertEqual(blue.source, "colors.json")
        
        self.assertIsNotNone(green)
        assert green is not None  # Type assertion for Pylance
        self.assertEqual(green.source, "user-colors.json")
    
    def test_color_nearest_color_priority(self):
        """Test that nearest_color respects user overrides."""
        # User red overrides core red
        user_colors = [
            {
                "name": "red",
                "hex": "#DC143C", 
                "rgb": [220, 20, 60],
                "hsl": [348.0, 83.3, 47.1],
                "lab": [47.1, 70.8, 33.2], 
                "lch": [47.1, 78.3, 25.1]
            }
        ]
        self._create_user_colors(user_colors)
        
        colors = self._load_with_custom_dir(load_colors)
        palette = Palette(colors)
        
        # Exact match should return user override
        nearest, distance = palette.nearest_color((220, 20, 60), space="rgb")
        self.assertEqual(distance, 0.0)
        assert nearest is not None  # Type assertion for Pylance
        self.assertEqual(nearest.source, "user-colors.json")
        self.assertEqual(nearest.name, "red")


class TestFilamentOverrides(TestUserOverrideSystem):
    """Test filament override behavior."""
    
    def test_filament_rgb_override_priority(self):
        """Test that find_by_rgb prioritizes user filaments."""
        # User filament with same RGB as core but different attributes
        user_filaments = [
            {
                "maker": "Custom Maker",
                "type": "PETG", 
                "finish": "Silk",
                "color": "Custom Red",
                "hex": "#FF0000"  # Same RGB as core Bambu Lab PLA Red
            }
        ]
        self._create_user_filaments(user_filaments)
        
        filaments = self._load_with_custom_dir(load_filaments)
        palette = FilamentPalette(filaments)
        
        # RGB lookup should return user filament first
        red_filaments = palette.find_by_rgb((255, 0, 0))
        self.assertGreater(len(red_filaments), 0)
        
        # First result should be user filament
        first_result = red_filaments[0]
        assert first_result is not None  # Type assertion for Pylance
        self.assertEqual(first_result.source, "user-filaments.json")
        self.assertEqual(first_result.maker, "Custom Maker")
        self.assertEqual(first_result.type, "PETG")
        self.assertEqual(first_result.color, "Custom Red")
    
    def test_filament_nearest_filament_priority(self):
        """Test that nearest_filament prioritizes user filaments."""
        user_filaments = [
            {
                "maker": "User Maker",
                "type": "ABS",
                "finish": "Matte",
                "color": "User Blue", 
                "hex": "#0000FF"  # Same as core Test Maker PLA Blue
            }
        ]
        self._create_user_filaments(user_filaments)
        
        filaments = self._load_with_custom_dir(load_filaments)
        palette = FilamentPalette(filaments)
        
        # Exact match should return user filament
        nearest, distance = palette.nearest_filament((0, 0, 255))
        self.assertEqual(distance, 0.0)
        assert nearest is not None  # Type assertion for Pylance
        self.assertEqual(nearest.source, "user-filaments.json")
        self.assertEqual(nearest.maker, "User Maker")
    
    def test_filament_maker_search_no_override(self):
        """Test that maker searches work normally with user additions."""
        # User adds new filament for existing maker
        user_filaments = [
            {
                "maker": "Bambu Lab",
                "type": "ABS",
                "finish": "Silk",
                "color": "Purple",
                "hex": "#800080"
            }
        ]
        self._create_user_filaments(user_filaments)
        
        filaments = self._load_with_custom_dir(load_filaments)
        palette = FilamentPalette(filaments)
        
        # Should find both core and user filaments for Bambu Lab
        bambu_filaments = palette.find_by_maker("Bambu Lab")
        
        # Should have at least 2 (core red + user purple)
        self.assertGreaterEqual(len(bambu_filaments), 2)
        
        sources = {f.source for f in bambu_filaments}
        self.assertIn("filaments.json", sources)
        self.assertIn("user-filaments.json", sources)
    
    def test_filament_addition_no_conflict(self):
        """Test user filaments can add new makers without conflicts."""
        user_filaments = [
            {
                "maker": "New Maker",
                "type": "PLA+",
                "finish": "Transparent",
                "color": "Clear",
                "hex": "#FFFFFF"
            }
        ]
        self._create_user_filaments(user_filaments)
        
        filaments = self._load_with_custom_dir(load_filaments)
        palette = FilamentPalette(filaments)
        
        # Should find new maker
        new_maker_filaments = palette.find_by_maker("New Maker")
        self.assertEqual(len(new_maker_filaments), 1)
        assert len(new_maker_filaments) > 0  # Type assertion for Pylance
        self.assertEqual(new_maker_filaments[0].source, "user-filaments.json")
        
        # Original makers should still exist
        bambu_filaments = palette.find_by_maker("Bambu Lab")
        self.assertGreater(len(bambu_filaments), 0)
        
        test_filaments = palette.find_by_maker("Test Maker") 
        self.assertGreater(len(test_filaments), 0)


class TestSynonymOverrides(TestUserOverrideSystem):
    """Test synonym override behavior."""
    
    def test_synonym_replacement_override(self):
        """Test that user synonyms completely replace core synonyms."""
        # User completely replaces Bambu Lab synonyms
        user_synonyms = {
            "Bambu Lab": ["BambuCustom", "BCL"]  # Completely new list
        }
        self._create_user_synonyms(user_synonyms)
        
        synonyms = self._load_with_custom_dir(load_maker_synonyms)
        filaments = self._load_with_custom_dir(load_filaments)
        palette = FilamentPalette(filaments, synonyms)
        
        # New synonyms should work
        bambu_new = palette.find_by_maker("BambuCustom") 
        self.assertGreater(len(bambu_new), 0)
        
        bcl_result = palette.find_by_maker("BCL")
        self.assertGreater(len(bcl_result), 0)
        
        # Old synonyms should NOT work (replaced, not extended)
        bambu_old = palette.find_by_maker("Bambu")  # Core synonym
        self.assertEqual(len(bambu_old), 0)  # Should be empty
        
        bll_old = palette.find_by_maker("BLL")  # Core synonym
        self.assertEqual(len(bll_old), 0)  # Should be empty
        
        # Canonical name should still work
        bambu_canonical = palette.find_by_maker("Bambu Lab")
        self.assertGreater(len(bambu_canonical), 0)
    
    def test_synonym_addition_no_conflict(self):
        """Test that user synonyms can add new makers without conflicts."""
        # User adds synonyms for new maker
        user_synonyms = {
            "New Company": ["NC", "NewCo"]
        }
        self._create_user_synonyms(user_synonyms)
        
        synonyms = self._load_with_custom_dir(load_maker_synonyms)
        
        # Core synonyms should still exist
        self.assertIn("Bambu Lab", synonyms)
        self.assertIn("Bambu", synonyms["Bambu Lab"])
        self.assertIn("BLL", synonyms["Bambu Lab"])
        
        # User synonyms should be added
        self.assertIn("New Company", synonyms)
        self.assertIn("NC", synonyms["New Company"])
        self.assertIn("NewCo", synonyms["New Company"])
    
    def test_synonym_extension_vs_replacement_detection(self):
        """Test detection of synonym extension vs replacement."""
        # Test replacement case (conflicting maker)
        user_synonyms_replace = {
            "Test Maker": ["NewTM", "TestMakerNew"]  # Replaces ["TM"]
        }
        self._create_user_synonyms(user_synonyms_replace)
        
        synonyms = self._load_with_custom_dir(load_maker_synonyms)
        
        # Should be replacement (core "TM" not present)
        self.assertEqual(synonyms["Test Maker"], ["NewTM", "TestMakerNew"])
        self.assertNotIn("TM", synonyms["Test Maker"])
    
    def test_synonym_override_detection_logging(self):
        """Test that synonym overrides are properly logged."""
        # Set up logging capture
        log_stream = []
        
        class ListHandler(logging.Handler):
            def emit(self, record):
                log_stream.append(self.format(record))
        
        # Add handler to capture logs
        logger = logging.getLogger("color_tools.palette")
        handler = ListHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        try:
            # Create override scenario
            user_synonyms = {
                "Bambu Lab": ["CustomBambu"],  # Replaces ["Bambu", "BLL"]
                "New Maker": ["NM"]           # Addition, no conflict
            }
            self._create_user_synonyms(user_synonyms)
            
            # Load with overrides
            synonyms = self._load_with_custom_dir(load_maker_synonyms)
            
            # Check that override was logged
            log_messages = ' '.join(log_stream)
            self.assertIn("Bambu Lab", log_messages)
            self.assertIn("override", log_messages.lower())
            
        finally:
            # Clean up logger
            logger.removeHandler(handler)


class TestOverrideReporting(TestUserOverrideSystem):
    """Test override detection and reporting."""
    
    def test_color_override_detection(self):
        """Test detection of color overrides."""
        # Create overrides
        user_colors = [
            {
                "name": "red",  # Name override
                "hex": "#DC143C",
                "rgb": [220, 20, 60], 
                "hsl": [348.0, 83.3, 47.1],
                "lab": [47.1, 70.8, 33.2],
                "lch": [47.1, 78.3, 25.1]
            },
            {
                "name": "my_blue",  # RGB override
                "hex": "#0000FF",
                "rgb": [0, 0, 255],
                "hsl": [240.0, 100.0, 50.0],
                "lab": [32.30, 79.19, -107.86], 
                "lch": [32.30, 133.81, 306.3]
            }
        ]
        self._create_user_colors(user_colors)
        
        colors = self._load_with_custom_dir(load_colors)
        palette = Palette(colors)
        
        # Get override information
        overrides = palette.get_override_info()
        
        # Should detect both overrides
        self.assertIn("colors", overrides)
        color_overrides = overrides["colors"]
        
        # Check name override
        name_overrides = color_overrides.get("name", {})
        self.assertIn("red", name_overrides)
        
        # Check RGB override  
        rgb_overrides = color_overrides.get("rgb", {})
        self.assertIn("(0, 0, 255)", rgb_overrides)
    
    def test_filament_override_detection(self):
        """Test detection of filament overrides.""" 
        user_filaments = [
            {
                "maker": "Custom Maker",
                "type": "PETG",
                "finish": "Silk", 
                "color": "Custom Red",
                "hex": "#FF0000"  # RGB override
            }
        ]
        self._create_user_filaments(user_filaments)
        
        filaments = self._load_with_custom_dir(load_filaments)
        palette = FilamentPalette(filaments)
        
        overrides = palette.get_override_info()
        
        # Should detect filament RGB override
        self.assertIn("filaments", overrides)
        filament_overrides = overrides["filaments"]
        
        rgb_overrides = filament_overrides.get("rgb", {})
        self.assertIn("(255, 0, 0)", rgb_overrides)
    
    def test_synonym_override_detection(self):
        """Test detection of synonym overrides."""
        user_synonyms = {
            "Bambu Lab": ["CustomBambu"],  # Replacement
            "New Maker": ["NM"]           # Addition
        }
        self._create_user_synonyms(user_synonyms)
        
        synonyms = self._load_with_custom_dir(load_maker_synonyms)
        filaments = self._load_with_custom_dir(load_filaments) 
        palette = FilamentPalette(filaments, synonyms)
        
        overrides = palette.get_override_info()
        
        # Should detect synonym override
        self.assertIn("synonyms", overrides)
        synonym_overrides = overrides["synonyms"]
        
        self.assertIn("Bambu Lab", synonym_overrides)
        self.assertEqual(synonym_overrides["Bambu Lab"]["type"], "replaced")
        self.assertEqual(synonym_overrides["Bambu Lab"]["old"], ["Bambu", "BLL"])
        self.assertEqual(synonym_overrides["Bambu Lab"]["new"], ["CustomBambu"])
    
    def test_no_overrides_empty_report(self):
        """Test that no overrides results in empty report."""
        # No user files - no overrides
        colors = self._load_with_custom_dir(load_colors)
        palette = Palette(colors)
        
        overrides = palette.get_override_info()
        
        # Should be empty or have empty sections
        self.assertTrue(
            len(overrides.get("colors", {}).get("name", {})) == 0 and
            len(overrides.get("colors", {}).get("rgb", {})) == 0
        )


class TestOverrideIntegration(TestUserOverrideSystem):
    """Test end-to-end override system integration."""
    
    def test_comprehensive_override_scenario(self):
        """Test complex scenario with all types of overrides."""
        # User colors override core colors
        user_colors = [
            {
                "name": "red",  # Name override
                "hex": "#DC143C",
                "rgb": [220, 20, 60],
                "hsl": [348.0, 83.3, 47.1],
                "lab": [47.1, 70.8, 33.2],
                "lch": [47.1, 78.3, 25.1]
            }
        ]
        
        # User filaments override core filaments
        user_filaments = [
            {
                "maker": "Custom Maker", 
                "type": "PETG",
                "finish": "Silk",
                "color": "Custom Blue",
                "hex": "#0000FF"  # Same RGB as core
            }
        ]
        
        # User synonyms replace core synonyms
        user_synonyms = {
            "Bambu Lab": ["CustomBambu", "CB"],  # Replace core synonyms
            "Custom Maker": ["CM", "CustomM"]   # New maker synonyms
        }
        
        # Create all user files
        self._create_user_colors(user_colors)
        self._create_user_filaments(user_filaments)
        self._create_user_synonyms(user_synonyms)
        
        # Load with all overrides
        colors = self._load_with_custom_dir(load_colors)
        filaments = self._load_with_custom_dir(load_filaments)
        synonyms = self._load_with_custom_dir(load_maker_synonyms)
        
        color_palette = Palette(colors)
        filament_palette = FilamentPalette(filaments, synonyms)
        
        # Test color override
        red = color_palette.find_by_name("red")
        assert red is not None  # Type assertion for Pylance
        self.assertEqual(red.source, "user-colors.json")
        self.assertEqual(red.hex, "#DC143C")
        
        # Test filament override
        blue_filaments = filament_palette.find_by_rgb((0, 0, 255))
        user_filament = blue_filaments[0]  # Should be first (prioritized)
        assert user_filament is not None  # Type assertion for Pylance
        self.assertEqual(user_filament.source, "user-filaments.json")
        self.assertEqual(user_filament.maker, "Custom Maker")
        
        # Test synonym override - old synonyms shouldn't work
        bambu_old = filament_palette.find_by_maker("Bambu")
        self.assertEqual(len(bambu_old), 0)
        
        # Test synonym override - new synonyms should work
        bambu_new = filament_palette.find_by_maker("CustomBambu")
        self.assertGreater(len(bambu_new), 0)
        
        # Test new maker synonyms
        custom_maker = filament_palette.find_by_maker("CM")
        self.assertGreater(len(custom_maker), 0)
        assert len(custom_maker) > 0  # Type assertion for Pylance
        self.assertEqual(custom_maker[0].maker, "Custom Maker")
    
    def test_override_transparency_and_logging(self):
        """Test that all overrides are transparent and properly logged."""
        # Create scenario with all override types
        user_colors = [{"name": "red", "hex": "#DC143C", "rgb": [220, 20, 60], 
                       "hsl": [348.0, 83.3, 47.1], "lab": [47.1, 70.8, 33.2], 
                       "lch": [47.1, 78.3, 25.1]}]
        
        user_filaments = [{"maker": "User Maker", "type": "PETG", "finish": "Silk",
                          "color": "User Red", "hex": "#FF0000"}]
        
        user_synonyms = {"Bambu Lab": ["UserBambu"]}
        
        self._create_user_colors(user_colors)
        self._create_user_filaments(user_filaments)
        self._create_user_synonyms(user_synonyms)
        
        # Load everything
        colors = self._load_with_custom_dir(load_colors) 
        filaments = self._load_with_custom_dir(load_filaments)
        synonyms = self._load_with_custom_dir(load_maker_synonyms)
        
        color_palette = Palette(colors)
        filament_palette = FilamentPalette(filaments, synonyms)
        
        # Get comprehensive override reports
        color_overrides = color_palette.get_override_info()
        filament_overrides = filament_palette.get_override_info()
        
        # Verify all overrides are detected
        self.assertIn("colors", color_overrides)
        self.assertIn("filaments", filament_overrides)
        self.assertIn("synonyms", filament_overrides)
        
        # Check specific overrides
        self.assertIn("red", color_overrides["colors"].get("name", {}))
        self.assertIn("(255, 0, 0)", filament_overrides["filaments"].get("rgb", {}))
        self.assertIn("Bambu Lab", filament_overrides["synonyms"])


if __name__ == '__main__':
    # Set up logging to see override messages during tests
    logging.basicConfig(level=logging.INFO)
    
    unittest.main()