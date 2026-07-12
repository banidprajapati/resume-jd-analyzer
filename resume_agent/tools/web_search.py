"""
Web search tool using Tavily API.
"""

from tavily import TavilyClient

from resume_agent.agents.llm_calling import call_llm
from resume_agent.agents.prompt import EXTRACT_SYSTEM_PROMPT
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


def extract_requirements(search_results: list[dict], jd_text: str) -> dict:
    """
    Use 1 LLM call to clean raw web search results into proper JD requirements.

    Returns:
        {"status": "ok", "requirements": [...]} or
        {"status": "error", "reason": "..."}
    """
    if not search_results:
        return {"status": "error", "reason": "No search results to process"}

    content_parts = []
    for r in search_results:
        content_parts.append(r.get("content", ""))
    raw_content = "\n---\n".join(content_parts)

    user_prompt = f"""Job description:
{jd_text[:500]}

Raw web search results:
{raw_content}

Extract the key requirements for this role."""

    try:
        result = call_llm(EXTRACT_SYSTEM_PROMPT, user_prompt, force_json=True)
        data = result.as_json()

        if "_parse_error" in data:
            return {"status": "error", "reason": "LLM returned invalid JSON",
                    "prompt_tokens": result.prompt_tokens, "completion_tokens": result.completion_tokens}

        requirements = data.get("requirements", [])
        if not requirements:
            return {"status": "error", "reason": "No requirements extracted",
                    "prompt_tokens": result.prompt_tokens, "completion_tokens": result.completion_tokens}

        log.info("Extracted %d requirements from web search", len(requirements))
        return {"status": "ok", "requirements": requirements,
                "prompt_tokens": result.prompt_tokens, "completion_tokens": result.completion_tokens}
 
    except Exception as e:
        log.error("Requirement extraction failed: %s", e)
        return {"status": "error", "reason": str(e)}
