import os
import sys
import argparse
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, Tuple

# --- Graceful Dependency Check ---
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
ss: SafeStore | None = None
VECTORIZER_MODEL: str = "st:all-MiniLM-L6-v2"

# --- Authentication and User Context ---
# AUTHORIZATION_SERVER_URL must be set via environment variable to your lollms-webui instance
AUTHORIZATION_SERVER_URL = os.environ.get("AUTHORIZATION_SERVER_URL","http://localhost:9642")
if not AUTHORIZATION_SERVER_URL:
    logging.critical("FATAL: The 'AUTHORIZATION_SERVER_URL' environment variable is not set.")
    logging.critical("Please set it to the URL of your lollms-webui instance (e.g., http://localhost:9600)")
    sys.exit(1)

class MyTokenInfo(AccessToken):
    user_id: int | None = None
    username: str | None = None

token_info_context: ContextVar[MyTokenInfo | None] = ContextVar("token_info_context", default=None)

class IntrospectionTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken:
        async with httpx.AsyncClient() as client:
            try:
                # The introspection endpoint in lollms-webui is typically /api/auth/introspect
                response = await client.post(
                    f"{AUTHORIZATION_SERVER_URL}/api/auth/introspect",
                    data={"token": token}
                )
                response.raise_for_status()
            except httpx.RequestError as e:
                logging.error(f"Could not connect to introspection endpoint at {AUTHORIZATION_SERVER_URL}: {e}")
                return AccessToken(active=False)

        token_info_dict = response.json()
        if not token_info_dict.get("active", False):
            return AccessToken(active=False)
            
        token_info_dict["token"] = token
        token_info_dict["client_id"] = str(token_info_dict.get("user_id"))
        token_info_dict["scopes"] = []
        token_info = MyTokenInfo(**token_info_dict)
        token_info_context.set(token_info)
        return token_info

# --- Per-User Data Scoping Helper ---
class AuthError(Exception):
    pass

def _get_user_scoped_collection(user_collection_name: str) -> Tuple[str, int]:
    """
    Gets the authenticated user's ID and creates a unique, private collection name for the database.
    Raises AuthError if the user is not authenticated.
    """
    token_info = token_info_context.get()
    if not token_info or not token_info.active or token_info.user_id is None:
        raise AuthError("Authentication failed or user information not found in token.")
    
    user_id = token_info.user_id
    # Sanitize user-provided collection name to be safe for file systems/DBs
    safe_collection_name = "".join(c for c in user_collection_name if c.isalnum() or c in ('_', '-')).rstrip()
    if not safe_collection_name:
        safe_collection_name = "default"

    # This creates the unique collection key, e.g., "user_123_project_notes"
    scoped_collection = f"user_{user_id}_{safe_collection_name}"
    return scoped_collection, user_id

# --- Argument Parsing and Configuration ---
def setup_logging(log_level_str: str):
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", stream=sys.stdout)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)

def parse_args():
    parser = argparse.ArgumentParser(description="Secure, Multi-User MCP Server for LLM Long-Term Memory.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--host", type=str, default=os.getenv("MCP_HOST", "localhost"), help="Hostname to bind to. (Env: MCP_HOST)")
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", 9625)), help="Port to listen on. (Env: MCP_PORT)")
    parser.add_argument("--log-level", dest="log_level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default=os.getenv("MCP_LOG_LEVEL", "INFO"), help="Logging level. (Env: MCP_LOG_LEVEL)")
    parser.add_argument("--db-path", type=str, default=os.getenv("MCP_DB_PATH", "long_term_memory.db"), help="Path to the SafeStore database file. (Env: MCP_DB_PATH)")
    parser.add_argument("--vectorizer", type=str, default=os.getenv("MCP_VECTORIZER", "st:all-MiniLM-L6-v2"), help="Sentence-transformer model for vectorization. (Env: MCP_VECTORIZER)")
    # Note: Authentication is no longer an optional choice for this server.
    
    args = parser.parse_args()
    if not (1 <= args.port <= 65535):
        parser.error("Port must be between 1 and 65535")
    return args

def main_cli():
    try:
        from mcp.server.fastmcp import FastMCP
        from dotenv import load_dotenv
        from safe_store import SafeStore
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        sys.stderr.write(f"FATAL: A required dependency '{e.name}' is not installed. Please run 'pip install -r requirements.txt'\n")
        sys.exit(1)

    args = parse_args()
    setup_logging(args.log_level)
    
    global ss, VECTORIZER_MODEL
    VECTORIZER_MODEL = args.vectorizer
    logging.info(f"Initializing SafeStore with database: {args.db_path}")
    try:
        logging.info(f"Loading vectorizer model: {VECTORIZER_MODEL}. This may take a moment...")
        SentenceTransformer(VECTORIZER_MODEL.split(":")[-1])
        logging.info("Vectorizer model loaded successfully.")
        ss = SafeStore(args.db_path, name="mcp_long_term_memory", description="Persistent memory for LLM agents")
    except Exception as e:
        logging.error(f"Failed to initialize SafeStore or load the vectorizer model: {e}")
        sys.exit(1)
    
    logging.info("Starting Multi-User Long-Term Memory MCP Server...")
    logging.info(f"Authentication required via: {AUTHORIZATION_SERVER_URL}")

    resource_server_url = f"http://{args.host}:{args.port}"
    mcp = FastMCP(
        name="LongTermMemoryServer",
        description="Provides tools to give a Large Language Model a persistent, searchable, and private memory for each user.",
        version="2.0.0",
        host=args.host,
        port=args.port,
        log_level=args.log_level.upper(),
        token_verifier=IntrospectionTokenVerifier(),
        auth=AuthSettings(
            issuer_url=AUTHORIZATION_SERVER_URL,
            resource_server_url=resource_server_url,
            required_scopes=[]
        )
    )
        
    # --- MCP Tool Definitions (Now User-Aware) ---

    @mcp.tool(name="add_to_memory", description="Saves a piece of text to your private long-term memory. Use this to remember facts, user preferences, or details for later retrieval. Returns a unique ID for the stored memory item.")
    async def add_to_memory(text: str, collection: str = "default") -> Dict[str, Any]:
        try:
            scoped_collection, user_id = _get_user_scoped_collection(collection)
            logging.info(f"User '{user_id}' calling 'add_to_memory' for collection '{collection}' (maps to '{scoped_collection}').")
            item_id = str(uuid.uuid4())
            ss.add_text(id=item_id, text=text, collection=scoped_collection, vectorizer=VECTORIZER_MODEL)
            return {"status": "success", "message": "Memory stored successfully.", "item_id": item_id}
        except AuthError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logging.error(f"Failed to add text to memory: {e}")
            return {"status": "error", "message": str(e)}

    @mcp.tool(name="recall_from_memory", description="Searches your private long-term memory for information related to a query. Returns a list of the most relevant memories found, ranked by similarity.")
    async def recall_from_memory(query: str, collection: str = "default", top_k: int = 5) -> Dict[str, Any]:
        try:
            scoped_collection, user_id = _get_user_scoped_collection(collection)
            logging.info(f"User '{user_id}' calling 'recall_from_memory' for collection '{collection}'.")
            results = ss.query(query_text=query, collection=scoped_collection, top_k=top_k, vectorizer=VECTORIZER_MODEL)
            cleaned_results = [{"id": r.get('id'), "chunk_text": r.get('chunk_text'), "similarity_percent": r.get('similarity_percent')} for r in results]
            return {"status": "success", "results": cleaned_results}
        except AuthError as e:
            return {"status": "error", "message": str(e), "results": []}
        except Exception as e:
            logging.error(f"Failed to recall from memory: {e}")
            return {"status": "error", "message": str(e), "results": []}

    @mcp.tool(name="list_memory_collections", description="Lists all of your available memory collection names. Useful for knowing where your memories are stored.")
    async def list_memory_collections() -> Dict[str, Any]:
        try:
            _, user_id = _get_user_scoped_collection("dummy") # Just to get user_id and check auth
            logging.info(f"User '{user_id}' calling 'list_memory_collections'.")
            all_collections = ss.list_collections()
            user_prefix = f"user_{user_id}_"
            user_collections = [c.replace(user_prefix, "", 1) for c in all_collections if c.startswith(user_prefix)]
            return {"status": "success", "collections": user_collections}
        except AuthError as e:
            return {"status": "error", "message": str(e), "collections": []}
        except Exception as e:
            logging.error(f"Failed to list collections: {e}")
            return {"status": "error", "message": str(e), "collections": []}

    @mcp.tool(name="delete_from_memory", description="Deletes a specific memory item from one of your collections using its unique ID. Use this when information is outdated or you have been asked to forget something.")
    async def delete_from_memory(item_id: str, collection: str = "default") -> Dict[str, Any]:
        try:
            scoped_collection, user_id = _get_user_scoped_collection(collection)
            logging.info(f"User '{user_id}' calling 'delete_from_memory' for item '{item_id}'.")
            ss.delete(id=item_id, collection=scoped_collection)
            return {"status": "success", "message": f"Memory item '{item_id}' deleted from your '{collection}' collection."}
        except AuthError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": f"Could not delete item '{item_id}'. It may not exist. Error: {e}"}

    @mcp.tool(name="clear_memory_collection", description="Deletes all memory items within one of your collections. This is a destructive action and should be used with caution.")
    async def clear_memory_collection(collection: str) -> Dict[str, Any]:
        try:
            scoped_collection, user_id = _get_user_scoped_collection(collection)
            logging.warning(f"User '{user_id}' calling 'clear_memory_collection' for collection '{collection}'. This is a destructive action.")
            ss.delete_collection(collection=scoped_collection)
            return {"status": "success", "message": f"Your memory collection '{collection}' has been cleared."}
        except AuthError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # --- Run the Server ---
    # The transport argument is only relevant for FastMCP's internal run command
    # for stdio, but not for HTTP-based transports which are run via uvicorn.
    # We keep it for compatibility with the MCP standard runner.
    mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main_cli()