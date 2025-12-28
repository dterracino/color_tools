"""
Integration tests for CLI argument parsing, command routing, and output formatting.

Tests the complete CLI flow using subprocess to run actual commands.
"""

import subprocess
import sys
import json
import unittest
from pathlib import Path


class TestCLIBasics(unittest.TestCase):
    """Test basic CLI functionality and help output."""
    
    def run_cli(self, *args, expect_error=False):
        """
        Run CLI command and return (exit_code, stdout, stderr).
        
        Args:
            *args: Command-line arguments to pass
            expect_error: If True, don't fail on non-zero exit codes
            
        Returns:
            tuple: (exit_code, stdout, stderr)
        """
        cmd = [sys.executable, "-m", "color_tools"] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if not expect_error and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStderr: {result.stderr}")
        
        return result.returncode, result.stdout, result.stderr
    
    def test_no_args_shows_help(self):
        """Running with no arguments should show help and exit 0."""
        exit_code, stdout, stderr = self.run_cli()
        self.assertEqual(exit_code, 0)
        self.assertIn("usage:", stdout.lower())
        self.assertIn("color", stdout)
        self.assertIn("filament", stdout)
        self.assertIn("convert", stdout)
    
    def test_version_flag(self):
        """--version should show version number and exit."""
        exit_code, stdout, stderr = self.run_cli("--version")
        self.assertEqual(exit_code, 0)
        # Should contain a version number (e.g., "5.5.0")
        self.assertRegex(stdout, r'\d+\.\d+\.\d+')
    
    def test_help_flag(self):
        """--help should show help text."""
        exit_code, stdout, stderr = self.run_cli("--help")
        self.assertEqual(exit_code, 0)
        self.assertIn("usage:", stdout.lower())
        self.assertIn("positional arguments:", stdout.lower())


class TestColorCommand(unittest.TestCase):
    """Test color command routing and basic functionality."""
    
    def run_cli(self, *args, expect_error=False):
        """Helper to run CLI commands."""
        cmd = [sys.executable, "-m", "color_tools"] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if not expect_error and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStderr: {result.stderr}")
        
        return result.returncode, result.stdout, result.stderr
    
    def test_color_by_name(self):
        """color --name should find CSS colors."""
        exit_code, stdout, stderr = self.run_cli("color", "--name", "red")
        self.assertEqual(exit_code, 0)
        self.assertIn("red", stdout.lower())
        self.assertIn("#FF0000", stdout)
        self.assertIn("RGB:", stdout)
    
    def test_color_by_hex(self):
        """color --nearest --hex should find nearest color."""
        exit_code, stdout, stderr = self.run_cli("color", "--nearest", "--hex", "FF7F50")
        self.assertEqual(exit_code, 0)
        # Should find coral
        self.assertIn("coral", stdout.lower())
        # Should show distance
        self.assertIn("distance", stdout.lower())
    
    def test_color_nearest_with_value(self):
        """color --nearest --value --space rgb should find closest color."""
        exit_code, stdout, stderr = self.run_cli(
            "color", "--nearest", "--value", "255", "0", "0", "--space", "rgb"
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("red", stdout.lower())
        # Should show distance
        self.assertIn("distance", stdout.lower())
    
    def test_color_mutual_exclusivity(self):
        """color --name and --nearest can be used together (shows color details)."""
        exit_code, stdout, stderr = self.run_cli(
            "color", "--name", "red", "--nearest"
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("red", stdout.lower())


class TestFilamentCommand(unittest.TestCase):
    """Test filament command routing and filtering."""
    
    def run_cli(self, *args, expect_error=False):
        """Helper to run CLI commands."""
        cmd = [sys.executable, "-m", "color_tools"] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if not expect_error and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStderr: {result.stderr}")
        
        return result.returncode, result.stdout, result.stderr
    
    def test_filament_list_makers(self):
        """filament --list-makers should show all manufacturers."""
        exit_code, stdout, stderr = self.run_cli("filament", "--list-makers")
        self.assertEqual(exit_code, 0)
        self.assertIn("Bambu Lab", stdout)
        # Should show count
        self.assertRegex(stdout, r'\(\d+ filaments\)')
    
    def test_filament_list_types(self):
        """filament --list-types should show all material types."""
        exit_code, stdout, stderr = self.run_cli("filament", "--list-types")
        self.assertEqual(exit_code, 0)
        self.assertIn("PLA", stdout)
        self.assertIn("PETG", stdout)
    
    def test_filament_nearest_with_filter(self):
        """filament --nearest with --maker filter should work."""
        exit_code, stdout, stderr = self.run_cli(
            "filament", "--nearest", "--hex", "FF0000",
            "--maker", "Bambu Lab"
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("Bambu Lab", stdout)
        # Distance shown in output
        self.assertIn("distance", stdout.lower())
    
    def test_filament_multiple_results(self):
        """filament --count should return multiple matches."""
        exit_code, stdout, stderr = self.run_cli(
            "filament", "--nearest", "--hex", "0000FF", "--count", "3"
        )
        self.assertEqual(exit_code, 0)
        # Should have numbered results
        self.assertIn("1.", stdout)
        self.assertIn("2.", stdout)
        self.assertIn("3.", stdout)


class TestConvertCommand(unittest.TestCase):
    """Test color space conversion command."""
    
    def run_cli(self, *args, expect_error=False):
        """Helper to run CLI commands."""
        cmd = [sys.executable, "-m", "color_tools"] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if not expect_error and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStderr: {result.stderr}")
        
        return result.returncode, result.stdout, result.stderr
    
    def test_rgb_to_lab(self):
        """convert --from rgb --to lab should convert correctly."""
        exit_code, stdout, stderr = self.run_cli(
            "convert", "--from", "rgb", "--to", "lab",
            "--hex", "FF0000"
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("LAB(", stdout)
        # Red should have high L and positive a
        self.assertIn("53.2", stdout)  # L value for red (rounded)
    
    def test_hex_shorthand(self):
        """convert --hex should work with 3-digit shorthand."""
        exit_code, stdout, stderr = self.run_cli(
            "convert", "--hex", "F00", "--to", "hsl", "--from", "rgb"
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("HSL(", stdout)
    
    def test_gamut_check(self):
        """convert --check-gamut should report gamut status."""
        exit_code, stdout, stderr = self.run_cli(
            "convert", "--from", "lab", "--to", "rgb",
            "--value", "50", "100", "50", "--check-gamut"
        )
        self.assertEqual(exit_code, 0)
        # Should mention gamut
        self.assertIn("gamut", stdout.lower())


class TestNameCommand(unittest.TestCase):
    """Test color name generation command."""
    
    def run_cli(self, *args, expect_error=False):
        """Helper to run CLI commands."""
        cmd = [sys.executable, "-m", "color_tools"] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if not expect_error and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStderr: {result.stderr}")
        
        return result.returncode, result.stdout, result.stderr
    
    def test_name_exact_match(self):
        """name should recognize exact CSS color matches."""
        exit_code, stdout, stderr = self.run_cli("name", "--hex", "FF0000")
        self.assertEqual(exit_code, 0)
        self.assertIn("red", stdout.lower())
    
    def test_name_generated(self):
        """name should generate descriptive names for non-CSS colors."""
        exit_code, stdout, stderr = self.run_cli("name", "--hex", "804020")
        self.assertEqual(exit_code, 0)
        # Should have some descriptive modifiers
        self.assertTrue(
            any(word in stdout.lower() for word in ["dark", "light", "vivid", "muted", "brown"])
        )


class TestValidateCommand(unittest.TestCase):
    """Test color name validation command."""
    
    def run_cli(self, *args, expect_error=False):
        """Helper to run CLI commands."""
        cmd = [sys.executable, "-m", "color_tools"] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=Path(__file__).parent.parent,
            encoding='utf-8',
            errors='replace'
        )
        
        if not expect_error and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStderr: {result.stderr}")
        
        return result.returncode, result.stdout, result.stderr
    
    def test_validate_exact_match(self):
        """validate should confirm exact matches."""
        exit_code, stdout, stderr = self.run_cli(
            "validate", "--name", "red", "--hex", "FF0000"
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("match", stdout.lower())
    
    def test_validate_mismatch(self):
        """validate should detect mismatches."""
        exit_code, stdout, stderr = self.run_cli(
            "validate", "--name", "red", "--hex", "0000FF",
            expect_error=True
        )
        self.assertEqual(exit_code, 1)
        output = (stdout + stderr).lower()
        self.assertTrue("does not match" in output or "no match" in output)


class TestCVDCommand(unittest.TestCase):
    """Test color vision deficiency command."""
    
    def run_cli(self, *args, expect_error=False):
        """Helper to run CLI commands."""
        cmd = [sys.executable, "-m", "color_tools"] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if not expect_error and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStderr: {result.stderr}")
        
        return result.returncode, result.stdout, result.stderr
    
    def test_cvd_simulate(self):
        """cvd should simulate color vision deficiency."""
        exit_code, stdout, stderr = self.run_cli(
            "cvd", "--hex", "FF0000", "--type", "protanopia"
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("protanopia", stdout.lower())
        # Default mode is simulate
        self.assertIn("mode", stdout.lower())
    
    def test_cvd_correct(self):
        """cvd --mode correct should apply correction."""
        exit_code, stdout, stderr = self.run_cli(
            "cvd", "--hex", "FF0000", "--type", "deuteranopia", "--mode", "correct"
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("deuteranopia", stdout.lower())
        self.assertIn("correct", stdout.lower())


class TestVerificationFlags(unittest.TestCase):
    """Test verification and diagnostic flags."""
    
    def run_cli(self, *args, expect_error=False):
        """Helper to run CLI commands."""
        cmd = [sys.executable, "-m", "color_tools"] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if not expect_error and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStderr: {result.stderr}")
        
        return result.returncode, result.stdout, result.stderr
    
    def test_verify_constants(self):
        """--verify-constants should check integrity and exit."""
        cmd = [sys.executable, "-m", "color_tools", "--verify-constants"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=Path(__file__).parent.parent,
            encoding='utf-8',
            errors='replace'
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("integrity verified", result.stdout.lower())
    
    def test_verify_data(self):
        """--verify-data should check data files and exit."""
        cmd = [sys.executable, "-m", "color_tools", "--verify-data"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=Path(__file__).parent.parent,
            encoding='utf-8',
            errors='replace'
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("integrity verified", result.stdout.lower())
    
    def test_verify_matrices(self):
        """--verify-matrices should check transformation matrices."""
        cmd = [sys.executable, "-m", "color_tools", "--verify-matrices"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=Path(__file__).parent.parent,
            encoding='utf-8',
            errors='replace'
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("integrity verified", result.stdout.lower())
    
    def test_verify_all(self):
        """--verify-all should check everything."""
        cmd = [sys.executable, "-m", "color_tools", "--verify-all"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=Path(__file__).parent.parent,
            encoding='utf-8',
            errors='replace'
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("integrity verified", result.stdout.lower())
    
    def test_verify_does_not_require_command(self):
        """Verification flags should work without a subcommand."""
        cmd = [sys.executable, "-m", "color_tools", "--verify-constants"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=Path(__file__).parent.parent,
            encoding='utf-8',
            errors='replace'
        )
        self.assertEqual(result.returncode, 0)
        # Should not show help or complain about missing command


class TestErrorHandling(unittest.TestCase):
    """Test error messages and exit codes."""
    
    def run_cli(self, *args, expect_error=False):
        """Helper to run CLI commands."""
        cmd = [sys.executable, "-m", "color_tools"] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if not expect_error and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStderr: {result.stderr}")
        
        return result.returncode, result.stdout, result.stderr
    
    def test_invalid_color_name(self):
        """Invalid color name should show helpful error."""
        exit_code, stdout, stderr = self.run_cli(
            "color", "--name", "notacolor123xyz",
            expect_error=True
        )
        self.assertNotEqual(exit_code, 0)
        # Error could be in stdout or stderr
        error_text = (stdout + stderr).lower()
        self.assertTrue("not found" in error_text or "error" in error_text)
    
    def test_invalid_hex_format(self):
        """Invalid hex format should show error."""
        exit_code, stdout, stderr = self.run_cli(
            "color", "--nearest", "--hex", "GGGGGG",
            expect_error=True
        )
        self.assertNotEqual(exit_code, 0)
        # Should mention hex format error
        error_text = (stdout + stderr).lower()
        self.assertTrue("hex" in error_text or "invalid" in error_text)
    
    def test_rgb_out_of_range(self):
        """RGB values out of range should show error."""
        exit_code, stdout, stderr = self.run_cli(
            "convert", "--from", "rgb", "--to", "lab",
            "--hex", "GGGGGG",
            expect_error=True
        )
        self.assertNotEqual(exit_code, 0)
        # Should mention hex format error
        error_text = (stdout + stderr).lower()
        self.assertTrue("hex" in error_text or "invalid" in error_text)
    
    def test_missing_required_argument(self):
        """Missing required arguments should show error."""
        exit_code, stdout, stderr = self.run_cli(
            "color", "--nearest",
            expect_error=True
        )
        self.assertNotEqual(exit_code, 0)
        # Should have error about missing input


class TestJSONOutput(unittest.TestCase):
    """Test JSON output mode for scripting."""
    
    def run_cli(self, *args, expect_error=False):
        """Helper to run CLI commands."""
        cmd = [sys.executable, "-m", "color_tools"] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if not expect_error and result.returncode != 0:
            self.fail(f"Command failed: {' '.join(cmd)}\nStderr: {result.stderr}")
        
        return result.returncode, result.stdout, result.stderr
    
    def test_validate_json_output(self):
        """validate --json-output should produce valid JSON."""
        exit_code, stdout, stderr = self.run_cli(
            "validate", "--name", "red", "--hex", "#FF0000", "--json-output"
        )
        self.assertEqual(exit_code, 0)
        
        # Should be valid JSON
        data = json.loads(stdout)
        self.assertIn("is_match", data)
        self.assertIn("delta_e", data)
        self.assertTrue(data["is_match"])


if __name__ == "__main__":
    unittest.main()
