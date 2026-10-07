"""
Real-world tools for the research supervisor system.

Two kinds of functions live here:
  - "pure" helper functions (format_search_results, summarize_stock_data)
    that only do formatting/logic. They're covered by unit tests in
    tests/test_tools.py and need no network access and no API keys.
  - the actual @tool-decorated functions the agents call, which wrap those
    pure helpers with real network calls (DuckDuckGo search, page fetch,
    Yahoo Finance). Their third-party imports are deliberately done INSIDE
    the function body, not at module level, so the pure helpers above stay
    importable/testable even in an environment that doesn't have
    `ddgs`, `requests`, `beautifulsoup4`, or `yfinance` installed.
"""

from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Pure helpers — no I/O, fully unit-testable (see tests/test_tools.py)
# ---------------------------------------------------------------------------


def format_search_results(results: list[dict]) -> str:
    """Turn a list of {title, body, href} dicts into a readable block of text."""
    if not results:
        return "No search results found."
    lines = []
    for i, r in enumerate(results, start=1):
        title = r.get("title", "untitled")
        body = (r.get("body") or "").strip()
        href = r.get("href", "")
        lines.append(f"{i}. {title}\n   {body}\n   source: {href}")
    return "\n".join(lines)


def summarize_stock_data(
    ticker: str,
    fast_info: dict,
    company_name: str | None,
    news_titles: list[str],
) -> str:
    """Format raw stock fields into a readable summary. fast_info is a plain
    dict (not yfinance's FastInfo object) so this function needs no yfinance
    installed to test."""

    def fmt(key: str, label: str, prefix: str = "") -> str:
        value = fast_info.get(key)
        if value is None:
            return f"{label}: unavailable"
        return f"{label}: {prefix}{value}"

    lines = [f"Stock summary for {ticker} ({company_name or 'unknown company'})"]
    lines.append(fmt("last_price", "Last price", "$"))
    lines.append(fmt("year_high", "52-week high", "$"))
    lines.append(fmt("year_low", "52-week low", "$"))
    lines.append(fmt("market_cap", "Market cap"))
    if news_titles:
        lines.append("Recent headlines:")
        lines.extend(f"  - {t}" for t in news_titles[:5])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Real tools — these do actual network I/O. Agents call these.
# ---------------------------------------------------------------------------


@tool
def web_search(query: str) -> str:
    """Search the web for recent news and information about a topic.
    Returns up to 5 results with title, short snippet, and source URL."""
    from ddgs import DDGS  # lazy import: 'duckduckgo-search' was renamed to 'ddgs'

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
    except Exception as e:  # network hiccups, rate limiting, etc.
        return f"Search failed: {e}"
    return format_search_results(results)


@tool
def fetch_page(url: str) -> str:
    """Fetch a web page and return its main readable text (truncated to a
    safe length). Use this when a search snippet isn't detailed enough."""
    import requests
    from bs4 import BeautifulSoup

    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as e:
        return f"Could not fetch page: {e}"

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text[:3000]  # keep the agent's context window sane


@tool
def get_stock_summary(ticker: str) -> str:
    """Get the current price, 52-week range, market cap, and recent
    headlines for a stock ticker symbol (e.g. 'TSLA', 'AAPL')."""
    import yfinance as yf

    try:
        t = yf.Ticker(ticker)
        fast = t.fast_info
        fast_dict = {
            "last_price": getattr(fast, "last_price", None),
            "year_high": getattr(fast, "year_high", None),
            "year_low": getattr(fast, "year_low", None),
            "market_cap": getattr(fast, "market_cap", None),
        }

        company_name = None
        try:
            company_name = t.info.get("shortName")
        except Exception:
            pass  # Yahoo's full .info endpoint is flaky; fast_info is the reliable part

        news_titles = []
        try:
            news_titles = [n.get("title", "") for n in (t.news or []) if n.get("title")]
        except Exception:
            pass
    except Exception as e:
        return f"Could not retrieve data for ticker '{ticker}': {e}"

    return summarize_stock_data(ticker, fast_dict, company_name, news_titles)
