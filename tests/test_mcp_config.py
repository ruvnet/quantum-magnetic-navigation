import unittest
import json
import os
import subprocess
import sys
from pathlib import Path

class TestMCPConfig(unittest.TestCase):
    def test_mcp_json_exists(self):
        """Test that the mcp.json file exists."""
        mcp_json_path = Path(".roo/mcp.json")
        self.assertTrue(mcp_json_path.exists(), "mcp.json file should exist")
    
    def test_mcp_json_format(self):
        """Test that the mcp.json file has the correct format with server configuration."""
        with open(".roo/mcp.json", "r") as f:
            mcp_config = json.load(f)
        
        self.assertIn("mcpServers", mcp_config, "mcp.json should have mcpServers key")
        self.assertIsInstance(mcp_config["mcpServers"], dict, "mcpServers should be a dictionary")
        
        # Check if there's at least one server configured
        self.assertGreater(len(mcp_config["mcpServers"]), 0, "At least one MCP server should be configured")
        
        # Check the first server configuration
        server_name = next(iter(mcp_config["mcpServers"]))
        server_config = mcp_config["mcpServers"][server_name]
        
        self.assertIn("command", server_config, "Server config should have a command")
        self.assertIn("--map", server_config["command"], "Command should specify a map file")
    
    def test_mcp_server_script_exists(self):
        """Test that the MCP server script exists."""
        script_path = Path("scripts/run_mcp_server_fixed.py")
        self.assertTrue(script_path.exists(), "MCP server script should exist")
    
    def test_mcp_server_can_start(self):
        """Test that the MCP server can be started with the correct arguments."""
        # This is a dry run test - it just checks if the command is valid
        # without actually starting the server
        test_map_path = "tests/data/5x5_grid.tif"
        
        # Verify the test map exists
        self.assertTrue(Path(test_map_path).exists(), f"Test map {test_map_path} should exist")
        
        # Check if the command is valid (dry run)
        cmd = [sys.executable, "-m", "scripts.run_mcp_server_fixed", "--map", test_map_path, "--help"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check if the command executed without errors
        self.assertEqual(result.returncode, 0, 
                        f"MCP server command failed: {result.stderr}")

if __name__ == "__main__":
    unittest.main()