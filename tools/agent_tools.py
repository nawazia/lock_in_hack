import os
from typing import Annotated

from dotenv import load_dotenv
from langchain.tools import tool
from langsmith import traceable
from valyu import Valyu

load_dotenv()


@tool
@traceable(name="valyu_search_tool", run_type="tool")
def valyu_search_tool(query: Annotated[str, "Search query to run on Valyu"]) -> str:
    """
    Search Valyu for relevant information about the query.
    Returns a concise text summary of the top results.
    """

    api_key = os.getenv("VALYU_API_KEY")
    if not api_key:
        return "VALYU_API_KEY is not set in the environment."

    valyu = Valyu(api_key=api_key)

    # Use the actual query from the agent/user
    response = valyu.search(query)

    # Build a readable summary for the LLM
    if not getattr(response, "results", None):
        return f"No results found for query: {query}"

    lines = []
    for i, result in enumerate(response.results[:5], start=1):  # limit to top 5
        title = getattr(result, "title", "(no title)")
        url = getattr(result, "url", "(no url)")
        content = getattr(result, "content", "")[:500]  # truncate long content
        lines.append(
            f"Result {i}:\nTitle: {title}\nURL: {url}\nContent snippet: {content}\n"
        )

    return "\n\n".join(lines)


@tool
def search_docs(query: Annotated[str, "What you want to look up"]) -> str:
    """Dummy search over some docs. Replace with real logic."""
    # For now, just fake it:
    return f"Results for '{query}': nothing real here yet."
