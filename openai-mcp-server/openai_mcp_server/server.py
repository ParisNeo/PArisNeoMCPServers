# openai-mcp-server/openai_mcp_server/server.py
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any, Literal
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from ascii_colors import ASCIIColors, trace_exception




try:
    from . import openai_wrapper 
except ImportError:
    import openai_wrapper


from typing import Dict, Any, Optional
import argparse  

def parse_args():
    # Initialize parser
    parser = argparse.ArgumentParser(description="Server configuration")

    # Add arguments
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Hostname or IP address (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9624,
        help="Port number (1-65535)"
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    # New transport argument
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse", "streamable-http"],
        default="streamable-http",
        help="Transport protocol: stdio, sse, or streamable-http"
    )

    # Parse arguments
    args = parser.parse_args()

    # Validate port range
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
    ASCIIColors.yellow(f".env file not found at {env_path}. Relying on existing environment variables or wrapper defaults.")

if not os.getenv("OPENAI_API_KEY"):
    ASCIIColors.red("FATAL: OPENAI_API_KEY is not set.")

# --- MCP Server Initialization ---
args = parse_args()
if args.transport=="streamable-http":
    mcp = FastMCP(
        name="OpenAIMCPServer",
        description="Provides OpenAI functionalities (TTS, DALL-E) via MCP.", # Updated description
        version="0.1.0",
        host=args.host,
        port=args.port,
        log_level=args.log_level
    )
    ASCIIColors.cyan(f"{mcp.settings}")
else:
    mcp = FastMCP(
        name="OpenAIMCPServer",
        description="Provides OpenAI functionalities (TTS, DALL-E) via MCP.", # Updated description
        version="0.1.0"
    )


# --- TTS Tool ---
@mcp.tool(
    name="generate_tts",
    description="Generates audio from text using OpenAI Text-to-Speech (TTS) and returns base64 encoded audio."
)
async def openai_generate_tts(
    input_text: str,
    model: Optional[Literal["tts-1", "tts-1-hd"]] = None,
    voice: Optional[Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]] = None,
    response_format: Optional[Literal["mp3", "opus", "aac", "flac"]] = "mp3",
    speed: Optional[float] = 1.0
) -> Dict[str, Any]:
    if not openai_wrapper.client: return {"error": "OpenAI client not available."}
    if not input_text: return {"error": "Input text cannot be empty."}
    ASCIIColors.info(f"MCP Tool 'generate_tts' called for text '{input_text[:30]}...'.")
    return await openai_wrapper.generate_tts_audio(
        input_text=input_text, model=model, voice=voice,
        response_format=response_format or "mp3", speed=speed if speed is not None else 1.0
    )

# --- DALL-E Image Generation Tool ---
@mcp.tool(
    name="generate_image_dalle",
    description="Generates an image using OpenAI DALL-E based on a text prompt."
)
async def openai_generate_image_dalle(
    prompt: str,
    model: Optional[Literal["dall-e-2", "dall-e-3"]] = None,
    n: Optional[int] = 1,
    quality: Optional[Literal["standard", "hd"]] = "standard",
    response_format: Optional[Literal["url", "b64_json"]] = "url",
    size: Optional[str] = None,
    style: Optional[Literal["vivid", "natural"]] = "natural"
) -> Dict[str, Any]:
    if not openai_wrapper.client: return {"error": "OpenAI client not available."}
    if not prompt: return {"error": "Prompt cannot be empty for image generation."}
    num_images = n if n is not None and n >=1 else 1
    ASCIIColors.info(f"MCP Tool 'generate_image_dalle' called for prompt '{prompt[:50]}...'.")
    return await openai_wrapper.generate_dalle_image(
        prompt=prompt, model=model, n=num_images, quality=quality or "standard",
        response_format=response_format or "url", size=size, style=style or "natural"
    )

# --- Main CLI Entry Point ---
def main_cli():
    if not os.getenv("OPENAI_API_KEY"):
        ASCIIColors.red("OpenAI API Key (OPENAI_API_KEY) not found in environment.")
    ASCIIColors.cyan(f"Starting OpenAI MCP Server. Focus: TTS & DALL-E.")
    ASCIIColors.cyan(" MCP server will list tools upon connection.")
    ASCIIColors.cyan(f"Listening for MCP messages on {mcp.run(transport=args.transport)}...")
    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main_cli()