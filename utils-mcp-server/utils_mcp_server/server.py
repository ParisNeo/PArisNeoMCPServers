# PArisNeoMCPServers/utils-mcp-server/utils_mcp_server/server.py
import sys
from pathlib import Path

# --- Dependency Check FIRST ---
# This block runs before anything else to provide clear, actionable error messages.
try:
    from mcp.server.fastmcp import FastMCP
    from dotenv import load_dotenv
    from ascii_colors import ASCIIColors
    import httpx  # Check for the actual 'httpx' library
except ImportError as e:
    missing_module = e.name
    # Use stderr for error messages to avoid interfering with MCP's stdout
    print("="*80, file=sys.stderr)
    print(f"FATAL: A required dependency '{missing_module}' is not installed.", file=sys.stderr)
    print("The Utils MCP Server cannot start.", file=sys.stderr)
    print("\nPlease install the server's requirements.", file=sys.stderr)
    print("To fix this, navigate to the server's directory in your terminal and run:", file=sys.stderr)
    print("\n    cd path/to/PArisNeoMCPServers/utils-mcp-server", file=sys.stderr)
    print("    uv pip install -e .", file=sys.stderr)
    print("\n(If not using uv, you can use 'pip install -e .')", file=sys.stderr)
    print("="*80, file=sys.stderr)
    sys.exit(1) # Exit immediately with a non-zero code to indicate failure

# --- Now that dependencies are confirmed, proceed with normal imports ---
from typing import Dict, Any, Optional
import utils_wrapper
import argparse

def parse_args():
    # Initialize parser
    parser = argparse.ArgumentParser(description="Utilities MCP Server configuration")

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
        default=9625,  # Using a different default port than the arxiv server
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

# --- MCP Server Initialization ---
args = parse_args()
if args.transport == "streamable-http":
    mcp = FastMCP(
        name="UtilsMCPServer",
        description="Provides basic utility tools like getting the current time, weather forecasts, and cryptocurrency prices.",
        version="0.1.0",
        host=args.host,
        port=args.port,
        log_level=args.log_level
    )
    ASCIIColors.cyan(f"{mcp.settings}")
else:
    mcp = FastMCP(
        name="UtilsMCPServer",
        description="Provides basic utility tools like getting the current time, weather forecasts, and cryptocurrency prices.",
        version="0.1.0"
    )

# --- MCP Tool Definitions ---

@mcp.tool(
    name="get_current_time",
    description="Gets the current time in UTC. Returns the time in both ISO format and a human-readable string."
)
async def get_current_time() -> Dict[str, Any]:
    """
    MCP tool to get the current time. The timezone is fixed to UTC.
    """
    ASCIIColors.info("MCP Tool 'get_current_time' called.")
    return await utils_wrapper.get_current_time("UTC")

@mcp.tool(
    name="get_weather_forecast",
    description="Gets the current weather for a specified location (e.g., 'Paris, France', 'Tokyo', 'New York')."
)
async def get_weather_forecast(location: str) -> Dict[str, Any]:
    """
    MCP tool to get a weather forecast.
    """
    ASCIIColors.info(f"MCP Tool 'get_weather_forecast' called for location: '{location}'.")
    if not location:
        return {"error": "Location cannot be empty."}
    return await utils_wrapper.get_weather_forecast(location)

@mcp.tool(
    name="get_bitcoin_price",
    description="Gets the current price of Bitcoin (BTC) in a specified fiat currency."
)
async def get_bitcoin_price(currency: Optional[str] = "usd") -> Dict[str, Any]:
    """
    MCP tool to retrieve the current price of Bitcoin.
    """
    ASCIIColors.info(f"MCP Tool 'get_bitcoin_price' called for currency: '{currency}'.")
    normalized_currency = (currency or "usd").lower()
    return await utils_wrapper.get_bitcoin_price(normalized_currency)

# --- Main CLI Entry Point ---
def main_cli():
    ASCIIColors.cyan("Starting Utilities MCP Server...")
    ASCIIColors.cyan("MCP server will list utility tools upon connection.")
    ASCIIColors.cyan(f"Listening for MCP messages on {args.transport}...")
    ASCIIColors.magenta(f"Running the server with the following arguments:\n{args}")

    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main_cli()