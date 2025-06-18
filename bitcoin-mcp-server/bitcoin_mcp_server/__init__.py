# PArisNeoMCPServers/bitcoin-mcp-server/bitcoin_mcp_server/__init__.py
"""
Bitcoin MCP Server Package.

This package provides an MCP server for interacting with the Bitcoin
network, managing wallets, and retrieving market data.

WARNING: This is a demonstration tool. It manages private keys in memory
and should not be used with significant amounts of real cryptocurrency.
"""

from .server import mcp as bitcoin_mcp_instance
from .bitcoin_wrapper import (
    create_new_wallet,
    load_wallet_from_wif,
    get_wallet_status,
    get_btc_price,
    get_transaction_details,
    send_btc,
)

# Expose key components for potential programmatic use.
__all__ = [
    "bitcoin_mcp_instance",
    "create_new_wallet",
    "load_wallet_from_wif",
    "get_wallet_status",
    "get_btc_price",
    "get_transaction_details",
    "send_btc",
]