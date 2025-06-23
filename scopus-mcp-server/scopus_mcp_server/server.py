import os
from pathlib import Path
from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from ascii_colors import ASCIIColors
import requests
import io
from PyPDF2 import PdfReader

# Load environment variables
env_path_parent = Path(__file__).resolve().parent.parent / '.env'
env_path_project_root = Path('.') / '.env'

if env_path_parent.exists():
    ASCIIColors.cyan(f"Loading environment variables from: {env_path_parent.resolve()}")
    load_dotenv(dotenv_path=env_path_parent)
elif env_path_project_root.exists():
    ASCIIColors.cyan(f"Loading environment variables from: {env_path_project_root.resolve()}")
    load_dotenv(dotenv_path=env_path_project_root)
else:
    ASCIIColors.yellow(".env file not found in parent or current directory. Relying on existing environment variables.")

# Retrieve API key from environment
SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY")

if not SCOPUS_API_KEY:
    raise EnvironmentError("SCOPUS_API_KEY not found in environment variables.")

# Initialize FastMCP Server
mcp = FastMCP(
    name="ScopusMCPServer",
    description="Provides search capabilities using Elsevier's Scopus API.",
    version="0.1.0"
)

# Define the MCP Tool for Scopus Search
@mcp.tool(
    name="scopus_search",
    description="Performs a literature search using Scopus API and returns a list of matching documents."
)
async def perform_scopus_search(
    query: str,
    count: Optional[int] = 5,
    start: Optional[int] = 0
) -> Dict[str, Any]:
    """
    MCP tool endpoint for performing a Scopus search.
    """
    if not query:
        return {"error": "Query parameter is required and cannot be empty."}

    ASCIIColors.info(f"MCP Tool 'scopus_search' called with query: '{query}'")

    headers = {
        "X-ELS-APIKey": SCOPUS_API_KEY,
        "Accept": "application/json"
    }

    params = {
        "query": query,
        "count": count,
        "start": start
    }

    url = "https://api.elsevier.com/content/search/scopus"

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        entries = data.get("search-results", {}).get("entry", [])

        results = []
        for entry in entries:
            results.append({
                "title": entry.get("dc:title"),
                "doi": entry.get("prism:doi"),
                "publicationName": entry.get("prism:publicationName"),
                "url": entry.get("prism:url"),
                "coverDate": entry.get("prism:coverDate"),
                "authors": entry.get("dc:creator"),
            })

        ASCIIColors.green(f"Search successful. Returning {len(results)} results.")
        return {
            "status": "success",
            "results": results
        }

    except Exception as e:
        ASCIIColors.red(f"Error during Scopus API call: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "results": []
        }

# Define the MCP Tool for Reading PDF from URL
@mcp.tool(
    name="read_pdf_from_url",
    description="Downloads a PDF from the specified URL and extracts its text content."
)
async def read_pdf_from_url(
    url: str
) -> Dict[str, Any]:
    """
    MCP tool endpoint to extract text content from a PDF file at a given URL.
    """
    if not url:
        return {"error": "PDF URL is required."}

    try:
        response = requests.get(url)
        response.raise_for_status()

        with io.BytesIO(response.content) as pdf_file:
            reader = PdfReader(pdf_file)
            content = "\n".join(page.extract_text() or "" for page in reader.pages)

        ASCIIColors.green(f"Successfully extracted text from PDF at {url}")
        return {
            "status": "success",
            "text": content[:10000]  # Truncate to 10k characters for safety
        }

    except Exception as e:
        ASCIIColors.red(f"Error reading PDF from URL: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "text": ""
        }

# --- Main CLI Entry Point ---
def main_cli():
    ASCIIColors.cyan("Starting Scopus MCP Server...")
    ASCIIColors.cyan("MCP server will list 'scopus_search' and 'read_pdf_from_url' tools upon connection.")
    ASCIIColors.cyan("Listening for MCP messages on stdio...")
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main_cli()
