# DuckDuckGo MCP Server

An MCP (Model Context Protocol) server that integrates with DuckDuckGo to provide web search capabilities.
This allows LLM clients connected via MCP to perform real-time web searches.

## Features

- Exposes DuckDuckGo web search as an MCP tool named `duckduckgo_search`.
- Configurable default number of results and search region via environment variables (uses `.env` file).
- Designed to be run with `uvx` or as a standalone Python MCP server using `stdio`.

## Prerequisites

- Python 3.9+
- `uv` (for running with `uvx` or `uv run`). Install with `pip install uv`.

## Installation & Setup

1.  **Clone the PArisNeoMCPServers repository (if you haven't already):**
    ```bash
    git clone <repository_url>
    cd PArisNeoMCPServers/duckduckgo-mcp-server
    ```
    Or, if you have the files locally, navigate to the `duckduckgo-mcp-server` directory.

2.  **Create a `.env` file (Optional):**
    You can create a `.env` file in the root of the `duckduckgo-mcp-server` project directory to customize default behavior. Copy `.env.example` to `.env`:
    ```bash
    cp .env.example .env
    ```
    Then edit `.env` if needed:
    ```env
    # Default number of search results to return if not specified in the tool call.
    DDG_DEFAULT_MAX_RESULTS=3

    # Default search region if not specified in the tool call.
    # 'wt-wt' is worldwide. Other examples: 'us-en' (US English), 'de-de' (Germany German).
    DDG_DEFAULT_REGION="us-en"
    ```
    If `.env` is not present or these variables are not set, the server uses internal defaults (5 results, 'wt-wt' region).

3.  **Install dependencies:**
    It's highly recommended to use a virtual environment.
    ```bash
    # From the PArisNeoMCPServers/duckduckgo-mcp-server directory
    uv venv .venv # Create virtual environment
    source .venv/bin/activate # Or .venv\Scripts\activate on Windows
    uv pip install -e . # Install project in editable mode with its dependencies
    ```

## Running the Server

### With `uv run` (Recommended for development/local use)

From the root of the `duckduckgo-mcp-server` project directory (after `uv pip install .` or `uv pip install -e .`):
```bash
uv run duckduckgo-mcp-server
```
This command will execute the `duckduckgo-mcp-server` script defined in `pyproject.toml`.

### With `uvx` (For use with clients like LollmsClient)

Once the `duckduckgo-mcp-server` package is considered "runnable" by `uvx` (e.g., after local editable install in an environment `uvx` can access, or if published):

Configure your MCP client (like `LollmsClient`'s `StandardMCPBinding`) to use:
- `command`: `"uvx"`
- `args`: `["duckduckgo-mcp-server"]`
- `cwd`: (Should be set to the `duckduckgo-mcp-server` directory if `.env` is to be loaded from there by the server itself, or ensure environment variables are passed through by the client).

*Note: For `uvx` to reliably find and run a local, unpublished project, you typically need to have installed it (e.g., `uv pip install -e .`) in a Python environment that `uvx` is configured to use or can discover.*

### Directly with Python (for development)

From the root of the `duckduckgo-mcp-server` project directory:
```bash
# Ensure dependencies are installed in the active environment
# (e.g., after 'source .venv/bin/activate')
python duckduckgo_mcp_server/server.py
```

## Available MCP Tool

- **`duckduckgo_search`**:
    - **Description**: Performs a web search using DuckDuckGo and returns a list of results.
    - **Parameters**:
        - `query` (string, required): The search query string (e.g., "What is the weather like in Paris?").
        - `num_results` (integer, optional): The maximum number of search results to return. Defaults to server configuration (e.g., 5, or as set by `DDG_DEFAULT_MAX_RESULTS` in `.env`).
        - `region` (string, optional): The region for the search (e.g., "us-en", "wt-wt" for worldwide). Defaults to server configuration (e.g., "wt-wt", or as set by `DDG_DEFAULT_REGION` in `.env`).
        - `timelimit` (string, optional): Filter results by time. Examples: "d" (past day), "w" (past week), "m" (past month), "y" (past year). If `null` or not provided, no time filter is applied.
    - **Example Tool Call (JSON for MCP client):**
      ```json
      {
        "tool_name": "duckduckgo_search",
        "parameters": {
          "query": "latest AI research papers",
          "num_results": 3,
          "region": "us-en",
          "timelimit": "m"
        }
      }
      ```
    - **Returns**: A JSON object containing:
        - `status` (string): "success" or "error".
        - `query_used` (string): The query string that was actually used.
        - `region_used` (string): The region parameter used for the search.
        - `results` (list of objects): A list of search result items. Each item is an object with:
            - `title` (string): The title of the search result.
            - `href` (string): The URL of the search result.
            - `body` (string): A snippet or summary of the search result content.
        - `message` (string, optional): An error message if `status` is "error".
    - **Example Successful Return (JSON from MCP tool):**
      ```json
      {
        "status": "success",
        "query_used": "latest AI research papers",
        "region_used": "us-en",
        "results": [
          {
            "title": "Example AI Paper Title 1",
            "href": "https://example.com/paper1",
            "body": "This paper discusses..."
          },
          {
            "title": "Another AI Discovery",
            "href": "https://example.org/discovery",
            "body": "Researchers have found that..."
          }
        ]
      }
      ```
    - **Example Error Return (JSON from MCP tool):**
      ```json
      {
        "status": "error",
        "message": "Query parameter is required and cannot be empty.",
        "results": []
      }
      ```

## Development

- Ensure `duckduckgo-search` library is installed.
- The core search logic is in `duckduckgo_mcp_server/duckduckgo_wrapper.py`.
- The MCP server and tool definition are in `duckduckgo_mcp_server/server.py`.
- Test with `run_duckduckgo_mcp_example.py` located in the parent `PArisNeoMCPServers` directory.
