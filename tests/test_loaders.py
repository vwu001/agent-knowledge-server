from io import BytesIO
from unittest.mock import MagicMock

from agent_knowledge_server.loaders import load_file_documents, load_url_documents


def test_load_file_documents_supports_pdf(sample_pdf):
    docs, meta = load_file_documents(sample_pdf)
    assert meta["content_type"] == "pdf"
    assert len(docs) == 2


def test_load_file_documents_supports_markdown(sample_markdown):
    docs, meta = load_file_documents(sample_markdown)
    assert meta["content_type"] == "markdown"
    assert "markdown knowledge note" in docs[0].content.lower()


def test_load_file_documents_supports_html(sample_html):
    docs, meta = load_file_documents(sample_html)
    assert meta["content_type"] == "html"
    assert meta["title"] == "Example Page"


def test_load_url_documents_saves_snapshot(tmp_path, monkeypatch):
    response = MagicMock()
    response.read.return_value = b"<html><head><title>Remote</title></head><body><p>Fetched page</p></body></html>"
    response.headers.get_content_charset.return_value = "utf-8"
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: response)

    source_dir = tmp_path / "source"
    docs, meta = load_url_documents("https://example.com", source_dir)

    assert meta["title"] == "Remote"
    assert (source_dir / "snapshot.html").exists()
    assert "Fetched page" in docs[0].content
