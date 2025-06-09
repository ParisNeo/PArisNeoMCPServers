# PArisNeoMCPServers/matplotlib-mcp-server/matplotlib_mcp_server/__init__.py
"""
Matplotlib MCP Server Package.
"""

from .server import mcp as matplotlib_mcp_instance
from .matplotlib_wrapper import generate_plot

# You can choose to expose or not expose items here.
# For an MCP server, usually, only the `mcp_instance` might be relevant if someone
# were to import and run the server programmatically in a more complex setup,
# but the primary entry point is through the script defined in pyproject.toml.
__all__ = ["matplotlib_mcp_instance", "generate_plot"]