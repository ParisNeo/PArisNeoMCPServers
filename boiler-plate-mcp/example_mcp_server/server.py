# PArisNeoMCPServers/Example-mcp-server/Example_mcp_server/server.py
import os
import sys
from pathlib import Path

# --- Dependency Check FIRST ---
# This block runs before anything else to provide clear, actionable error messages.
try:
    from mcp.server.fastmcp import FastMCP
    from dotenv import load_dotenv
    from ascii_colors import ASCIIColors
except ImportError as e:
    missing_module = e.name
    # Use stderr for error messages to avoid interfering with MCP's stdout
    print("="*80, file=sys.stderr)
    print(f"FATAL: A required dependency '{missing_module}' is not installed.", file=sys.stderr)
    print("The Example MCP Server cannot start.", file=sys.stderr)
    print("\nPlease install the server's requirements.", file=sys.stderr)
    print("To fix this, navigate to the server's directory in your terminal and run:", file=sys.stderr)
    print("\n    cd path/to/PArisNeoMCPServers/Example-mcp-server", file=sys.stderr)
    print("    uv pip install -e .", file=sys.stderr)
    print("\n(If not using uv, you can use 'pip install -e .')", file=sys.stderr)
    print("="*80, file=sys.stderr)
    sys.exit(1) # Exit immediately with a non-zero code to indicate failure

# --- Now that dependencies are confirmed, proceed with normal imports ---
from typing import Dict, Any, Optional
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
        default="streamable-http",
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
        name="ExampleMCPServer",
        description="Provides tools to search Example, download papers, and manage local databases of articles.",
        version="0.1.0",
        host=args.host,
        port=args.port,
        log_level=args.log_level
    )
    ASCIIColors.cyan(f"{mcp.settings}")
else:
    mcp = FastMCP(
        name="ExampleMCPServer",
        description="Provides tools to search Example, download papers, and manage local databases of articles.",
        version="0.1.0"
    )


# --- MCP Tool Definitions ---

@mcp.tool(
    name="hello",
    description="An example mcp tool that returns hello"
)
async def hello() -> Dict[str, Any]:
    """
    Example of mcp tool that returns hello
    """
    ASCIIColors.info("MCP Tool 'list_Example_databases' called.")
    return {"status":"success","answer":"Hello"}


# --- Main CLI Entry Point ---
def main_cli():
    ASCIIColors.cyan("Starting Example MCP Server...")
    ASCIIColors.cyan(f"Listening for MCP messages on {args.transport}...")
    ASCIIColors.magenta(f"Running the server with the following arguments:\n{args}")

    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main_cli()