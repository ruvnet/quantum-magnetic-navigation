import unittest
import importlib
import subprocess
import sys
import os

class TestBuildBackend(unittest.TestCase):
    def test_hatchling_build_module(self):
        """Test that the hatchling.build module exists and can be imported."""
        try:
            import hatchling.build
            self.assertTrue(True, "hatchling.build module can be imported")
        except ImportError as e:
            self.fail(f"Failed to import hatchling.build module: {e}")
    
    def test_build_backend_not_build_backend(self):
        """Test that the incorrect module path doesn't exist."""
        try:
            import hatchling.build_backend
            self.fail("hatchling.build_backend should not exist")
        except ImportError:
            self.assertTrue(True, "Correctly failed to import non-existent module")
    
    def test_pyproject_toml_content(self):
        """Test that pyproject.toml has the correct build backend."""
        with open("pyproject.toml", "r") as f:
            content = f.read()
        
        self.assertIn('build-backend = "hatchling.build"', content, 
                     "pyproject.toml should specify 'hatchling.build' as the build backend")
        self.assertNotIn('build-backend = "hatchling.build_backend"', content,
                        "pyproject.toml should not specify 'hatchling.build_backend'")
    
    def test_editable_install(self):
        """Test that the package can be installed in editable mode."""
        # Check if hatchling supports editable installs
        try:
            import hatchling
            import hatchling.build
            # We don't need to directly access the hook, just verify the module exists
            self.assertTrue(hasattr(hatchling.build, "__file__"),
                           "hatchling.build module exists")
            
            # Check if pip can install the package in editable mode
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", ".", "--dry-run"],
                capture_output=True,
                text=True,
                check=False
            )
            self.assertEqual(result.returncode, 0,
                            f"Dry run of editable install failed: {result.stderr}")
        except Exception as e:
            self.fail(f"Failed to verify editable install capability: {e}")

if __name__ == "__main__":
    unittest.main()