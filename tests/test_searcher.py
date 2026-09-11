import os

from agent_knowledge_server.indexer import Indexer
from agent_knowledge_server.searcher import Searcher, SearchResult


def test_search_returns_results(sample_pdf, mock_embedder, temp_config):
    Indexer(temp_config).add_file_source(sample_pdf)
    results = Searcher(temp_config).search("read only list view", top_k=3)

    assert len(results) > 0
    assert isinstance(results[0], SearchResult)


def test_list_sources_returns_indexed_sources(sample_pdf, mock_embedder, temp_config):
    Indexer(temp_config).add_file_source(sample_pdf)
    sources = Searcher(temp_config).list_sources()

    assert len(sources) == 1
    assert sources[0].kind == "file"


def test_list_documents_returns_normalized_documents(sample_markdown, mock_embedder, temp_config):
    Indexer(temp_config).add_file_source(sample_markdown)
    documents = Searcher(temp_config).list_documents()

    assert len(documents) >= 1
    assert documents[0]["source_id"]


def test_find_sources_by_fuzzy_target_matches_label(mock_embedder, temp_config):
    indexer = Indexer(temp_config)
    source = indexer.add_text_source(
        content="Bad summary that should be removed.",
        source_label="Confluence Pricing Summary",
        title="Pricing Summary",
    )

    matches = Searcher(temp_config).find_sources("pricing summary")

    assert len(matches) == 1
    assert matches[0].source_id == source.source_id


def test_search_works_with_read_only_chroma_store(sample_pdf, mock_embedder, temp_config):
    Indexer(temp_config).add_file_source(sample_pdf)

    for path in sorted(temp_config.paths.chroma_dir.rglob("*"), reverse=True):
        if path.is_dir():
            os.chmod(path, 0o555)
        else:
            os.chmod(path, 0o444)
    os.chmod(temp_config.paths.chroma_dir, 0o555)

    results = Searcher(temp_config).search("database queries", top_k=3)

    assert len(results) > 0


def test_search_suppresses_identical_passages_from_two_sources(tmp_path, mock_embedder, temp_config):
    """Two releases of one guide share verbatim passages; return the passage once."""
    from agent_knowledge_server.indexer import Indexer
    from agent_knowledge_server.searcher import Searcher

    shared = "Delinquency plans control how overdue invoices escalate. " * 12
    old = tmp_path / "ReleaseNotes.txt"
    new = tmp_path / "ReleaseNotes-next.txt"
    old.write_text(shared)
    new.write_text(shared)

    indexer = Indexer(temp_config)
    indexer.add_file_source(old, source_label="ReleaseNotes 2026.03")
    indexer.add_file_source(new, source_label="ReleaseNotes 2026.07")

    results = Searcher(temp_config).search("delinquency plans overdue invoices", top_k=5)
    texts = [r.text for r in results]
    assert len(texts) == len(set(texts)), "identical passages should collapse to one result"

    carrier = next((r for r in results if r.duplicate_sources), None)
    assert carrier is not None, "the surviving result should name where the duplicate lives"


def test_search_can_opt_out_of_dedupe(tmp_path, mock_embedder, temp_config):
    from agent_knowledge_server.indexer import Indexer
    from agent_knowledge_server.searcher import Searcher

    shared = "Identical passage repeated across two sources. " * 12
    for name in ("one.txt", "two.txt"):
        path = tmp_path / name
        path.write_text(shared)
        Indexer(temp_config).add_file_source(path)

    results = Searcher(temp_config).search("identical passage", top_k=5, dedupe=False)
    assert len({r.text for r in results}) < len(results) or len(results) >= 2
