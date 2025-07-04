
import os
import sys
import argparse
import logging
import uuid
from pathlib import Path
from typing import Dict, Any

# --- Graceful Dependency Check ---
# We check for dependencies inside main_cli to provide a clean error message.
try:
    from mcp.server.auth.provider import AccessToken, TokenVerifier
    from mcp.server.auth.settings import AuthSettings
    import httpx
    from contextvars import ContextVar
except ImportError as e:
    sys.stderr.write(f"FATAL: A required MCP dependency '{e.name}' is not installed.\n")
    sys.stderr.write("Please run 'pip install -r requirements.txt'\n")
    sys.exit(1)

from safe_store import SafeStore
# --- Global Variables ---
# Will be initialized in main_cli after parsing args
ss: SafeStore | None = None
VECTORIZER_MODEL: str = "st:all-MiniLM-L6-v2"

# --- Authentication Boilerplate (from example) ---
AUTHORIZATION_SERVER_URL = os.environ.get("AUTHORIZATION_SERVER_URL", "http://localhost:9642")

class MyTokenInfo(AccessToken):
    user_id: int | None = None
    username: str | None = None

token_info_context: ContextVar[MyTokenInfo | None] = ContextVar("token_info_context", default=None)

class IntrospectionTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{AUTHORIZATION_SERVER_URL}/api/auth/introspect",
                    data={"token": token}
                )
                response.raise_for_status()
            except httpx.RequestError as e:
                logging.error(f"Could not connect to introspection endpoint: {e}")
                return AccessToken(active=False)

        token_info_dict = response.json()
        token_info_dict["token"] = token
        token_info_dict["client_id"] = str(token_info_dict.get("user_id"))
        token_info_dict["scopes"] = []
        token_info = MyTokenInfo(**token_info_dict)
        token_info_context.set(token_info)
        return token_info

# --- Argument Parsing and Configuration ---
def setup_logging(log_level_str: str):
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

def parse_args():
    parser = argparse.ArgumentParser(
        description="MCP Server for LLM Long-Term Memory.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--host", type=str, default=os.getenv("MCP_HOST", "localhost"), help="Hostname to bind to. (Env: MCP_HOST)")
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", 9625)), help="Port to listen on. (Env: MCP_PORT)")
    parser.add_argument("--log-level", dest="log_level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default=os.getenv("MCP_LOG_LEVEL", "INFO"), help="Logging level. (Env: MCP_LOG_LEVEL)")
    parser.add_argument("--transport", type=str, choices=["stdio", "sse", "streamable-http"], default=os.getenv("MCP_TRANSPORT", "streamable-http"), help="Transport protocol. (Env: MCP_TRANSPORT)")
    parser.add_argument("--authentication", type=str, choices=["none", "lollms_chat_auth", "bearer"], default=os.getenv("MCP_AUTHENTICATION", "none"), help="Authentication mode. (Env: MCP_AUTHENTICATION)")
    parser.add_argument("--db-path", type=str, default=os.getenv("MCP_DB_PATH", "long_term_memory.db"), help="Path to the SafeStore database file. (Env: MCP_DB_PATH)")
    parser.add_argument("--vectorizer", type=str, default=os.getenv("MCP_VECTORIZER", "st:all-MiniLM-L6-v2"), help="Sentence-transformer model for vectorization. (Env: MCP_VECTORIZER)")

    args = parser.parse_args()
    if not (1 <= args.port <= 65535):
        parser.error("Port must be between 1 and 65535")
    return args

def main_cli():
    """The main command-line interface entry point for the server."""
    try:
        from mcp.server.fastmcp import FastMCP
        from dotenv import load_dotenv
        from safe_store import SafeStore
        # This import triggers model download if not cached
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        missing_module = e.name
        sys.stderr.write("="*80 + "\n")
        sys.stderr.write(f"FATAL: A required dependency '{missing_module}' is not installed.\n")
        sys.stderr.write("Please install the required packages by running:\n\n")
        sys.stderr.write("    pip install -r requirements.txt\n\n")
        sys.stderr.write("="*80 + "\n")
        sys.exit(1)

    # --- Configuration and Environment Setup ---
    SERVER_ROOT_PATH = Path(__file__).resolve().parent
    env_path = SERVER_ROOT_PATH / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"INFO: Loading environment variables from: {env_path.resolve()}")

    args = parse_args()
    setup_logging(args.log_level)
    
    # --- Global variable initialization ---
    global ss, VECTORIZER_MODEL
    VECTORIZER_MODEL = args.vectorizer
    logging.info(f"Initializing SafeStore with database: {args.db_path}")
    try:
        # Pre-load the model to avoid a delay on the first API call.
        logging.info(f"Loading vectorizer model: {VECTORIZER_MODEL}. This may take a moment...")
        SentenceTransformer(VECTORIZER_MODEL.split(":")[-1])
        logging.info("Vectorizer model loaded successfully.")
        
        ss = SafeStore(db_path=args.db_path, db_name="mcp_long_term_memory", db_description="Persistent memory for LLM agents")
    except Exception as e:
        logging.error(f"Failed to initialize SafeStore or load the vectorizer model: {e}")
        sys.exit(1)
    
    logging.info("Starting Long-Term Memory MCP Server...")
    logging.info(f"Configuration: transport={args.transport}, host={args.host}, port={args.port}")

    # --- MCP Server Initialization ---
    auth_settings = None
    if args.authentication != "none":
        resource_server_url = f"http://{args.host}:{args.port}"
        auth_settings = AuthSettings(
            issuer_url=AUTHORIZATION_SERVER_URL,
            resource_server_url=resource_server_url,
            required_scopes=[]
        )

    mcp = FastMCP(
        name="LongTermMemoryServer",
        description="Provides tools to give a Large Language Model a persistent, searchable memory.",
        version="1.0.0",
        host=args.host,
        port=args.port,
        log_level=args.log_level.upper(),
        token_verifier=IntrospectionTokenVerifier() if auth_settings else None,
        auth=auth_settings
    )
        
    # --- MCP Tool Definitions ---

    @mcp.tool(
        name="add_to_memory",
        description="Saves a piece of text to a persistent long-term memory collection. Use this to remember facts, user preferences, or details for later retrieval. Returns a unique ID for the stored memory item."
    )
    async def add_to_memory(text: str, collection: str = "default") -> Dict[str, Any]:
        """Stores a piece of text into a specified memory collection."""
        logging.info(f"Tool 'add_to_memory' called for collection '{collection}'.")
        try:
            item_id = str(uuid.uuid4())
            ss.add_text(id=item_id, text=text, collection=collection, vectorizer=VECTORIZER_MODEL)
            return {"status": "success", "message": "Memory stored successfully.", "item_id": item_id}
        except Exception as e:
            logging.error(f"Failed to add text to memory: {e}")
            return {"status": "error", "message": str(e)}

    @mcp.tool(
        name="recall_from_memory",
        description="Searches long-term memory for information related to a query. Returns a list of the most relevant memories found, ranked by similarity."
    )
    async def recall_from_memory(query: str, collection: str = "default", top_k: int = 5) -> Dict[str, Any]:
        """Searches memory semantically and returns the top_k most relevant results."""
        logging.info(f"Tool 'recall_from_memory' called for collection '{collection}' with query: '{query[:50]}...'")
        try:
            results = ss.query(query_text=query, collection=collection, top_k=top_k, vectorizer=VECTORIZER_MODEL)
            # SafeStore returns more fields than we need; let's simplify for the LLM
            cleaned_results = [{"id": r.get('id'), "chunk_text": r.get('chunk_text'), "similarity_percent": r.get('similarity_percent')} for r in results]
            return {"status": "success", "results": cleaned_results}
        except Exception as e:
            logging.error(f"Failed to recall from memory: {e}")
            return {"status": "error", "message": str(e), "results": []}

    @mcp.tool(
        name="list_memory_collections",
        description="Lists all available memory collection names. Useful for knowing where memories can be stored or recalled from."
    )
    async def list_memory_collections() -> Dict[str, Any]:
        """Lists all existing memory collections."""
        logging.info("Tool 'list_memory_collections' called.")
        try:
            collections = ss.list_collections()
            return {"status": "success", "collections": collections}
        except Exception as e:
            logging.error(f"Failed to list collections: {e}")
            return {"status": "error", "message": str(e), "collections": []}

    @mcp.tool(
        name="delete_from_memory",
        description="Deletes a specific memory item from a collection using its unique ID. Use this when information is outdated or explicitly asked to be forgotten."
    )
    async def delete_from_memory(item_id: str, collection: str = "default") -> Dict[str, Any]:
        """Deletes a specific item from memory using its ID."""
        logging.info(f"Tool 'delete_from_memory' called for item '{item_id}' in collection '{collection}'.")
        try:
            ss.delete(id=item_id, collection=collection)
            return {"status": "success", "message": f"Memory item '{item_id}' deleted from collection '{collection}'."}
        except Exception as e:
            # Handle case where item doesn't exist gracefully
            logging.warning(f"Failed to delete item '{item_id}': {e}")
            return {"status": "error", "message": f"Could not delete item '{item_id}'. It may not exist. Error: {e}"}

    @mcp.tool(
        name="clear_memory_collection",
        description="Deletes all memory items within an entire collection. This is a destructive action and should be used with caution."
    )
    async def clear_memory_collection(collection: str) -> Dict[str, Any]:
        """Deletes all items within a specified collection."""
        logging.warning(f"Tool 'clear_memory_collection' called for collection '{collection}'. This is a destructive action.")
        if not collection:
            return {"status": "error", "message": "Collection name cannot be empty."}
        try:
            ss.delete_collection(collection=collection)
            return {"status": "success", "message": f"Memory collection '{collection}' has been cleared."}
        except Exception as e:
            logging.error(f"Failed to clear collection '{collection}': {e}")
            return {"status": "error", "message": str(e)}


    # --- Run the Server ---
    logging.info(f"Listening for MCP messages on {args.transport}...")
    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main_cli()