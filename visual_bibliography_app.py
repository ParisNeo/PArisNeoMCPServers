import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import re
from typing import Optional

# Use pipmaster or a similar tool for dependency checking
try:
    import pipmaster as pm
    pm.ensure_packages(["lollms-client", "gradio", "mcp", "pandas", "ollama", "python-dotenv", "ascii-colors"])
except ImportError:
    print("Warning: pipmaster not found. Please ensure all dependencies are installed manually.")
    print("pip install lollms-client gradio mcp pandas ollama python-dotenv ascii-colors")

import gradio as gr

# --- Path and Dependency Setup ---
ROOT_PATH = Path(__file__).resolve().parent
sys.path.append(str(ROOT_PATH))

try:
    from lollms_client import LollmsClient
    from lollms_client.lollms_types import MSG_TYPE
    from ascii_colors import ASCIIColors, trace_exception
except ImportError as e:
    print("="*80, file=sys.stderr)
    print("FATAL: A required lollms-client dependency is not installed.", file=sys.stderr)
    trace_exception(e)
    sys.exit(1)

# --- Client Management ---
# Using a dictionary to hold the client instance to manage state in Gradio
app_state = {"client": None, "last_config": {}}

def get_client(llm_binding: str, model_name: str, api_key: str):
    """
    Initializes or retrieves the LollmsClient instance.
    Re-initializes if the configuration has changed.
    """
    global app_state
    
    current_config = {
        "binding_name": llm_binding,
        "model_name": model_name,
        "api_key": api_key,
    }

    # If client exists and config hasn't changed, return existing client
    if app_state["client"] and app_state["last_config"] == current_config:
        return app_state["client"]

    ASCIIColors.cyan("--- Initializing or Re-initializing LollmsClient ---")
    
    # Close existing client if it exists
    if app_state["client"]:
        try:
            app_state["client"].close()
        except Exception as ex:
            ASCIIColors.warning(f"Could not close previous client: {ex}")

    path_to_server_project = ROOT_PATH / "arxiv-mcp-server"
    full_server_script_path = (path_to_server_project / "arxiv_mcp_server/server.py").resolve()
    if not full_server_script_path.exists():
        raise FileNotFoundError(f"Server script not found at {full_server_script_path}")

    mcp_config = {
        "initial_servers": {
            "arxiv_manager": {
                "command": [sys.executable, str(full_server_script_path)],
                "args": ["--transport", "stdio"],
                "cwd": str(path_to_server_project.resolve()),
            }
        }
    }
    
    # Prepare binding credentials
    credentials = {"personal_api_key": api_key} if api_key else {}

    try:
        client = LollmsClient(
            binding_name=llm_binding,
            model_name=model_name,
            mcp_binding_name="standard_mcp",
            mcp_binding_config=mcp_config,
        )
        app_state["client"] = client
        app_state["last_config"] = current_config
        ASCIIColors.green("--- LollmsClient Initialized Successfully ---")
        return client
    except Exception as e:
        ASCIIColors.error("Failed to initialize LollmsClient.")
        trace_exception(e)
        raise gr.Error(f"Failed to initialize LLM Client. Please check your settings and console logs. Error: {e}")


def parse_markdown_table_to_df(md_text: str) -> Optional[pd.DataFrame]:
    """Tries to parse a Markdown table from text into a Pandas DataFrame."""
    try:
        # Find table headers and rows
        matches = re.findall(r'\|(.+?)\|\s*\n\|[-| :]+?\|\s*\n((?:\|.+?\|\s*\n?)*)', md_text)
        if not matches:
            return None

        header_line, body_lines_str = matches[0]
        headers = [h.strip() for h in header_line.split('|') if h.strip()]
        
        body_lines = body_lines_str.strip().split('\n')
        data = []
        for line in body_lines:
            if line.strip():
                row_data = [d.strip() for d in line.split('|')][1:-1] # Get content between pipes
                if len(row_data) == len(headers):
                    data.append(row_data)
        
        if not data:
            return None

        return pd.DataFrame(data, columns=headers)
    except Exception:
        # If any parsing error occurs, just return None
        return None


def build_bibliography(prompt: str, llm_binding: str, model_name: str, api_key: str, max_steps: int):
    """
    The core generator function for the Gradio interface.
    """
    yield "Initializing...", "", gr.update(visible=False), gr.update(visible=False)
    
    try:
        client = get_client(llm_binding, model_name, api_key)
    except gr.Error as e:
        yield "Error", str(e), gr.update(visible=False), gr.update(visible=False)
        return

    thinking_log = ""
    def get_timestamp():
        return datetime.now().strftime("%H:%M:%S")

    def streaming_callback(chunk: str, msg_type: MSG_TYPE, metadata: dict = None, history: list = None) -> bool:
        nonlocal thinking_log
        log_entry = ""
        prefix = f"`{get_timestamp()}`"

        if msg_type == MSG_TYPE.MSG_TYPE_CHUNK and metadata and metadata.get("source") == "llm_binding":
            log_entry = f"{prefix} **🧠 LLM Thought:** {chunk}"
        elif msg_type == MSG_TYPE.MSG_TYPE_TOOL_CALL:
            log_entry = (
                f"{prefix} **🛠️ Tool Call:** `{metadata.get('tool_name')}`\n"
                f"```json\n{json.dumps(metadata.get('parameters', {}), indent=2)}\n```"
            )
        elif msg_type == MSG_TYPE.MSG_TYPE_TOOL_OUTPUT:
            try:
                pretty_chunk = json.dumps(json.loads(chunk), indent=2)
            except:
                pretty_chunk = chunk
            log_entry = f"{prefix} **📄 Tool Output:**\n```json\n{pretty_chunk}\n```"
        elif msg_type == MSG_TYPE.MSG_TYPE_EXCEPTION:
            log_entry = f"{prefix} **🔥 ERROR:**\n```\n{chunk}\n```"

        if log_entry:
            thinking_log += log_entry + "\n\n---\n\n"
        
        yield "Researching...", thinking_log, gr.update(visible=False), gr.update(visible=False)
        return True

    thinking_log = f"`{get_timestamp()}` **🚀 Starting request...**\n\n---\n\n"
    yield "Researching...", thinking_log, gr.update(visible=False), gr.update(visible=False)

    try:
        final_response = client.generate_with_mcp(
            prompt=prompt,
            streaming_callback=streaming_callback,
            max_tool_calls=int(max_steps)
        )
        final_answer = final_response.get("output", "No final text answer was generated.")
        
        thinking_log += f"`{get_timestamp()}` **✅ Process Finished.**"
        
        # Try to parse the final answer as a table
        df = parse_markdown_table_to_df(final_answer)
        if df is not None:
            # If successful, show the DataFrame and hide the Markdown
            yield "Finished", thinking_log, gr.update(visible=False), gr.update(value=df, visible=True)
        else:
            # Otherwise, show the Markdown answer
            yield "Finished", thinking_log, gr.update(value=final_answer, visible=True), gr.update(visible=False)

    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        trace_exception(e)
        thinking_log += f"`{get_timestamp()}` **🔥 FATAL ERROR:**\n```\n{error_message}\n```"
        yield "Error", thinking_log, gr.update(value=error_message, visible=True), gr.update(visible=False)


# --- Gradio UI Definition ---
with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue", secondary_hue="sky"), title="Visual Bibliography Builder") as demo:
    gr.Markdown("# 📚 Visual Bibliography Builder")
    gr.Markdown("### An AI-powered research assistant using the Arxiv toolkit. Watch the AI think, use tools, and build knowledge in real-time.")

    with gr.Accordion("⚙️ AI & Model Settings", open=False):
        with gr.Row():
            llm_binding = gr.Dropdown(["ollama", "openai", "huggingface"], value="ollama", label="LLM Binding")
            model_name = gr.Textbox(label="Model Name", value="mistral-nemo:latest", placeholder="e.g., mistral-nemo:latest, gpt-4-turbo, etc.")
            api_key = gr.Textbox(label="API Key (if required)", type="password", placeholder="Enter your OpenAI or Hugging Face API key")
    
    with gr.Row():
        with gr.Column(scale=1):
            with gr.Group(): # <-- CHANGED from gr.Box
                gr.Markdown("#### 📝 Your Research Request")
                prompt_input = gr.Textbox(
                    label="Prompt",
                    show_label=False,
                    placeholder="Enter your research goal here...",
                    lines=5
                )
                max_steps = gr.Slider(minimum=1, maximum=20, value=10, step=1, label="Max AI Steps (Tool Calls)")
                with gr.Row():
                    submit_button = gr.Button("Start Research", variant="primary", scale=3)
                    status_output = gr.Textbox(label="Status", value="Idle", interactive=False, scale=1)
            
            with gr.Group(): # <-- CHANGED from gr.Box
                gr.Markdown("#### ✨ Example Prompts & Tips")
                gr.Markdown(
                    "* **Be specific:** Tell the AI exactly what to name databases.\n"
                    "* **Chain commands:** You can ask it to perform multiple steps in one prompt.\n"
                    "* **Request formatting:** Ask for a 'table' or a 'summary' in your final step."
                )
                gr.Examples(
                    [
                        "Create a new database called 'llm_agents_2023'. Then, find up to 5 papers from 2023 about LLM-based autonomous agents and add them to it.",
                        "Search for papers by the author 'Yann LeCun' and add the top 3 results to a new database called 'lecun_papers'. After that, tell me the contents of that database.",
                        "Find papers on 'Mixture of Experts' from 2023 and 2024. Then, for the top result, fetch its abstract.",
                        "Please search for recent papers comparing LLM benchmark results like MMLU and HumanEval. Summarize your findings in a Markdown table."
                    ],
                    inputs=[prompt_input]
                )

        with gr.Column(scale=2):
            with gr.Accordion("🤖 AI's Thinking Process Log", open=True):
                thinking_process_output = gr.Markdown("Awaiting request...")
            
            with gr.Group(): # <-- CHANGED from gr.Box
                gr.Markdown("#### 💡 Final Result")
                final_answer_markdown = gr.Markdown(visible=False)
                final_answer_df = gr.DataFrame(visible=False)

    submit_button.click(
        fn=build_bibliography,
        inputs=[prompt_input, llm_binding, model_name, api_key, max_steps],
        outputs=[status_output, thinking_process_output, final_answer_markdown, final_answer_df]
    )

if __name__ == "__main__":
    demo.launch()