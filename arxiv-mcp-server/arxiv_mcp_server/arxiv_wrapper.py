# PArisNeoMCPServers/arxiv-mcp-server/arxiv_mcp_server/arxiv_wrapper.py
import os
import json
import re
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
import arxiv
from ascii_colors import ASCIIColors, trace_exception
from dotenv import load_dotenv

# --- Configuration ---
# Determine the server project root (the 'arxiv-mcp-server' folder)
SERVER_ROOT_PATH = Path(__file__).resolve().parent.parent

# Load environment variables from .env in the server's root
env_path = SERVER_ROOT_PATH / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    ASCIIColors.cyan(f"Arxiv Wrapper: Loaded .env from {env_path}")

# The root directory for storing all Arxiv databases.
# Defaults to a folder within 'mcp_example_outputs' in the main project root.
DEFAULT_DB_ROOT = SERVER_ROOT_PATH.parent / "mcp_example_outputs" / "arxiv_databases"
ARXIV_DATABASES_ROOT = Path(os.getenv("ARXIV_DATABASES_ROOT", DEFAULT_DB_ROOT))

METADATA_FILENAME = "metadata.json"

# --- Helper Functions ---

def _ensure_db_root_exists() -> bool:
    """Ensures the root directory for all databases exists. Returns True on success."""
    if ARXIV_DATABASES_ROOT.is_dir():
        return True
    try:
        ARXIV_DATABASES_ROOT.mkdir(parents=True, exist_ok=True)
        ASCIIColors.info(f"Created Arxiv databases root at: {ARXIV_DATABASES_ROOT}")
        return True
    except OSError as e:
        ASCIIColors.error(f"Could not create Arxiv databases root at {ARXIV_DATABASES_ROOT}. Error: {e}")
        return False

def _sanitize_db_name(name: str) -> str:
    """Removes characters that are invalid for directory names."""
    return re.sub(r'[\\/*?:"<>|]', "", name)

def _get_db_path(database_name: str) -> Optional[Path]:
    """Validates and returns the path for a given database name."""
    sanitized_name = _sanitize_db_name(database_name)
    if not sanitized_name or sanitized_name != database_name:
        ASCIIColors.warning(f"Invalid characters in database name '{database_name}'. Use simple alphanumeric names.")
        return None
    
    db_path = ARXIV_DATABASES_ROOT / sanitized_name
    return db_path

def _read_metadata(db_path: Path) -> Dict[str, Dict]:
    """Reads the metadata file from a database directory."""
    metadata_file = db_path / METADATA_FILENAME
    if not metadata_file.exists():
        return {}
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            # The file stores a dict of {entry_id: paper_meta}
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        ASCIIColors.error(f"Error reading metadata from {metadata_file}: {e}")
        return {}

def _write_metadata(db_path: Path, metadata: Dict[str, Dict]):
    """Writes the metadata to the database directory."""
    metadata_file = db_path / METADATA_FILENAME
    try:
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4)
    except IOError as e:
        ASCIIColors.error(f"Error writing metadata to {metadata_file}: {e}")

# --- Core Wrapper Functions ---

async def list_databases() -> Dict[str, Any]:
    """Lists all existing Arxiv databases (subdirectories)."""
    if not _ensure_db_root_exists():
        return {"error": f"Arxiv database root directory could not be created or accessed: {ARXIV_DATABASES_ROOT}"}
    
    ASCIIColors.info("Arxiv Wrapper: Listing databases.")
    try:
        databases = [d.name for d in ARXIV_DATABASES_ROOT.iterdir() if d.is_dir()]
        return {"databases": databases, "root_path": str(ARXIV_DATABASES_ROOT)}
    except Exception as e:
        trace_exception(e)
        return {"error": f"Failed to list databases: {e}"}

async def create_database(database_name: str) -> Dict[str, Any]:
    """Creates a new, empty database."""
    if not _ensure_db_root_exists():
        return {"error": f"Arxiv database root directory could not be created or accessed: {ARXIV_DATABASES_ROOT}"}

    ASCIIColors.info(f"Arxiv Wrapper: Attempting to create database '{database_name}'.")
    db_path = _get_db_path(database_name)
    if not db_path:
        return {"error": "Invalid database name provided. Avoid special characters."}

    if db_path.exists():
        return {"error": f"Database '{database_name}' already exists."}
    
    try:
        db_path.mkdir(parents=True, exist_ok=True)
        # Create an empty metadata file
        _write_metadata(db_path, {})
        ASCIIColors.green(f"Database '{database_name}' created at {db_path}")
        return {"status": "success", "message": f"Database '{database_name}' created successfully."}
    except Exception as e:
        trace_exception(e)
        return {"error": f"Failed to create database directory: {e}"}

async def search_and_download(database_name: str, query: str, max_results: int = 5) -> Dict[str, Any]:
    """Searches Arxiv, downloads new papers to the specified database, and updates metadata."""
    if not _ensure_db_root_exists():
        return {"error": f"Arxiv database root directory could not be created or accessed: {ARXIV_DATABASES_ROOT}"}

    ASCIIColors.info(f"Arxiv Wrapper: Searching in '{database_name}' for query='{query}' (max={max_results}).")
    db_path = _get_db_path(database_name)
    if not db_path or not db_path.exists():
        return {"error": f"Database '{database_name}' not found."}

    try:
        metadata = await asyncio.to_thread(_read_metadata, db_path)
        
        # Use asyncio.to_thread for the synchronous arxiv library calls
        def sync_search_and_download():
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )
            
            newly_downloaded = []
            skipped_existing = []
            client = arxiv.Client()
            
            for result in client.results(search):
                paper_id = result.entry_id.split('/')[-1] # Get clean ID like '2103.12345v1'
                
                if paper_id in metadata:
                    skipped_existing.append(paper_id)
                    continue

                # Download PDF
                pdf_filename = f"{paper_id.replace('v', '_v')}.pdf" # Sanitize for filename
                pdf_path = db_path / pdf_filename
                result.download_pdf(dirpath=str(db_path), filename=pdf_filename)
                
                # Add to metadata
                paper_meta = {
                    "entry_id": paper_id,
                    "title": result.title,
                    "authors": [str(a) for a in result.authors],
                    "summary": result.summary,
                    "published": result.published.isoformat(),
                    "pdf_url": result.pdf_url,
                    "local_path": str(pdf_path)
                }
                metadata[paper_id] = paper_meta
                newly_downloaded.append(paper_meta)

            # Write updated metadata back to file
            if newly_downloaded:
                _write_metadata(db_path, metadata)
                
            return {
                "downloaded_count": len(newly_downloaded),
                "skipped_count": len(skipped_existing),
                "new_papers": newly_downloaded,
                "message": f"Search complete. Downloaded {len(newly_downloaded)} new papers."
            }

        result = await asyncio.to_thread(sync_search_and_download)
        ASCIIColors.green(result["message"])
        return {"status": "success", **result}

    except Exception as e:
        trace_exception(e)
        return {"error": f"An unexpected error occurred during search and download: {e}"}

async def load_database_metadata(database_name: str) -> Dict[str, Any]:
    """Loads and returns the metadata for all papers in a database."""
    ASCIIColors.info(f"Arxiv Wrapper: Loading metadata for database '{database_name}'.")
    db_path = _get_db_path(database_name)
    if not db_path or not db_path.exists():
        return {"error": f"Database '{database_name}' not found."}
    
    metadata = await asyncio.to_thread(_read_metadata, db_path)
    return {
        "status": "success",
        "database": database_name,
        "paper_count": len(metadata),
        "papers": list(metadata.values()) # Return a list of paper objects
    }
    
async def get_paper_summary(database_name: str, paper_id: str) -> Dict[str, Any]:
    """Retrieves the summary (abstract) for a specific paper from a local database."""
    ASCIIColors.info(f"Arxiv Wrapper: Getting summary for paper '{paper_id}' from '{database_name}'.")
    db_path = _get_db_path(database_name)
    if not db_path or not db_path.exists():
        return {"error": f"Database '{database_name}' not found."}
        
    metadata = await asyncio.to_thread(_read_metadata, db_path)
    
    # Allow for partial matching of paper_id (e.g., without version)
    found_paper = None
    for pid, paper_meta in metadata.items():
        if pid.startswith(paper_id):
            found_paper = paper_meta
            break
            
    if found_paper:
        return {
            "status": "success",
            "paper_id": found_paper["entry_id"],
            "title": found_paper["title"],
            "summary": found_paper["summary"]
        }
    else:
        return {"error": f"Paper with ID '{paper_id}' not found in database '{database_name}'."}

# --- Standalone Test Block ---
if __name__ == '__main__':
    import shutil

    async def test_arxiv_wrapper():
        ASCIIColors.red("--- Testing Arxiv Wrapper ---")
        test_db_name = "test_ai_safety_db"
        test_db_path = _get_db_path(test_db_name)

        # Cleanup previous test runs
        if test_db_path and test_db_path.exists():
            ASCIIColors.yellow(f"Removing previous test database: {test_db_path}")
            shutil.rmtree(test_db_path)

        # 1. List initial databases
        ASCIIColors.magenta("\n1. Listing initial databases...")
        dbs = await list_databases()
        print(dbs)
        assert test_db_name not in dbs.get("databases", [])

        # 2. Create a new database
        ASCIIColors.magenta(f"\n2. Creating database '{test_db_name}'...")
        create_res = await create_database(test_db_name)
        print(create_res)
        assert create_res["status"] == "success"
        assert test_db_path.exists()

        # 3. List databases again
        ASCIIColors.magenta("\n3. Listing databases again...")
        dbs = await list_databases()
        print(dbs)
        assert test_db_name in dbs.get("databases", [])

        # 4. Search and download
        ASCIIColors.magenta("\n4. Searching for 'AI Safety' and downloading (max 2)...")
        search_res = await search_and_download(test_db_name, "au:Geoffrey Hinton", max_results=2)
        print(json.dumps(search_res, indent=2))
        assert search_res["status"] == "success"
        assert search_res["downloaded_count"] > 0
        paper_to_test = search_res["new_papers"][0] if search_res["new_papers"] else None

        # 5. Load metadata
        ASCIIColors.magenta("\n5. Loading metadata from the database...")
        meta_res = await load_database_metadata(test_db_name)
        # print(json.dumps(meta_res, indent=2))
        print(f"Found {meta_res['paper_count']} papers.")
        assert meta_res["paper_count"] == search_res["downloaded_count"]
        
        # 6. Get a specific summary
        if paper_to_test:
            paper_id_to_get = paper_to_test["entry_id"]
            ASCIIColors.magenta(f"\n6. Getting summary for paper ID: {paper_id_to_get}...")
            summary_res = await get_paper_summary(test_db_name, paper_id_to_get)
            print(f"Title: {summary_res.get('title')}")
            print(f"Summary: {summary_res.get('summary', '')[:200]}...")
            assert summary_res["status"] == "success"
            assert "summary" in summary_res
        else:
            ASCIIColors.yellow("Skipping summary test as no papers were downloaded.")
            
        # 7. Test error cases
        ASCIIColors.magenta("\n7. Testing error cases...")
        # Bad DB name
        bad_name_res = await create_database("../invalid")
        print(f"Create bad name: {bad_name_res}")
        assert "error" in bad_name_res
        # Non-existent DB
        non_existent_res = await search_and_download("non_existent_db", "test")
        print(f"Search non-existent DB: {non_existent_res}")
        assert "error" in non_existent_res

        ASCIIColors.red("\n--- Arxiv Wrapper Tests Finished ---")

    asyncio.run(test_arxiv_wrapper())