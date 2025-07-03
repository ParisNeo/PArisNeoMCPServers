import asyncio
import subprocess
from contextlib import AsyncExitStack
from typing import Optional, List, Dict, Any
from lollms_client.lollms_mcp_binding import LollmsMCPBinding
from ascii_colors import ASCIIColors, trace_exception
import threading
import json
from lollms_client import LollmsClient


# --- MCP Library Dependency Check ---
try:
    from mcp import ClientSession, types
    # Import the specific client connection helpers we'll need
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.client.process import subprocess_client
    MCP_LIBRARY_AVAILABLE = True
except ImportError:
    MCP_LIBRARY_AVAILABLE = False
    ClientSession = None
    types = None
    streamablehttp_client = None
    subprocess_client = None

LollmsClient("ollama",)