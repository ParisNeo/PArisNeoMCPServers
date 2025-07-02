# example_mcp_server/server.py
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any

# --- Graceful Dependency Check within Main Entry Point ---
# We wrap the main logic in a try/except block to catch ImportErrors.
# This provides a clean, user-friendly error message if dependencies are not installed,
# without running complex code at the top-level of the module.

def setup_logging(log_level_str: str):
    """Configures the root logger for the application."""
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout, # MCP requires logs on stdout/stderr
    )
    # Silence overly verbose libraries if necessary
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


def parse_args():
    """Parses command-line arguments, using environment variables as defaults."""
    parser = argparse.ArgumentParser(
        description="Example MCP Server: Integrates with APIs to manage academic papers.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Shows defaults in --help
    )

    # Use os.getenv to set defaults from environment variables
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("MCP_HOST", "localhost"),
        help="Hostname or IP address to bind to. (Env: MCP_HOST)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", 9624)),
        help="Port number to listen on (1-65535). (Env: MCP_PORT)"
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.getenv("MCP_LOG_LEVEL", "INFO"),
        help="Set the logging level. (Env: MCP_LOG_LEVEL)"
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse", "streamable-http"],
        default=os.getenv("MCP_TRANSPORT", "streamable-http"),
        help="Transport protocol to use. (Env: MCP_TRANSPORT)"
    )

    args = parser.parse_args()

    # Validate port range after parsing
    if not (1 <= args.port <= 65535):
        parser.error("Port must be between 1 and 65535")

    return args

def main_cli():
    """The main command-line interface entry point for the server."""
    try:
        # --- Dependency Imports ---
        # Keep these imports inside the function that needs them.
        from mcp.server.fastmcp import FastMCP
        from dotenv import load_dotenv

    except ImportError as e:
        # --- User-Friendly Error for Missing Dependencies ---
        missing_module = e.name
        sys.stderr.write("="*80 + "\n")
        sys.stderr.write(f"FATAL: A required dependency '{missing_module}' is not installed.\n")
        sys.stderr.write("The Example MCP Server cannot start.\n\n")
        sys.stderr.write("Please install the required packages by navigating to the project's\n")
        sys.stderr.write("root directory in your terminal and running:\n\n")
        sys.stderr.write("    pip install -e .\n\n")
        sys.stderr.write("This command installs the project in 'editable' mode with all its dependencies.\n")
        sys.stderr.write("="*80 + "\n")
        sys.exit(1)

    # --- Configuration and Environment Setup ---
    SERVER_ROOT_PATH = Path(__file__).resolve().parent.parent
    env_path = SERVER_ROOT_PATH / '.env'

    # load_dotenv() will not override existing environment variables,
    # allowing for flexible configuration.
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"INFO: Loading environment variables from: {env_path.resolve()}")

    args = parse_args()
    setup_logging(args.log_level)
    
    logging.info("Starting Example MCP Server...")
    logging.info(f"Configuration: transport={args.transport}, host={args.host}, port={args.port}, log_level={args.log_level}")

    # --- MCP Server Initialization ---
    # FastMCP uses host/port only for HTTP-based transports
    mcp = FastMCP(
        name="ExampleMCPServer",
        description="Provides tools to search Example, download papers, and manage local databases of articles.",
        version="0.1.0",
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower() # FastMCP uses lowercase log levels
    )

    # --- MCP Tool Definitions ---
    @mcp.tool(
        name="hello",
        description="An example MCP tool that returns a greeting.",
        # Add parameter and return value schemas for better client integration
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name to include in the greeting."
                }
            },
            "required": ["name"]
        },
        returns={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["success"]},
                "greeting": {"type": "string"}
            }
        }
    )
    async def hello(name: str) -> Dict[str, Any]:
        """
        An example MCP tool that returns a personalized greeting.
        """
        logging.info(f"Tool 'hello' called with name='{name}'.")
        return {"status": "success", "greeting": f"Hello, {name}!"}

    # --- Run the Server ---
    logging.info(f"Listening for MCP messages on {args.transport}...")
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main_cli()