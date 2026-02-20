"""Tests for owned filament ID tracking functionality."""

import unittest
from pathlib import Path
import tempfile
import json

from color_tools.palette import FilamentPalette, FilamentRecord, load_filaments, load_owned_filaments


class TestOwnedFilaments(unittest.TestCase):
    """Test owned filament tracking via ID-based reference system."""
    
    def setUp(self):
        """Create test data with filaments that have IDs."""
        self.test_filaments = [
            {
                "id": "test-bambu-pla-black",
                "maker": "Bambu Lab",
                "type": "PLA",
                "finish": "Basic",
                "color": "Black",
                "hex": "#1A1A1A"
            },
            {
                "id": "test-bambu-pla-white",
                "maker": "Bambu Lab",
                "type": "PLA",
                "finish": "Basic",
                "color": "White",
                "hex": "#F0F0F0"
            },
            {
                "id": "test-polymaker-pla-blue",
                "maker": "Polymaker",
                "type": "PLA",
                "finish": "Matte",
                "color": "Blue",
                "hex": "#0000FF"
            },
            {
                "id": "test-polymaker-pla-red",
                "maker": "Polymaker",
                "type": "PLA",
                "finish": "Matte",
                "color": "Red",
                "hex": "#FF0000"
            }
        ]
    
    def test_load_owned_filaments_list_format(self):
        """Test loading owned filaments from list format."""
        owned_data = [
            "test-bambu-pla-black",
            "test-bambu-pla-white"
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            user_dir = Path(temp_dir) / "user"
            user_dir.mkdir()
            owned_file = user_dir / "owned-filaments.json"
            
            with open(owned_file, 'w') as f:
                json.dump(owned_data, f)
            
            owned_ids = load_owned_filaments(temp_dir)
            
            self.assertEqual(len(owned_ids), 2)
            self.assertIn("test-bambu-pla-black", owned_ids)
            self.assertIn("test-bambu-pla-white", owned_ids)
    
    def test_load_owned_filaments_dict_format(self):
        """Test loading owned filaments from dict format with 'owned_ids' key."""
        owned_data = {
            "owned_ids": [
                "test-bambu-pla-black",
                "test-polymaker-pla-red"
            ]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            user_dir = Path(temp_dir) / "user"
            user_dir.mkdir()
            owned_file = user_dir / "owned-filaments.json"
            
            with open(owned_file, 'w') as f:
                json.dump(owned_data, f)
            
            owned_ids = load_owned_filaments(temp_dir)
            
            self.assertEqual(len(owned_ids), 2)
            self.assertIn("test-bambu-pla-black", owned_ids)
            self.assertIn("test-polymaker-pla-red", owned_ids)
    
    def test_load_owned_filaments_missing_file(self):
        """Test loading owned filaments when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            owned_ids = load_owned_filaments(temp_dir)
            
            # Should return empty set when file doesn't exist
            self.assertEqual(len(owned_ids), 0)
            self.assertIsInstance(owned_ids, set)
    
    def test_filament_palette_with_owned_ids(self):
        """Test FilamentPalette initialization with owned IDs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_filaments, f)
            temp_path = f.name
        
        try:
            records = load_filaments(temp_path)
            owned_ids = {"test-bambu-pla-black", "test-bambu-pla-white"}
            
            palette = FilamentPalette(records, {}, owned_ids)
            
            self.assertEqual(len(palette.owned_ids), 2)
            self.assertIn("test-bambu-pla-black", palette.owned_ids)
        finally:
            Path(temp_path).unlink()
    
    def test_filter_owned_only(self):
        """Test FilamentPalette.filter() with owned_only parameter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_filaments, f)
            temp_path = f.name
        
        try:
            records = load_filaments(temp_path)
            owned_ids = {"test-bambu-pla-black", "test-bambu-pla-white"}
            palette = FilamentPalette(records, {}, owned_ids)
            
            # Filter for owned filaments only
            owned = palette.filter(owned_only=True)
            self.assertEqual(len(owned), 2, "Should have 2 owned filaments")
            
            # Check we got the right filaments
            colors = {f.color for f in owned}
            self.assertEqual(colors, {"Black", "White"})
            
            # Filter without owned_only (default should include all)
            all_filaments = palette.filter(owned_only=False)
            self.assertEqual(len(all_filaments), 4, "Should have all 4 filaments")
            
            # Combine owned_only with other filters
            owned_bambu = palette.filter(maker="Bambu Lab", owned_only=True)
            self.assertEqual(len(owned_bambu), 2, "Should have 2 owned Bambu filaments")
            self.assertTrue(all(f.maker == "Bambu Lab" for f in owned_bambu))
            
            # Filter for owned Polymaker (should be empty - we only own Bambu)
            owned_poly = palette.filter(maker="Polymaker", owned_only=True)
            self.assertEqual(len(owned_poly), 0, "Should have no owned Polymaker filaments")
        finally:
            Path(temp_path).unlink()
    
    def test_nearest_filament_owned_only(self):
        """Test nearest_filament() with owned_only parameter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_filaments, f)
            temp_path = f.name
        
        try:
            records = load_filaments(temp_path)
            owned_ids = {"test-bambu-pla-black", "test-bambu-pla-white"}
            palette = FilamentPalette(records, {}, owned_ids)
            
            # Search for nearest to black (RGB: 0, 0, 0) among owned filaments
            nearest, distance = palette.nearest_filament((0, 0, 0), owned_only=True)
            self.assertEqual(nearest.color, "Black", "Black should be nearest to RGB(0,0,0)")
            self.assertEqual(nearest.id, "test-bambu-pla-black")
            
            # Search for nearest to blue among ALL filaments (should find Blue)
            nearest_all, _ = palette.nearest_filament((0, 0, 255), owned_only=False)
            self.assertEqual(nearest_all.color, "Blue", "Blue should be nearest to RGB(0,0,255)")
            
            # Search for nearest to blue among OWNED filaments only (should NOT find Blue)
            nearest_owned, _ = palette.nearest_filament((0, 0, 255), owned_only=True)
            self.assertNotEqual(nearest_owned.color, "Blue", "Blue is not owned")
            # Should be either Black or White (both are owned)
            self.assertIn(nearest_owned.color, ["Black", "White"])
        finally:
            Path(temp_path).unlink()
    
    def test_nearest_filaments_owned_only(self):
        """Test nearest_filaments() (plural) with owned_only parameter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_filaments, f)
            temp_path = f.name
        
        try:
            records = load_filaments(temp_path)
            owned_ids = {"test-bambu-pla-black", "test-bambu-pla-white"}
            palette = FilamentPalette(records, {}, owned_ids)
            
            # Get top 3 nearest to gray among ALL filaments
            results_all = palette.nearest_filaments((128, 128, 128), count=3, owned_only=False)
            self.assertEqual(len(results_all), 3, "Should return 3 results")
            
            # Get top 3 nearest to gray among OWNED filaments (only 2 owned, so should get 2)
            results_owned = palette.nearest_filaments((128, 128, 128), count=3, owned_only=True)
            self.assertEqual(len(results_owned), 2, "Should return only 2 (all owned)")
            
            # Verify they're all owned
            for filament, _ in results_owned:
                self.assertIn(filament.id, owned_ids, f"{filament.id} should be owned")
            
            # Verify they're sorted by distance
            distances = [d for _, d in results_owned]
            self.assertEqual(distances, sorted(distances), "Results should be sorted by distance")
        finally:
            Path(temp_path).unlink()
    
    def test_no_owned_filaments_error(self):
        """Test that searching with owned_only raises error when no owned filaments match."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_filaments, f)
            temp_path = f.name
        
        try:
            records = load_filaments(temp_path)
            # Create palette with owned IDs that don't exist
            owned_ids = {"non-existent-id"}
            palette = FilamentPalette(records, {}, owned_ids)
            
            # Should raise error when no owned filaments match
            with self.assertRaises(ValueError) as context:
                palette.nearest_filament((128, 128, 128), owned_only=True)
            self.assertIn("No filaments match", str(context.exception))
        finally:
            Path(temp_path).unlink()
    
    def test_owned_ids_persistence(self):
        """Test that owned_ids are properly stored and accessible."""
        records = []
        owned_ids = {"id1", "id2", "id3"}
        
        palette = FilamentPalette(records, {}, owned_ids)
        
        self.assertEqual(palette.owned_ids, owned_ids)
        self.assertIsInstance(palette.owned_ids, set)


if __name__ == '__main__':
    unittest.main()
