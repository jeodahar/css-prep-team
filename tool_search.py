"""Web tools: search (DuckDuckGo via `ddgs`) and read a web page."""
from crewai.tools import tool

from config import truncate


@tool("Web Search")
def web_search(query: str) -> str:
    """Search the web and return the top results (title, link, short summary)."""
    try:
        from ddgs import DDGS  # imported here so a missing package cannot crash startup

        results = DDGS().text(query, max_results=4)
    except Exception as e:
        return f"Search failed: {e}"
    if not results:
        return "No results found."
    lines = [
        f"- {r.get('title', '')[:80]} | {r.get('href', '')} | {r.get('body', '')[:220]}"
        for r in results
    ]
    return truncate("\n".join(lines))


@tool("Read Web Page")
def fetch_webpage(url: str) -> str:
    """Download a web page and return its main text."""
    try:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        return f"Could not open the page: {e}"
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return truncate(text)
