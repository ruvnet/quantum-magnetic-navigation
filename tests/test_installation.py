import unittest
import importlib
import subprocess
import sys
import os

class TestInstallation(unittest.TestCase):
    def test_package_importable(self):
        """Test that the qmag_nav package can be imported."""
        try:
            import qmag_nav
            self.assertTrue(True, "qmag_nav package can be imported")
        except ImportError:
            self.fail("qmag_nav package cannot be imported")
    
    def test_package_modules_importable(self):
        """Test that key modules in the package can be imported."""
        modules = [
            "qmag_nav.models",
            "qmag_nav.filter",
            "qmag_nav.mapping",
            "qmag_nav.sensor",
            "qmag_nav.service",
            "qmag_nav.mcp"
        ]
        
        for module in modules:
            try:
                importlib.import_module(module)
                self.assertTrue(True, f"{module} can be imported")
            except ImportError as e:
                self.fail(f"Failed to import {module}: {e}")
    
    def test_cli_executable(self):
        """Test that the CLI module can be executed."""
        try:
            # Just import the module to check it's valid
            import qmag_nav.cli
            self.assertTrue(True, "CLI module can be imported")
        except ImportError as e:
            self.fail(f"Failed to import CLI module: {e}")

if __name__ == "__main__":
    unittest.main()