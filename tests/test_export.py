"""
Unit tests for export functionality.

Tests export to various formats (CSV, JSON, AutoForge)
including auto-filename generation and filtering integration.
"""

import unittest
import json
import csv
import tempfile
from pathlib import Path
from datetime import datetime

from color_tools.export import (
    export_filaments,
    export_colors,
    export_filaments_autoforge,
    export_filaments_csv,
    export_filaments_json,
    export_colors_csv,
    export_colors_json,
    list_export_formats,
    generate_filename,
    EXPORT_FORMATS,
)
from color_tools.palette import (
    FilamentRecord,
    ColorRecord,
    FilamentPalette,
    Palette,
)


class TestExportFormats(unittest.TestCase):
    """Test export format definitions."""
    
    def test_export_formats_structure(self):
        """Verify EXPORT_FORMATS has expected structure."""
        self.assertIn('autoforge', EXPORT_FORMATS)
        self.assertIn('csv', EXPORT_FORMATS)
        self.assertIn('json', EXPORT_FORMATS)
        
        # Check autoforge format
        af = EXPORT_FORMATS['autoforge']
        self.assertEqual(af['file_extension'], 'csv')
        self.assertEqual(af['applies_to'], 'filaments')
        
        # Check csv format (applies to both)
        csv_fmt = EXPORT_FORMATS['csv']
        self.assertEqual(csv_fmt['file_extension'], 'csv')
        self.assertEqual(csv_fmt['applies_to'], 'both')
    
    def test_list_export_formats_filaments(self):
        """Test listing filament export formats."""
        formats = list_export_formats('filaments')
        
        self.assertIn('autoforge', formats)
        self.assertIn('csv', formats)
        self.assertIn('json', formats)
        
        # Check descriptions are strings
        for name, desc in formats.items():
            self.assertIsInstance(desc, str)
            self.assertTrue(len(desc) > 0)
    
    def test_list_export_formats_colors(self):
        """Test listing color export formats."""
        formats = list_export_formats('colors')
        
        # AutoForge is filament-only
        self.assertNotIn('autoforge', formats)
        self.assertIn('csv', formats)
        self.assertIn('json', formats)
    
    def test_list_export_formats_both(self):
        """Test listing all export formats."""
        formats = list_export_formats('both')
        
        self.assertIn('autoforge', formats)
        self.assertIn('csv', formats)
        self.assertIn('json', formats)


class TestFilenameGeneration(unittest.TestCase):
    """Test auto-generated filename creation."""
    
    def test_generate_filename_structure(self):
        """Test filename follows expected pattern."""
        filename = generate_filename('filaments', 'autoforge')
        
        # Should match: filaments_autoforge_YYYYMMDD_HHMMSS.csv
        parts = filename.split('_')
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0], 'filaments')
        self.assertEqual(parts[1], 'autoforge')
        
        # Date part should be 8 digits
        self.assertEqual(len(parts[2]), 8)
        self.assertTrue(parts[2].isdigit())
        
        # Time part should end with .csv
        time_part = parts[3]
        self.assertTrue(time_part.endswith('.csv'))
        self.assertEqual(len(time_part), 10)  # HHMMSS.csv
    
    def test_generate_filename_extensions(self):
        """Test correct file extensions for each format."""
        csv_name = generate_filename('filaments', 'csv')
        self.assertTrue(csv_name.endswith('.csv'))
        
        json_name = generate_filename('colors', 'json')
        self.assertTrue(json_name.endswith('.json'))
        
        autoforge_name = generate_filename('filaments', 'autoforge')
        self.assertTrue(autoforge_name.endswith('.csv'))
    
    def test_generate_filename_uniqueness(self):
        """Test that successive calls generate different filenames."""
        import time
        
        name1 = generate_filename('filaments', 'csv')
        time.sleep(1.1)  # Ensure second changes
        name2 = generate_filename('filaments', 'csv')
        
        # Should be different due to timestamp
        self.assertNotEqual(name1, name2)


class TestFilamentExport(unittest.TestCase):
    """Test filament export functionality."""
    
    def setUp(self):
        """Create test filaments."""
        self.filaments = [
            FilamentRecord(
                id='test-pla-black',
                maker='Test Co',
                type='PLA',
                finish='Basic',
                color='Black',
                hex='#000000',
                td_value=0.1,
                source='test'
            ),
            FilamentRecord(
                id='test-pla-white',
                maker='Test Co',
                type='PLA',
                finish='Matte',
                color='White',
                hex='#FFFFFF',
                td_value=None,
                source='test'
            ),
        ]
    
    def test_export_filaments_autoforge_content(self):
        """Test AutoForge CSV export content."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            output_path = f.name
        
        try:
            result_path = export_filaments_autoforge(self.filaments, output_path)
            self.assertEqual(result_path, output_path)
            
            # Read and verify content
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Should have 2 rows
            self.assertEqual(len(rows), 2)
            
            # Check first row
            row1 = rows[0]
            self.assertEqual(row1['Brand'], 'Test Co PLA Basic')
            self.assertEqual(row1['Name'], 'Black')
            self.assertEqual(row1['TD'], '0.1')
            self.assertEqual(row1['Color'], '#000000')
            self.assertEqual(row1['Owned'], 'TRUE')
            
            # Check second row (no TD value)
            row2 = rows[1]
            self.assertEqual(row2['Brand'], 'Test Co PLA Matte')
            self.assertEqual(row2['Name'], 'White')
            self.assertEqual(row2['TD'], '')  # None becomes empty string
            self.assertEqual(row2['Color'], '#FFFFFF')
            self.assertEqual(row2['Owned'], 'TRUE')
        
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    def test_export_filaments_csv_content(self):
        """Test generic CSV export content."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            output_path = f.name
        
        try:
            result_path = export_filaments_csv(self.filaments, output_path)
            
            # Read and verify content
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Should have all fields
            self.assertEqual(len(rows), 2)
            row = rows[0]
            self.assertIn('id', row)
            self.assertIn('maker', row)
            self.assertIn('type', row)
            self.assertIn('finish', row)
            self.assertIn('color', row)
            self.assertIn('hex', row)
            self.assertIn('td_value', row)
            self.assertIn('source', row)
        
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    def test_export_filaments_json_content(self):
        """Test JSON export content."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_path = f.name
        
        try:
            result_path = export_filaments_json(self.filaments, output_path)
            
            # Read and verify content
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Should be a list of dicts
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 2)
            
            # Check first item
            item = data[0]
            self.assertEqual(item['id'], 'test-pla-black')
            self.assertEqual(item['maker'], 'Test Co')
            self.assertEqual(item['type'], 'PLA')
            self.assertEqual(item['finish'], 'Basic')
            self.assertEqual(item['color'], 'Black')
            self.assertEqual(item['hex'], '#000000')
            self.assertEqual(item['td_value'], 0.1)
        
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    def test_export_filaments_auto_filename(self):
        """Test auto-generated filename for filaments."""
        import tempfile
        import os
        
        # Export with auto-generated filename (in current directory)
        try:
            output_path = export_filaments(self.filaments, 'autoforge')
            
            # Should exist
            self.assertTrue(Path(output_path).exists())
            
            # Should match pattern
            self.assertTrue(output_path.startswith('filaments_autoforge_'))
            self.assertTrue(output_path.endswith('.csv'))
        
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    def test_export_filaments_invalid_format(self):
        """Test error handling for invalid format."""
        with self.assertRaises(ValueError) as ctx:
            export_filaments(self.filaments, 'invalid_format')
        
        self.assertIn('Unknown export format', str(ctx.exception))


class TestColorExport(unittest.TestCase):
    """Test color export functionality."""
    
    def setUp(self):
        """Create test colors."""
        self.colors = [
            ColorRecord(
                name='test-red',
                hex='#FF0000',
                rgb=(255, 0, 0),
                hsl=(0.0, 100.0, 50.0),
                lab=(53.2, 80.1, 67.2),
                lch=(53.2, 104.6, 40.0),
                source='test'
            ),
            ColorRecord(
                name='test-blue',
                hex='#0000FF',
                rgb=(0, 0, 255),
                hsl=(240.0, 100.0, 50.0),
                lab=(32.3, 79.2, -107.9),
                lch=(32.3, 133.8, 306.3),
                source='test'
            ),
        ]
    
    def test_export_colors_csv_content(self):
        """Test CSV export content for colors."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            output_path = f.name
        
        try:
            result_path = export_colors_csv(self.colors, output_path)
            
            # Read and verify content
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            self.assertEqual(len(rows), 2)
            
            # Check first row
            row = rows[0]
            self.assertEqual(row['name'], 'test-red')
            self.assertEqual(row['hex'], '#FF0000')
            self.assertEqual(row['rgb'], '255,0,0')
            self.assertIn('0.0', row['hsl'])  # Hue
            self.assertIn('53.2', row['lab'])  # L*
        
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    def test_export_colors_json_content(self):
        """Test JSON export content for colors."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_path = f.name
        
        try:
            result_path = export_colors_json(self.colors, output_path)
            
            # Read and verify content
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 2)
            
            # Check first item
            item = data[0]
            self.assertEqual(item['name'], 'test-red')
            self.assertEqual(item['hex'], '#FF0000')
            self.assertEqual(item['rgb'], [255, 0, 0])
            self.assertEqual(item['hsl'][0], 0.0)
        
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    def test_export_colors_auto_filename(self):
        """Test auto-generated filename for colors."""
        try:
            output_path = export_colors(self.colors, 'json')
            
            # Should exist
            self.assertTrue(Path(output_path).exists())
            
            # Should match pattern
            self.assertTrue(output_path.startswith('colors_json_'))
            self.assertTrue(output_path.endswith('.json'))
        
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    def test_export_colors_invalid_format(self):
        """Test error handling for invalid format."""
        with self.assertRaises(ValueError) as ctx:
            export_colors(self.colors, 'autoforge')  # AutoForge is filament-only
        
        self.assertIn('does not support colors', str(ctx.exception))


class TestExportIntegration(unittest.TestCase):
    """Integration tests using real data."""
    
    def test_export_real_bambu_filaments(self):
        """Test exporting real Bambu Lab filaments."""
        # Load real data
        palette = FilamentPalette.load_default()
        
        # Filter Bambu Lab Basic
        bambu_basic = [
            f for f in palette.records
            if f.maker == 'Bambu Lab' and f.finish == 'Basic'
        ]
        
        self.assertGreater(len(bambu_basic), 0, "Should have Bambu Lab Basic filaments")
        
        # Export to AutoForge format
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            output_path = f.name
        
        try:
            result_path = export_filaments_autoforge(bambu_basic, output_path)
            
            # Verify file exists and has content
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            self.assertEqual(len(rows), len(bambu_basic))
            
            # Verify all rows have required AutoForge fields
            for row in rows:
                self.assertIn('Brand', row)
                self.assertIn('Name', row)
                self.assertIn('TD', row)
                self.assertIn('Color', row)
                self.assertIn('Owned', row)
                self.assertEqual(row['Owned'], 'TRUE')
        
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    def test_export_real_css_colors(self):
        """Test exporting real CSS colors."""
        # Load real data
        palette = Palette.load_default()
        
        self.assertGreater(len(palette.records), 0, "Should have CSS colors")
        
        # Export to JSON
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_path = f.name
        
        try:
            result_path = export_colors_json(palette.records, output_path)
            
            # Verify file exists and has content
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.assertEqual(len(data), len(palette.records))
            
            # Verify all items have required fields
            for item in data:
                self.assertIn('name', item)
                self.assertIn('hex', item)
                self.assertIn('rgb', item)
                self.assertIn('hsl', item)
                self.assertIn('lab', item)
                self.assertIn('lch', item)
        
        finally:
            Path(output_path).unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
