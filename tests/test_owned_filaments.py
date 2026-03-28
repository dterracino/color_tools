"""Unit tests for owned filaments tracking feature."""

import unittest
import tempfile
import json
from pathlib import Path

from color_tools.palette import (
    FilamentPalette,
    FilamentRecord,
    load_owned_filaments,
    save_owned_filaments,
)


class TestOwnedFilamentsLoading(unittest.TestCase):
    """Test loading and saving owned filaments."""
    
    def test_load_owned_filaments_nonexistent_file(self):
        """Test loading when file doesn't exist returns empty set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "owned-filaments.json"
            result = load_owned_filaments(path)
            self.assertEqual(result, set())
    
    def test_load_owned_filaments_valid(self):
        """Test loading valid owned filaments file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "owned-filaments.json"
            
            # Create test file
            data = {
                "owned_filaments": [
                    "bambu-lab_pla-matte_jet-black",
                    "polymaker_polyterra-pla_charcoal-black"
                ]
            }
            with open(path, 'w') as f:
                json.dump(data, f)
            
            result = load_owned_filaments(path)
            self.assertEqual(result, {
                "bambu-lab_pla-matte_jet-black",
                "polymaker_polyterra-pla_charcoal-black"
            })
    
    def test_load_owned_filaments_empty_list(self):
        """Test loading file with empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "owned-filaments.json"
            
            data = {"owned_filaments": []}
            with open(path, 'w') as f:
                json.dump(data, f)
            
            result = load_owned_filaments(path)
            self.assertEqual(result, set())
    
    def test_load_owned_filaments_invalid_structure_no_key(self):
        """Test loading file with invalid structure (missing key)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "owned-filaments.json"
            
            # Wrong structure - missing 'owned_filaments' key
            data = {"filaments": ["id1"]}
            with open(path, 'w') as f:
                json.dump(data, f)
            
            with self.assertRaises(ValueError) as ctx:
                load_owned_filaments(path)
            self.assertIn("owned_filaments", str(ctx.exception))
    
    def test_load_owned_filaments_invalid_structure_not_dict(self):
        """Test loading file with invalid structure (not dict)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "owned-filaments.json"
            
            # Wrong structure - array instead of dict
            data = ["id1", "id2"]
            with open(path, 'w') as f:
                json.dump(data, f)
            
            with self.assertRaises(ValueError) as ctx:
                load_owned_filaments(path)
            self.assertIn("owned_filaments", str(ctx.exception))
    
    def test_load_owned_filaments_invalid_value_type(self):
        """Test loading file with invalid value type (not list)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "owned-filaments.json"
            
            # Wrong type - string instead of list
            data = {"owned_filaments": "bambu-lab_pla-matte_jet-black"}
            with open(path, 'w') as f:
                json.dump(data, f)
            
            with self.assertRaises(ValueError) as ctx:
                load_owned_filaments(path)
            self.assertIn("list", str(ctx.exception))
    
    def test_save_owned_filaments(self):
        """Test saving owned filaments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "owned-filaments.json"
            
            ids = {"id2", "id1", "id3"}  # Out of order
            save_owned_filaments(ids, path)
            
            # Verify file was created
            self.assertTrue(path.exists())
            
            # Verify content is correct and sorted
            with open(path, 'r') as f:
                data = json.load(f)
            
            self.assertEqual(data, {"owned_filaments": ["id1", "id2", "id3"]})
    
    def test_save_owned_filaments_empty(self):
        """Test saving empty set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "owned-filaments.json"
            
            save_owned_filaments(set(), path)
            
            with open(path, 'r') as f:
                data = json.load(f)
            
            self.assertEqual(data, {"owned_filaments": []})


class TestFilamentPaletteOwnedIntegration(unittest.TestCase):
    """Test FilamentPalette owned filaments integration."""
    
    def setUp(self):
        """Create test filament records."""
        self.filaments = [
            FilamentRecord(
                maker="Bambu Lab",
                type="PLA",
                finish="Matte",
                color="Jet Black",
                hex="#000000",
                td_value=0.1,
                source="test",
                id="bambu-lab_pla-matte_jet-black"
            ),
            FilamentRecord(
                maker="Bambu Lab",
                type="PLA",
                finish="Matte",
                color="White",
                hex="#FFFFFF",
                td_value=0.9,
                source="test",
                id="bambu-lab_pla-matte_white"
            ),
            FilamentRecord(
                maker="Polymaker",
                type="PolyTerra PLA",
                finish=None,
                color="Charcoal Black",
                hex="#1A1A1A",
                td_value=0.15,
                source="test",
                id="polymaker_polyterra-pla_charcoal-black"
            ),
        ]
    
    def test_palette_init_without_owned(self):
        """Test palette initialization without owned filaments."""
        palette = FilamentPalette(self.filaments)
        self.assertEqual(palette.owned_filaments, set())
    
    def test_palette_init_with_owned(self):
        """Test palette initialization with owned filaments."""
        owned = {"bambu-lab_pla-matte_jet-black", "polymaker_polyterra-pla_charcoal-black"}
        palette = FilamentPalette(self.filaments, owned_filaments=owned)
        self.assertEqual(palette.owned_filaments, owned)
    
    def test_get_filament_by_id(self):
        """Test getting filament by ID."""
        palette = FilamentPalette(self.filaments)
        
        result = palette.get_filament_by_id("bambu-lab_pla-matte_jet-black")
        self.assertIsNotNone(result)
        assert result is not None  # Type narrowing for Pyright
        self.assertEqual(result.id, "bambu-lab_pla-matte_jet-black")
        self.assertEqual(result.color, "Jet Black")
        
        # Non-existent ID
        result = palette.get_filament_by_id("nonexistent")
        self.assertIsNone(result)
    
    def test_list_owned_empty(self):
        """Test listing owned when none are owned."""
        palette = FilamentPalette(self.filaments)
        result = palette.list_owned()
        self.assertEqual(result, [])
    
    def test_list_owned_with_filaments(self):
        """Test listing owned filaments."""
        owned = {"bambu-lab_pla-matte_white", "bambu-lab_pla-matte_jet-black"}
        palette = FilamentPalette(self.filaments, owned_filaments=owned)
        
        result = palette.list_owned()
        self.assertEqual(len(result), 2)
        
        # Check sorting (by maker, type, color)
        self.assertEqual(result[0].color, "Jet Black")
        self.assertEqual(result[1].color, "White")
    
    def test_list_owned_with_invalid_ids(self):
        """Test listing owned with some invalid IDs."""
        owned = {"bambu-lab_pla-matte_jet-black", "nonexistent-id"}
        palette = FilamentPalette(self.filaments, owned_filaments=owned)
        
        result = palette.list_owned()
        # Should only include valid IDs
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "bambu-lab_pla-matte_jet-black")
    
    def test_add_owned_valid(self):
        """Test adding owned filament."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "owned-filaments.json"
            
            palette = FilamentPalette(self.filaments)
            palette.add_owned("bambu-lab_pla-matte_jet-black", path)
            
            # Check in-memory set
            self.assertIn("bambu-lab_pla-matte_jet-black", palette.owned_filaments)
            
            # Check file was created
            self.assertTrue(path.exists())
            loaded = load_owned_filaments(path)
            self.assertEqual(loaded, {"bambu-lab_pla-matte_jet-black"})
    
    def test_add_owned_invalid_id(self):
        """Test adding non-existent filament ID."""
        palette = FilamentPalette(self.filaments)
        
        with self.assertRaises(ValueError) as ctx:
            palette.add_owned("nonexistent-id")
        self.assertIn("not found", str(ctx.exception))
    
    def test_remove_owned_valid(self):
        """Test removing owned filament."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "owned-filaments.json"
            
            owned = {"bambu-lab_pla-matte_jet-black", "bambu-lab_pla-matte_white"}
            palette = FilamentPalette(self.filaments, owned_filaments=owned)
            
            palette.remove_owned("bambu-lab_pla-matte_jet-black", path)
            
            # Check in-memory set
            self.assertNotIn("bambu-lab_pla-matte_jet-black", palette.owned_filaments)
            self.assertIn("bambu-lab_pla-matte_white", palette.owned_filaments)
            
            # Check file
            loaded = load_owned_filaments(path)
            self.assertEqual(loaded, {"bambu-lab_pla-matte_white"})
    
    def test_remove_owned_not_in_list(self):
        """Test removing filament that's not in owned list."""
        palette = FilamentPalette(self.filaments)
        
        with self.assertRaises(ValueError) as ctx:
            palette.remove_owned("bambu-lab_pla-matte_jet-black")
        self.assertIn("not in owned list", str(ctx.exception))
    
    def test_save_owned(self):
        """Test save_owned method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "owned-filaments.json"
            
            palette = FilamentPalette(self.filaments)
            palette.owned_filaments.add("bambu-lab_pla-matte_jet-black")
            palette.save_owned(path)
            
            loaded = load_owned_filaments(path)
            self.assertEqual(loaded, {"bambu-lab_pla-matte_jet-black"})


class TestFilamentPaletteOwnedFiltering(unittest.TestCase):
    """Test owned filaments filtering behavior."""
    
    def setUp(self):
        """Create test filament records."""
        self.filaments = [
            FilamentRecord(
                maker="Bambu Lab",
                type="PLA",
                finish="Matte",
                color="Jet Black",
                hex="#000000",
                td_value=0.1,
                source="test",
                id="bambu-lab_pla-matte_jet-black"
            ),
            FilamentRecord(
                maker="Bambu Lab",
                type="PLA",
                finish="Matte",
                color="White",
                hex="#FFFFFF",
                td_value=0.9,
                source="test",
                id="bambu-lab_pla-matte_white"
            ),
            FilamentRecord(
                maker="Polymaker",
                type="PolyTerra PLA",
                finish=None,
                color="Charcoal Black",
                hex="#1A1A1A",
                td_value=0.15,
                source="test",
                id="polymaker_polyterra-pla_charcoal-black"
            ),
        ]
        
        self.owned = {"bambu-lab_pla-matte_jet-black", "polymaker_polyterra-pla_charcoal-black"}
    
    def test_filter_owned_none_auto_detects_false(self):
        """Test filter with owned=None and no owned filaments (auto-detects False)."""
        palette = FilamentPalette(self.filaments)
        result = palette.filter(owned=None)
        
        # Should return all filaments (no owned list)
        self.assertEqual(len(result), 3)
    
    def test_filter_owned_none_auto_detects_true(self):
        """Test filter with owned=None and owned filaments exist (auto-detects True)."""
        palette = FilamentPalette(self.filaments, owned_filaments=self.owned)
        result = palette.filter(owned=None)
        
        # Should return only owned filaments
        self.assertEqual(len(result), 2)
        ids = {r.id for r in result}
        self.assertEqual(ids, self.owned)
    
    def test_filter_owned_true(self):
        """Test filter with owned=True explicitly."""
        palette = FilamentPalette(self.filaments, owned_filaments=self.owned)
        result = palette.filter(owned=True)
        
        self.assertEqual(len(result), 2)
        ids = {r.id for r in result}
        self.assertEqual(ids, self.owned)
    
    def test_filter_owned_false(self):
        """Test filter with owned=False explicitly."""
        palette = FilamentPalette(self.filaments, owned_filaments=self.owned)
        result = palette.filter(owned=False)
        
        # Should return all filaments
        self.assertEqual(len(result), 3)
    
    def test_filter_owned_with_other_filters(self):
        """Test owned filtering combined with other filters."""
        palette = FilamentPalette(self.filaments, owned_filaments=self.owned)
        
        # Owned + maker filter
        result = palette.filter(owned=True, maker="Bambu Lab")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "bambu-lab_pla-matte_jet-black")
        
        # Owned + type filter
        result = palette.filter(owned=True, type_name="PolyTerra PLA")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "polymaker_polyterra-pla_charcoal-black")
    
    def test_nearest_filament_owned_auto_detect(self):
        """Test nearest_filament with auto-detect owned filtering."""
        palette = FilamentPalette(self.filaments, owned_filaments=self.owned)
        
        # Black color - should find owned Jet Black
        result, distance = palette.nearest_filament((10, 10, 10), owned=None)
        self.assertEqual(result.id, "bambu-lab_pla-matte_jet-black")
    
    def test_nearest_filament_owned_false_override(self):
        """Test nearest_filament with owned=False override."""
        palette = FilamentPalette(self.filaments, owned_filaments=self.owned)
        
        # White color - should find White even though not owned
        result, distance = palette.nearest_filament((255, 255, 255), owned=False)
        self.assertEqual(result.id, "bambu-lab_pla-matte_white")
    
    def test_nearest_filaments_owned_filtering(self):
        """Test nearest_filaments with owned filtering."""
        palette = FilamentPalette(self.filaments, owned_filaments=self.owned)
        
        # Get top 3 nearest to black with owned filtering
        results = palette.nearest_filaments((10, 10, 10), count=3, owned=True)
        
        # Should only return 2 results (owned filaments)
        self.assertEqual(len(results), 2)
        ids = {r[0].id for r in results}
        self.assertEqual(ids, self.owned)
    
    def test_filter_owned_empty_owned_set(self):
        """Test behavior when owned set is empty."""
        palette = FilamentPalette(self.filaments, owned_filaments=set())
        
        # Auto-detect should see empty set and return all
        result = palette.filter(owned=None)
        self.assertEqual(len(result), 3)
        
        # Explicit True should return empty (no owned)
        result = palette.filter(owned=True)
        self.assertEqual(len(result), 0)


if __name__ == '__main__':
    unittest.main()
