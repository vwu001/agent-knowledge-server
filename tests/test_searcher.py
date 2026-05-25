from local_knowledge_mcp.indexer import Indexer
from local_knowledge_mcp.searcher import Searcher, SearchResult


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
