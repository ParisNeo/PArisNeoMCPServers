# openai-mcp-server/openai_mcp_server/file_server.py
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from ascii_colors import ASCIIColors

def create_file_server_app(static_dir: Path, sub_path: str = "/"):
    """
    Creates a FastAPI application to serve static files.
    """
    app = FastAPI()
    
    # Ensure the static directory exists
    static_dir.mkdir(parents=True, exist_ok=True)
    
    # Mount the static directory at the specified sub-path
    app.mount(sub_path, StaticFiles(directory=static_dir, html=False), name="static")
    ASCIIColors.cyan(f"File server will serve files from: {static_dir.resolve()} at path '{sub_path}'")
    
    return app

def run_file_server(host: str, port: int, static_dir: Path):
    """
    Runs the Uvicorn server for the FastAPI app.
    """
    app = create_file_server_app(static_dir, "/")
    ASCIIColors.cyan(f"Starting file server on http://{host}:{port}")
    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except Exception as e:
        ASCIIColors.red(f"File server failed to start: {e}")