from agent_knowledge_server.indexer import Indexer


def test_add_file_source_indexes_chunks(sample_pdf, mock_embedder, temp_config):
    indexer = Indexer(temp_config)
    source = indexer.add_file_source(sample_pdf)

    assert source.status == "indexed"
    assert source.content_type == "pdf"
    assert len(source.documents) >= 1


def test_refresh_source_replaces_existing_chunks(sample_pdf, mock_embedder, temp_config):
    indexer = Indexer(temp_config)
    source = indexer.add_file_source(sample_pdf)
    refreshed = indexer.refresh_source(source.source_id)

    assert refreshed.source_id == source.source_id
    assert refreshed.status == "indexed"


def test_forget_source_removes_registry_entry(sample_pdf, mock_embedder, temp_config):
    indexer = Indexer(temp_config)
    source = indexer.add_file_source(sample_pdf)

    indexer.forget_source(source.source_id)

    assert indexer.registry.get(source.source_id) is None


def test_add_text_source_indexes_llm_provided_content(mock_embedder, temp_config):
    indexer = Indexer(temp_config)
    source = indexer.add_text_source(
        content="Confluence pricing guidance and policy details.",
        source_label="Confluence: Pricing Guide",
        title="Pricing Guide",
        source_kind="llm_text",
        original_ref="confluence://pricing-guide",
    )

    assert source.status == "indexed"
    assert source.kind == "text"
    assert source.title == "Pricing Guide"


def test_import_pdf_folder_adds_each_pdf_as_individual_source(tmp_path, sample_pdf, mock_embedder, temp_config):
    folder = tmp_path / "pdfs"
    folder.mkdir()
    first = folder / "GuideA.pdf"
    second = folder / "GuideB.pdf"
    first.write_bytes(sample_pdf.read_bytes())
    second.write_bytes(sample_pdf.read_bytes())

    imported = Indexer(temp_config).import_pdf_folder(folder)

    assert len(imported) == 2
    assert all(source.kind == "file" for source in imported)
