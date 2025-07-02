# Arxiv MCP Server

An MCP (Model Context Protocol) server that integrates with the Arxiv API to search for, download, and manage academic papers in local databases. This allows LLM clients to build and query collections of scientific literature.

## Features

- Exposes Arxiv search and paper management as a suite of MCP tools.
- **Database Management**:
    - `list_arxiv_databases`: See all your local paper collections.
    - `create_arxiv_database`: Start a new collection for a specific topic.
- **Population**:
    - `search_and_populate_database`: Find papers on Arxiv with a query and download the PDFs and metadata into a chosen database. It intelligently skips papers that are already downloaded.
- **Analysis & Retrieval**:
    - `get_database_contents`: Get a full list of all papers stored in a database.
    - `get_paper_abstract`: Quickly retrieve the abstract for a specific paper in a database.
- **Configuration**:
    - The root directory for all databases can be configured via an `.env` file.

## Prerequisites

- Python 3.9+
- `uv` (for running with `uvx` or `uv run`). Install with `pip install uv`.
- (Optional but recommended) A virtual environment.

## Installation & Setup

1.  **Navigate to the server directory:**
    From the root of the `PArisNeoMCPServers` repository, go to:
    ```bash
    cd arxiv-mcp-server
    ```

2.  **Create a `.env` file (Optional):**
    You can customize where the paper databases are stored. Copy the example to create your own configuration:
    ```bash
    cp .env.example .env
    ```
    Then edit `.env` if you want to change the default path:
    ```env
    # The root directory where all Arxiv databases (subfolders) will be stored.
    # Default is PArisNeoMCPServers/mcp_example_outputs/arxiv_databases
    ARXIV_DATABASES_ROOT="path/to/my/arxiv_collections"
    ```

3.  **Install dependencies:**
    It's highly recommended to use a Python virtual environment.
    ```bash
    # From the PArisNeoMCPServers/arxiv-mcp-server directory
    uv venv .venv # Create virtual environment
    source .venv/bin/activate # Or .venv\Scripts\activate on Windows
    uv pip install -e . # Install project in editable mode with its dependencies
    ```

## Running the Server

### With `uv run` (Recommended for development/local use)

From the root of the `arxiv-mcp-server` project directory (after `uv pip install -e .`):
```bash
uv run arxiv-mcp-server
```
This command will execute the `arxiv-mcp-server` script defined in `pyproject.toml`.

### Directly with Python (for development)

From the root of the `arxiv-mcp-server` project directory:
```bash
# Ensure dependencies are installed in the active environment
# (e.g., after 'source .venv/bin/activate')
python arxiv_mcp_server/server.py
```

## Available MCP Tools

### 1. `list_arxiv_databases`
- **Description**: Lists all available local Arxiv paper databases.
- **Parameters**: None.
- **Returns**: A JSON object with a list of database names.
    ```json
    {
      "databases": ["ai_safety", "quantum_computing"],
      "root_path": "/path/to/PArisNeoMCPServers/mcp_example_outputs/arxiv_databases"
    }
    ```

### 2. `create_arxiv_database`
- **Description**: Creates a new, empty local database to store Arxiv papers.
- **Parameters**:
    - `database_name` (string, required): The name for the new database (e.g., "transformer_models").
- **Returns**: A success or error message.

### 3. `search_and_populate_database`
- **Description**: Searches Arxiv for a query, downloads new papers, and adds them to a specified local database.
- **Parameters**:
    - `database_name` (string, required): The target database.
    - `query` (string, required): The Arxiv search query (e.g., `"au:Yann LeCun"`, `"ti:attention is all you need"`).
    - `max_results` (integer, optional): Maximum number of results to fetch from Arxiv. Defaults to 5, max 25.
- **Returns**: A summary of the operation, including newly downloaded papers.
    ```json
    {
        "status": "success",
        "downloaded_count": 1,
        "skipped_count": 4,
        "new_papers": [
            {
                "entry_id": "2305.12345v1",
                "title": "A new paper on Large Language Models",
                "authors": ["Jane Doe", "John Smith"],
                "summary": "This paper explores...",
                "published": "2023-05-20T18:00:00+00:00",
                "pdf_url": "http://arxiv.org/pdf/2305.12345v1",
                "local_path": "/path/to/db/2305.12345_v1.pdf"
            }
        ],
        "message": "Search complete. Downloaded 1 new papers."
    }
    ```

### 4. `get_database_contents`
- **Description**: Retrieves a list of all papers and their metadata from a specified local database.
- **Parameters**:
    - `database_name` (string, required): The database to inspect.
- **Returns**: A list of all paper metadata objects within that database.
    ```json
    {
      "status": "success",
      "database": "ai_safety",
      "paper_count": 12,
      "papers": [ { "entry_id": "...", ... }, { "entry_id": "...", ... } ]
    }
    ```

### 5. `get_paper_abstract`
- **Description**: Gets the title and abstract (summary) for a specific paper ID from a local database.
- **Parameters**:
    - `database_name` (string, required): The database where the paper is stored.
    - `paper_id` (string, required): The Arxiv entry ID (e.g., `"2305.12345v1"` or just `"2305.12345"`).
- **Returns**: The paper's title and abstract.
    ```json
    {
        "status": "success",
        "paper_id": "2305.12345v1",
        "title": "A new paper on Large Language Models",
        "summary": "This paper explores..."
    }
    ```
## Development

- The core Arxiv interaction logic is in `arxiv_mcp_server/arxiv_wrapper.py`.
- The MCP server and tool definitions are in `arxiv_mcp_server/server.py`.
- Test with the `run_arxiv_mcp_example.py` script located in the parent `PArisNeoMCPServers` directory.