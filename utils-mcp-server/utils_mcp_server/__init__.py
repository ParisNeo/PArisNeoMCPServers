# PArisNeoMCPServers/utils-mcp-server/utils_mcp_server/__init__.py
"""
Utilities MCP Server Package.

This package provides an MCP server for common utilities like getting
the time, weather, and cryptocurrency prices.
"""

from .server import mcp as utils_mcp_instance
from .utils_wrapper import (
    get_current_time,
    get_weather_forecast,
    get_bitcoin_price
)

# Expose key components for potential programmatic use.
__all__ = [
    "utils_mcp_instance",
    "get_current_time",
    "get_weather_forecast",
    "get_bitcoin_price"
]