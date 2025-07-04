# Example MCP Server

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A boilerplate MCP (Model Context Protocol) server designed to be a robust starting point for integrating custom tools and APIs with LLM clients. This example provides a foundation for building servers that can run in both public and secure, authenticated modes.

This version includes a key enhancement: **optional integration with an external authentication server (like `lollms-chat`)** to secure your tools.

## Key Features

This boilerplate isn't just a simple script; it's a fully-featured starting point providing:

-   **Flexible Configuration**: Configure the server via command-line arguments, `.env` files, or environment variables.
-   **Optional Authentication**: Secure your tools by integrating with an external OAuth2/OIDC-style authentication server. The server can validate Bearer tokens before executing a tool.
-   **Multiple Transport Protocols**: Supports `stdio`, Server-Sent Events (`sse`), and a production-ready `streamable-http` transport out of the box.
-   **Structured Logging**: Uses Python's standard `logging` module, configurable with a `--log-level` flag.
-   **Simple Installation**: Packaged with `pyproject.toml`, making installation with `pip` a breeze.
-   **Easy to Extend**: Add new tools simply by using the `@mcp.tool` decorator.

## Prerequisites

-   [Git](https://git-scm.com/)
-   Python 3.9 or higher
-   An instance of [lollms-chat](https://github.com/ParisNeo/lollms-webui) (for the authentication example)

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

    # Authentication mode: 'none', 'lollms_chat_auth', or 'bearer'
    MCP_AUTHENTICATION=none

    # URL for the authentication server (only used if authentication is not 'none')
    # This should point to your lollms-chat instance or other auth provider.
    AUTHORIZATION_SERVER_URL=http://localhost:9642
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

### Running without Authentication

This is the simplest mode, where all tools are publicly accessible.

```bash
# This command uses the 'none' authentication mode by default
example-mcp-server
```
You should see output indicating the server has started:
```
INFO: Starting Example MCP Server...
INFO: Configuration: transport=streamable-http, host=localhost, port=9624, log_level=INFO
INFO: Listening for MCP messages on streamable-http...
INFO:     Uvicorn running on http://localhost:9624 (Press CTRL+C to quit)
```

### Running with Authentication

In this mode, the server protects all tools and requires a valid Bearer token for access.

```bash
# Run with lollms_chat authentication enabled
example-mcp-server --authentication lollms_chat_auth
```
**Note:** This mode requires an authorization server (like `lollms-chat`) running at the `AUTHORIZATION_SERVER_URL`. The MCP server will contact it to validate tokens.

## 🚀 Usage Examples

An MCP client (like an LLM agent) can communicate with this server using JSON-RPC 2.0 formatted messages over HTTP.

### Unauthenticated Request

A client can send an HTTP POST request to `http://localhost:9624/` with the following JSON body:
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

### Authenticated Request with `curl`

When the server is running with authentication enabled, the client **must** provide a valid Bearer token in the `Authorization` header.

```bash
curl -X POST http://localhost:9624/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_access_token_here" \
  -d '{
    "jsonrpc": "2.0",
    "method": "hello",
    "params": { "name": "Authenticated User" },
    "id": 2
}'
```
---
## 🧩 Integrating with lollms-chat

The primary goal of this server is to be used within `lollms-chat`. The `lollms_chat_auth` mode creates a seamless and secure connection where `lollms-chat` itself acts as both the **client** and the **authentication server**.

Here’s how to set it up:

**Step 1: Run the MCP Server with Authentication**

Open a terminal, activate your virtual environment, and run the server, ensuring you enable authentication.

```bash
example-mcp-server --authentication lollms_chat_auth
```
Keep this terminal running.

**Step 2: Configure lollms-chat**

1.  Open your `lollms-chat` web UI.
2.  Navigate to `Settings` > `MCP Servers`.
3.  Click `Add new server`.
4.  Fill in the details for your new MCP server:
    -   **Name:** `Example Tools Server` (or any name you prefer)
    -   **URL:** `http://localhost:9624/` (must match the host and port of your running server)
    -   **Authentication:** Select `lollms_chat_auth` from the dropdown list.
5.  Click the `Save` button and restart `lollms-chat` to apply the changes.

**Step 3: Use the Tool**

That's it! Now, when you chat with your LLM, it will be aware of the new `hello` tool. You can ask it something like:
> "Use the hello tool to greet the lollms-chat user."

`lollms-chat` will automatically handle the authentication behind the scenes.

### How It Works: The Authentication Loop

When you use the `lollms_chat_auth` method, a clever, self-contained authentication process occurs:

1.  **Request with Token**: `lollms-chat` (the client) sends a request to your MCP server. It automatically generates a token and includes it in the `Authorization` header.
2.  **Token Introspection**: Your MCP server receives the request, sees the token, and sends it back to `lollms-chat`'s `/api/auth/introspect` endpoint for validation.
3.  **Validation**: `lollms-chat` (the auth server) checks if the token it just issued is valid. If so, it returns a success message with user info.
4.  **Execution**: Your MCP server receives the confirmation and executes the tool.

```
+--------------------------+        1. Call hello tool         +-----------------------+
|                          |    (with Authorization token)     |                       |
|   lollms-chat (Client)   +---------------------------------->|  Example MCP Server   |
|                          |                                   |                       |
+------------^-------------+        4. Return result           +-----------+-----------+
             |              <----------------------------------            |
             |                                                             | 2. Introspect Token
             |                                                             |
+------------+-------------+        3. Token is valid          +-----------v-----------+
|                          |   (returns user information)      |                       |
| lollms-chat (Auth Server)|<----------------------------------+   lollms-chat API   |
|  (/api/auth/introspect)  |                                   | (/api/auth/introspect)|
+--------------------------+                                   +-----------------------+
```
This closed-loop system ensures that only your `lollms-chat` instance can access the tools on your MCP server, providing robust security with minimal configuration.

---

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