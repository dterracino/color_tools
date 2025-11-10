"""
Tests for database integrity and filament record validation.

This module validates the entire filament database to ensure:
- All filaments have valid, unique IDs
- IDs follow the expected slug format
- Required fields are present and valid
- No duplicate entries exist
"""

from __future__ import annotations
import re
import unittest
from collections import Counter
from color_tools.palette import FilamentRecord, load_filaments


class TestFilamentDatabaseIntegrity(unittest.TestCase):
    """Test integrity of the filament database."""
    
    @classmethod
    def setUpClass(cls):
        """Load filaments once for all tests."""
        cls.filaments = load_filaments()
    
    def test_database_loads_successfully(self):
        """Test that database loads without errors."""
        self.assertIsNotNone(self.filaments)
        self.assertGreater(len(self.filaments), 0, "Database should contain filaments")
    
    def test_all_filaments_have_ids(self):
        """Test that all filaments have non-empty ID fields."""
        for i, filament in enumerate(self.filaments):
            with self.subTest(filament=filament.color, maker=filament.maker):
                self.assertIsNotNone(filament.id, f"Filament at index {i} has None ID")
                self.assertNotEqual(filament.id, "", f"Filament at index {i} has empty ID")
                self.assertIsInstance(filament.id, str, f"Filament at index {i} ID is not a string")
    
    def test_all_ids_are_unique(self):
        """Test that all filament IDs are unique (no collisions)."""
        id_counts = Counter(f.id for f in self.filaments)
        duplicates = {id_: count for id_, count in id_counts.items() if count > 1}
        
        self.assertEqual(len(duplicates), 0, 
            f"Found {len(duplicates)} duplicate IDs: {dict(list(duplicates.items())[:5])}")
    
    def test_id_format_is_valid_slug(self):
        """Test that all IDs follow valid slug format (lowercase, hyphens, no spaces)."""
        # Valid slug: lowercase letters, numbers, hyphens only
        # Should NOT contain: spaces, uppercase, special chars (except hyphen)
        slug_pattern = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
        
        invalid_ids = []
        for filament in self.filaments:
            if not slug_pattern.match(filament.id):
                invalid_ids.append({
                    'id': filament.id,
                    'maker': filament.maker,
                    'color': filament.color
                })
        
        self.assertEqual(len(invalid_ids), 0,
            f"Found {len(invalid_ids)} filaments with invalid ID format:\n" +
            "\n".join(f"  - {f['id']} ({f['maker']} - {f['color']})" 
                     for f in invalid_ids[:10]))
    
    def test_all_filaments_have_required_fields(self):
        """Test that all filaments have required non-None fields."""
        required_fields = ['id', 'maker', 'type', 'color', 'hex']
        
        for i, filament in enumerate(self.filaments):
            with self.subTest(filament=filament.color, maker=filament.maker):
                for field in required_fields:
                    value = getattr(filament, field)
                    self.assertIsNotNone(value, 
                        f"Filament at index {i} has None {field}")
                    self.assertNotEqual(value, "", 
                        f"Filament at index {i} has empty {field}")
    
    def test_all_hex_codes_are_valid(self):
        """Test that all hex codes are valid and can be converted to RGB."""
        # The FilamentRecord.rgb property handles dual-color format,
        # so we just need to test that it returns valid RGB tuples
        invalid_hex = []
        
        for filament in self.filaments:
            try:
                rgb = filament.rgb
                # Check it's a tuple of 3 integers in valid range
                if not isinstance(rgb, tuple) or len(rgb) != 3:
                    invalid_hex.append({
                        'id': filament.id,
                        'hex': filament.hex,
                        'rgb': rgb,
                        'reason': f'RGB is not a 3-tuple: {rgb}'
                    })
                elif not all(isinstance(v, int) and 0 <= v <= 255 for v in rgb):
                    invalid_hex.append({
                        'id': filament.id,
                        'hex': filament.hex,
                        'rgb': rgb,
                        'reason': f'RGB values out of range [0-255]: {rgb}'
                    })
            except Exception as e:
                invalid_hex.append({
                    'id': filament.id,
                    'hex': filament.hex,
                    'rgb': None,
                    'reason': f'Exception converting to RGB: {str(e)}'
                })
        
        self.assertEqual(len(invalid_hex), 0,
            f"Found {len(invalid_hex)} filaments with invalid hex codes:\n" +
            "\n".join(f"  - {f['id']}: {f['hex']} - {f['reason']}" 
                     for f in invalid_hex[:10]))
    
    def test_dual_color_hex_format(self):
        """Test that dual-color filaments use dash separator (not comma)."""
        # Dual-color format: #XXXXXX-#YYYYYY
        # Invalid format: #XXXXXX, #YYYYYY or #XXXXXX,#YYYYYY
        
        invalid_format = []
        for filament in self.filaments:
            if ',' in filament.hex:
                invalid_format.append({
                    'id': filament.id,
                    'hex': filament.hex,
                    'maker': filament.maker,
                    'color': filament.color
                })
        
        self.assertEqual(len(invalid_format), 0,
            f"Found {len(invalid_format)} filaments with comma in hex (should use dash):\n" +
            "\n".join(f"  - {f['id']}: {f['hex']} ({f['maker']} - {f['color']})" 
                     for f in invalid_format[:10]))
    
    def test_td_value_range_if_present(self):
        """Test that td_value is a valid number when present."""
        # TD values can be > 1.0 (they're not normalized percentages)
        # Just check they're reasonable positive numbers
        invalid_td = []
        
        for filament in self.filaments:
            if filament.td_value is not None:
                # Check it's a number and not negative or absurdly large
                if not isinstance(filament.td_value, (int, float)):
                    invalid_td.append({
                        'id': filament.id,
                        'td_value': filament.td_value,
                        'type': type(filament.td_value).__name__,
                        'reason': 'not a number'
                    })
                elif filament.td_value < 0:
                    invalid_td.append({
                        'id': filament.id,
                        'td_value': filament.td_value,
                        'type': type(filament.td_value).__name__,
                        'reason': 'negative value'
                    })
                elif filament.td_value > 100:  # Arbitrary upper bound
                    invalid_td.append({
                        'id': filament.id,
                        'td_value': filament.td_value,
                        'type': type(filament.td_value).__name__,
                        'reason': 'unreasonably large (>100)'
                    })
        
        self.assertEqual(len(invalid_td), 0,
            f"Found {len(invalid_td)} filaments with invalid td_value:\n" +
            "\n".join(f"  - {f['id']}: {f['td_value']} ({f['type']}) - {f['reason']}" 
                     for f in invalid_td[:10]))
    
    def test_other_names_format_if_present(self):
        """Test that other_names is a list of strings when present."""
        invalid_other_names = []
        
        for filament in self.filaments:
            if filament.other_names is not None:
                # Should be a list
                if not isinstance(filament.other_names, list):
                    invalid_other_names.append({
                        'id': filament.id,
                        'other_names': filament.other_names,
                        'type': type(filament.other_names).__name__,
                        'reason': 'not a list'
                    })
                # Should be a list of strings
                elif not all(isinstance(name, str) for name in filament.other_names):
                    invalid_other_names.append({
                        'id': filament.id,
                        'other_names': filament.other_names,
                        'reason': 'contains non-string values'
                    })
                # Should not be empty
                elif len(filament.other_names) == 0:
                    invalid_other_names.append({
                        'id': filament.id,
                        'other_names': filament.other_names,
                        'reason': 'empty list (should be null instead)'
                    })
        
        self.assertEqual(len(invalid_other_names), 0,
            f"Found {len(invalid_other_names)} filaments with invalid other_names:\n" +
            "\n".join(f"  - {f['id']}: {f.get('other_names')} - {f['reason']}" 
                     for f in invalid_other_names[:10]))
    
    def test_no_exact_duplicates(self):
        """Test that there are no exact duplicate filament entries."""
        # Create signature of each filament (excluding ID)
        seen = {}
        duplicates = []
        
        for filament in self.filaments:
            # Signature: maker, type, finish, color, hex
            signature = (
                filament.maker,
                filament.type,
                filament.finish,
                filament.color,
                filament.hex
            )
            
            if signature in seen:
                duplicates.append({
                    'filament1_id': seen[signature],
                    'filament2_id': filament.id,
                    'maker': filament.maker,
                    'type': filament.type,
                    'color': filament.color
                })
            else:
                seen[signature] = filament.id
        
        self.assertEqual(len(duplicates), 0,
            f"Found {len(duplicates)} exact duplicate filament entries:\n" +
            "\n".join(f"  - {d['filament1_id']} == {d['filament2_id']} "
                     f"({d['maker']} {d['type']} {d['color']})" 
                     for d in duplicates[:10]))


class TestFilamentRecordValidation(unittest.TestCase):
    """Test FilamentRecord field validation."""
    
    def test_id_field_is_required(self):
        """Test that ID field is required (not optional)."""
        # This should work
        filament = FilamentRecord(
            id="test-maker-pla-red",
            maker="Test",
            type="PLA",
            finish=None,
            color="Red",
            hex="#FF0000",
            td_value=None
        )
        self.assertEqual(filament.id, "test-maker-pla-red")
    
    def test_id_field_must_be_string(self):
        """Test that ID field must be a string."""
        filament = FilamentRecord(
            id="valid-slug",
            maker="Test",
            type="PLA",
            finish=None,
            color="Red",
            hex="#FF0000"
        )
        self.assertIsInstance(filament.id, str)
    
    def test_finish_can_be_none(self):
        """Test that finish field can be None."""
        filament = FilamentRecord(
            id="test-maker-pla-red",
            maker="Test",
            type="PLA",
            finish=None,
            color="Red",
            hex="#FF0000"
        )
        self.assertIsNone(filament.finish)
    
    def test_td_value_can_be_none(self):
        """Test that td_value field can be None."""
        filament = FilamentRecord(
            id="test-maker-pla-red",
            maker="Test",
            type="PLA",
            finish=None,
            color="Red",
            hex="#FF0000",
            td_value=None
        )
        self.assertIsNone(filament.td_value)
    
    def test_other_names_can_be_none(self):
        """Test that other_names field can be None."""
        filament = FilamentRecord(
            id="test-maker-pla-red",
            maker="Test",
            type="PLA",
            finish=None,
            color="Red",
            hex="#FF0000",
            other_names=None
        )
        self.assertIsNone(filament.other_names)
    
    def test_other_names_can_be_list(self):
        """Test that other_names field can be a list of strings."""
        filament = FilamentRecord(
            id="test-maker-pla-red",
            maker="Test",
            type="PLA",
            finish=None,
            color="Red",
            hex="#FF0000",
            other_names=["Classic Red", "Ruby Red"]
        )
        self.assertEqual(filament.other_names, ["Classic Red", "Ruby Red"])


if __name__ == "__main__":
    unittest.main()
