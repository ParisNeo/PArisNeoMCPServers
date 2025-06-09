# PArisNeoMCPServers/matplotlib-mcp-server/matplotlib_mcp_server/server.py
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from ascii_colors import ASCIIColors

# Load environment variables
env_path_parent = Path(__file__).resolve().parent.parent / '.env'
env_path_project_root = Path('.') / '.env' # If running from project root

if env_path_parent.exists():
    ASCIIColors.cyan(f"Loading environment variables from: {env_path_parent.resolve()}")
    load_dotenv(dotenv_path=env_path_parent)
elif env_path_project_root.exists():
    ASCIIColors.cyan(f"Loading environment variables from: {env_path_project_root.resolve()}")
    load_dotenv(dotenv_path=env_path_project_root)
else:
    ASCIIColors.yellow(".env file not found in parent or current directory. Relying on existing environment variables.")

try:
    from . import matplotlib_wrapper
except ImportError:
    # Fallback for direct script execution for testing
    import matplotlib_wrapper

# Initialize FastMCP Server
mcp = FastMCP(
    name="MatplotlibMCPServer",
    description="Provides data visualization capabilities by generating plots using Matplotlib.",
    version="0.1.0"
)

# Define the MCP Tool for Matplotlib Plot Generation
@mcp.tool(
    name="generate_plot",
    description=(
        "Generates a plot (e.g., line, bar, scatter, pie, histogram) from provided data "
        "and returns it as a base64 encoded image."
    )
)
async def generate_matplotlib_plot(
    plot_type: matplotlib_wrapper.SUPPORTED_PLOT_TYPES,
    data: Dict[str, Any],
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    output_format: Optional[matplotlib_wrapper.SUPPORTED_FORMATS] = None, # Default handled by wrapper
    dpi: Optional[int] = None, # Default handled by wrapper
    grid: bool = False,
    legend_loc: Optional[str] = None,
    plot_kwargs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    MCP tool endpoint for generating Matplotlib plots.
    Data structure examples:
    - line: {"x": [...], "y_values": [[...], [...]], "labels": ["series1", "series2"]} OR {"x": [...], "y": [...]}
    - bar: {"categories": [...], "values": [...]} OR {"categories": [...], "series": [{"name": "S1", "values": [...]}, ...]}
    - scatter: {"x": [...], "y": [...], "sizes": (optional)[...], "colors": (optional)[...]}
    - pie: {"labels": [...], "sizes": [...], "explode": (optional)[...]}
    - histogram: {"values": [...], "bins": (optional)int_or_list}
    """
    ASCIIColors.info(
        f"MCP Tool 'generate_plot' called with plot_type: '{plot_type}', title: '{title or 'Untitled'}'"
    )

    if not plot_type:
        return {"error": "Parameter 'plot_type' is required."}
    if not data:
        return {"error": "Parameter 'data' is required and cannot be empty."}

    # Use wrapper's defaults if optional parameters are None
    current_output_format = output_format or matplotlib_wrapper.DEFAULT_FORMAT
    current_dpi = dpi or matplotlib_wrapper.DEFAULT_DPI

    plot_result = await matplotlib_wrapper.generate_plot(
        plot_type=plot_type,
        data=data,
        title=title,
        xlabel=xlabel,
        ylabel=ylabel,
        output_format=current_output_format,
        dpi=current_dpi,
        grid=grid,
        legend_loc=legend_loc,
        plot_kwargs=plot_kwargs or {}
    )

    if "error" in plot_result:
        ASCIIColors.error(f"Error from matplotlib_wrapper: {plot_result['error']}")
        return {"status": "error", "message": plot_result["error"]}
    
    ASCIIColors.green(f"Plot generation successful. Returning base64 image ({plot_result['format']}).")
    # Return structure should be suitable for MCP client processing
    return {
        "status": "success",
        "image_base64": plot_result.get("image_base64"),
        "format": plot_result.get("format"),
        "plot_type_used": plot_result.get("plot_type_used"),
        "title_used": plot_result.get("title_used"),
        "message": plot_result.get("message", "Plot generated successfully.")
    }

@mcp.tool(
    name="get_supported_plot_info",
    description="Returns a list of supported plot types and output formats."
)
async def get_supported_plot_info() -> Dict[str, Any]:
    """
    MCP tool endpoint to get information about supported plot types and formats.
    """
    ASCIIColors.info("MCP Tool 'get_supported_plot_info' called.")
    return {
        "status": "success",
        "supported_plot_types": matplotlib_wrapper.get_supported_plot_types(),
        "supported_output_formats": matplotlib_wrapper.get_supported_formats(),
        "default_output_format": matplotlib_wrapper.DEFAULT_FORMAT,
        "default_dpi": matplotlib_wrapper.DEFAULT_DPI
    }

# --- Main CLI Entry Point ---
def main_cli():
    ASCIIColors.cyan("Starting Matplotlib MCP Server...")
    ASCIIColors.cyan("MCP server will list 'generate_plot' and 'get_supported_plot_info' tools upon connection.")
    ASCIIColors.cyan("Listening for MCP messages on stdio...")
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main_cli()