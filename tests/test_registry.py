from local_knowledge_mcp.registry import SourceRegistry


def test_upsert_file_source_persists_record(sample_pdf, temp_config):
    registry = SourceRegistry(temp_config)
    source = registry.upsert_file(sample_pdf)

    assert source.kind == "file"
    assert source.original == str(sample_pdf)
    assert registry.get(source.source_id) is not None


def test_upsert_url_source_persists_record(temp_config):
    registry = SourceRegistry(temp_config)
    source = registry.upsert_url("https://example.com/page")

    assert source.kind == "url"
    assert source.original == "https://example.com/page"


def test_delete_source_removes_record(sample_pdf, temp_config):
    registry = SourceRegistry(temp_config)
    source = registry.upsert_file(sample_pdf)
    registry.delete(source.source_id)

    assert registry.get(source.source_id) is None
