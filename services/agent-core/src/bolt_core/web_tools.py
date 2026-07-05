"""Web tools: search and extract. Read-only, no side effects."""

import json
import urllib.request
from dataclasses import dataclass


DEFAULT_SEARCH_URL = "https://searx.be/search"
DEFAULT_CHAR_LIMIT = 15000


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    description: str


@dataclass(frozen=True)
class ExtractResult:
    url: str
    content: str
    error: str | None = None


def web_search(query: str, limit: int = 5, search_url: str | None = None) -> list[SearchResult]:
    url = (search_url or DEFAULT_SEARCH_URL).rstrip("/")
    params = f"?q={urllib.parse.quote(query)}&format=json&limit={limit}"
    try:
        req = urllib.request.Request(url + params, headers={"User-Agent": "Bolt/0.1"})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []
    results = data if isinstance(data, list) else data.get("results", [])
    return [
        SearchResult(
            title=str(r.get("title", "")),
            url=str(r.get("url", "")),
            description=str(r.get("description", r.get("snippet", ""))),
        )
        for r in results[:limit]
    ]


def web_extract(urls: list[str], char_limit: int = DEFAULT_CHAR_LIMIT) -> list[ExtractResult]:
    results = []
    for url in urls[:5]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Bolt/0.1"})
            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode("utf-8", errors="replace")
            content = _html_to_text(html)
            if len(content) > char_limit:
                content = content[:char_limit] + "\n[truncated]"
            results.append(ExtractResult(url, content, None))
        except Exception as exc:
            results.append(ExtractResult(url, "", str(exc)))
    return results


def _html_to_text(html: str) -> str:
    """Minimal HTML to text: strip tags, decode entities, collapse whitespace."""
    import re
    import html as html_module
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_module.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


import urllib.parse
