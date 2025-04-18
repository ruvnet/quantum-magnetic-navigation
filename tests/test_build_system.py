import unittest
import os
import subprocess
import sys
import importlib.util

class TestBuildSystem(unittest.TestCase):
    def test_hatchling_installed(self):
        """Test that hatchling is installed and can be imported."""
        try:
            import hatchling
            self.assertTrue(True, "hatchling can be imported")
        except ImportError:
            self.fail("hatchling is not installed")
    
    def test_build_backend_module_exists(self):
        """Test that the build backend module specified in pyproject.toml exists."""
        # The correct module path should be "hatchling.build"
        spec = importlib.util.find_spec("hatchling.build")
        self.assertIsNotNone(spec, "hatchling.build module exists")
        
        # The incorrect module path that's causing the error
        spec = importlib.util.find_spec("hatchling.build_backend")
        self.assertIsNone(spec, "hatchling.build_backend module does not exist")
    
    def test_pyproject_toml_content(self):
        """Test that pyproject.toml has the correct build backend."""
        with open("pyproject.toml", "r") as f:
            content = f.read()
        
        self.assertIn('build-backend = "hatchling.build"', content, 
                     "pyproject.toml should specify 'hatchling.build' as the build backend")
        self.assertNotIn('build-backend = "hatchling.build_backend"', content,
                        "pyproject.toml should not specify 'hatchling.build_backend'")

if __name__ == "__main__":
    unittest.main()