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
from typing import Callable, TypeVar

from color_tools.palette import (
    ColorRecord,
    Palette,
    load_colors,
)
from color_tools.filament_palette import (
    FilamentPalette,
    load_filaments, load_maker_synonyms
)

_LoadedData = TypeVar("_LoadedData")


def _user_color(name: str, hex_code: str) -> dict[str, str]:
    """Return one canonical user-authored color record."""
    return {"name": name, "hex": hex_code}


class TestUserOverrideSystem(unittest.TestCase):
    """Test the comprehensive user override system."""
    
    def setUp(self) -> None:
        """Set up test environment with temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Create core data files
        self._create_core_data()
        
        # Store original data directory for restoration
        self.original_data_dir = None
    
    def tearDown(self) -> None:
        """Clean up test environment."""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def _create_core_data(self) -> None:
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
                "id": "bambu-lab-pla-matte-red",
                "maker": "Bambu Lab",
                "type": "PLA",
                "finish": "Matte",
                "color": "Red",
                "hex": "#FF0000"
            },
            {
                "id": "test-maker-pla-glossy-blue",
                "maker": "Test Maker",
                "type": "PLA",
                "finish": "Glossy", 
                "color": "Blue",
                "hex": "#0000FF"
            }
        ]
        
        # Core synonyms
        core_synonyms = {
            "Bambu Lab": ["Bambu", "BBL"],
            "Test Maker": ["TM"]
        }
        
        # Write core files
        with open(self.data_dir / "colors.json", "w") as f:
            json.dump(core_colors, f, indent=2)
        
        with open(self.data_dir / "filaments.json", "w") as f:
            json.dump(core_filaments, f, indent=2)
            
        with open(self.data_dir / "maker_synonyms.json", "w") as f:
            json.dump(core_synonyms, f, indent=2)
    
    def _create_user_colors(self, colors_data: object) -> None:
        """Create user/user-colors.json file with given data."""
        user_dir = self.data_dir / "user"
        user_dir.mkdir(exist_ok=True)
        with open(user_dir / "user-colors.json", "w") as f:
            json.dump(colors_data, f, indent=2)
    
    def _create_user_filaments(self, filaments_data: object) -> None:
        """Create user/user-filaments.json file with given data."""
        user_dir = self.data_dir / "user"
        user_dir.mkdir(exist_ok=True)
        with open(user_dir / "user-filaments.json", "w") as f:
            json.dump(filaments_data, f, indent=2)
    
    def _create_user_synonyms(self, synonyms_data: object) -> None:
        """Create user/user-synonyms.json file with given data."""
        user_dir = self.data_dir / "user"
        user_dir.mkdir(exist_ok=True)
        with open(user_dir / "user-synonyms.json", "w") as f:
            json.dump(synonyms_data, f, indent=2)
    
    def _load_with_custom_dir(self, loader_func: Callable[[str], _LoadedData]) -> _LoadedData:
        """Load data using custom directory."""
        return loader_func(str(self.data_dir))


class TestColorOverrides(TestUserOverrideSystem):
    """Test color override behavior."""
    
    def test_color_name_override(self) -> None:
        """Test that user colors override core colors by name."""
        # User color overrides core red with different RGB
        user_colors = [_user_color("red", "#DC143C")]
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
        
        # The replaced system record is removed from the merged list.
        core_red_rgb = palette.find_by_rgb((255, 0, 0))
        self.assertIsNone(core_red_rgb)
        
        # User RGB should be findable  
        user_red_rgb = palette.find_by_rgb((220, 20, 60))
        self.assertIsNotNone(user_red_rgb)
        assert user_red_rgb is not None  # Type assertion for Pylance
        self.assertEqual(user_red_rgb.name, "red")
        self.assertEqual(user_red_rgb.source, "user-colors.json")
    
    def test_color_rgb_conflict_is_rejected(self) -> None:
        """A different name cannot reuse an existing effective RGB value."""
        # User color uses same RGB as core blue but different name
        user_colors = [_user_color("my_blue", "#0000FF")]
        self._create_user_colors(user_colors)
        
        with self.assertRaisesRegex(ValueError, "conflicts with existing color 'blue'"):
            self._load_with_custom_dir(load_colors)
    
    def test_color_addition_no_conflict(self) -> None:
        """Test that user colors can add new colors without conflicts."""
        user_colors = [_user_color("green", "#00FF00")]
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
    
    def test_color_nearest_color_priority(self) -> None:
        """Test that nearest_color respects user overrides."""
        # User red overrides core red
        user_colors = [_user_color("red", "#DC143C")]
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
    
    def test_filament_rgb_override_priority(self) -> None:
        """Test that find_by_rgb prioritizes user filaments."""
        # User filament with same RGB as core but different attributes
        user_filaments = [
            {
                "id": "custom-maker-petg-silk-custom-red",
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
    
    def test_filament_nearest_filament_priority(self) -> None:
        """Test that nearest_filament prioritizes user filaments."""
        user_filaments = [
            {
                "id": "user-maker-abs-matte-user-blue",
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
    
    def test_filament_maker_search_no_override(self) -> None:
        """Test that maker searches work normally with user additions."""
        # User adds new filament for existing maker
        user_filaments = [
            {
                "id": "bambu-lab-abs-silk-purple",
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
    
    def test_filament_addition_no_conflict(self) -> None:
        """Test user filaments can add new makers without conflicts."""
        user_filaments = [
            {
                "id": "new-maker-pla-plus-transparent-clear",
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
    
    def test_synonym_replacement_override(self) -> None:
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
        
        bbl_old = palette.find_by_maker("BBL")  # Core synonym
        self.assertEqual(len(bbl_old), 0)  # Should be empty
        
        # Canonical name should still work
        bambu_canonical = palette.find_by_maker("Bambu Lab")
        self.assertGreater(len(bambu_canonical), 0)
    
    def test_synonym_addition_no_conflict(self) -> None:
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
        self.assertIn("BBL", synonyms["Bambu Lab"])
        
        # User synonyms should be added
        self.assertIn("New Company", synonyms)
        self.assertIn("NC", synonyms["New Company"])
        self.assertIn("NewCo", synonyms["New Company"])
    
    def test_synonym_extension_vs_replacement_detection(self) -> None:
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

    def test_synonym_report_covers_unchanged_extended_and_added(self) -> None:
        """Every supported synonym merge action is explicit and ordered."""
        self._create_user_synonyms({
            "Bambu Lab": ["BBL", "Bambu"],
            "Test Maker": ["TM", "TestCo"],
            "New Company": ["NC"],
        })

        synonyms, report = load_maker_synonyms(self.data_dir, include_report=True)

        self.assertEqual(report.makers_unchanged, 1)
        self.assertEqual(report.makers_extended, 1)
        self.assertEqual(report.makers_added, 1)
        self.assertEqual(
            [event.action for event in report.events],
            ["unchanged", "extended", "added"],
        )
        self.assertEqual(synonyms["Test Maker"], ["TM", "TestCo"])

    def test_missing_core_synonym_file_starts_with_empty_mapping(self) -> None:
        """A user synonym file can load when no system mapping exists."""
        (self.data_dir / "maker_synonyms.json").unlink()
        self._create_user_synonyms({"New Company": ["NC"]})

        synonyms, report = load_maker_synonyms(self.data_dir, include_report=True)

        self.assertEqual(synonyms, {"New Company": ["NC"]})
        self.assertEqual(report.system_makers_loaded, 0)
        self.assertEqual(report.makers_added, 1)
    
    def test_synonym_override_detection_report(self) -> None:
        """Synonym replacements and additions are returned as typed events."""
        self._create_user_synonyms({
            "Bambu Lab": ["CustomBambu"],
            "New Maker": ["NM"],
        })

        _synonyms, report = load_maker_synonyms(
            self.data_dir,
            include_report=True,
        )

        self.assertEqual(report.makers_replaced, 1)
        self.assertEqual(report.makers_added, 1)
        self.assertEqual(
            [(event.maker, event.action) for event in report.events],
            [("Bambu Lab", "replaced"), ("New Maker", "added")],
        )


class TestOverrideReporting(TestUserOverrideSystem):
    """Test override detection and reporting."""
    
    def test_color_override_detection(self) -> None:
        """Structured loading reports additions and name replacements."""
        user_colors = [
            _user_color("red", "#DC143C"),
            _user_color("green", "#00FF00"),
        ]
        self._create_user_colors(user_colors)

        colors, report = load_colors(self.data_dir, include_report=True)

        self.assertEqual([record.name for record in colors], ["red", "blue", "green"])
        self.assertEqual(report.system_colors_loaded, 2)
        self.assertEqual(report.user_colors_loaded, 2)
        self.assertEqual(report.colors_overridden_by_name, 1)
        self.assertEqual(report.unique_user_colors_loaded, 1)
        self.assertEqual(report.total_colors_available, 3)
        self.assertEqual([event.action for event in report.events], ["overridden", "added"])
        self.assertEqual(report.events[0].replaced_record, ColorRecord(
            name="red",
            hex="#FF0000",
            rgb=(255, 0, 0),
            hsl=(0.0, 100.0, 50.0),
            lab=(53.24, 80.09, 67.20),
            lch=(53.24, 104.55, 40.0),
            source="colors.json",
        ))
    
    def test_filament_override_detection(self) -> None:
        """Test detection of filament overrides.""" 
        user_filaments = [
            {
                "id": "bambu-lab-pla-matte-red",
                "maker": "Custom Maker",
                "type": "PETG",
                "finish": "Silk", 
                "color": "Custom Red",
                "hex": "#F01010"
            }
        ]
        self._create_user_filaments(user_filaments)
        
        filaments, report = load_filaments(self.data_dir, include_report=True)

        self.assertEqual(len(filaments), 2)
        self.assertEqual(report.filaments_overridden_by_id, 1)
        self.assertEqual(report.unique_user_filaments_loaded, 0)
        self.assertEqual(report.events[0].record.maker, "Custom Maker")
        replaced = report.events[0].replaced_record
        self.assertIsNotNone(replaced)
        assert replaced is not None
        self.assertEqual(replaced.id, "bambu-lab-pla-matte-red")
    
    def test_synonym_override_detection(self) -> None:
        """Test detection of synonym overrides."""
        user_synonyms = {
            "Bambu Lab": ["CustomBambu"],  # Replacement
            "New Maker": ["NM"]           # Addition
        }
        self._create_user_synonyms(user_synonyms)
        
        _synonyms, report = load_maker_synonyms(self.data_dir, include_report=True)

        self.assertEqual(report.makers_replaced, 1)
        self.assertEqual(report.makers_added, 1)
        event = report.events[0]
        self.assertEqual(event.maker, "Bambu Lab")
        self.assertEqual(event.previous_synonyms, ("Bambu", "BBL"))
        self.assertEqual(event.effective_synonyms, ("CustomBambu",))
    
    def test_no_overrides_empty_report(self) -> None:
        """Test that no overrides results in empty report."""
        _colors, report = load_colors(self.data_dir, include_report=True)
        self.assertEqual(report.colors_overridden_by_name, 0)
        self.assertEqual(report.unique_user_colors_loaded, 0)
        self.assertEqual(report.events, ())


class TestOverrideIntegration(TestUserOverrideSystem):
    """Test end-to-end override system integration."""
    
    def test_comprehensive_override_scenario(self) -> None:
        """Test complex scenario with all types of overrides."""
        # User colors override core colors
        user_colors = [_user_color("red", "#DC143C")]
        
        # User filament replaces one core record by stable ID
        user_filaments = [
            {
                "id": "test-maker-pla-glossy-blue",
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
    
    def test_override_transparency_and_logging(self) -> None:
        """Test that all overrides are transparent and properly logged."""
        # Create scenario with all override types
        user_colors = [_user_color("red", "#DC143C")]
        
        user_filaments = [{"maker": "User Maker", "type": "PETG", "finish": "Silk",
                          "id": "bambu-lab-pla-matte-red",
                          "color": "User Red", "hex": "#FF0000"}]
        
        user_synonyms = {"Bambu Lab": ["UserBambu"]}
        
        self._create_user_colors(user_colors)
        self._create_user_filaments(user_filaments)
        self._create_user_synonyms(user_synonyms)
        
        # Load everything
        # Get comprehensive override reports
        _colors, color_report = load_colors(self.data_dir, include_report=True)
        _filaments, filament_report = load_filaments(self.data_dir, include_report=True)
        _synonyms, synonym_report = load_maker_synonyms(self.data_dir, include_report=True)
        
        # Verify all overrides are detected
        self.assertEqual(color_report.colors_overridden_by_name, 1)
        self.assertEqual(filament_report.filaments_overridden_by_id, 1)
        self.assertEqual(synonym_report.makers_replaced, 1)
        
        # Check specific overrides
        self.assertEqual(color_report.events[0].record.name, "red")
        self.assertEqual(filament_report.events[0].record.id, "bambu-lab-pla-matte-red")
        self.assertEqual(synonym_report.events[0].maker, "Bambu Lab")


if __name__ == '__main__':
    unittest.main()
