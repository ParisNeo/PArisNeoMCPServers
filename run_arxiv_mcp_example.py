# File: PArisNeoMCPServers/run_arxiv_mcp_example.py
import sys
import os
import shutil
from pathlib import Path
import json
from dotenv import load_dotenv

# Load .env from the script's directory for LollmsClient/API keys if needed
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
    print("Please ensure lollms-client, ascii-colors, and python-dotenv are installed: pip install lollms-client ascii-colors python-dotenv")
    trace_exception(e)
    sys.exit(1)

# --- Path Setup ---
# Path to the Arxiv MCP Server project
PATH_TO_ARXIV_MCP_SERVER_PROJECT = Path(__file__).resolve().parent / "arxiv-mcp-server"
if not PATH_TO_ARXIV_MCP_SERVER_PROJECT.is_dir():
    print(f"ERROR: Arxiv MCP server project not found at {PATH_TO_ARXIV_MCP_SERVER_PROJECT}")
    sys.exit(1)

# Server script relative to its project root
SERVER_SCRIPT_RELATIVE_PATH = "arxiv_mcp_server/server.py"
FULL_SERVER_SCRIPT_PATH = (PATH_TO_ARXIV_MCP_SERVER_PROJECT / SERVER_SCRIPT_RELATIVE_PATH).resolve()

if not FULL_SERVER_SCRIPT_PATH.exists():
    print(f"ERROR: Server script not found at {FULL_SERVER_SCRIPT_PATH}")
    sys.exit(1)

# Define the database name for this test run
TEST_DB_NAME = "llm_reasoning_papers"
ARXIV_DB_ROOT_FOR_TEST = Path(__file__).resolve().parent / "mcp_example_outputs" / "arxiv_databases"
TEST_DB_PATH = ARXIV_DB_ROOT_FOR_TEST / TEST_DB_NAME

def main():
    ASCIIColors.red("--- Example: Using LollmsClient with Arxiv MCP Server ---")
    ASCIIColors.red(f"--- Server project path: {PATH_TO_ARXIV_MCP_SERVER_PROJECT} ---")
    ASCIIColors.red(f"--- Server script: {FULL_SERVER_SCRIPT_PATH} ---")
    ASCIIColors.yellow("--- This example runs the server script directly using the current Python interpreter. ---")
    ASCIIColors.yellow("--- Ensure Arxiv and other server dependencies are met in this environment. ---")
    
    # --- Cleanup from previous runs ---
    if TEST_DB_PATH.exists():
        ASCIIColors.yellow(f"Removing existing test database from previous run: {TEST_DB_PATH}")
        shutil.rmtree(TEST_DB_PATH)

    python_executable = sys.executable
    ASCIIColors.cyan(f"Using Python interpreter: {python_executable}")

    mcp_config = {
        "initial_servers": {
            "my_arxiv_manager": {
                "command": [
                    python_executable,
                    str(FULL_SERVER_SCRIPT_PATH)
                ],
                "args": [],
                "cwd": str(PATH_TO_ARXIV_MCP_SERVER_PROJECT.resolve()),
            }
        }
    }

    ASCIIColors.magenta("\n1. Initializing LollmsClient...")
    try:
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
        """
        Refactored callback to correctly handle different message types from LollmsClient.
        """
        # Set default prefix and color
        prefix = f"MCP ({str(msg_type).split('.')[-1]})"
        color_func = ASCIIColors.yellow # Default for info

        # Customize based on metadata if available
        if metadata:
            type_info = metadata.get('type', 'unknown')
            tool_name_info = metadata.get('tool_name', '')
            prefix = f"MCP ({type_info}{f' - {tool_name_info}' if tool_name_info else ''})"

        # Handle message types with specific formatting
        if msg_type == MSG_TYPE.MSG_TYPE_CHUNK:
            if metadata and metadata.get("source") == "llm_binding":
                ASCIIColors.green(chunk, end="") # LLM response chunks
            # We ignore other chunk types for this example
            return True # Don't print a prefix for simple chunks

        elif msg_type == MSG_TYPE.MSG_TYPE_TOOL_OUTPUT:
            # THIS IS THE KEY FIX: Tool output arrives as a single message.
            # The 'chunk' contains the full JSON string of the tool's return value.
            color_func = ASCIIColors.blue
            try:
                # Pretty-print the JSON for readability
                output_data = json.loads(chunk)
                pretty_chunk = json.dumps(output_data, indent=2)
                color_func(f"\n\n{pretty_chunk}")
            except (json.JSONDecodeError, TypeError):
                # Fallback if the output isn't valid JSON
                color_func(f"\n {chunk}")

        elif msg_type in [MSG_TYPE.MSG_TYPE_STEP_START, MSG_TYPE.MSG_TYPE_STEP_END]:
            color_func = ASCIIColors.cyan
            color_func(f"\n{chunk}")

        elif msg_type == MSG_TYPE.MSG_TYPE_TOOL_CALL:
            color_func = ASCIIColors.yellow
            try:
                # Pretty-print the tool call arguments
                call_data = metadata
                pretty_chunk = json.dumps(call_data, indent=2)
                color_func(f"\n\n{pretty_chunk}")
            except (json.JSONDecodeError, TypeError):
                color_func(f"\n{chunk}")

        elif msg_type == MSG_TYPE.MSG_TYPE_EXCEPTION:
            color_func = ASCIIColors.red
            color_func(f"\n{chunk}")
        
        else:
            # Catch-all for any other message types like MSG_TYPE_INFO
            color_func(f"\n{chunk}")

        sys.stdout.flush()
        return True

    # --- Test Workflow ---
    
    # 2. Create a new database
    ASCIIColors.magenta(f"\n2. Test: Create a new database named '{TEST_DB_NAME}'")
    create_db_prompt = f"Please create a new Arxiv database called '{TEST_DB_NAME}' for me."
    create_db_response = client.generate_with_mcp(prompt=create_db_prompt, streaming_callback=mcp_streaming_callback)
    print()
    assert create_db_response.get("error") is None, "Error creating database."
    assert len(create_db_response.get("tool_calls",[])) > 0, "Tool call for create_arxiv_database failed."

    # 3. List databases to confirm creation
    ASCIIColors.magenta("\n3. Test: List databases to confirm creation")
    list_dbs_prompt = "Can you list all my current Arxiv databases?"
    list_dbs_response = client.generate_with_mcp(prompt=list_dbs_prompt, streaming_callback=mcp_streaming_callback)
    print()
    assert list_dbs_response.get("error") is None, "Error listing databases."
    list_output = list_dbs_response.get("tool_calls", [{}])[0].get("result", {}).get("output", {})
    assert TEST_DB_NAME in list_output.get("databases", []), f"Database '{TEST_DB_NAME}' was not found after creation."
    ASCIIColors.green(f"Database '{TEST_DB_NAME}' successfully created and verified.")

    # 4. Search and populate the database
    ASCIIColors.magenta("\n4. Test: Search and populate the database")
    search_query = "ti:\"chain of thought\" AND cat:cs.AI"
    search_prompt = f"Please search Arxiv for '{search_query}' and add up to 3 results to the '{TEST_DB_NAME}' database."
    search_response = client.generate_with_mcp(prompt=search_prompt, streaming_callback=mcp_streaming_callback, max_tool_calls=1)
    print()
    assert search_response.get("error") is None, "Error during search and populate."
    search_output = search_response.get("tool_calls", [{}])[0].get("result", {}).get("output", {})
    assert search_output.get("status") == "success", "Search and populate tool did not return success status."
    downloaded_papers = search_output.get("new_papers", [])
    paper_to_get = downloaded_papers[0] if downloaded_papers else None

    # 5. Get the contents of the database
    ASCIIColors.magenta("\n5. Test: Get contents of the populated database")
    get_contents_prompt = f"Show me all the papers in my '{TEST_DB_NAME}' database."
    get_contents_response = client.generate_with_mcp(prompt=get_contents_prompt, streaming_callback=mcp_streaming_callback)
    print()
    assert get_contents_response.get("error") is None, "Error getting database contents."
    contents_output = get_contents_response.get("tool_calls", [{}])[0].get("result", {}).get("output", {})
    assert contents_output.get("paper_count") > 0, "Database appears empty after population step."
    ASCIIColors.green(f"Database contains {contents_output.get('paper_count')} papers.")
    
    # 6. Get a specific paper's abstract
    if paper_to_get:
        paper_id = paper_to_get["entry_id"]
        ASCIIColors.magenta(f"\n6. Test: Get abstract for paper {paper_id}")
        get_abstract_prompt = f"From the '{TEST_DB_NAME}' database, can you give me the abstract for paper {paper_id}?"
        get_abstract_response = client.generate_with_mcp(prompt=get_abstract_prompt, streaming_callback=mcp_streaming_callback)
        print()
        assert get_abstract_response.get("error") is None, "Error getting paper abstract."
        abstract_output = get_abstract_response.get("tool_calls", [{}])[0].get("result", {}).get("output", {})
        assert "summary" in abstract_output, "Result for get_paper_abstract missing 'summary'."
        ASCIIColors.blue(f"Abstract for {paper_id}:\n{abstract_output['summary'][:300]}...")
    else:
        ASCIIColors.yellow("Skipping 'get abstract' test as no new papers were downloaded.")

    # --- Teardown ---
    ASCIIColors.magenta("\n7. Closing LollmsClient...")
    if client and hasattr(client, 'close'):
        try:
            client.close()
        except Exception as e:
            ASCIIColors.error(f"Error closing LollmsClient: {e}")
            trace_exception(e)

    ASCIIColors.info(f"Arxiv MCP example finished. Check {ARXIV_DB_ROOT_FOR_TEST} for the created database.")
    ASCIIColors.red("\n--- LollmsClient with Arxiv MCP Server Example Finished ---")

if __name__ == "__main__":
    main()