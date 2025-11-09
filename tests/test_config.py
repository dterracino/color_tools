"""Unit tests for color_tools.config module."""

import unittest
import sys
from pathlib import Path
import threading

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from color_tools.config import (
    set_dual_color_mode,
    get_dual_color_mode,
)


class TestDualColorMode(unittest.TestCase):
    """Test dual color mode configuration."""
    
    def setUp(self):
        """Reset to default before each test."""
        set_dual_color_mode("first")
    
    def test_default_mode(self):
        """Test that default mode is 'first'."""
        mode = get_dual_color_mode()
        self.assertEqual(mode, "first")
    
    def test_set_first_mode(self):
        """Test setting mode to 'first'."""
        set_dual_color_mode("first")
        self.assertEqual(get_dual_color_mode(), "first")
    
    def test_set_last_mode(self):
        """Test setting mode to 'last'."""
        set_dual_color_mode("last")
        self.assertEqual(get_dual_color_mode(), "last")
    
    def test_set_mix_mode(self):
        """Test setting mode to 'mix'."""
        set_dual_color_mode("mix")
        self.assertEqual(get_dual_color_mode(), "mix")
    
    def test_thread_local_isolation(self):
        """Test that configuration is thread-local."""
        # Set mode in main thread
        set_dual_color_mode("first")
        
        # Track results from other thread
        results = {}
        
        def thread_function():
            # This thread should have default value
            results['initial'] = get_dual_color_mode()
            # Set different value in this thread
            set_dual_color_mode("last")
            results['after_set'] = get_dual_color_mode()
        
        # Run in another thread
        thread = threading.Thread(target=thread_function)
        thread.start()
        thread.join()
        
        # Thread should start with default
        self.assertEqual(results['initial'], "first")
        # Thread should have its own value
        self.assertEqual(results['after_set'], "last")
        # Main thread should still have original value
        self.assertEqual(get_dual_color_mode(), "first")
    
    def test_mode_persistence_within_thread(self):
        """Test that mode persists across calls within same thread."""
        set_dual_color_mode("mix")
        # Multiple calls should return same value
        self.assertEqual(get_dual_color_mode(), "mix")
        self.assertEqual(get_dual_color_mode(), "mix")
        self.assertEqual(get_dual_color_mode(), "mix")


class TestConfigEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        """Reset to default before each test."""
        set_dual_color_mode("first")
    
    def test_invalid_mode_raises_error(self):
        """Test that invalid mode raises ValueError."""
        with self.assertRaises(ValueError):
            set_dual_color_mode("invalid")
    
    def test_case_sensitive(self):
        """Test that mode values are case-sensitive."""
        # Valid modes are lowercase
        with self.assertRaises(ValueError):
            set_dual_color_mode("FIRST")
        with self.assertRaises(ValueError):
            set_dual_color_mode("Last")
        with self.assertRaises(ValueError):
            set_dual_color_mode("MIX")


if __name__ == '__main__':
    unittest.main()
