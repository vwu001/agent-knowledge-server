from local_knowledge_mcp.server import (
    handle_add,
    handle_add_text_source,
    handle_forget,
    handle_list_documents,
    handle_list_sources,
    handle_refresh,
    handle_search,
)


def test_handle_add_file_indexes_source(sample_pdf, mock_embedder, temp_config):
    result = handle_add({"file_path": str(sample_pdf)}, temp_config)
    assert "indexed" in result.lower()


def test_handle_list_sources_returns_added_source(sample_pdf, mock_embedder, temp_config):
    handle_add({"file_path": str(sample_pdf)}, temp_config)
    result = handle_list_sources({}, temp_config)
    assert sample_pdf.name in result


def test_handle_search_returns_text(sample_pdf, mock_embedder, temp_config):
    handle_add({"file_path": str(sample_pdf)}, temp_config)
    result = handle_search({"query": "database queries"}, temp_config)
    assert "Query.make" in result


def test_handle_refresh_and_forget(sample_pdf, mock_embedder, temp_config):
    add_result = handle_add({"file_path": str(sample_pdf)}, temp_config)
    source_id = add_result.split("source_id=")[1].strip()

    refreshed = handle_refresh({"source_id": source_id}, temp_config)
    forgotten = handle_forget({"source_id": source_id}, temp_config)

    assert "refreshed" in refreshed.lower()
    assert "forgot" in forgotten.lower()


def test_handle_list_documents_returns_document_titles(sample_markdown, mock_embedder, temp_config):
    handle_add({"file_path": str(sample_markdown)}, temp_config)
    result = handle_list_documents({}, temp_config)
    assert "notes.md" in result.lower() or "notes" in result.lower()


def test_handle_add_text_source_indexes_llm_content(mock_embedder, temp_config):
    result = handle_add_text_source(
        {
            "content": "Repository onboarding notes for local setup.",
            "source_label": "repo onboarding notes",
            "title": "Onboarding Notes",
            "original_ref": "repo:/README.md",
        },
        temp_config,
    )
    assert "indexed" in result.lower()


def test_handle_forget_supports_fuzzy_target(mock_embedder, temp_config):
    handle_add_text_source(
        {
            "content": "This is not right and should be forgotten.",
            "source_label": "wrong pricing note",
            "title": "Wrong Pricing Note",
        },
        temp_config,
    )
    result = handle_forget({"fuzzy_target": "pricing note"}, temp_config)
    assert "forgot" in result.lower()
