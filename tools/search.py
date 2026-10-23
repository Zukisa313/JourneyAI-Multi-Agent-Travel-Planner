"""Web search tool backed by Tavily."""
import os

from langchain_core.tools import tool
from tavily import TavilyClient


@tool
def web_search(query: str, max_results: int = 3) -> str:
    """Search the web with Tavily for current travel information.

    Use it for hotels, prices, attractions, restaurants, weather, visa rules,
    local transport, or anything else that needs up-to-date answers.

    Args:
        query: A specific search query, e.g. "best boutique hotels in Lisbon Alfama".
        max_results: Number of results to return (default 3).
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY is not set."

    try:
        client = TavilyClient(api_key=api_key)
        res = client.search(query=query, max_results=max_results, include_answer=True)
    except Exception as exc:  # noqa: BLE001
        return f"Error calling Tavily: {exc}"

    parts = []
    if res.get("answer"):
        parts.append(f"Summary: {res['answer']}")
    for r in res.get("results", []):
        content = (r.get("content") or "")[:300]
        parts.append(f"- {r.get('title')} ({r.get('url')})\n  {content}")
    return "\n".join(parts) or "No results found."
