# PArisNeoMCPServers/arxiv-mcp-server/arxiv_mcp_server/server.py
import os
import sys
from pathlib import Path

# --- Dependency Check FIRST ---
# This block runs before anything else to provide clear, actionable error messages.
try:
    from mcp.server.fastmcp import FastMCP
    from dotenv import load_dotenv
    from ascii_colors import ASCIIColors
    import arxiv  # Check for the actual 'arxiv' library
except ImportError as e:
    missing_module = e.name
    # Use stderr for error messages to avoid interfering with MCP's stdout
    print("="*80, file=sys.stderr)
    print(f"FATAL: A required dependency '{missing_module}' is not installed.", file=sys.stderr)
    print("The Arxiv MCP Server cannot start.", file=sys.stderr)
    print("\nPlease install the server's requirements.", file=sys.stderr)
    print("To fix this, navigate to the server's directory in your terminal and run:", file=sys.stderr)
    print("\n    cd path/to/PArisNeoMCPServers/arxiv-mcp-server", file=sys.stderr)
    print("    uv pip install -e .", file=sys.stderr)
    print("\n(If not using uv, you can use 'pip install -e .')", file=sys.stderr)
    print("="*80, file=sys.stderr)
    sys.exit(1) # Exit immediately with a non-zero code to indicate failure

# --- Now that dependencies are confirmed, proceed with normal imports ---
from typing import Dict, Any, Optional
import arxiv_wrapper
import argparse  

def parse_args():
    # Initialize parser
    parser = argparse.ArgumentParser(description="Server configuration")

    # Add arguments
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Hostname or IP address (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9624,
        help="Port number (1-65535)"
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    # New transport argument
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport protocol: stdio, sse, or streamable-http"
    )

    # Parse arguments
    args = parser.parse_args()

    # Validate port range
    if not (1 <= args.port <= 65535):
        parser.error("Port must be between 1 and 65535")

    return args

# --- Environment and Path Setup ---
SERVER_ROOT_PATH = Path(__file__).resolve().parent.parent
env_path = SERVER_ROOT_PATH / '.env'

if env_path.exists():
    ASCIIColors.cyan(f"Loading environment variables from: {env_path.resolve()}")
    load_dotenv(dotenv_path=env_path)
else:
    ASCIIColors.yellow(f".env file not found at {env_path}. Relying on existing environment variables or wrapper defaults.")

# --- MCP Server Initialization ---
args = parse_args()
if args.transport=="streamable-http":
    mcp = FastMCP(
        name="ArxivMCPServer",
        description="Provides tools to search Arxiv, download papers, and manage local databases of articles.",
        version="0.1.0",
        host=args.host,
        port=args.port,
        log_level=args.log_level
    )
    ASCIIColors.cyan(f"{mcp.settings}")
else:
    mcp = FastMCP(
        name="ArxivMCPServer",
        description="Provides tools to search Arxiv, download papers, and manage local databases of articles.",
        version="0.1.0"
    )

ASCIIColors.cyan(f"Arxiv databases will be stored in: {arxiv_wrapper.ARXIV_DATABASES_ROOT.resolve()}")

# --- MCP Tool Definitions ---

@mcp.tool(
    name="list_arxiv_databases",
    description="Lists all available local Arxiv paper databases."
)
async def list_arxiv_databases() -> Dict[str, Any]:
    """
    MCP tool to get a list of all created Arxiv databases.
    """
    ASCIIColors.info("MCP Tool 'list_arxiv_databases' called.")
    return await arxiv_wrapper.list_databases()

@mcp.tool(
    name="create_arxiv_database",
    description="Creates a new, empty local database to store Arxiv papers."
)
async def create_arxiv_database(database_name: str) -> Dict[str, Any]:
    """
    MCP tool to create a new folder for an Arxiv database.
    """
    ASCIIColors.info(f"MCP Tool 'create_arxiv_database' called for name: '{database_name}'.")
    if not database_name:
        return {"error": "Database name cannot be empty."}
    return await arxiv_wrapper.create_database(database_name)

@mcp.tool(
    name="search_and_populate_database",
    description="Searches Arxiv for a query, downloads new papers, and adds them to a specified local database."
)
async def search_and_populate_database(
    database_name: str,
    query: str,
    max_results: Optional[int] = 5
) -> Dict[str, Any]:
    """
    MCP tool to search Arxiv and download results into a database.
    """
    ASCIIColors.info(f"MCP Tool 'search_and_populate_database' called for db '{database_name}' with query '{query}'.")
    if not database_name:
        return {"error": "Database name cannot be empty."}
    if not query:
        return {"error": "Search query cannot be empty."}
    
    # Ensure max_results is a reasonable number to prevent abuse
    num_results = min(max_results or 5, 25)

    return await arxiv_wrapper.search_and_download(database_name, query, num_results)

@mcp.tool(
    name="get_database_contents",
    description="Retrieves a list of all papers and their metadata from a specified local database."
)
async def get_database_contents(database_name: str) -> Dict[str, Any]:
    """
    MCP tool to load and list all papers in a given database.
    """
    ASCIIColors.info(f"MCP Tool 'get_database_contents' called for db '{database_name}'.")
    if not database_name:
        return {"error": "Database name cannot be empty."}
    return await arxiv_wrapper.load_database_metadata(database_name)

@mcp.tool(
    name="get_paper_abstract",
    description="Gets the title and abstract (summary) for a specific paper ID from a local database."
)
async def get_paper_abstract(database_name: str, paper_id: str) -> Dict[str, Any]:
    """
    MCP tool to retrieve a specific paper's summary from a local database.
    The LLM should provide the paper ID (e.g., '2103.12345v1').
    """
    ASCIIColors.info(f"MCP Tool 'get_paper_abstract' called for paper '{paper_id}' in db '{database_name}'.")
    if not database_name:
        return {"error": "Database name cannot be empty."}
    if not paper_id:
        return {"error": "Paper ID cannot be empty."}
    return await arxiv_wrapper.get_paper_summary(database_name, paper_id)

# --- Main CLI Entry Point ---
def main_cli():
    ASCIIColors.cyan("Starting Arxiv MCP Server...")
    ASCIIColors.cyan("MCP server will list Arxiv tools upon connection.")
    ASCIIColors.cyan(f"Listening for MCP messages on {args.transport}...")
    ASCIIColors.magenta(f"Running the server with the following arguments:\n{args}")

    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main_cli()