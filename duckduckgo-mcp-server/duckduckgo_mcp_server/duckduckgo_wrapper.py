# PArisNeoMCPServers/duckduckgo-mcp-server/duckduckgo_mcp_server/duckduckgo_wrapper.py
import os
from typing import List, Dict, Optional, Any
from duckduckgo_search import DDGS
from ascii_colors import ASCIIColors, trace_exception

# Default configuration from environment variables
DEFAULT_MAX_RESULTS = int(os.getenv("DDG_DEFAULT_MAX_RESULTS", 5))
DEFAULT_REGION = os.getenv("DDG_DEFAULT_REGION", "wt-wt") # World-Wide, no region

# Known regions, not exhaustive, for reference.
# User can supply any valid region string.
# Full list: https://duckduckgo.com/params or search for "duckduckgo regions"
# Common ones: 'us-en', 'uk-en', 'de-de', 'fr-fr', 'es-es', 'jp-jp', 'cn-zh'

async def perform_search(
    query: str,
    max_results: Optional[int] = None,
    region: Optional[str] = None,
    timelimit: Optional[str] = None # e.g., 'd' (day), 'w' (week), 'm' (month), 'y' (year)
) -> Dict[str, Any]:
    """
    Performs a web search using DuckDuckGo.

    Args:
        query: The search query string.
        max_results: The maximum number of results to return.
        region: The region for the search (e.g., 'us-en', 'wt-wt').
        timelimit: Filter results by time (e.g., 'd' for past day, 'w' for past week).

    Returns:
        A dictionary containing a list of search results or an error message.
        Each result is a dict with 'title', 'href', and 'body'.
    """
    if not query:
        return {"error": "Search query cannot be empty."}

    current_max_results = max_results if max_results is not None else DEFAULT_MAX_RESULTS
    current_region = region if region else DEFAULT_REGION

    ASCIIColors.info(
        f"DuckDuckGo Wrapper: Performing search for '{query}' "
        f"(max_results={current_max_results}, region='{current_region}', timelimit='{timelimit or 'None'}')."
    )

    try:
        # The DDGS().text() method is synchronous.
        # To make this wrapper async and avoid blocking, we'd typically run
        # synchronous IO-bound operations in a thread pool executor.
        # For simplicity in this initial version, and since many MCP server
        # environments might not heavily rely on extreme concurrency for this specific tool,
        # we'll call it directly. If this becomes a bottleneck,
        # `asyncio.to_thread` (Python 3.9+) would be the way to go.
        # from asyncio import to_thread
        # results = await to_thread(
        #     DDGS().text,
        #     keywords=query,
        #     region=current_region,
        #     safesearch='moderate', # Or 'off', 'strict'
        #     timelimit=timelimit,
        #     max_results=current_max_results
        # )

        # For now, using the synchronous version directly
        with DDGS() as ddgs:
            results = ddgs.text(
                keywords=query,
                region=current_region,
                safesearch='moderate', # Or 'off', 'strict'
                timelimit=timelimit, # Pass timelimit here
                max_results=current_max_results
            )

        if results:
            # The library might return more if max_results isn't perfectly respected,
            # or if it internally fetches in pages. Let's ensure we cap it.
            # However, the `max_results` param in `ddgs.text` should handle this.
            formatted_results = [
                {"title": r.get("title"), "href": r.get("href"), "body": r.get("body")}
                for r in results #[:current_max_results] # Slicing might not be needed if max_results is respected
            ]
            ASCIIColors.green(f"DuckDuckGo Wrapper: Found {len(formatted_results)} results.")
            return {"results": formatted_results, "query_used": query, "region_used": current_region}
        else:
            ASCIIColors.yellow("DuckDuckGo Wrapper: No results found.")
            return {"results": [], "query_used": query, "region_used": current_region, "message": "No results found."}

    except Exception as e:
        trace_exception(e)
        ASCIIColors.error(f"DuckDuckGo Wrapper: Error during search: {str(e)}")
        return {"error": f"An unexpected error occurred during the DuckDuckGo search: {str(e)}"}

if __name__ == '__main__':
    # Example usage (synchronous for this test block)
    import asyncio
    async def test_search():
        ASCIIColors.cyan("--- Testing DuckDuckGo Wrapper ---")
        
        # Test 1: Basic search
        res1 = await perform_search("What is the capital of France?", max_results=3)
        if "results" in res1:
            ASCIIColors.green("Test 1 Results:")
            for r in res1["results"]:
                print(f"  Title: {r['title']}")
                print(f"  Link: {r['href']}")
                print(f"  Snippet: {r['body'][:100]}...")
        else:
            ASCIIColors.red(f"Test 1 Error: {res1.get('error')}")
        
        print("-" * 20)

        # Test 2: Search with region and timelimit
        res2 = await perform_search("Latest AI news", max_results=2, region="us-en", timelimit="w")
        if "results" in res2:
            ASCIIColors.green("Test 2 Results (US, past week):")
            for r in res2["results"]:
                print(f"  Title: {r['title']}")
                # print(f"  Link: {r['href']}")
                # print(f"  Snippet: {r['body'][:100]}...")
        else:
            ASCIIColors.red(f"Test 2 Error: {res2.get('error')}")

        print("-" * 20)

        # Test 3: No results expected (highly specific query)
        res3 = await perform_search("asdfqwerlkjhzxcvbnmpoiuytrewq", max_results=2)
        if "results" in res3 and not res3["results"]:
            ASCIIColors.green(f"Test 3: Correctly returned no results: {res3.get('message')}")
        elif "results" in res3:
            ASCIIColors.yellow(f"Test 3: Unexpectedly found results for a gibberish query.")
        else:
            ASCIIColors.red(f"Test 3 Error: {res3.get('error')}")

        print("-" * 20)

        # Test 4: Empty query
        res4 = await perform_search("")
        if "error" in res4:
            ASCIIColors.green(f"Test 4: Correctly handled empty query: {res4['error']}")
        else:
            ASCIIColors.red(f"Test 4: Failed to catch empty query error.")

    asyncio.run(test_search())