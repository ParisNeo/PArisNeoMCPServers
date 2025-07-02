# Example MCP Server

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A boilerplate MCP (Model Context Protocol) server designed to be a robust starting point for integrating custom tools and APIs. This example provides a foundation for building servers that allow LLM clients to interact with external services, such as searching for and managing academic papers.

## Key Features

This boilerplate isn't just a single tool; it's a fully-featured starting point providing:

-   **Flexible Configuration**: Configure the server via command-line arguments, `.env` files, or environment variables.
-   **Multiple Transport Protocols**: Supports `stdio`, Server-Sent Events (`sse`), and a production-ready `streamable-http` transport out of the box.
-   **Structured Logging**: Uses Python's standard `logging` module, configurable with a `--log-level` flag.
-   **Simple Installation**: Packaged with `pyproject.toml`, making installation with `pip` a breeze.
-   **Easy to Extend**: Add new tools simply by using the `@mcp.tool` decorator.

## Prerequisites

-   [Git](https://git-scm.com/)
-   Python 3.9 or higher

## ⚙️ Installation & Setup

Follow these steps to get the server up and running on your local machine.

**1. Clone the Repository**
```bash
git clone https://github.com/PArisNeoMCPServers/PArisNeoMCPServers.git
cd PArisNeoMCPServers/example-mcp-server
```

**2. Create and Activate a Virtual Environment**

It is highly recommended to use a virtual environment to manage project dependencies.

*   **Linux/macOS:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

*   **Windows:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

**3. Install Dependencies**

This project uses `pyproject.toml` to define its dependencies. Install them using `pip`. We recommend the `-e` (editable) flag for development, as it allows you to modify the source code without reinstalling.

```bash
pip install -e .
```

## 🔧 Configuration

The server can be configured using a `.env` file for convenience.

1.  **Create a `.env` file** by copying the example:
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file** to set your desired configuration.

    ```dotenv
    # .env
    # Server configuration
    MCP_HOST=localhost
    MCP_PORT=9624
    MCP_TRANSPORT=streamable-http
    MCP_LOG_LEVEL=INFO
    ```

**Configuration Priority:**
The server loads configuration in the following order of precedence (where 1 is highest):
1.  Command-line arguments (e.g., `--port 8000`)
2.  Environment variables (e.g., `export MCP_PORT=8000`)
3.  Values in the `.env` file
4.  Hardcoded default values in the script

## ▶️ Running the Server

Once installed, the server is available as a command-line script called `example-mcp-server`.

**To see all available options, run:**
```bash
example-mcp-server --help
```

**To run the server with the default (or `.env`) configuration:**
```bash
example-mcp-server
```
You should see output indicating the server has started:
```
INFO: Starting Example MCP Server...
INFO: Configuration: transport=streamable-http, host=localhost, port=9624, log_level=INFO
INFO: Listening for MCP messages on streamable-http...
INFO:     Uvicorn running on http://localhost:9624 (Press CTRL+C to quit)
```

**To run with a different port and transport:**
```bash
example-mcp-server --port 8001 --transport stdio
```

## 🚀 Usage Example

An MCP client (like an LLM agent) can communicate with this server using JSON-RPC 2.0 formatted messages. Here is an example of how a client would call the `hello` tool.

**Request:**
A client would send an HTTP POST request to `http://localhost:9624/` with the following JSON body:
```json
{
    "jsonrpc": "2.0",
    "method": "hello",
    "params": {
        "name": "World"
    },
    "id": 1
}
```

**Response:**
The server will respond with:
```json
{
    "jsonrpc": "2.0",
    "result": {
        "status": "success",
        "greeting": "Hello, World!"
    },
    "id": 1
}
```

## 📁 Project Structure

```
.
├── .env.example            # Example environment variables
├── pyproject.toml          # Project metadata and dependencies
├── README.md               # This file
└── example_mcp_server/
    └── server.py           # The main server application and tool definitions
```

-   **`.env.example`**: A template for your local configuration. Copy this to `.env`.
-   **`pyproject.toml`**: Defines the project, its dependencies, and the `example-mcp-server` script entry point.
-   **`example_mcp_server/server.py`**: The core logic. This is where you will add your own tools and integrations.

## License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.