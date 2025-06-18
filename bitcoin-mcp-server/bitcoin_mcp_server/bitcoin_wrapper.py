# PArisNeoMCPServers/bitcoin-mcp-server/bitcoin_mcp_server/bitcoin_wrapper.py
from pathlib import Path
from typing import Dict, Any, Optional

import requests
from ascii_colors import ASCIIColors, trace_exception
from bitcoinlib.services.services import Service
from bitcoinlib.wallets import Wallet, wallet_delete_if_exists
from dotenv import load_dotenv

# --- Configuration ---
SERVER_ROOT_PATH = Path(__file__).resolve().parent.parent
env_path = SERVER_ROOT_PATH / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    ASCIIColors.cyan(f"Bitcoin Wrapper: Loaded .env from {env_path}")

# --- State Management ---
# This is a simple in-memory representation of the active wallet.
# In a real-world scenario, this would require secure, persistent storage.
ACTIVE_WALLET: Optional[Wallet] = None
ACTIVE_WALLET_NAME: Optional[str] = None


# --- Helper Functions ---

def _get_network_provider() -> Service:
    """Gets a network service provider instance."""
    # Using Blockchair as a reliable provider, but others are available.
    return Service(provider='blockchair')


def _format_wallet_status() -> Dict[str, Any]:
    """Formats the status of the currently active wallet."""
    if not ACTIVE_WALLET:
        return {"error": "No wallet is currently loaded. Create or load a wallet first."}

    try:
        ACTIVE_WALLET.scan()  # Update wallet info from the network
        balance_sats = ACTIVE_WALLET.balance()

        return {
            "status": "success",
            "wallet_name": ACTIVE_WALLET.name,
            "address": ACTIVE_WALLET.get_key().address,
            "balance_satoshi": int(balance_sats),
            "balance_btc": balance_sats / 100_000_000,
            "network": ACTIVE_WALLET.network.name,
            "utxos": ACTIVE_WALLET.utxos(),
        }
    except Exception as e:
        trace_exception(e)
        return {"error": f"Failed to get wallet status: {e}"}


# --- Core Wrapper Functions ---

async def create_new_wallet(wallet_name: str) -> Dict[str, Any]:
    """Creates a new Bitcoin wallet and sets it as the active wallet."""
    global ACTIVE_WALLET, ACTIVE_WALLET_NAME
    ASCIIColors.info(f"Bitcoin Wrapper: Creating new wallet '{wallet_name}'.")

    # To avoid clashes in the bitcoinlib database, we remove any previous wallet with the same name.
    try:
        wallet_delete_if_exists(wallet_name, force=True)
        wallet = Wallet.create(wallet_name, network='bitcoin')
        ACTIVE_WALLET = wallet
        ACTIVE_WALLET_NAME = wallet_name

        key = wallet.get_key()

        ASCIIColors.green(f"Successfully created wallet '{wallet_name}'.")
        ASCIIColors.yellow("IMPORTANT: Store the private key securely!")

        return {
            "status": "success",
            "wallet_name": wallet_name,
            "address": key.address,
            "private_key_wif": key.wif,
            "message": "Wallet created successfully. It is now the active wallet. SAVE THE PRIVATE KEY."
        }
    except Exception as e:
        trace_exception(e)
        return {"error": f"Failed to create wallet: {e}"}


async def load_wallet_from_wif(private_key_wif: str) -> Dict[str, Any]:
    """Loads a wallet from a WIF private key and sets it as active."""
    global ACTIVE_WALLET, ACTIVE_WALLET_NAME
    ASCIIColors.info("Bitcoin Wrapper: Loading wallet from WIF.")

    wallet_name = "loaded_from_wif"  # Use a generic, temporary name
    try:
        wallet_delete_if_exists(wallet_name, force=True)
        wallet = Wallet.create(wallet_name, keys=private_key_wif, network='bitcoin')
        ACTIVE_WALLET = wallet
        ACTIVE_WALLET_NAME = wallet_name

        status = _format_wallet_status()
        if "error" in status:
            return status

        return {
            "status": "success",
            "message": "Wallet loaded successfully from WIF and is now active.",
            "wallet_status": status,
        }
    except Exception as e:
        trace_exception(e)
        return {"error": f"Failed to load wallet from WIF: {e}. Ensure the WIF is correct."}


async def get_wallet_status() -> Dict[str, Any]:
    """Gets the status of the currently loaded wallet."""
    ASCIIColors.info("Bitcoin Wrapper: Getting active wallet status.")
    return _format_wallet_status()


async def get_btc_price(currency: str = 'usd') -> Dict[str, Any]:
    """Fetches the current price of Bitcoin from CoinGecko."""
    ASCIIColors.info(f"Bitcoin Wrapper: Fetching BTC price in {currency.upper()}.")
    currency = currency.lower()
    url = f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={currency}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        price = data.get("bitcoin", {}).get(currency)
        if price is None:
            return {"error": f"Currency '{currency}' not found in API response."}
        return {"status": "success", "source": "CoinGecko", "currency": currency.upper(), "price": price}
    except requests.exceptions.RequestException as e:
        trace_exception(e)
        return {"error": f"Failed to fetch price from CoinGecko API: {e}"}


async def get_transaction_details(txid: str) -> Dict[str, Any]:
    """Retrieves details for a specific transaction ID."""
    ASCIIColors.info(f"Bitcoin Wrapper: Getting details for transaction '{txid}'.")
    try:
        provider = _get_network_provider()
        tx_info = provider.gettransaction(txid)
        if not tx_info:
            return {"error": f"Transaction with ID '{txid}' not found or API error."}
        return {"status": "success", "transaction": tx_info.as_dict()}
    except Exception as e:
        trace_exception(e)
        return {"error": f"Failed to retrieve transaction details: {e}"}


async def send_btc(recipient_address: str, amount_btc: float) -> Dict[str, Any]:
    """Sends a specified amount of BTC from the active wallet."""
    ASCIIColors.info(f"Bitcoin Wrapper: Attempting to send {amount_btc} BTC to {recipient_address}.")
    if not ACTIVE_WALLET:
        return {"error": "No wallet is loaded. Cannot send transaction."}

    try:
        # bitcoinlib handles fee estimation automatically by default
        tx = ACTIVE_WALLET.send_to(recipient_address, f"{amount_btc} BTC")
        ASCIIColors.green(f"Transaction broadcasted with txid: {tx.txid}")
        return {
            "status": "success",
            "message": "Transaction broadcasted successfully.",
            "transaction_details": tx.as_dict()
        }
    except Exception as e:
        # Common errors: InsufficientFundsError, InvalidAddressError
        trace_exception(e)
        return {"error": f"Failed to send transaction: {e}"}