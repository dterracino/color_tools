"""Tests for owned filament functionality."""

import unittest
from pathlib import Path
import tempfile
import json

from color_tools.palette import FilamentPalette, FilamentRecord, load_filaments


class TestOwnedFilaments(unittest.TestCase):
    """Test owned filament tracking and filtering."""
    
    def setUp(self):
        """Create test data with owned and non-owned filaments."""
        self.test_data = [
            {
                "id": "test-bambu-pla-black",
                "maker": "Bambu Lab",
                "type": "PLA",
                "finish": "Basic",
                "color": "Black",
                "hex": "#1A1A1A",
                "owned": True
            },
            {
                "id": "test-bambu-pla-white",
                "maker": "Bambu Lab",
                "type": "PLA",
                "finish": "Basic",
                "color": "White",
                "hex": "#F0F0F0",
                "owned": True
            },
            {
                "id": "test-polymaker-pla-blue",
                "maker": "Polymaker",
                "type": "PLA",
                "finish": "Matte",
                "color": "Blue",
                "hex": "#0000FF",
                "owned": False
            },
            {
                "id": "test-polymaker-pla-red",
                "maker": "Polymaker",
                "type": "PLA",
                "finish": "Matte",
                "color": "Red",
                "hex": "#FF0000",
                # No owned field - should default to False
            }
        ]
    
    def test_filament_record_owned_field(self):
        """Test FilamentRecord accepts and stores owned field."""
        # Test with owned=True
        owned_filament = FilamentRecord(
            id="test-1",
            maker="Test Maker",
            type="PLA",
            finish="Matte",
            color="Red",
            hex="#FF0000",
            owned=True
        )
        self.assertTrue(owned_filament.owned)
        
        # Test with owned=False
        not_owned_filament = FilamentRecord(
            id="test-2",
            maker="Test Maker",
            type="PLA",
            finish="Matte",
            color="Blue",
            hex="#0000FF",
            owned=False
        )
        self.assertFalse(not_owned_filament.owned)
        
        # Test default value (should be False)
        default_filament = FilamentRecord(
            id="test-3",
            maker="Test Maker",
            type="PLA",
            finish="Matte",
            color="Green",
            hex="#00FF00"
        )
        self.assertFalse(default_filament.owned)
    
    def test_load_filaments_with_owned_field(self):
        """Test loading filaments from JSON with owned field."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_data, f)
            temp_path = f.name
        
        try:
            records = load_filaments(temp_path)
            
            # Should load 4 filaments
            self.assertEqual(len(records), 4)
            
            # Check owned flags
            owned_count = sum(1 for r in records if r.owned)
            self.assertEqual(owned_count, 2, "Should have 2 owned filaments")
            
            not_owned_count = sum(1 for r in records if not r.owned)
            self.assertEqual(not_owned_count, 2, "Should have 2 not-owned filaments")
            
            # Check specific filaments
            black = next(r for r in records if r.color == "Black")
            self.assertTrue(black.owned)
            
            blue = next(r for r in records if r.color == "Blue")
            self.assertFalse(blue.owned)
            
            # Check that missing owned field defaults to False
            red = next(r for r in records if r.color == "Red")
            self.assertFalse(red.owned)
        finally:
            Path(temp_path).unlink()
    
    def test_filter_owned_only(self):
        """Test FilamentPalette.filter() with owned_only parameter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_data, f)
            temp_path = f.name
        
        try:
            records = load_filaments(temp_path)
            palette = FilamentPalette(records, {})
            
            # Filter for owned filaments only
            owned = palette.filter(owned_only=True)
            self.assertEqual(len(owned), 2, "Should have 2 owned filaments")
            self.assertTrue(all(r.owned for r in owned), "All should be owned")
            
            # Check we got the right filaments
            colors = {r.color for r in owned}
            self.assertEqual(colors, {"Black", "White"})
            
            # Filter without owned_only (default should include all)
            all_filaments = palette.filter(owned_only=False)
            self.assertEqual(len(all_filaments), 4, "Should have all 4 filaments")
            
            # Combine owned_only with other filters
            owned_bambu = palette.filter(maker="Bambu Lab", owned_only=True)
            self.assertEqual(len(owned_bambu), 2, "Should have 2 owned Bambu filaments")
            self.assertTrue(all(r.maker == "Bambu Lab" for r in owned_bambu))
            self.assertTrue(all(r.owned for r in owned_bambu))
            
            # Filter for owned Polymaker (should be empty)
            owned_poly = palette.filter(maker="Polymaker", owned_only=True)
            self.assertEqual(len(owned_poly), 0, "Should have no owned Polymaker filaments")
        finally:
            Path(temp_path).unlink()
    
    def test_nearest_filament_owned_only(self):
        """Test nearest_filament() with owned_only parameter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_data, f)
            temp_path = f.name
        
        try:
            records = load_filaments(temp_path)
            palette = FilamentPalette(records, {})
            
            # Search for nearest to black (RGB: 0, 0, 0) among owned filaments
            nearest, distance = palette.nearest_filament((0, 0, 0), owned_only=True)
            self.assertEqual(nearest.color, "Black", "Black should be nearest to RGB(0,0,0)")
            self.assertTrue(nearest.owned, "Result should be owned")
            
            # Search for nearest to blue among ALL filaments (should find Blue)
            nearest_all, _ = palette.nearest_filament((0, 0, 255), owned_only=False)
            self.assertEqual(nearest_all.color, "Blue", "Blue should be nearest to RGB(0,0,255)")
            
            # Search for nearest to blue among OWNED filaments only (should find White)
            nearest_owned, _ = palette.nearest_filament((0, 0, 255), owned_only=True)
            self.assertNotEqual(nearest_owned.color, "Blue", "Blue is not owned")
            self.assertTrue(nearest_owned.owned, "Result should be owned")
            
            # Should be either Black or White (both are owned)
            self.assertIn(nearest_owned.color, ["Black", "White"])
        finally:
            Path(temp_path).unlink()
    
    def test_nearest_filaments_owned_only(self):
        """Test nearest_filaments() (plural) with owned_only parameter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_data, f)
            temp_path = f.name
        
        try:
            records = load_filaments(temp_path)
            palette = FilamentPalette(records, {})
            
            # Get top 3 nearest to gray among ALL filaments
            results_all = palette.nearest_filaments((128, 128, 128), count=3, owned_only=False)
            self.assertEqual(len(results_all), 3, "Should return 3 results")
            
            # Get top 3 nearest to gray among OWNED filaments (only 2 owned, so should get 2)
            results_owned = palette.nearest_filaments((128, 128, 128), count=3, owned_only=True)
            self.assertEqual(len(results_owned), 2, "Should return only 2 (all owned)")
            self.assertTrue(all(r.owned for r, _ in results_owned), "All should be owned")
            
            # Verify they're sorted by distance
            distances = [d for _, d in results_owned]
            self.assertEqual(distances, sorted(distances), "Results should be sorted by distance")
        finally:
            Path(temp_path).unlink()
    
    def test_no_owned_filaments_error(self):
        """Test that searching with owned_only raises error when no owned filaments."""
        test_data = [
            {
                "id": "test-1",
                "maker": "Test",
                "type": "PLA",
                "finish": "Basic",
                "color": "Red",
                "hex": "#FF0000",
                "owned": False
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name
        
        try:
            records = load_filaments(temp_path)
            palette = FilamentPalette(records, {})
            
            # Should raise error when no owned filaments
            with self.assertRaises(ValueError) as context:
                palette.nearest_filament((128, 128, 128), owned_only=True)
            self.assertIn("No filaments match", str(context.exception))
        finally:
            Path(temp_path).unlink()
    
    def test_backward_compatibility(self):
        """Test that existing code without owned field still works."""
        # Old-style filament data without owned field
        old_data = [
            {
                "id": "old-filament",
                "maker": "Old Maker",
                "type": "PLA",
                "finish": "Basic",
                "color": "Gray",
                "hex": "#808080"
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(old_data, f)
            temp_path = f.name
        
        try:
            records = load_filaments(temp_path)
            self.assertEqual(len(records), 1)
            self.assertFalse(records[0].owned, "Should default to False")
            
            palette = FilamentPalette(records, {})
            
            # Should work without owned_only parameter (backward compatibility)
            nearest, _ = palette.nearest_filament((128, 128, 128))
            self.assertEqual(nearest.color, "Gray")
            
            # Should work with owned_only=False
            results = palette.filter(owned_only=False)
            self.assertEqual(len(results), 1)
        finally:
            Path(temp_path).unlink()


if __name__ == '__main__':
    unittest.main()
