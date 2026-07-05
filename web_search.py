"""Simple web search via DuckDuckGo's HTML endpoint — no API key needed."""

import requests
from html import unescape
import re

SEARCH_URL = "https://html.duckduckgo.com/html/"


def web_search(query: str, max_results: int = 5) -> str:
    query = (query or "").strip()
    if not query:
        return "Error: empty search query."

    try:
        resp = requests.post(
            SEARCH_URL,
            data={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (JoshAI agent)"},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return f"Search failed: {exc}"

    # Cheap extraction — good enough for an agent tool, not meant to be a full parser.
    results = re.findall(
        r'class="result__a".*?href="(.*?)".*?>(.*?)</a>.*?class="result__snippet".*?>(.*?)</a>',
        resp.text,
        re.DOTALL,
    )

    if not results:
        return f"No results found for '{query}'."

    lines = []
    for url, title, snippet in results[:max_results]:
        title = unescape(re.sub("<.*?>", "", title)).strip()
        snippet = unescape(re.sub("<.*?>", "", snippet)).strip()
        lines.append(f"- {title}\n  {snippet}\n  {url}")

    return "\n".join(lines)
