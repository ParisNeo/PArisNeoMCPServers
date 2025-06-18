# PArisNeoMCPServers/bitcoin-mcp-server/bitcoin_mcp_server/server.py
import sys
from pathlib import Path

# --- Dependency Check FIRST ---
try:
    from mcp.server.fastmcp import FastMCP
    from dotenv import load_dotenv
    from ascii_colors import ASCIIColors
    import bitcoinlib
    import requests
except ImportError as e:
    missing_module = e.name
    print("=" * 80, file=sys.stderr)
    print(f"FATAL: A required dependency '{missing_module}' is not installed.", file=sys.stderr)
    print("The Bitcoin MCP Server cannot start.", file=sys.stderr)
    print("\nPlease install the server's requirements.", file=sys.stderr)
    print("To fix this, navigate to the server's directory in your terminal and run:", file=sys.stderr)
    print("\n    cd path/to/PArisNeoMCPServers/bitcoin-mcp-server", file=sys.stderr)
    print("    uv pip install -e .", file=sys.stderr)
    print("\n(If not using uv, you can use 'pip install -e .')", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    sys.exit(1)

# --- Now that dependencies are confirmed, proceed with normal imports ---
import argparse
from typing import Dict, Any, Optional
import bitcoin_wrapper


def parse_args():
    parser = argparse.ArgumentParser(description="Bitcoin MCP Server configuration")
    parser.add_argument("--host", type=str, default="localhost", help="Hostname or IP address (default: localhost)")
    parser.add_argument("--port", type=int, default=9625, help="Port number (1-65535)")
    parser.add_argument("--log-level", dest="log_level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO", help="Logging level (default: INFO)")
    parser.add_argument("--transport", type=str, choices=["stdio", "sse", "streamable-http"], default="stdio", help="Transport protocol: stdio, sse, or streamable-http")
    args = parser.parse_args()
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
    ASCIIColors.yellow(f".env file not found at {env_path}. Relying on existing environment variables.")

# --- MCP Server Initialization ---
args = parse_args()
server_desc = (
    "Provides tools to manage a Bitcoin wallet, query blockchain data, and get market information. "
    "WARNING: This server manages private keys in memory for the duration of its runtime. "
    "Use with caution, especially with real funds. Recommended for testnet or educational use."
)

if args.transport == "streamable-http":
    mcp = FastMCP(
        name="BitcoinMCPServer",
        description=server_desc,
        version="0.1.0",
        host=args.host,
        port=args.port,
        log_level=args.log_level
    )
    ASCIIColors.cyan(f"{mcp.settings}")
else:
    mcp = FastMCP(
        name="BitcoinMCPServer",
        description=server_desc,
        version="0.1.0"
    )

# --- MCP Tool Definitions ---

@mcp.tool(
    name="create_new_bitcoin_wallet",
    description="Creates a new Bitcoin wallet (private/public key pair). The new wallet becomes the active wallet for other operations. The response contains the private key, which must be saved by the user as it cannot be recovered later."
)
async def create_new_bitcoin_wallet(wallet_name: str) -> Dict[str, Any]:
    ASCIIColors.info(f"MCP Tool 'create_new_bitcoin_wallet' called for name: '{wallet_name}'.")
    if not wallet_name:
        return {"error": "Wallet name cannot be empty."}
    return await bitcoin_wrapper.create_new_wallet(wallet_name)

@mcp.tool(
    name="load_wallet_from_private_key",
    description="Loads an existing Bitcoin wallet using its private key in WIF (Wallet Import Format). This wallet becomes the active wallet for sending funds or checking balance."
)
async def load_wallet_from_private_key(private_key_wif: str) -> Dict[str, Any]:
    ASCIIColors.info("MCP Tool 'load_wallet_from_private_key' called.")
    if not private_key_wif:
        return {"error": "Private key (WIF) cannot be empty."}
    return await bitcoin_wrapper.load_wallet_from_wif(private_key_wif)

@mcp.tool(
    name="get_active_wallet_status",
    description="Shows details for the currently active wallet, including its address, balance in BTC and satoshis, and UTXOs (Unspent Transaction Outputs)."
)
async def get_active_wallet_status() -> Dict[str, Any]:
    ASCIIColors.info("MCP Tool 'get_active_wallet_status' called.")
    return await bitcoin_wrapper.get_wallet_status()

@mcp.tool(
    name="get_bitcoin_price",
    description="Gets the current price of Bitcoin in a specified fiat currency (e.g., 'usd', 'eur', 'jpy')."
)
async def get_bitcoin_price(currency: Optional[str] = 'usd') -> Dict[str, Any]:
    ASCIIColors.info(f"MCP Tool 'get_bitcoin_price' called for currency '{currency}'.")
    return await bitcoin_wrapper.get_btc_price(currency)

@mcp.tool(
    name="get_transaction_info",
    description="Looks up and returns detailed information for a specific Bitcoin transaction using its transaction ID (txid)."
)
async def get_transaction_info(transaction_id: str) -> Dict[str, Any]:
    ASCIIColors.info(f"MCP Tool 'get_transaction_info' called for txid '{transaction_id}'.")
    if not transaction_id:
        return {"error": "Transaction ID cannot be empty."}
    return await bitcoin_wrapper.get_transaction_details(transaction_id)

@mcp.tool(
    name="send_bitcoin",
    description="Sends a specified amount of Bitcoin to a recipient address from the currently active wallet. The fee is calculated automatically. DANGER: This action is irreversible. Ensure the recipient address and amount are correct."
)
async def send_bitcoin(recipient_address: str, amount_btc: float) -> Dict[str, Any]:
    ASCIIColors.info(f"MCP Tool 'send_bitcoin' called to send {amount_btc} BTC to {recipient_address}.")
    if not recipient_address:
        return {"error": "Recipient address cannot be empty."}
    if not amount_btc or amount_btc <= 0:
        return {"error": "Amount in BTC must be a positive number."}
    return await bitcoin_wrapper.send_btc(recipient_address, amount_btc)

# --- Main CLI Entry Point ---
def main_cli():
    ASCIIColors.red("--- Bitcoin MCP Server ---")
    ASCIIColors.yellow("WARNING: This server handles private keys in-memory. For educational/testnet use only.")
    ASCIIColors.cyan(f"Listening for MCP messages on {args.transport}...")
    ASCIIColors.magenta(f"Running the server with the following arguments:\n{args}")

    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main_cli()