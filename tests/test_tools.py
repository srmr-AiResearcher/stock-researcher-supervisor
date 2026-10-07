"""
Unit tests for the pure-logic helpers in src/tools.py.

These need no network access, no API key, and no ddgs/yfinance/requests
installed — they only exercise plain formatting logic, which is why that
logic was deliberately pulled out of the network-calling @tool functions
in the first place. Run with: pytest
"""

from src.tools import format_search_results, summarize_stock_data


def test_format_search_results_empty():
    assert format_search_results([]) == "No search results found."


def test_format_search_results_basic():
    results = [
        {
            "title": "Tesla stock rises on delivery beat",
            "body": "Shares up 3% in after-hours trading.",
            "href": "https://example.com/a",
        }
    ]
    out = format_search_results(results)
    assert "Tesla stock rises on delivery beat" in out
    assert "Shares up 3% in after-hours trading." in out
    assert "https://example.com/a" in out


def test_format_search_results_multiple_numbered():
    results = [
        {"title": "First", "body": "a", "href": "u1"},
        {"title": "Second", "body": "b", "href": "u2"},
    ]
    out = format_search_results(results)
    assert "1. First" in out
    assert "2. Second" in out


def test_format_search_results_missing_fields():
    # body/href absent entirely — should not raise
    out = format_search_results([{"title": "Only a title"}])
    assert "Only a title" in out


def test_summarize_stock_data_missing_fields():
    out = summarize_stock_data("TSLA", {}, None, [])
    assert "TSLA" in out
    assert "unknown company" in out
    assert "unavailable" in out


def test_summarize_stock_data_full():
    fast_info = {
        "last_price": 250.5,
        "year_high": 300,
        "year_low": 150,
        "market_cap": 800_000_000_000,
    }
    news = ["Tesla unveils new battery", "Recall issued for Model Y"]
    out = summarize_stock_data("TSLA", fast_info, "Tesla, Inc.", news)
    assert "Tesla, Inc." in out
    assert "$250.5" in out
    assert "$300" in out
    assert "Tesla unveils new battery" in out


def test_summarize_stock_data_caps_news_to_five():
    fast_info = {"last_price": 100}
    news = [f"Headline {i}" for i in range(10)]
    out = summarize_stock_data("ABC", fast_info, "ABC Corp", news)
    assert "Headline 0" in out
    assert "Headline 4" in out
    assert "Headline 5" not in out
