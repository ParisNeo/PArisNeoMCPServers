# OpenAI MCP Server

An MCP (Model Context Protocol) server that integrates with OpenAI APIs, allowing
LLM clients to leverage OpenAI's capabilities like GPT chat completions and
(optionally in the future) DALL-E image generation.

## Features

- Exposes OpenAI chat completion (e.g., GPT-3.5-turbo, GPT-4) as an MCP tool.
- Configurable via environment variables (uses `.env` file).
- Designed to be run with `uvx` or as a standalone Python MCP server.

## Prerequisites

- Python 3.9+
- An active OpenAI API key.
- `uv` (for running with `uvx` or `uv run`). Install with `pip install uv`.

## Installation & Setup

1.  **Clone the repository (if applicable) or create the project files as described.**

2.  **Create a `.env` file:**
    Copy `.env.example` to `.env` in the root of the `openai-mcp-server` project directory and fill in your OpenAI API key:
    ```env
    OPENAI_API_KEY="sk-your_actual_openai_api_key_xxxxxxxx"
    OPENAI_CHAT_MODEL="gpt-4-turbo-preview" # Optional: set your preferred default chat model
    ```

3.  **Install dependencies (if developing locally):**
    It's recommended to use a virtual environment.
    ```bash
    uv venv .venv # Create virtual environment
    source .venv/bin/activate # Or .venv\Scripts\activate on Windows
    uv pip install -e . # Install project in editable mode with its dependencies
    ```

## Running the Server

### With `uvx` (Recommended for use with clients like LollmsClient)

Once the `openai-mcp-server` package is published (e.g., to PyPI or a private index) or if you want to run it from a local path that `uvx` can resolve (e.g., via a git URL or local path reference if `uvx` supports it for non-PyPI packages):

You would configure your MCP client (like `LollmsClient`'s `StandardMCPBinding`) to use:
- `command`: `"uvx"`
- `args`: `["openai-mcp-server"]` (or the specific name if published differently)
- `env`: (The client should pass the `OPENAI_API_KEY` or the server should pick it up from its own `.env` when run by `uvx` if `uvx` sets the CWD correctly).

To test locally with `uvx` if you haven't published it (assuming `uvx` can run local projects if they are installable, which it can if you `uv pip install -e .` first in its target environment or if `uvx` itself builds it):
This part is a bit tricky for `uvx` with purely local, unpublished projects without some form of local "installation" step that `uvx` recognizes.

**The most straightforward way to run with `uv` for development/local use:**
From the root of the `openai-mcp-server` project directory (after `uv pip install .` or `uv pip install -e .`):
```bash
uv run openai-mcp-server
```
This command will execute the `openai-mcp-server` script defined in `pyproject.toml`.

### Directly with Python (for development)

From the root of the `openai-mcp-server` project directory:
```bash
# Ensure .env is in this directory or dependencies are installed globally
python openai_mcp_server/server.py
```

## Available MCP Tools

- **`generate_tts`**:
    - Description: Generates audio from text using OpenAI Text-to-Speech (TTS) and returns base64 encoded audio.
    - Parameters: (As before)
    - Returns: (As before)

- **`generate_image_dalle`**:
    - Description: Generates an image using OpenAI DALL-E based on a text prompt.
    - Parameters: (As before)
    - Returns: (As before)

## Configuration

The server is configured using environment variables, typically loaded from a `.env` file in the project root:

- `OPENAI_API_KEY` (Required): Your OpenAI API key.
- `OPENAI_CHAT_MODEL` (Optional): Default chat model to use (e.g., `gpt-3.5-turbo`, `gpt-4-turbo-preview`). Defaults to `gpt-3.5-turbo` if not set.

## TODO

- [ ] Add MCP tool for DALL-E image generation.
- [ ] Add MCP tool for OpenAI embeddings.
- [ ] More robust error handling and reporting via MCP.
- [ ] Implement resource endpoints if applicable (e.g., list available OpenAI models).