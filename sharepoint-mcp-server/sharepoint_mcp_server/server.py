# sharepoint_mcp_server/server.py
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# --- Global variable to hold the SharePoint client context (singleton) ---
sharepoint_context = None

def get_sharepoint_context():
    """
    Authenticates with SharePoint using credentials from environment variables
    and returns a ClientContext object. Implements a singleton pattern
    to avoid re-authenticating on every tool call.
    """
    global sharepoint_context
    if sharepoint_context:
        return sharepoint_context

    # --- Dependency Imports ---
    # Placed here to ensure configuration is checked first.
    from office365.runtime.auth.authentication_context import AuthenticationContext
    from office365.sharepoint.client_context import ClientContext

    # --- Load Credentials ---
    sharepoint_url = os.getenv("SHAREPOINT_URL")
    tenant_id = os.getenv("TENANT_ID")
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    if not all([sharepoint_url, tenant_id, client_id, client_secret]):
        raise ConnectionError(
            "SharePoint configuration is incomplete. "
            "Please set SHAREPOINT_URL, TENANT_ID, CLIENT_ID, and CLIENT_SECRET in your .env file or environment."
        )

    logging.info(f"Attempting to authenticate with SharePoint site: {sharepoint_url}")
    auth_ctx = AuthenticationContext(url=f'https://login.microsoftonline.com/{tenant_id}')
    auth_ctx.acquire_token_for_app(client_id=client_id, client_secret=client_secret)
    
    ctx = ClientContext(sharepoint_url, auth_ctx)
    web = ctx.web.get().execute_query()
    logging.info(f"Successfully connected to SharePoint site: '{web.title}'")

    sharepoint_context = ctx
    return sharepoint_context


def main_cli():
    """The main command-line interface entry point for the server."""
    try:
        from mcp.server.fastmcp import FastMCP
        from dotenv import load_dotenv
    except ImportError as e:
        sys.stderr.write(f"FATAL: A required dependency '{e.name}' is not installed. Please run 'pip install -e .'\n")
        sys.exit(1)

    SERVER_ROOT_PATH = Path(__file__).resolve().parent.parent
    if (env_path := SERVER_ROOT_PATH / '.env').exists():
        load_dotenv(dotenv_path=env_path)
        print(f"INFO: Loading environment variables from: {env_path.resolve()}")

    # --- Argument Parsing and Logging Setup (Boilerplate) ---
    # (This part is identical to the enhanced example server and is omitted for brevity)
    # --- Assume 'args' variable is created and 'setup_logging' is called ---
    # START BOILERPLATE
    def setup_logging(log_level_str: str):
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
        logging.getLogger("office365").setLevel(logging.WARNING) # Quieten the verbose library
    
    def parse_args():
        parser = argparse.ArgumentParser(description="SharePoint MCP Server", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("--host", default=os.getenv("MCP_HOST", "localhost"), help="Hostname (Env: MCP_HOST)")
        parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", 9625)), help="Port (Env: MCP_PORT)")
        parser.add_argument("--log-level", default=os.getenv("MCP_LOG_LEVEL", "INFO"), help="Logging level (Env: MCP_LOG_LEVEL)")
        parser.add_argument("--transport", default=os.getenv("MCP_TRANSPORT", "streamable-http"), help="Transport protocol (Env: MCP_TRANSPORT)")
        return parser.parse_args()

    args = parse_args()
    setup_logging(args.log_level)
    # END BOILERPLATE

    logging.info("Initializing SharePoint MCP Server...")

    mcp = FastMCP(
        name="SharePointMCPServer",
        description="Provides tools to interact with a Microsoft SharePoint document library.",
        version="0.1.0",
        host=args.host, port=args.port, log_level=args.log_level.upper()
    )

    # --- MCP Tool Definitions ---
    @mcp.tool()
    async def list_document_libraries() -> Dict[str, Any]:
        """Lists all document libraries available in the configured SharePoint site."""
        try:
            ctx = get_sharepoint_context()
            # BaseTemplate 101 corresponds to a Document Library
            libraries = ctx.web.lists.get().filter("BaseTemplate eq 101").execute_query()
            library_names = [lib.properties['Title'] for lib in libraries]
            logging.info(f"Found {len(library_names)} document libraries.")
            return {"status": "success", "libraries": library_names}
        except Exception as e:
            logging.error(f"Error listing document libraries: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    @mcp.tool()
    async def list_files(library_name: str, folder_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Lists files and folders within a specific SharePoint document library.
        :param library_name: The name of the document library (e.g., "Documents").
        :param folder_path: The optional path to a subfolder within the library (e.g., "Reports/2023").
        """
        try:
            ctx = get_sharepoint_context()
            target_list = ctx.web.lists.get_by_title(library_name)
            
            if folder_path:
                # To get folder items, we need to construct a CAML query
                caml_query = f"""
                <View>
                    <Query>
                        <Where>
                            <Eq>
                                <FieldRef Name='FileDirRef' />
                                <Value Type='Text'>{target_list.root_folder.serverRelativeUrl}/{folder_path}</Value>
                            </Eq>
                        </Where>
                    </Query>
                </View>"""
                items = target_list.get_items(caml_query).execute_query()
            else:
                items = target_list.items.get().execute_query()

            files = [{"name": item.properties['FileLeafRef'], "type": "file" if item.properties['FileSystemObjectType'] == 0 else "folder"} for item in items]
            logging.info(f"Found {len(files)} items in library '{library_name}' at path '{folder_path or '/'}'.")
            return {"status": "success", "items": files}
        except Exception as e:
            logging.error(f"Error listing files in '{library_name}': {e}", exc_info=True)
            return {"status": "error", "message": f"Could not list files in '{library_name}'. Reason: {e}"}

    @mcp.tool()
    async def upload_file(local_file_path: str, library_name: str, remote_folder_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Uploads a file from the local filesystem to a SharePoint document library.
        :param local_file_path: The path to the file on the local machine running the server.
        :param library_name: The name of the target document library.
        :param remote_folder_path: Optional subfolder path to upload the file into.
        """
        try:
            local_path = Path(local_file_path)
            if not local_path.exists():
                return {"status": "error", "message": f"Local file not found: {local_file_path}"}

            ctx = get_sharepoint_context()
            target_folder_url = f"{library_name}"
            if remote_folder_path:
                target_folder_url += f"/{remote_folder_path}"

            target_folder = ctx.web.get_folder_by_server_relative_path(target_folder_url)
            with open(local_path, 'rb') as content_file:
                file_content = content_file.read()

            file_info = target_folder.upload_file(local_path.name, file_content).execute_query()
            logging.info(f"Successfully uploaded '{local_path.name}' to '{target_folder_url}'. URL: {file_info.serverRelativeUrl}")
            return {"status": "success", "message": "File uploaded successfully.", "sharepoint_url": file_info.serverRelativeUrl}
        except Exception as e:
            logging.error(f"Error uploading file '{local_file_path}': {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
            
    @mcp.tool()
    async def download_file(remote_file_path: str, local_save_path: str) -> Dict[str, Any]:
        """
        Downloads a file from SharePoint to the local filesystem.
        :param remote_file_path: The full path to the file in SharePoint (e.g., "Documents/Reports/Q1.pdf").
        :param local_save_path: The local directory and filename to save the file as.
        """
        try:
            ctx = get_sharepoint_context()
            file_url = f"{ctx.web.serverRelativeUrl}/{remote_file_path}".replace('//', '/')
            
            # Ensure local directory exists
            local_path = Path(local_save_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(local_path, "wb") as local_file:
                ctx.web.get_file_by_server_relative_path(file_url).download(local_file).execute_query()
            
            logging.info(f"Successfully downloaded '{file_url}' to '{local_path.resolve()}'.")
            return {"status": "success", "message": f"File downloaded to {local_path.resolve()}"}
        except Exception as e:
            logging.error(f"Error downloading file '{remote_file_path}': {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    @mcp.tool()
    async def search_sharepoint(query_text: str, library_name: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
        """
        Performs a full-text search across the SharePoint site or a specific library.
        Searches file contents and metadata.
        :param query_text: The search term or phrase.
        :param library_name: Optional. The name of the document library to limit the search to.
        :param max_results: The maximum number of results to return. Defaults to 10.
        """
        try:
            # --- Import Search-specific classes ---
            from office365.search.request import SearchRequest
            from office365.search.query.text import SearchQueryText

            ctx = get_sharepoint_context()
            
            # --- Build the search query ---
            final_query_text = query_text
            if library_name:
                # Use Keyword Query Language (KQL) to scope the search to a specific path
                site_url = os.getenv("SHAREPOINT_URL", "")
                path_filter = f"Path:{site_url}/{library_name}/*"
                final_query_text = f"{query_text} {path_filter}"
            
            search_request = SearchRequest(
                query=SearchQueryText(final_query_text),
                select_properties=["Title", "Path", "Author", "LastModifiedTime", "HitHighlightedSummary", "FileType"],
                row_limit=max_results
            )

            logging.info(f"Executing search with query: '{final_query_text}'")
            result = ctx.search.post_query(search_request).execute_query()
            
            # --- Process and format the results ---
            rows = result.value.PrimaryQueryResult.RelevantResults.Table.Rows
            search_results = []
            for row in rows:
                # The row is a dict-like object with a 'Cells' list of key-value pairs
                cell_dict = {cell['Key']: cell['Value'] for cell in row.Cells}
                search_results.append({
                    "title": cell_dict.get("Title"),
                    "path": cell_dict.get("Path"),
                    "author": cell_dict.get("Author"),
                    "last_modified": cell_dict.get("LastModifiedTime"),
                    "file_type": cell_dict.get("FileType"),
                    # The summary is HTML with <c0>...</c0> tags highlighting the match
                    "hit_highlighted_summary": cell_dict.get("HitHighlightedSummary")
                })

            logging.info(f"Search returned {len(search_results)} results.")
            return {"status": "success", "results": search_results}

        except Exception as e:
            logging.error(f"Error during SharePoint search for query '{query_text}': {e}", exc_info=True)
            return {"status": "error", "message": f"An error occurred during search. Reason: {e}"}
    # --- Run the Server ---
    logging.info(f"Starting SharePoint MCP Server on {args.transport}...")
    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main_cli()