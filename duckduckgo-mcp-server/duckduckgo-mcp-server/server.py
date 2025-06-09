# PArisNeoMCPServers/duckduckgo-mcp-server/duckduckgo_mcp_server/server.py
import os
from pathlib import Path
from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from ascii_colors import ASCIIColors

# Load environment variables
env_path_parent = Path(__file__).resolve().parent.parent / '.env'
env_path_project_root = Path('.') / '.env' # If running from project root

if env_path_parent.exists():
    ASCIIColors.cyan(f"Loading environment variables from: {env_path_parent.resolve()}")
    load_dotenv(dotenv_path=env_path_parent)
elif env_path_project_root.exists():
    ASCIIColors.cyan(f"Loading environment variables from: {env_path_project_root.resolve()}")
    load_dotenv(dotenv_path=env_path_project_root)
else:
    ASCIIColors.yellow(".env file not found in parent or current directory. Relying on existing environment variables.")

try:
    from . import duckduckgo_wrapper
except ImportError:
    # Fallback for cases where the script might be run directly for testing,
    # and the current directory is `duckduckgo_mcp_server`
    import duckduckgo_wrapper

# Initialize FastMCP Server
mcp = FastMCP(
    name="DuckDuckGoMCPServer",
    description="Provides web search capabilities via DuckDuckGo.",
    version="0.1.0"
)

# Define the MCP Tool for DuckDuckGo Search
@mcp.tool(
    name="duckduckgo_search",
    description="Performs a web search using DuckDuckGo and returns a list of results."
)
async def perform_duckduckgo_search(
    query: str,
    num_results: Optional[int] = None,
    region: Optional[str] = None,
    timelimit: Optional[str] = None
) -> Dict[str, Any]:
    """
    MCP tool endpoint for performing a DuckDuckGo search.
    """
    if not query:
        return {"error": "Query parameter is required and cannot be empty."}
    
    ASCIIColors.info(f"MCP Tool 'duckduckgo_search' called with query: '{query}'")

    # Use defaults from environment or wrapper if parameters are None
    # The wrapper itself handles defaults, so we can pass None if user doesn't specify.
    
    search_results = await duckduckgo_wrapper.perform_search(
        query=query,
        max_results=num_results, # Will use wrapper's default if None
        region=region,           # Will use wrapper's default if None
        timelimit=timelimit      # Will be None if not provided, wrapper handles it
    )
    
    if "error" in search_results:
        ASCIIColors.error(f"Error from duckduckgo_wrapper: {search_results['error']}")
        return {"status": "error", "message": search_results["error"], "results": []}
    
    ASCIIColors.green(f"Search successful. Returning {len(search_results.get('results', []))} results.")
    return {
        "status": "success",
        "query_used": search_results.get("query_used"),
        "region_used": search_results.get("region_used"),
        "results": search_results.get("results", [])
    }

# --- Main CLI Entry Point ---
def main_cli():
    ASCIIColors.cyan("Starting DuckDuckGo MCP Server...")
    ASCIIColors.cyan("MCP server will list 'duckduckgo_search' tool upon connection.")
    ASCIIColors.cyan("Listening for MCP messages on stdio...")
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main_cli()