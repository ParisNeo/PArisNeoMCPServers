# File: PArisNeoMCPServers/run_duckduckgo_mcp_example.py
import sys
import os
from pathlib import Path
import json
from dotenv import load_dotenv

# Load .env from the script's directory or parent for LollmsClient/API keys if needed
# For this script, it's mainly for LollmsClient setup if it requires env vars.
# The MCP server itself will load its own .env.
script_env_path = Path(__file__).resolve().parent / '.env'
if script_env_path.exists():
    load_dotenv(dotenv_path=script_env_path)
    print(f"Loaded .env from {script_env_path}")


try:
    from lollms_client import LollmsClient
    from ascii_colors import ASCIIColors, trace_exception
    from lollms_client.lollms_types import MSG_TYPE
except ImportError as e:
    print(f"ERROR: Could not import LollmsClient components: {e}")
    print("Please ensure lollms-client is installed: pip install lollms-client ascii-colors python-dotenv")
    trace_exception(e)
    sys.exit(1)

# Path to the DuckDuckGo MCP Server project
# Assumes this script is in PArisNeoMCPServers/ and the server is in PArisNeoMCPServers/duckduckgo-mcp-server/
PATH_TO_DDG_MCP_SERVER_PROJECT = Path(__file__).resolve().parent / "duckduckgo-mcp-server"
if not PATH_TO_DDG_MCP_SERVER_PROJECT.is_dir():
    print(f"ERROR: DuckDuckGo MCP server project not found at {PATH_TO_DDG_MCP_SERVER_PROJECT}")
    sys.exit(1)

# The server script relative to its project root
# This example will use python directly to run the server script
# instead of relying on `uvx` or `uv run` for simplicity in this example context,
# but in a real deployment, `uvx` or `uv run` is preferred.
SERVER_SCRIPT_RELATIVE_PATH = "duckduckgo-mcp-server/server.py"
FULL_SERVER_SCRIPT_PATH = (PATH_TO_DDG_MCP_SERVER_PROJECT / SERVER_SCRIPT_RELATIVE_PATH).resolve()
print(FULL_SERVER_SCRIPT_PATH)
if not FULL_SERVER_SCRIPT_PATH.exists():
    print(f"ERROR: Server script not found at {FULL_SERVER_SCRIPT_PATH}")
    sys.exit(1)


def main():
    ASCIIColors.red("--- Example: Using LollmsClient with DuckDuckGo MCP Server ---")
    ASCIIColors.red(f"--- Server project path: {PATH_TO_DDG_MCP_SERVER_PROJECT} ---")
    ASCIIColors.red(f"--- Server script: {FULL_SERVER_SCRIPT_PATH} ---")
    ASCIIColors.yellow("--- Make sure the server's virtual environment (if used) is activated OR "
                       "its dependencies are met in the Python env running this script. ---")
    ASCIIColors.yellow("--- This example runs the server script directly using the current Python interpreter. ---")

    # Determine the Python executable.
    # For robust execution, especially if the server has its own .venv,
    # you might want to point to server_project_path/.venv/bin/python.
    # For this example, we'll use sys.executable (the one running this script).
    # This implies that the 'duckduckgo-search' and 'mcp' libraries must be available
    # in the environment running this example script.
    python_executable = sys.executable
    ASCIIColors.cyan(f"Using Python interpreter: {python_executable}")


    mcp_config = {
        "initial_servers": {
            "my_ddg_search_server": {
                "command": [
                    python_executable, # Use the determined python interpreter
                    str(FULL_SERVER_SCRIPT_PATH) # Full path to the server script
                ],
                "args": [], # No additional arguments for server.py itself
                "cwd": str(PATH_TO_DDG_MCP_SERVER_PROJECT.resolve()), # CRUCIAL for .env loading by server
            }
        }
    }

    ASCIIColors.magenta("\n1. Initializing LollmsClient...")
    try:
        # Using a local LLM binding (e.g., ollama) as the primary.
        # The MCP client will connect to our DuckDuckGo server.
        client = LollmsClient(
            binding_name="ollama", # Replace with your preferred LLM binding
            model_name="mistral-nemo:latest",   # Replace with your model
            mcp_binding_name="standard_mcp",
            mcp_binding_config=mcp_config,
        )
    except Exception as e:
        ASCIIColors.error(f"Failed to initialize LollmsClient: {e}")
        trace_exception(e)
        sys.exit(1)

    if not client.binding or not client.mcp:
        ASCIIColors.error("LollmsClient LLM or MCP binding failed to load.")
        if hasattr(client, 'close'): client.close()
        sys.exit(1)
    ASCIIColors.green("LollmsClient initialized successfully.")

    def mcp_streaming_callback(chunk: str, msg_type: MSG_TYPE, metadata: dict = None, history: list = None) -> bool:
        prefix = ""
        color_func = ASCIIColors.green
        if metadata:
            type_info = metadata.get('type', 'unknown_type')
            tool_name_info = metadata.get('tool_name', '')
            prefix = f"MCP ({type_info}{f' - {tool_name_info}' if tool_name_info else ''})"
            if msg_type == MSG_TYPE.MSG_TYPE_STEP_START: color_func = ASCIIColors.cyan; prefix += " Step Start"
            elif msg_type == MSG_TYPE.MSG_TYPE_STEP_END: color_func = ASCIIColors.cyan; prefix += " Step End"
            elif msg_type == MSG_TYPE.MSG_TYPE_STEP_START: color_func = ASCIIColors.yellow; prefix += " Tool Call Start"
            elif msg_type == MSG_TYPE.MSG_TYPE_STEP_END: color_func = ASCIIColors.yellow; prefix += " Tool Call End"
            elif msg_type == MSG_TYPE.MSG_TYPE_INFO: color_func = ASCIIColors.yellow; prefix += " Info"
            elif msg_type == MSG_TYPE.MSG_TYPE_EXCEPTION: color_func = ASCIIColors.red; prefix += " Exception"
        else:
            prefix = f"MCP (Type: {str(msg_type).split('.')[-1]})"

        if msg_type == MSG_TYPE.MSG_TYPE_CHUNK:
            # Only print LLM chunks, not tool output chunks unless desired
            if metadata and metadata.get("source") == "llm_binding":
                ASCIIColors.green(chunk, end="")
            elif metadata and metadata.get("source") == "mcp_tool_output_chunk":
                # Optionally print tool output chunks if they are large and streamed
                # ASCIIColors.blue(f"[Tool Chunk]: {chunk}", end="")
                pass
        else:
            color_func(f"{prefix}: {chunk}")
        sys.stdout.flush()
        return True

    # --- Test 1: Web Search via DuckDuckGo MCP ---
    ASCIIColors.magenta("\n2. Test: DuckDuckGo Web Search via MCP")
    search_query = "What are the latest developments in renewable energy in Europe?"
    #search_prompt_for_llm = f"Please search the web for: '{search_query}'. Summarize the findings."
    search_prompt_for_llm = f"Please search the web for: '{search_query}' using only 3 results from the 'eu-en' region published in the last month. Then summarize the findings."


    search_response = client.generate_with_mcp(
        prompt=search_prompt_for_llm,
        streaming_callback=mcp_streaming_callback,
        max_tool_calls=1 # Expect one call to the search tool
    )
    print() # Newline after streaming output
    ASCIIColors.blue(f"Final response object for search prompt: {json.dumps(search_response, indent=2)}")

    assert search_response.get("error") is None, f"Search query error: {search_response.get('error')}"
    assert search_response.get("final_answer"), "Search query: no final answer from LLM."
    
    tool_calls_search = search_response.get("tool_calls", [])
    assert len(tool_calls_search) > 0, "Search prompt should have called the DuckDuckGo tool."
    
    if tool_calls_search:
        first_tool_call = tool_calls_search[0]
        assert first_tool_call["name"] == "my_ddg_search_server::duckduckgo_search", "Incorrect tool called for search."
        
        tool_call_params = first_tool_call.get("parameters", {})
        ASCIIColors.info(f"Tool call parameters sent: {json.dumps(tool_call_params)}")

        search_result_output = first_tool_call.get("result", {}).get("output", {})
        assert "results" in search_result_output, "Search tool result missing 'results' key."
        
        if "results" in search_result_output and search_result_output["results"]:
            ASCIIColors.green("\nSearch Results from DuckDuckGo:")
            for i, res in enumerate(search_result_output["results"]):
                ASCIIColors.yellow(f"  Result {i+1}:")
                ASCIIColors.cyan(f"    Title: {res.get('title')}")
                ASCIIColors.cyan(f"    URL: {res.get('href')}")
                ASCIIColors.cyan(f"    Snippet: {res.get('body', '')[:150]}...")
        elif "results" in search_result_output:
            ASCIIColors.yellow("\nSearch returned no results from DuckDuckGo.")
        
        if search_result_output.get("status") == "error":
            ASCIIColors.error(f"Error from search tool: {search_result_output.get('message')}")

    ASCIIColors.magenta("\n3. Closing LollmsClient...")
    if client and hasattr(client, 'close'):
        try:
            client.close()
        except Exception as e:
            ASCIIColors.error(f"Error closing LollmsClient: {e}")
            trace_exception(e)

    ASCIIColors.info("DuckDuckGo MCP example finished.")
    ASCIIColors.red("\n--- LollmsClient with DuckDuckGo MCP Server Example Finished ---")

if __name__ == "__main__":
    main()