# PArisNeoMCPServers

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-brightgreen.svg)](https://www.python.org/)
[![MCP Standard](https://img.shields.io/badge/MCP-Compliant-orange)](https://github.com/ParisNeo/mcp_standard) <!-- Replace with actual MCP standard link if available -->
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](CONTRIBUTING.md) <!-- Assuming a CONTRIBUTING.md will exist -->

**A curated collection of versatile and useful MCP (Model Context Protocol) servers designed to extend the capabilities of Large Language Models.**

This repository hosts a growing suite of MCP servers, each providing distinct functionalities that LLMs can leverage through the Model Context Protocol. These servers enable LLMs to interact with external tools, APIs, and information sources in a standardized way.

## What is MCP?

The Model Context Protocol (MCP) is a specification that allows Large Language Models to communicate with external tools and services. It defines a standard way for LLMs to request actions, send parameters, and receive results, effectively expanding their operational range beyond text generation. MCP servers act as bridges, exposing various capabilities as "tools" that MCP-compliant LLM clients (like [LollmsClient](https://github.com/ParisNeo/lollms-client)) can discover and utilize.

## Available MCP Servers

This collection currently includes the following MCP servers:

1.  ### 🔵 OpenAI MCP Server (`openai-mcp-server`)
    *   **Description**: Integrates with various OpenAI APIs.
    *   **Current Tools**:
        *   `generate_tts`: Text-to-Speech generation using OpenAI's TTS models (e.g., `tts-1`, `tts-1-hd`).
        *   `generate_image_dalle`: Image generation using OpenAI's DALL-E models (e.g., `dall-e-2`, `dall-e-3`).
        *   *(Chat completion tool was part of its initial design but has been removed from the server as LLM clients typically handle core chat functionalities directly. This server focuses on supplementary OpenAI services.)*
    *   **Key Features**: Base64 encoded audio/image data, configurable models, voices, image sizes, and quality.
    *   **Details**: See [`openai-mcp-server/README.md`](./openai-mcp-server/README.md)

2.  ### 🦆 DuckDuckGo MCP Server (`duckduckgo-mcp-server`)
    *   **Description**: Enables LLMs to perform anonymous web searches using the DuckDuckGo search engine.
    *   **Current Tools**:
        *   `duckduckgo_search`: Fetches search results (title, URL, snippet) based on a query.
    *   **Key Features**: Configurable number of results, search region, and time-filtering.
    *   **Details**: See [`duckduckgo-mcp-server/README.md`](./duckduckgo-mcp-server/README.md)

*(More servers planned and welcomed!)*

## Getting Started

Each MCP server is a standalone project within its own subdirectory (e.g., `openai-mcp-server/`, `duckduckgo-mcp-server/`). Please refer to the `README.md` file within each server's directory for specific installation, configuration, and usage instructions.

**General Workflow:**

1.  **Clone this repository:**
    ```bash
    git clone https://github.com/PArisNeoMCPServers/PArisNeoMCPServers.git <your_local_path>
    cd <your_local_path>
    ```
2.  **Navigate to the desired server directory:**
    ```bash
    cd openai-mcp-server # or duckduckgo-mcp-server, etc.
    ```
3.  **Follow the setup instructions** in that server's `README.md` (typically involving creating a virtual environment and installing dependencies with `uv pip install -e .`).
4.  **Run the server** as described (e.g., `uv run <server-name>` or `python <server_module>/server.py`).
5.  **Configure your MCP client** (e.g., LollmsClient) to connect to the running MCP server. Example client scripts are provided (e.g., `run_openai_mcp_example.py`, `run_duckduckgo_mcp_example.py`) in the root of this repository.

## Requirements

*   Python 3.9+
*   `uv` (recommended for environment and package management): `pip install uv`
*   Dependencies specific to each server (listed in their respective `pyproject.toml` files).

## Contributing

Contributions are highly welcome! Whether it's a new MCP server, an improvement to an existing one, documentation enhancements, or bug fixes, please feel free to:

1.  Fork the repository.
2.  Create a new branch for your feature or fix.
3.  Develop your changes.
4.  Submit a Pull Request.

Please ensure new servers follow a similar structure and include:
*   A `pyproject.toml` for packaging and dependencies.
*   A clear `README.md` with setup and usage instructions.
*   An example `.env.example` file if configuration is needed.
*   An example client script (e.g., `run_<new_server>_mcp_example.py`) in the root `PArisNeoMCPServers` directory.

*(A more formal `CONTRIBUTING.md` will be added soon.)*

## License

This project and all its sub-projects (MCP servers) are licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for more details. (You'll need to add a LICENSE file with Apache 2.0 text).

---

Happy building and extending your LLMs!