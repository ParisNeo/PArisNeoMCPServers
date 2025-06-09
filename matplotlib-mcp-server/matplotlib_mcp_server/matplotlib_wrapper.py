# PArisNeoMCPServers/matplotlib-mcp-server/matplotlib_mcp_server/matplotlib_wrapper.py
import os
import io
import base64
from typing import Dict, Any, List, Optional, Literal, Union
import matplotlib
matplotlib.use('Agg') # Use a non-interactive backend
import matplotlib.pyplot as plt
from ascii_colors import ASCIIColors, trace_exception

# Environment variable for default DPI and format
DEFAULT_DPI = int(os.getenv("MPL_DEFAULT_DPI", 100))
DEFAULT_FORMAT = os.getenv("MPL_DEFAULT_FORMAT", "png").lower() # e.g., png, jpg, svg

SUPPORTED_PLOT_TYPES = Literal["line", "bar", "scatter", "pie", "histogram"]
SUPPORTED_FORMATS = Literal["png", "jpeg", "jpg", "svg", "pdf"] # Matplotlib supported savefig formats

def _validate_data_structure(plot_type: str, data: Any) -> Optional[str]:
    """Validates the data structure for the given plot type."""
    if plot_type == "line":
        # Expects: {"x": [1, 2, 3], "y_values": [[10, 20, 15], [5, 12, 8]], "labels": ["Series A", "Series B"]}
        # Or: {"x": [1, 2, 3], "y": [10, 20, 15]} (single series)
        if not isinstance(data, dict) or ("x" not in data):
            return "For line plot, 'data' must be a dictionary with at least an 'x' key (list of x-values)."
        if "y" in data and not isinstance(data["y"], list): return "'y' must be a list of y-values."
        if "y_values" in data:
            if not isinstance(data["y_values"], list) or not all(isinstance(sublist, list) for sublist in data["y_values"]):
                return "'y_values' must be a list of lists (each sublist is a series)."
            if "labels" in data and (not isinstance(data["labels"], list) or len(data["labels"]) != len(data["y_values"])):
                return "'labels' must be a list of strings matching the number of series in 'y_values'."
            if len(data["x"]) != len(data["y_values"][0]): # Assuming all y_values sublists have same length as x
                return "Length of 'x' must match length of each series in 'y_values'."
        elif "y" in data:
            if len(data["x"]) != len(data["y"]):
                return "Length of 'x' must match length of 'y'."
        else:
            return "Line plot requires either 'y' (for single series) or 'y_values' (for multiple series) in data."

    elif plot_type == "bar":
        # Expects: {"categories": ["A", "B", "C"], "values": [10, 20, 15]}
        # Or for grouped: {"categories": ["G1", "G2"], "series": [{"name": "S1", "values": [10,12]}, {"name": "S2", "values": [5,8]}]}
        if not isinstance(data, dict): return "For bar plot, 'data' must be a dictionary."
        if "categories" not in data or "values" not in data: # Basic bar
            if "categories" not in data or "series" not in data: # Grouped bar
                 return "For bar plot, 'data' must contain 'categories' and 'values' (for simple bar) or 'categories' and 'series' (for grouped bar)."
        if "values" in data and (not isinstance(data["categories"], list) or not isinstance(data["values"], list) or len(data["categories"]) != len(data["values"])):
            return "For simple bar plot, 'categories' and 'values' must be lists of equal length."
        if "series" in data:
            if not isinstance(data["series"], list) or not all(isinstance(s, dict) and "name" in s and "values" in s for s in data["series"]):
                return "For grouped bar plot, 'series' must be a list of dicts, each with 'name' and 'values'."
            if not all(len(s["values"]) == len(data["categories"]) for s in data["series"]):
                return "For grouped bar plot, all series values must match the length of categories."


    elif plot_type == "scatter":
        # Expects: {"x": [1, 2, 3], "y": [10, 20, 15], "sizes": [optional], "colors": [optional]}
        if not isinstance(data, dict) or not all(k in data for k in ["x", "y"]):
            return "For scatter plot, 'data' must be a dictionary with 'x' and 'y' keys (lists of coordinates)."
        if not (isinstance(data["x"], list) and isinstance(data["y"], list) and len(data["x"]) == len(data["y"])):
            return "'x' and 'y' must be lists of equal length."
        if "sizes" in data and (not isinstance(data["sizes"], list) or len(data["sizes"]) != len(data["x"])):
            return "'sizes' (if provided) must be a list of the same length as 'x' and 'y'."
        if "colors" in data and (not isinstance(data["colors"], list) or len(data["colors"]) != len(data["x"])):
             return "'colors' (if provided) must be a list/array of the same length as 'x' and 'y'."


    elif plot_type == "pie":
        # Expects: {"labels": ["A", "B", "C"], "sizes": [10, 20, 15], "explode": [optional]}
        if not isinstance(data, dict) or not all(k in data for k in ["labels", "sizes"]):
            return "For pie chart, 'data' must be a dictionary with 'labels' and 'sizes' keys."
        if not (isinstance(data["labels"], list) and isinstance(data["sizes"], list) and len(data["labels"]) == len(data["sizes"])):
            return "'labels' and 'sizes' must be lists of equal length."
        if "explode" in data and (not isinstance(data["explode"], list) or len(data["explode"]) != len(data["labels"])):
            return "'explode' (if provided) must be a list of the same length as 'labels'."

    elif plot_type == "histogram":
        # Expects: {"values": [1, 2, 2, 3, 3, 3, 4], "bins": 10 (optional)}
        if not isinstance(data, dict) or "values" not in data:
            return "For histogram, 'data' must be a dictionary with a 'values' key (list of numbers)."
        if not isinstance(data["values"], list) or not all(isinstance(v, (int, float)) for v in data["values"]):
            return "'values' must be a list of numbers."
        if "bins" in data and not isinstance(data["bins"], (int, list)): # Can be int or sequence of scalars
            return "'bins' (if provided) must be an integer (number of bins) or a list of bin edges."

    return None


async def generate_plot(
    plot_type: SUPPORTED_PLOT_TYPES,
    data: Dict[str, Any],
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    output_format: SUPPORTED_FORMATS = DEFAULT_FORMAT,
    dpi: int = DEFAULT_DPI,
    grid: bool = False,
    legend_loc: Optional[str] = None, # e.g., 'upper right'
    plot_kwargs: Optional[Dict[str, Any]] = None # Additional kwargs for specific plot functions
) -> Dict[str, Any]:
    """
    Generates a plot using Matplotlib and returns it as a base64 encoded string.

    Args:
        plot_type: Type of plot (e.g., "line", "bar", "scatter", "pie", "histogram").
        data: Dictionary containing data for the plot. Structure depends on plot_type.
              - line: {"x": [...], "y_values": [[...], [...]], "labels": ["series1", "series2"]} OR {"x": [...], "y": [...]}
              - bar: {"categories": [...], "values": [...]} OR {"categories": [...], "series": [{"name": "S1", "values": [...]}, ...]}
              - scatter: {"x": [...], "y": [...], "sizes": (optional)[...], "colors": (optional)[...]}
              - pie: {"labels": [...], "sizes": [...], "explode": (optional)[...]}
              - histogram: {"values": [...], "bins": (optional)int_or_list}
        title: Title of the plot.
        xlabel: Label for the X-axis.
        ylabel: Label for the Y-axis.
        output_format: Desired output image format (e.g., "png", "jpeg", "svg").
        dpi: Dots Per Inch for the output image.
        grid: Whether to display a grid.
        legend_loc: Location of the legend, if applicable (e.g., 'best', 'upper right').
        plot_kwargs: Additional keyword arguments to pass to the specific Matplotlib plot function.

    Returns:
        A dictionary containing:
        - "image_base64" (str): Base64 encoded image string.
        - "format" (str): The image format used.
        - "plot_type_used" (str): The plot type generated.
        Or, if an error occurs:
        - "error" (str): Error message.
    """
    ASCIIColors.info(f"Matplotlib Wrapper: Generating '{plot_type}' plot titled '{title or 'Untitled'}'.")
    if not plot_kwargs: plot_kwargs = {}

    validation_error = _validate_data_structure(plot_type, data)
    if validation_error:
        ASCIIColors.error(f"Invalid data structure for {plot_type}: {validation_error}")
        return {"error": f"Invalid data structure for {plot_type}: {validation_error}"}

    if output_format not in get_supported_formats():
        ASCIIColors.error(f"Unsupported output format: {output_format}. Supported: {get_supported_formats()}")
        return {"error": f"Unsupported output format: {output_format}. Supported: {', '.join(get_supported_formats())}"}

    fig, ax = plt.subplots(dpi=dpi)
    try:
        if plot_type == "line":
            x_data = data["x"]
            if "y_values" in data: # Multiple series
                for i, y_series in enumerate(data["y_values"]):
                    label = data.get("labels", [])[i] if i < len(data.get("labels", [])) else f"Series {i+1}"
                    ax.plot(x_data, y_series, label=label, **plot_kwargs)
                if data.get("labels"): ax.legend(loc=legend_loc or 'best')
            elif "y" in data: # Single series
                ax.plot(x_data, data["y"], **plot_kwargs)

        elif plot_type == "bar":
            categories = data["categories"]
            if "values" in data: # Simple bar chart
                ax.bar(categories, data["values"], **plot_kwargs)
            elif "series" in data: # Grouped bar chart
                num_series = len(data["series"])
                num_categories = len(categories)
                bar_width = 0.8 / num_series # Adjust as needed
                
                indices = range(num_categories) # should be simple numbers for positioning
                
                for i, series_item in enumerate(data["series"]):
                    # Calculate offset for each series
                    offsets = [x - (0.8 - bar_width)/2 + i * bar_width for x in indices]
                    ax.bar(offsets, series_item["values"], width=bar_width, label=series_item["name"], **plot_kwargs.get(series_item["name"], {}))
                ax.set_xticks([i + bar_width * (num_series - 1) / 2 - (0.8-bar_width*num_series)/2 for i in indices])
                ax.set_xticklabels(categories)
                ax.legend(loc=legend_loc or 'best')


        elif plot_type == "scatter":
            ax.scatter(data["x"], data["y"], s=data.get("sizes"), c=data.get("colors"), **plot_kwargs)

        elif plot_type == "pie":
            # Pie charts often look better with equal aspect ratio
            ax.axis('equal')
            ax.pie(
                data["sizes"],
                explode=data.get("explode"),
                labels=data.get("labels"),
                autopct='%1.1f%%', # Default percentage format
                startangle=data.get("startangle", 90),
                **plot_kwargs
            )

        elif plot_type == "histogram":
            ax.hist(data["values"], bins=data.get("bins", 10), **plot_kwargs) # Matplotlib's default bins=10

        else:
            return {"error": f"Unsupported plot type: {plot_type}. Supported types are: {', '.join(get_supported_plot_types())}"}

        if title: ax.set_title(title)
        if xlabel: ax.set_xlabel(xlabel)
        if ylabel: ax.set_ylabel(ylabel)
        if grid: ax.grid(True)

        # Save plot to a BytesIO object
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format=output_format, dpi=dpi, bbox_inches='tight')
        img_buffer.seek(0)
        
        img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
        img_buffer.close()

        ASCIIColors.green(f"Matplotlib Wrapper: Plot '{plot_type}' generated successfully as {output_format}.")
        return {
            "image_base64": img_base64,
            "format": output_format,
            "plot_type_used": plot_type,
            "title_used": title,
            "message": f"Plot '{plot_type}' generated successfully."
        }

    except Exception as e:
        trace_exception(e)
        ASCIIColors.error(f"Matplotlib Wrapper: Error generating plot: {str(e)}")
        return {"error": f"An unexpected error occurred during plot generation: {str(e)}"}
    finally:
        # Ensure the figure is closed to free memory
        if 'fig' in locals() and fig:
            plt.close(fig)

def get_supported_plot_types() -> List[str]:
    return list(SUPPORTED_PLOT_TYPES.__args__)

def get_supported_formats() -> List[str]:
    return list(SUPPORTED_FORMATS.__args__)


if __name__ == '__main__':
    import asyncio

    async def test_plot_generation():
        ASCIIColors.cyan("--- Testing Matplotlib Wrapper ---")
        output_dir = "test_plots_output"
        os.makedirs(output_dir, exist_ok=True)
        ASCIIColors.yellow(f"Generated test plots will be saved in ./{output_dir}/ (if successful and base64 decoded)")

        def save_b64(b64_str, filename, fmt):
            try:
                with open(os.path.join(output_dir, f"{filename}.{fmt}"), "wb") as f:
                    f.write(base64.b64decode(b64_str))
                ASCIIColors.green(f"Saved {filename}.{fmt}")
            except Exception as e:
                ASCIIColors.error(f"Failed to save {filename}.{fmt}: {e}")

        # Test 1: Line Plot (Single Series)
        ASCIIColors.magenta("\n--- Test 1: Line Plot (Single Series) ---")
        line_data_single = {"x": list(range(1, 11)), "y": [i**2 for i in range(1, 11)]}
        res_line_single = await generate_plot("line", line_data_single, "Single Line Plot", "X-axis", "Y-axis", grid=True)
        if "image_base64" in res_line_single:
            ASCIIColors.green(f"Line Plot (Single) OK. Format: {res_line_single['format']}")
            save_b64(res_line_single["image_base64"], "test_line_single", res_line_single["format"])
        else: ASCIIColors.red(f"Line Plot (Single) Error: {res_line_single.get('error')}")

        # Test 2: Line Plot (Multiple Series)
        ASCIIColors.magenta("\n--- Test 2: Line Plot (Multiple Series) ---")
        line_data_multi = {
            "x": list(range(1, 6)),
            "y_values": [[1, 4, 2, 5, 3], [3, 2, 4, 1, 5]],
            "labels": ["Alpha", "Beta"]
        }
        res_line_multi = await generate_plot("line", line_data_multi, "Multiple Lines", "Time", "Value", legend_loc="upper left")
        if "image_base64" in res_line_multi:
            ASCIIColors.green(f"Line Plot (Multi) OK. Format: {res_line_multi['format']}")
            save_b64(res_line_multi["image_base64"], "test_line_multi", res_line_multi["format"])
        else: ASCIIColors.red(f"Line Plot (Multi) Error: {res_line_multi.get('error')}")


        # Test 3: Bar Chart (Simple)
        ASCIIColors.magenta("\n--- Test 3: Bar Chart (Simple) ---")
        bar_data_simple = {"categories": ["Apples", "Bananas", "Cherries"], "values": [15, 25, 10]}
        res_bar_simple = await generate_plot("bar", bar_data_simple, "Fruit Counts", "Fruit", "Quantity")
        if "image_base64" in res_bar_simple:
            ASCIIColors.green(f"Bar Chart (Simple) OK. Format: {res_bar_simple['format']}")
            save_b64(res_bar_simple["image_base64"], "test_bar_simple", res_bar_simple["format"])
        else: ASCIIColors.red(f"Bar Chart (Simple) Error: {res_bar_simple.get('error')}")

        # Test 4: Bar Chart (Grouped)
        ASCIIColors.magenta("\n--- Test 4: Bar Chart (Grouped) ---")
        bar_data_grouped = {
            "categories": ["Q1", "Q2", "Q3"],
            "series": [
                {"name": "Product A", "values": [100, 120, 150]},
                {"name": "Product B", "values": [80, 90, 110]}
            ]
        }
        res_bar_grouped = await generate_plot("bar", bar_data_grouped, "Quarterly Sales", "Quarter", "Sales", legend_loc="best")
        if "image_base64" in res_bar_grouped:
            ASCIIColors.green(f"Bar Chart (Grouped) OK. Format: {res_bar_grouped['format']}")
            save_b64(res_bar_grouped["image_base64"], "test_bar_grouped", res_bar_grouped["format"])
        else: ASCIIColors.red(f"Bar Chart (Grouped) Error: {res_bar_grouped.get('error')}")


        # Test 5: Scatter Plot
        ASCIIColors.magenta("\n--- Test 5: Scatter Plot ---")
        scatter_data = {
            "x": [i/10 for i in range(50)],
            "y": [i/10 + 0.5 * (i % 5) for i in range(50)], # Some pattern
            "sizes": [(i % 10 + 1) * 10 for i in range(50)],
            "colors": [i / 50 for i in range(50)] # Gradient
        }
        res_scatter = await generate_plot("scatter", scatter_data, "Scatter Example", "X Val", "Y Val", plot_kwargs={"cmap": "viridis"})
        if "image_base64" in res_scatter:
            ASCIIColors.green(f"Scatter Plot OK. Format: {res_scatter['format']}")
            save_b64(res_scatter["image_base64"], "test_scatter", res_scatter["format"])
        else: ASCIIColors.red(f"Scatter Plot Error: {res_scatter.get('error')}")

        # Test 6: Pie Chart
        ASCIIColors.magenta("\n--- Test 6: Pie Chart ---")
        pie_data = {
            "labels": ["Work", "Sleep", "Eat", "Play"],
            "sizes": [8, 7, 3, 6],
            "explode": [0, 0.1, 0, 0] # Explode 'Sleep'
        }
        res_pie = await generate_plot("pie", pie_data, "Daily Activities", output_format="svg")
        if "image_base64" in res_pie:
            ASCIIColors.green(f"Pie Chart OK. Format: {res_pie['format']}")
            save_b64(res_pie["image_base64"], "test_pie", res_pie["format"])
        else: ASCIIColors.red(f"Pie Chart Error: {res_pie.get('error')}")

        # Test 7: Histogram
        ASCIIColors.magenta("\n--- Test 7: Histogram ---")
        import random
        hist_data = {"values": [random.gauss(100, 15) for _ in range(1000)], "bins": 20}
        res_hist = await generate_plot("histogram", hist_data, "Sample Distribution", "Value", "Frequency", plot_kwargs={"edgecolor": "black"})
        if "image_base64" in res_hist:
            ASCIIColors.green(f"Histogram OK. Format: {res_hist['format']}")
            save_b64(res_hist["image_base64"], "test_histogram", res_hist["format"])
        else: ASCIIColors.red(f"Histogram Error: {res_hist.get('error')}")

        # Test 8: Invalid Plot Type
        ASCIIColors.magenta("\n--- Test 8: Invalid Plot Type ---")
        res_invalid_type = await generate_plot("boxplot", {}, "Invalid Plot") # type: ignore
        if "error" in res_invalid_type:
            ASCIIColors.green(f"Invalid Plot Type Test OK. Error: {res_invalid_type['error']}")
        else: ASCIIColors.red("Invalid Plot Type Test Failed. Expected error.")

        # Test 9: Invalid Data Structure (for line plot)
        ASCIIColors.magenta("\n--- Test 9: Invalid Data Structure ---")
        invalid_line_data = {"x_values": [1,2,3], "y_vals": [4,5,6]} # Wrong keys
        res_invalid_data = await generate_plot("line", invalid_line_data, "Invalid Data")
        if "error" in res_invalid_data:
            ASCIIColors.green(f"Invalid Data Structure Test OK. Error: {res_invalid_data['error']}")
        else: ASCIIColors.red("Invalid Data Structure Test Failed. Expected error.")
        
        ASCIIColors.cyan("\n--- Matplotlib Wrapper Tests Finished ---")

    asyncio.run(test_plot_generation())