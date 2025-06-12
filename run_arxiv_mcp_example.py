import asyncio
import subprocess
from contextlib import AsyncExitStack
from typing import Optional, List, Dict, Any
from lollms_client.lollms_mcp_binding import LollmsMCPBinding
from ascii_colors import ASCIIColors, trace_exception
import threading
import json

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

# This separator is used to create a unique tool name across all connected servers.
# e.g., "my_arxiv_manager::create_arxiv_database"
TOOL_NAME_SEPARATOR = "::"

class StandardMCPBinding(LollmsMCPBinding):
    """
    A standard binding for LollmsClient to connect to MCP servers.

    This binding can manage both:
    1. Local MCP servers launched as subprocesses (via `stdio`).
    2. Remote MCP servers connected over HTTP (via `streamable-http`).

    Tools from all connected servers are aggregated, and their names are prefixed
    with the server's alias to prevent naming conflicts.
    """

    def __init__(self, mcp_binding_config: Dict[str, Any], **other_config_params: Any):
        """
        Initializes the binding to connect to multiple MCP servers.

        Args:
            mcp_binding_config (Dict[str, Any]): A dictionary containing the configuration.
                It should have keys like `initial_servers` and/or `remote_servers`.
                Example:
                {
                    "initial_servers": {
                        "local_arxiv": {
                            "command": ["python", "server.py"],
                            "args": ["--transport", "stdio"],
                            "cwd": "/path/to/server"
                        }
                    },
                    "remote_servers": {
                        "shared_tools": "http://10.0.0.5:9000"
                    }
                }
            **other_config_params (Any): Additional configuration parameters.
        """
        super().__init__(binding_name="standard_mcp")

        if not MCP_LIBRARY_AVAILABLE:
            ASCIIColors.error(f"{self.binding_name}: The 'mcp' library is not installed. This binding will be disabled.")
            ASCIIColors.error("Please install it with: pip install mcp")
            return

        if not mcp_binding_config:
            ASCIIColors.error(f"{self.binding_name}: `mcp_binding_config` dictionary is required.")
            return

        self.config = mcp_binding_config
        self.servers: Dict[str, Dict[str, Any]] = {}

        # --- Process and consolidate server configurations ---
        initial_servers = mcp_binding_config.get("initial_servers", {})
        remote_servers = mcp_binding_config.get("remote_servers", {})

        for alias, server_conf in initial_servers.items():
            if "command" not in server_conf:
                ASCIIColors.warning(f"{self.binding_name}: Skipping stdio server '{alias}' due to missing 'command'.")
                continue
            self.servers[alias] = {
                "type": "stdio",
                "config": server_conf,
                "initialized": False,
                "initializing_lock": threading.Lock(),
                "session": None,
                "exit_stack": None,
                "process": None # To hold the subprocess object
            }

        for alias, server_url in remote_servers.items():
            if not isinstance(server_url, str):
                ASCIIColors.warning(f"{self.binding_name}: Skipping remote server '{alias}' due to invalid URL format.")
                continue
            self.servers[alias] = {
                "type": "http",
                "config": {"url": server_url},
                "initialized": False,
                "initializing_lock": threading.Lock(),
                "session": None,
                "exit_stack": None
            }

        self._discovered_tools_cache: List[Dict[str, Any]] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._loop_started_event = threading.Event()

        if self.servers:
            self._start_event_loop_thread()
        else:
            ASCIIColors.warning(f"{self.binding_name}: No valid servers configured.")

    # --- Async Event Loop Management (unchanged from the remote example) ---
    def _start_event_loop_thread(self):
        if self._loop and self._loop.is_running(): return
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop_forever, daemon=True)
        self._thread.start()

    def _run_loop_forever(self):
        if not self._loop: return
        asyncio.set_event_loop(self._loop)
        try:
            self._loop_started_event.set()
            self._loop.run_forever()
        finally:
            if not self._loop.is_closed(): self._loop.close()

    def _wait_for_loop(self, timeout=5.0):
        if not self._loop_started_event.wait(timeout=timeout):
            raise RuntimeError(f"{self.binding_name}: Event loop thread failed to start in time.")
        if not self._loop or not self._loop.is_running():
            raise RuntimeError(f"{self.binding_name}: Event loop is not running after start signal.")

    def _run_async(self, coro, timeout=None):
        if not self._loop or not self._loop.is_running():
            raise RuntimeError("Event loop not running.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout)

    # --- Core Connection and Tool Logic ---
    async def _initialize_connection_async(self, alias: str) -> bool:
        """Establishes a connection to a server based on its type (stdio or http)."""
        server_info = self.servers[alias]
        if server_info["initialized"]:
            return True

        ASCIIColors.info(f"{self.binding_name}: Initializing connection to '{alias}' (type: {server_info['type']})...")
        try:
            exit_stack = AsyncExitStack()
            
            # --- CONNECTION LOGIC SPLIT ---
            if server_info["type"] == "http":
                server_url = server_info["config"]["url"]
                client_streams = await exit_stack.enter_async_context(streamablehttp_client(server_url))
                read_stream, write_stream, _ = client_streams
                
            elif server_info["type"] == "stdio":
                conf = server_info["config"]
                process_streams = await exit_stack.enter_async_context(
                    subprocess_client(
                        command=conf["command"],
                        args=conf.get("args", []),
                        cwd=conf.get("cwd")
                    )
                )
                read_stream, write_stream, process = process_streams
                server_info["process"] = process # Store the process handle for termination
            else:
                raise ValueError(f"Unknown server type: {server_info['type']}")

            # --- COMMON SESSION LOGIC ---
            session = await exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()

            server_info["session"] = session
            server_info["exit_stack"] = exit_stack
            server_info["initialized"] = True

            ASCIIColors.green(f"{self.binding_name}: Connected to '{alias}'")
            return True

        except Exception as e:
            trace_exception(e)
            ASCIIColors.error(f"{self.binding_name}: Failed to connect to '{alias}': {e}")
            if 'exit_stack' in locals() and exit_stack:
                await exit_stack.aclose()
            
            server_info.update({"session": None, "exit_stack": None, "initialized": False, "process": None})
            return False

    def _ensure_initialized_sync(self, alias: str, timeout=30.0):
        """Thread-safe method to ensure a server connection is initialized."""
        self._wait_for_loop()
        server_info = self.servers[alias]
        with server_info["initializing_lock"]:
            if not server_info["initialized"]:
                success = self._run_async(self._initialize_connection_async(alias), timeout=timeout)
                if not success:
                    raise ConnectionError(f"Failed to initialize MCP connection to '{alias}'")
        if not server_info.get("session"):
             raise ConnectionError(f"MCP Session not valid after init attempt for '{alias}'")

    async def _refresh_all_tools_cache_async(self):
        """Fetches and aggregates tools from all successfully connected servers."""
        ASCIIColors.info(f"{self.binding_name}: Refreshing tools from all servers...")
        refresh_tasks = [self._fetch_tools_from_server_async(alias) for alias in self.servers.keys()]
        results = await asyncio.gather(*refresh_tasks, return_exceptions=True)
        
        all_tools = []
        for result in results:
            if isinstance(result, list):
                all_tools.extend(result)
        
        self._discovered_tools_cache = all_tools
        ASCIIColors.green(f"{self.binding_name}: Tool refresh complete. Found {len(all_tools)} tools.")

    async def _fetch_tools_from_server_async(self, alias: str) -> List[Dict[str, Any]]:
        """Fetches tools from a single server and prefixes their names."""
        server_info = self.servers[alias]
        if not server_info["initialized"] or not server_info["session"]:
            return []
        
        try:
            list_tools_result = await server_info["session"].list_tools()
            server_tools = []
            for tool_obj in list_tools_result.tools:
                input_schema = getattr(tool_obj, 'input_schema', {})
                input_schema_dict = input_schema.model_dump(mode='json', exclude_none=True) if hasattr(input_schema, 'model_dump') else dict(input_schema)
                
                # Prefix the tool name with the server alias
                tool_name_for_client = f"{alias}{TOOL_NAME_SEPARATOR}{tool_obj.name}"

                server_tools.append({
                    "name": tool_name_for_client,
                    "description": tool_obj.description or "",
                    "input_schema": input_schema_dict
                })
            ASCIIColors.info(f"{self.binding_name}: Found {len(server_tools)} tools on server '{alias}'.")
            return server_tools
        except Exception as e:
            trace_exception(e)
            ASCIIColors.error(f"{self.binding_name}: Error refreshing tools from '{alias}': {e}")
            return []

    def discover_tools(self, force_refresh: bool = False, timeout_per_server: float = 30.0, **kwargs) -> List[Dict[str, Any]]:
        if not self.servers: return []

        for alias in self.servers.keys():
            try:
                self._ensure_initialized_sync(alias, timeout=timeout_per_server)
            except Exception as e:
                ASCIIColors.warning(f"{self.binding_name}: Could not connect to '{alias}' for discovery: {e}")
        
        if force_refresh or not self._discovered_tools_cache:
            self._run_async(self._refresh_all_tools_cache_async(), timeout=timeout_per_server * len(self.servers))
        
        return self._discovered_tools_cache

    async def _execute_tool_async(self, alias: str, actual_tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        server_info = self.servers[alias]
        if not server_info["initialized"] or not server_info["session"]:
            return {"error": f"Not connected to server '{alias}'", "status_code": 503}
        
        ASCIIColors.info(f"{self.binding_name}: Executing '{actual_tool_name}' on '{alias}' with params: {json.dumps(params)}")
        try:
            mcp_call_result = await server_info["session"].call_tool(name=actual_tool_name, arguments=params)
            output_parts = [p.text for p in mcp_call_result.content if isinstance(p, types.TextContent) and p.text is not None] if mcp_call_result.content else []
            combined_output_str = "\n".join(output_parts)
            try:
                return {"output": json.loads(combined_output_str), "status_code": 200}
            except json.JSONDecodeError:
                return {"output": combined_output_str, "status_code": 200}
        except Exception as e:
            trace_exception(e)
            return {"error": f"Error executing tool '{actual_tool_name}' on '{alias}': {str(e)}", "status_code": 500}

    def execute_tool(self, tool_name_with_alias: str, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        timeout = float(kwargs.get('timeout', 60.0))
        
        if TOOL_NAME_SEPARATOR not in tool_name_with_alias:
            return {"error": f"Invalid tool name format. Expected 'alias{TOOL_NAME_SEPARATOR}tool_name', got '{tool_name_with_alias}'.", "status_code": 400}

        alias, actual_tool_name = tool_name_with_alias.split(TOOL_NAME_SEPARATOR, 1)
        if alias not in self.servers:
            return {"error": f"Unknown server alias '{alias}' in tool name.", "status_code": 400}

        try:
            self._ensure_initialized_sync(alias, timeout=min(timeout, 30.0))
            return self._run_async(self._execute_tool_async(alias, actual_tool_name, params), timeout=timeout)
        except Exception as e:
            trace_exception(e)
            return {"error": f"Failed to run tool '{actual_tool_name}' on '{alias}': {e}", "status_code": 500}

    def close(self):
        ASCIIColors.info(f"{self.binding_name}: Closing all MCP connections...")
        
        async def _close_all_connections():
            for alias, server_info in self.servers.items():
                if server_info.get("exit_stack"):
                    ASCIIColors.info(f"{self.binding_name}: Closing connection to '{alias}'...")
                    await server_info["exit_stack"].aclose()
                # For stdio servers, the process is managed by the subprocess_client
                # context manager, which sends SIGTERM on exit. We don't need to
                # manually terminate it here as the exit_stack handles it.

        if self._loop and self._loop.is_running():
            try:
                self._run_async(_close_all_connections(), timeout=10.0)
            finally:
                self._loop.call_soon_threadsafe(self._loop.stop)
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        ASCIIColors.green(f"{self.binding_name}: Standard MCP binding closed.")

    def get_binding_config(self) -> Dict[str, Any]:
        return self.config