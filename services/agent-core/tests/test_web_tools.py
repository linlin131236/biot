from unittest.mock import patch
from bolt_core.web_tools import web_search, web_extract, SearchResult, ExtractResult


def test_web_search_returns_results_with_mock():
    mock_data = [{"title": "Test", "url": "https://example.com", "description": "A test result"}]
    with patch("bolt_core.web_tools.urllib.request.urlopen") as mock_urlopen:
        import io
        import json
        mock_response = io.BytesIO(json.dumps(mock_data).encode("utf-8"))
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *a: None
        mock_response.read = mock_response.read1
        mock_urlopen.return_value = mock_response

        results = web_search("test query")

        assert len(results) >= 1
        assert results[0].title == "Test"


def test_web_search_returns_empty_on_failure():
    with patch("bolt_core.web_tools.urllib.request.urlopen", side_effect=Exception("network error")):
        results = web_search("test query")
        assert results == []


def test_web_extract_returns_content_with_mock():
    html = "<html><body><p>Hello World</p></body></html>"
    with patch("bolt_core.web_tools.urllib.request.urlopen") as mock_urlopen:
        import io
        mock_response = io.BytesIO(html.encode("utf-8"))
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *a: None
        mock_response.read = lambda: html.encode("utf-8")
        mock_urlopen.return_value = mock_response

        results = web_extract(["https://example.com"])

        assert len(results) == 1
        assert "Hello World" in results[0].content
        assert results[0].error is None


def test_web_extract_handles_failure():
    with patch("bolt_core.web_tools.urllib.request.urlopen", side_effect=Exception("connection error")):
        results = web_extract(["https://fail.test"])

        assert len(results) == 1
        assert results[0].content == ""
        assert results[0].error is not None
