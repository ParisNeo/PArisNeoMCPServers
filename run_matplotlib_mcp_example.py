# File: PArisNeoMCPServers/run_matplotlib_mcp_example.py
import sys
import os
import shutil
from pathlib import Path
import json
import base64
from dotenv import load_dotenv

# Load .env from the script's directory for LollmsClient/API keys if needed
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
    print("Please ensure lollms-client, ascii-colors, and python-dotenv are installed: pip install lollms-client ascii-colors python-dotenv")
    trace_exception(e)
    sys.exit(1)

# Path to the Matplotlib MCP Server project
# Assumes this script is in PArisNeoMCPServers/ and the server is in PArisNeoMCPServers/matplotlib-mcp-server/
PATH_TO_MPL_MCP_SERVER_PROJECT = Path(__file__).resolve().parent / "matplotlib-mcp-server"
if not PATH_TO_MPL_MCP_SERVER_PROJECT.is_dir():
    print(f"ERROR: Matplotlib MCP server project not found at {PATH_TO_MPL_MCP_SERVER_PROJECT}")
    sys.exit(1)

# Server script relative to its project root
SERVER_SCRIPT_RELATIVE_PATH = "matplotlib_mcp_server/server.py"
FULL_SERVER_SCRIPT_PATH = (PATH_TO_MPL_MCP_SERVER_PROJECT / SERVER_SCRIPT_RELATIVE_PATH).resolve()

if not FULL_SERVER_SCRIPT_PATH.exists():
    print(f"ERROR: Server script not found at {FULL_SERVER_SCRIPT_PATH}")
    sys.exit(1)

OUTPUT_DIRECTORY = Path(__file__).resolve().parent / "mcp_example_outputs"
OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

def save_base64_image_from_tool(tool_output: dict, filename_stem: str) -> Path | None:
    if tool_output.get("status") == "success" and "image_base64" in tool_output and "format" in tool_output:
        image_base64 = tool_output["image_base64"]
        img_format = tool_output["format"]
        image_bytes = base64.b64decode(image_base64)
        file_path = OUTPUT_DIRECTORY / f"{filename_stem}.{img_format}"
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        ASCIIColors.green(f"Image saved to: {file_path}")
        return file_path
    else:
        error_msg = tool_output.get('message', 'Unknown error during image generation.')
        ASCIIColors.error(f"Failed to generate or save image '{filename_stem}': {error_msg}")
        return None

def main():
    ASCIIColors.red("--- Example: Using LollmsClient with Matplotlib MCP Server ---")
    ASCIIColors.red(f"--- Server project path: {PATH_TO_MPL_MCP_SERVER_PROJECT} ---")
    ASCIIColors.red(f"--- Server script: {FULL_SERVER_SCRIPT_PATH} ---")
    ASCIIColors.yellow("--- This example runs the server script directly using the current Python interpreter. ---")
    ASCIIColors.yellow("--- Ensure Matplotlib and other server dependencies are met in this environment, or use the server's .venv python. ---")

    python_executable = sys.executable
    ASCIIColors.cyan(f"Using Python interpreter: {python_executable}")

    mcp_config = {
        "initial_servers": {
            "my_matplotlib_plotter": {
                "command": [
                    python_executable,
                    str(FULL_SERVER_SCRIPT_PATH)
                ],
                "args": [],
                "cwd": str(PATH_TO_MPL_MCP_SERVER_PROJECT.resolve()), # CRUCIAL for .env loading by server
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
        # Standard callback - copied from other examples, can be simplified if needed
        prefix = ""
        color_func = ASCIIColors.green
        if metadata:
            type_info = metadata.get('type', 'unknown_type')
            tool_name_info = metadata.get('tool_name', '')
            prefix = f"MCP ({type_info}{f' - {tool_name_info}' if tool_name_info else ''})"
            if msg_type == MSG_TYPE.MSG_TYPE_STEP_START: color_func = ASCIIColors.cyan; prefix += " Step Start"
            elif msg_type == MSG_TYPE.MSG_TYPE_STEP_END: color_func = ASCIIColors.cyan; prefix += " Step End"
            elif msg_type == MSG_TYPE.MSG_TYPE_STEP_START: color_func = ASCIIColors.yellow; prefix += " Tool Call Start" # Corrected constant
            elif msg_type == MSG_TYPE.MSG_TYPE_STEP_END: color_func = ASCIIColors.yellow; prefix += " Tool Call End"   # Corrected constant
            elif msg_type == MSG_TYPE.MSG_TYPE_INFO: color_func = ASCIIColors.yellow; prefix += " Info"
            elif msg_type == MSG_TYPE.MSG_TYPE_EXCEPTION: color_func = ASCIIColors.red; prefix += " Exception"
        else:
            prefix = f"MCP (Type: {str(msg_type).split('.')[-1]})"

        if msg_type == MSG_TYPE.MSG_TYPE_CHUNK:
            if metadata and metadata.get("source") == "llm_binding": ASCIIColors.green(chunk, end="")
        else:
            color_func(f"{prefix}: {chunk}")
        sys.stdout.flush()
        return True
    
    # --- Test 0: Get Supported Plot Info ---
    ASCIIColors.magenta("\n2. Test: Get Supported Plot Info from Matplotlib MCP")
    supported_info_prompt = "Can you tell me what plot types and image formats the Matplotlib tool supports?"
    supported_info_response = client.generate_with_mcp(
        prompt=supported_info_prompt,
        streaming_callback=mcp_streaming_callback,
        max_tool_calls=1
    )
    print()
    ASCIIColors.blue(f"Final response for supported info: {json.dumps(supported_info_response, indent=2)}")
    assert supported_info_response.get("error") is None, "Error getting supported info."
    if supported_info_response.get("tool_calls"):
        tool_call = supported_info_response["tool_calls"][0]
        assert tool_call["name"] == "my_matplotlib_plotter::get_supported_plot_info"
        ASCIIColors.green(f"Supported info from tool: {json.dumps(tool_call.get('result',{}).get('output',{}), indent=2)}")


    # --- Test 1: Line Plot via Matplotlib MCP ---
    ASCIIColors.magenta("\n3. Test: Line Plot via Matplotlib MCP")
    line_plot_data_description = "monthly sales figures for Product A (10, 12, 9, 15, 14 units for Jan to May) and Product B (5, 8, 11, 7, 10 units for Jan to May). The x-axis should represent months from 1 to 5."
    line_plot_prompt = f"Please create a line plot showing these sales figures: {line_plot_data_description}. Title it 'Monthly Sales Performance', X-axis 'Month', Y-axis 'Units Sold'. Show a legend."

    line_plot_response = client.generate_with_mcp(
        prompt=line_plot_prompt,
        streaming_callback=mcp_streaming_callback,
        max_tool_calls=1
    )
    print() # Newline after streaming output
    ASCIIColors.blue(f"Final response object for line plot: {json.dumps(line_plot_response, indent=2)}")

    assert line_plot_response.get("error") is None, f"Line plot query error: {line_plot_response.get('error')}"
    if line_plot_response.get("tool_calls"):
        tool_call_result = line_plot_response["tool_calls"][0].get("result", {}).get("output", {})
        save_base64_image_from_tool(tool_call_result, "matplotlib_line_plot_example")
    else:
        ASCIIColors.warning("Line plot prompt did not result in a tool call.")

    # --- Test 2: Bar Chart via Matplotlib MCP ---
    ASCIIColors.magenta("\n4. Test: Bar Chart via Matplotlib MCP")
    bar_chart_data_description = "population of three cities: CityA 1.2M, CityB 0.8M, CityC 2.1M."
    bar_chart_prompt = f"Generate a bar chart for the following city populations: {bar_chart_data_description}. Title it 'City Populations', X-axis 'City', Y-axis 'Population (Millions)'. Use SVG format."
    
    bar_chart_response = client.generate_with_mcp(
        prompt=bar_chart_prompt,
        streaming_callback=mcp_streaming_callback,
        max_tool_calls=1
    )
    print()
    ASCIIColors.blue(f"Final response object for bar chart: {json.dumps(bar_chart_response, indent=2)}")
    assert bar_chart_response.get("error") is None, f"Bar chart query error: {bar_chart_response.get('error')}"
    if bar_chart_response.get("tool_calls"):
        tool_call_result = bar_chart_response["tool_calls"][0].get("result", {}).get("output", {})
        save_base64_image_from_tool(tool_call_result, "matplotlib_bar_chart_example")
        if tool_call_result.get("format") == "svg":
            ASCIIColors.green("Bar chart correctly generated in SVG format as requested by LLM.")
    else:
        ASCIIColors.warning("Bar chart prompt did not result in a tool call.")

    # --- Test 3: Pie Chart via Matplotlib MCP ---
    ASCIIColors.magenta("\n5. Test: Pie Chart via Matplotlib MCP")
    pie_data_desc = "market share for three companies: Alpha Inc 40%, Beta Corp 35%, Gamma Ltd 25%."
    pie_prompt = f"Create a pie chart showing: {pie_data_desc}. Title it 'Market Share'. Explode the slice for 'Beta Corp'."

    pie_response = client.generate_with_mcp(
        prompt=pie_prompt, streaming_callback=mcp_streaming_callback, max_tool_calls=1
    )
    print()
    ASCIIColors.blue(f"Final response object for pie chart: {json.dumps(pie_response, indent=2)}")
    assert pie_response.get("error") is None, f"Pie chart query error: {pie_response.get('error')}"
    if pie_response.get("tool_calls"):
        tool_call_result = pie_response["tool_calls"][0].get("result", {}).get("output", {})
        save_base64_image_from_tool(tool_call_result, "matplotlib_pie_chart_example")
    else:
        ASCIIColors.warning("Pie chart prompt did not result in a tool call.")


    ASCIIColors.magenta("\n6. Closing LollmsClient...")
    if client and hasattr(client, 'close'):
        try:
            client.close()
        except Exception as e:
            ASCIIColors.error(f"Error closing LollmsClient: {e}")
            trace_exception(e)

    ASCIIColors.info(f"Matplotlib MCP example finished. Check {OUTPUT_DIRECTORY} for generated plots.")
    ASCIIColors.red("\n--- LollmsClient with Matplotlib MCP Server Example Finished ---")

if __name__ == "__main__":
    main()