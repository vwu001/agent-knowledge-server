"""End-to-end cover for the ingestion guards, labelling, and folder sync."""

from unittest.mock import MagicMock

import pytest

from agent_knowledge_server.indexer import Indexer
from agent_knowledge_server.server import handle_add, handle_list_sources, handle_sync_folder
from agent_knowledge_server.validation import EmptyExtractionError

# Byte-for-byte what docs.guidewire.com stored for five URL sources.
SPA_SHELL_HTML = (
    b"<html><head><title>Guidewire Documentation</title></head>"
    b"<body><noscript>You need to enable JavaScript to run this app.</noscript>"
    b'<div id="root"></div></body></html>'
)

REAL_PAGE_HTML = (
    b"<html><head><title>Real Page</title></head><body><p>"
    + b"Substantial documentation content. " * 20
    + b"</p></body></html>"
)


def _mock_fetch(monkeypatch, payload: bytes):
    response = MagicMock()
    response.read.return_value = payload
    response.headers.get_content_charset.return_value = "utf-8"
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: response)


def test_url_returning_js_shell_is_not_recorded_as_indexed(monkeypatch, mock_embedder, temp_config):
    _mock_fetch(monkeypatch, SPA_SHELL_HTML)
    indexer = Indexer(temp_config)

    with pytest.raises(EmptyExtractionError):
        indexer.add_url_source("https://docs.example.com/spa-page")

    record = indexer.registry.get(indexer.registry._source_id("url", "https://docs.example.com/spa-page"))
    assert record is not None
    assert record.status == "empty"
    assert "JavaScript app shell" in record.error


def test_handle_add_reports_refusal_instead_of_raising(monkeypatch, mock_embedder, temp_config):
    _mock_fetch(monkeypatch, SPA_SHELL_HTML)
    result = handle_add({"url": "https://docs.example.com/spa-page"}, temp_config)
    assert result.startswith("Refused to index:")
    assert "force=true" in result


def test_force_overrides_the_guard(monkeypatch, mock_embedder, temp_config):
    _mock_fetch(monkeypatch, SPA_SHELL_HTML)
    source = Indexer(temp_config).add_url_source("https://docs.example.com/spa-page", force=True)
    assert source.status == "indexed"


def test_real_url_still_indexes_with_a_custom_label(monkeypatch, mock_embedder, temp_config):
    _mock_fetch(monkeypatch, REAL_PAGE_HTML)
    source = Indexer(temp_config).add_url_source(
        "https://docs.example.com/real", source_label="APD adoption guide"
    )
    assert source.status == "indexed"
    # Without a label this would fall back to the page <title>.
    assert source.source_label == "APD adoption guide"


def test_short_local_file_is_allowed(sample_text, mock_embedder, temp_config):
    # A short file the user explicitly named is deliberate; only fetches get a floor.
    source = Indexer(temp_config).add_file_source(sample_text)
    assert source.status == "indexed"


def test_file_source_accepts_label_and_detects_version(tmp_path, mock_embedder, temp_config):
    note = tmp_path / "release.txt"
    note.write_text("Guidewire 2026.07.0 Application Guide. " * 10)
    source = Indexer(temp_config).add_file_source(note, source_label="BC App Guide")
    assert source.source_label == "BC App Guide"
    assert source.version == "2026.07.0"


def test_list_sources_surfaces_the_error_for_empty_sources(monkeypatch, mock_embedder, temp_config):
    _mock_fetch(monkeypatch, SPA_SHELL_HTML)
    handle_add({"url": "https://docs.example.com/spa-page"}, temp_config)
    listing = handle_list_sources({}, temp_config)
    assert "empty" in listing
    assert "JavaScript app shell" in listing


class TestSyncFolder:
    def test_adds_new_and_reports_unchanged(self, tmp_path, mock_embedder, temp_config):
        folder = tmp_path / "docs"
        folder.mkdir()
        (folder / "a.txt").write_text("alpha content here " * 10)
        (folder / "b.txt").write_text("beta content here " * 10)

        indexer = Indexer(temp_config)
        first = indexer.sync_folder(folder, pattern="*.txt")
        assert sorted(first["added"]) == ["a.txt", "b.txt"]

        second = indexer.sync_folder(folder, pattern="*.txt")
        assert second["added"] == []
        assert sorted(second["unchanged"]) == ["a.txt", "b.txt"]

    def test_reindexes_changed_file(self, tmp_path, mock_embedder, temp_config):
        folder = tmp_path / "docs"
        folder.mkdir()
        target = folder / "a.txt"
        target.write_text("original content " * 10)

        indexer = Indexer(temp_config)
        indexer.sync_folder(folder, pattern="*.txt")
        target.write_text("completely different content " * 10)
        report = indexer.sync_folder(folder, pattern="*.txt")

        assert report["updated"] == ["a.txt"]
        assert report["unchanged"] == []

    def test_reports_indexed_file_that_disappeared(self, tmp_path, mock_embedder, temp_config):
        folder = tmp_path / "docs"
        folder.mkdir()
        target = folder / "gone.txt"
        target.write_text("content that will vanish " * 10)

        indexer = Indexer(temp_config)
        indexer.sync_folder(folder, pattern="*.txt")
        target.unlink()
        report = indexer.sync_folder(folder, pattern="*.txt")

        assert len(report["missing"]) == 1
        assert "gone" in report["missing"][0]

    def test_backfills_fingerprint_without_reindexing(self, tmp_path, mock_embedder, temp_config):
        folder = tmp_path / "docs"
        folder.mkdir()
        target = folder / "a.txt"
        target.write_text("legacy content " * 10)

        indexer = Indexer(temp_config)
        source = indexer.add_file_source(target)
        # Simulate a record written before file fingerprints existed.
        source.file_fingerprint = ""
        indexer.registry.save(source)

        report = indexer.sync_folder(folder, pattern="*.txt")
        assert report["backfilled"] == ["a.txt"]
        assert indexer.registry.get(source.source_id).file_fingerprint

    def test_handler_renders_a_readable_report(self, tmp_path, mock_embedder, temp_config):
        folder = tmp_path / "docs"
        folder.mkdir()
        (folder / "a.txt").write_text("alpha content here " * 10)
        out = handle_sync_folder({"dir": str(folder), "pattern": "*.txt"}, temp_config)
        assert "Synced" in out
        assert "added (1)" in out
        assert "a.txt" in out
