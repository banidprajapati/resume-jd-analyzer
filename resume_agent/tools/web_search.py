"""
Web search tool using Tavily API.
"""

from tavily import TavilyClient

from resume_agent.core.config import settings
from resume_agent.core.loggings import get_logger

log = get_logger(__name__)


def _get_client() -> TavilyClient:
    return TavilyClient(api_key=settings.TAVILY_API_KEY)


def web_search_tool(query: str) -> dict:
    """
    Search the web using Tavily.

    Returns:
        {"status": "ok", "results": [...]} or
        {"status": "error", "reason": "..."}
    """
    try:
        client = _get_client()
        response = client.search(query=query, max_results=3)
        results = response.get("results", [])

        if not results:
            log.debug("Web search for '%s' returned 0 results", query)
            return {"status": "ok", "results": []}

        snippets = []
        for r in results:
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "")
            snippets.append({"title": title, "url": url, "content": content})
            log.debug(
                f"Result:  {title} | {url}",
            )
            log.debug(
                f"Content: {content[:500]}",
            )

        log.info("Web search for '%s' returned %d results", query, len(snippets))
        return {"status": "ok", "results": snippets}
    except Exception as e:
        log.error("Web search failed: %s", e)
        return {"status": "error", "reason": str(e)}
