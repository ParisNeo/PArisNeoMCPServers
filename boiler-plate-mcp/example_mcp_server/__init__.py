# PArisNeoMCPServers/arxiv-mcp-server/arxiv_mcp_server/__init__.py
"""
Arxiv MCP Server Package.

This package provides an MCP server to interact with the Arxiv API.
"""

from .server import mcp as arxiv_mcp_instance
from .arxiv_wrapper import (
    list_databases,
    create_database,
    search_and_download,
    load_database_metadata,
    get_paper_summary,
    ARXIV_DATABASES_ROOT
)

# Expose key components for potential programmatic use.
__all__ = [
    "arxiv_mcp_instance",
    "list_databases",
    "create_database",
    "search_and_download",
    "load_database_metadata",
    "get_paper_summary",
    "ARXIV_DATABASES_ROOT"
]