import threading
import time

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


def test_mutating_operations_are_serialized_across_indexers(mock_embedder, temp_config, monkeypatch):
    active_writers = 0
    max_active_writers = 0
    lock = threading.Lock()
    entered = threading.Event()

    original = Indexer._index_documents

    def wrapped(self, record, documents, meta):
        nonlocal active_writers, max_active_writers
        with lock:
            active_writers += 1
            max_active_writers = max(max_active_writers, active_writers)
            entered.set()
        time.sleep(0.2)
        try:
            return original(self, record, documents, meta)
        finally:
            with lock:
                active_writers -= 1

    monkeypatch.setattr(Indexer, "_index_documents", wrapped)

    indexer_a = Indexer(temp_config)
    indexer_b = Indexer(temp_config)
    results = []

    def add_note(indexer, label):
        results.append(
            indexer.add_text_source(
                content=f"{label} knowledge",
                source_label=label,
                title=label,
            )
        )

    first = threading.Thread(target=add_note, args=(indexer_a, "Note A"))
    second = threading.Thread(target=add_note, args=(indexer_b, "Note B"))

    first.start()
    entered.wait(timeout=1)
    second.start()
    first.join()
    second.join()

    assert len(results) == 2
    assert max_active_writers == 1
