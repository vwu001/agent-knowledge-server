from dataclasses import dataclass

from agent_knowledge_server.validation import (
    MIN_CONTENT_CHARS,
    assess_extraction,
    detect_version,
    normalize_for_dedupe,
    version_from_filename,
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


def test_version_from_filename_reads_release_codename():
    assert version_from_filename("whatsnew-qusar.pdf") == "2026.07.0"
    assert version_from_filename("ContactMgmtGuide-qusar.pdf") == "2026.07.0"
    assert version_from_filename("whatsnew-palisades.pdf") == "2026.03.0"
    assert version_from_filename("whatsnew-niseko.pdf") == "2025.07.0"


def test_version_from_filename_requires_a_separate_token():
    # An unsuffixed name means "whatever release was current at download time",
    # which is not recoverable from the name -- do not guess.
    assert version_from_filename("ContactMgmtGuide.pdf") == ""
    assert version_from_filename("GosuRefGuide.pdf") == ""
    assert version_from_filename("ConfigBC.pdf") == ""
    # A codename embedded in a larger word is not a match.
    assert version_from_filename("prequsarial-notes.pdf") == ""


def test_detect_version_prefers_document_text_over_filename_fallback():
    docs = [FakeDoc("Guidewire 2026.07.0 What's new"), FakeDoc("Guidewire 2026.07.0 page 2")]
    assert detect_version(docs, fallback=version_from_filename("SomeGuide-palisades.pdf")) == "2026.07.0"


def test_detect_version_uses_filename_fallback_when_text_has_none():
    docs = [FakeDoc("this guide never prints its release")]
    assert detect_version(docs, fallback=version_from_filename("ContactMgmtGuide-qusar.pdf")) == "2026.07.0"


def test_normalize_for_dedupe_ignores_whitespace_and_case():
    assert normalize_for_dedupe("Hello   World\n") == normalize_for_dedupe("hello world")
    assert normalize_for_dedupe("alpha") != normalize_for_dedupe("beta")


def test_detect_version_ignores_incidental_mentions_below_page_threshold():
    # A version named on a couple of pages of a long document is not that
    # document's release; the ContactManager guide names 2020.05 four times across
    # ~350 pages and has no release footer at all.
    docs = [FakeDoc("mentions 2020.05 once")] + [FakeDoc("ordinary body text") for _ in range(50)]
    assert detect_version(docs) == ""
    assert detect_version(docs, fallback="2026.07.0") == "2026.07.0"


def test_detect_version_counts_pages_not_occurrences():
    # One page repeating a version must not outvote a footer on every page.
    docs = [FakeDoc("2025.01.0 " * 50)] + [FakeDoc("Guidewire 2026.07.0 footer") for _ in range(9)]
    assert detect_version(docs) == "2026.07.0"
