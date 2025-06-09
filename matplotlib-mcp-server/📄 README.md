# Matplotlib MCP Server

An MCP (Model Context Protocol) server that leverages the Matplotlib library to generate various types of plots and charts from data. This allows LLM clients connected via MCP to request and receive data visualizations as images.

## Features

- Exposes Matplotlib plotting capabilities as MCP tools:
    - `generate_plot`: Creates plots like line, bar, scatter, pie, and histogram.
    - `get_supported_plot_info`: Lists available plot types and output formats.
- Returns plots as base64 encoded image strings.
- Configurable output format (PNG, JPG, SVG, etc.) and DPI.
- Supports common plot customizations (title, labels, grid, legend).
- Designed to be run with `uvx`, `uv run`, or as a standalone Python MCP server using `stdio`.

## Prerequisites

- Python 3.9+
- `uv` (for running with `uvx` or `uv run`). Install with `pip install uv`.
- (Optional but recommended) A virtual environment.

## Installation & Setup

1.  **Clone the PArisNeoMCPServers repository (if you haven't already):**
    ```bash
    git clone <repository_url>
    cd PArisNeoMCPServers/matplotlib-mcp-server
    ```
    Or, if you have the files locally, navigate to the `matplotlib-mcp-server` directory.

2.  **Create a `.env` file (Optional):**
    You can create a `.env` file in the root of the `matplotlib-mcp-server` project directory to customize default behavior. Copy `.env.example` to `.env`:
    ```bash
    cp .env.example .env
    ```
    Then edit `.env` if needed:
    ```env
    # Optional: Default Dots Per Inch for generated plots.
    # MPL_DEFAULT_DPI=100

    # Optional: Default image format for generated plots (e.g., png, jpg, svg).
    # MPL_DEFAULT_FORMAT="png"
    ```
    If `.env` is not present or these variables are not set, the server uses internal defaults (DPI: 100, Format: "png").

3.  **Install dependencies:**
    It's highly recommended to use a Python virtual environment.
    ```bash
    # From the PArisNeoMCPServers/matplotlib-mcp-server directory
    uv venv .venv # Create virtual environment
    source .venv/bin/activate # Or .venv\Scripts\activate on Windows
    uv pip install -e . # Install project in editable mode with its dependencies
    ```

## Running the Server

### With `uv run` (Recommended for development/local use)

From the root of the `matplotlib-mcp-server` project directory (after `uv pip install -e .`):
```bash
uv run matplotlib-mcp-server
```
This command will execute the `matplotlib-mcp-server` script defined in `pyproject.toml`.

### With `uvx` (For use with clients like LollmsClient)

Configure your MCP client (like `LollmsClient`'s `StandardMCPBinding`) to use:
- `command`: `"uvx"`
- `args`: `["matplotlib-mcp-server"]`
- `cwd`: (Should be set to the `matplotlib-mcp-server` directory if `.env` is to be loaded from there by the server itself, or ensure environment variables are passed through by the client).

*Note: For `uvx` to reliably find and run a local, unpublished project, you typically need to have installed it (e.g., `uv pip install -e .`) in a Python environment that `uvx` is configured to use or can discover.*

### Directly with Python (for development)

From the root of the `matplotlib-mcp-server` project directory:
```bash
# Ensure dependencies are installed in the active environment
# (e.g., after 'source .venv/bin/activate')
python matplotlib_mcp_server/server.py
```

## Available MCP Tools

### 1. `generate_plot`

-   **Description**: Generates a plot (e.g., line, bar, scatter, pie, histogram) from provided data and returns it as a base64 encoded image.
-   **Parameters**:
    -   `plot_type` (string, required): The type of plot to generate. Supported: `"line"`, `"bar"`, `"scatter"`, `"pie"`, `"histogram"`.
    -   `data` (object, required): A JSON object containing the data for the plot. The structure depends on `plot_type`:
        -   **line**:
            -   Single series: `{"x": [x1, x2,...], "y": [y1, y2,...]}`
            -   Multiple series: `{"x": [x1, x2,...], "y_values": [[s1y1, s1y2,...], [s2y1, s2y2,...]], "labels": ["Series A", "Series B"]}`
        -   **bar**:
            -   Simple: `{"categories": ["A", "B", ...], "values": [v1, v2, ...]}`
            -   Grouped: `{"categories": ["G1", "G2", ...], "series": [{"name": "S1", "values": [v1, v2, ...]}, {"name": "S2", "values": [v3, v4, ...]}]}`
        -   **scatter**: `{"x": [x1, x2,...], "y": [y1, y2,...], "sizes": [optional_s1, s2,...], "colors": [optional_c1, c2,...]}`
        -   **pie**: `{"labels": ["L1", "L2", ...], "sizes": [s1, s2, ...], "explode": [optional_e1, e2,...]}` (e.g., `[0, 0.1, 0]`)
        -   **histogram**: `{"values": [v1, v2, v2, v3,...], "bins": optional_int_or_list}` (e.g., `10` or `[0, 5, 10, 15]`)
    -   `title` (string, optional): Title for the plot.
    -   `xlabel` (string, optional): Label for the X-axis.
    -   `ylabel` (string, optional): Label for the Y-axis.
    -   `output_format` (string, optional): Desired image format (e.g., `"png"`, `"jpeg"`, `"svg"`, `"pdf"`). Defaults to server's `MPL_DEFAULT_FORMAT` or `"png"`.
    -   `dpi` (integer, optional): Dots Per Inch for the image. Defaults to server's `MPL_DEFAULT_DPI` or `100`.
    -   `grid` (boolean, optional): Whether to display a grid. Defaults to `false`.
    -   `legend_loc` (string, optional): Position for the legend (e.g., `"best"`, `"upper right"`). Applicable for plots with multiple series/labels.
    -   `plot_kwargs` (object, optional): Additional keyword arguments to pass directly to the underlying Matplotlib plot function (e.g., `{"color": "red"}` for a line plot, or `{"edgecolor": "black"}` for a histogram).
-   **Example Tool Call (JSON for MCP client):**
    ```json
    {
      "tool_name": "generate_plot",
      "parameters": {
        "plot_type": "line",
        "data": {
          "x": [1, 2, 3, 4, 5],
          "y_values": [
            [10, 12, 9, 15, 14],
            [5, 8, 11, 7, 10]
          ],
          "labels": ["Metric A", "Metric B"]
        },
        "title": "Performance Metrics Over Time",
        "xlabel": "Time (Days)",
        "ylabel": "Value",
        "output_format": "png",
        "grid": true,
        "legend_loc": "upper left"
      }
    }
    ```
-   **Returns**: A JSON object containing:
    -   `status` (string): `"success"` or `"error"`.
    -   `image_base64` (string, on success): Base64 encoded image data.
    -   `format` (string, on success): The image format used (e.g., `"png"`).
    -   `plot_type_used` (string, on success): The type of plot generated.
    -   `title_used` (string, on success): The title applied to the plot.
    -   `message` (string): A success or error message.
-   **Example Successful Return (JSON from MCP tool):**
    ```json
    {
      "status": "success",
      "image_base64": "iVBORw0KGgoAAAANSUhEUgAAA...",
      "format": "png",
      "plot_type_used": "line",
      "title_used": "Performance Metrics Over Time",
      "message": "Plot 'line' generated successfully."
    }
    ```
-   **Example Error Return (JSON from MCP tool):**
    ```json
    {
      "status": "error",
      "message": "Invalid data structure for line: 'x' and 'y' must be lists of equal length."
    }
    ```

### 2. `get_supported_plot_info`

-   **Description**: Returns a list of supported plot types, output formats, and current server defaults.
-   **Parameters**: None.
-   **Example Tool Call (JSON for MCP client):**
    ```json
    {
      "tool_name": "get_supported_plot_info",
      "parameters": {}
    }
    ```
-   **Returns**: A JSON object containing:
    -   `status` (string): `"success"`.
    -   `supported_plot_types` (list of strings): e.g., `["line", "bar", "scatter", "pie", "histogram"]`.
    -   `supported_output_formats` (list of strings): e.g., `["png", "jpeg", "jpg", "svg", "pdf"]`.
    -   `default_output_format` (string): e.g., `"png"`.
    -   `default_dpi` (integer): e.g., `100`.
-   **Example Successful Return (JSON from MCP tool):**
    ```json
    {
        "status": "success",
        "supported_plot_types": ["line", "bar", "scatter", "pie", "histogram"],
        "supported_output_formats": ["png", "jpeg", "jpg", "svg", "pdf"],
        "default_output_format": "png",
        "default_dpi": 100
    }
    ```

## Development

-   Ensure `matplotlib` library is installed.
-   The core plotting logic is in `matplotlib_mcp_server/matplotlib_wrapper.py`.
-   The MCP server and tool definitions are in `matplotlib_mcp_server/server.py`.
-   Test with `run_matplotlib_mcp_example.py` located in the parent `PArisNeoMCPServers` directory (to be created).