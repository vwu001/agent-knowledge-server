from dataclasses import dataclass

from agent_knowledge_server.validation import (
    MIN_CONTENT_CHARS,
    assess_extraction,
    detect_version,
    normalize_for_dedupe,
)


@dataclass
class FakeDoc:
    content: str


# The exact text that docs.guidewire.com stored for five URL sources: the SPA
# shell, recorded as a successful index with no error.
JS_SHELL = "Guidewire Documentation You need to enable JavaScript to run this app."


def test_rejects_javascript_app_shell():
    problem = assess_extraction([FakeDoc(JS_SHELL)], origin="https://docs.example.com/page")
    assert problem is not None
    assert "JavaScript app shell" in problem
    assert "https://docs.example.com/page" in problem
    assert "force=true" in problem


def test_rejects_empty_text():
    problem = assess_extraction([FakeDoc("   ")])
    assert problem is not None
    assert "no text at all" in problem


def test_rejects_text_below_minimum():
    problem = assess_extraction([FakeDoc("short but real")])
    assert problem is not None
    assert str(MIN_CONTENT_CHARS) in problem


def test_accepts_substantial_text():
    assert assess_extraction([FakeDoc("word " * 200)]) is None


def test_accepts_text_split_across_documents():
    # A PDF arrives as one document per page; no single page need clear the bar.
    docs = [FakeDoc("page one " * 20), FakeDoc("page two " * 20)]
    assert assess_extraction(docs) is None


def test_detect_version_picks_most_frequent_stamp():
    docs = [
        FakeDoc("Guidewire 2026.07.0 What's new in Qusar"),
        FakeDoc("footer 2026.07.0 again"),
        FakeDoc("a stray mention of 2026.03.0"),
    ]
    assert detect_version(docs) == "2026.07.0"


def test_detect_version_returns_fallback_when_absent():
    assert detect_version([FakeDoc("no version here")], fallback="unknown") == "unknown"


def test_normalize_for_dedupe_ignores_whitespace_and_case():
    assert normalize_for_dedupe("Hello   World\n") == normalize_for_dedupe("hello world")
    assert normalize_for_dedupe("alpha") != normalize_for_dedupe("beta")
