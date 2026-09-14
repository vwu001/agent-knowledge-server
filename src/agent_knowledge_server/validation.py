"""Guards against silently indexing content that carries no information.

The motivating failure: ``load_url_documents`` fetches with ``urllib``, which does
not execute JavaScript. Pointed at a single-page-app documentation site it stores
the loading shell -- e.g. ``"Guidewire Documentation You need to enable JavaScript
to run this app."`` -- and the source is recorded as ``status="indexed"`` with no
error. The source then never matches a query, and nothing tells you why.
"""

from __future__ import annotations

from pathlib import Path
import re

# Text shorter than this almost never carries retrievable information. The
# observed JS shells were ~70 characters; real doc pages run to thousands.
MIN_CONTENT_CHARS = 200

# Phrases that identify a client-side-rendered shell rather than real content.
JS_SHELL_MARKERS = (
    "you need to enable javascript",
    "please enable javascript",
    "javascript is required",
    "enable javascript to run this app",
    "this site requires javascript",
)

# Guidewire-style release stamps, e.g. "2026.07.0". Kept general enough to catch
# any YYYY.MM(.P) product version that appears in a document's own text.
_VERSION_RE = re.compile(r"\b(20\d{2}\.\d{2}(?:\.\d+)?)\b")

# Minimum share of scanned pages a version must appear on to count as this
# document's release. Real footers land on most pages; incidental body-text mentions
# sit far below. Measured over 41 Guidewire PDFs: documents with a real release
# footer scored 0.59-0.97, documents without one scored 0.00-0.12. The cutoff sits
# in that gap and is not delicate.
_VERSION_PAGE_SHARE = 0.20

# Guidewire ships releases under ski-resort codenames. Some guides (for example the
# ContactManager guide and the Gosu reference) never print the release in their own
# text, so a codename in the filename is the only signal available.
_RELEASE_CODENAMES = {
    "qusar": "2026.07.0",
    "palisades": "2026.03.0",
    "olos": "2025.11.0",
    "oslo": "2025.11.0",  # some downloads use this spelling
    "niseko": "2025.07.0",
    "mammoth": "2025.04.0",
    "lasleñas": "2024.11.0",
    "lasarenas": "2024.11.0",
    "kufri": "2024.08.0",
    "jasper": "2024.03.0",
    "innsbruck": "2023.11.0",
    "hakuba": "2023.08.0",
    "garmisch": "2023.04.0",
}


def version_from_filename(name: str) -> str:
    """Release version implied by a codename in a filename, or "".

    Only used as a fallback when a document does not stamp its own release. Matching
    is deliberately conservative: the codename must appear as a separate token (for
    example ``whatsnew-qusar.pdf`` or ``ContactMgmtGuide-qusar.pdf``), so an
    unsuffixed filename yields "" rather than a guess. An unsuffixed file means
    "whatever release was current when it was downloaded", which is not recoverable
    from the name.
    """
    stem = Path(name).stem.lower()
    tokens = {token for token in re.split(r"[^a-z0-9]+", stem) if token}
    for codename, version in _RELEASE_CODENAMES.items():
        if codename in tokens:
            return version
    return ""


class EmptyExtractionError(ValueError):
    """Raised when a loader produced no usable text."""


def _joined_text(documents) -> str:
    return "\n".join(getattr(doc, "content", "") or "" for doc in documents).strip()


def assess_extraction(
    documents,
    *,
    origin: str = "source",
    min_chars: int = MIN_CONTENT_CHARS,
) -> str | None:
    """Return a human-readable problem description, or None when the text looks usable.

    ``documents`` is any iterable of objects exposing ``.content``.

    ``min_chars=0`` disables the length floor while keeping the JS-shell and
    no-text-at-all checks. Callers use that for local files: a short file the user
    explicitly pointed at is a deliberate act, whereas a short *fetch* is nearly
    always a failure. An empty extraction is still rejected either way, which is
    what catches scanned PDFs with no text layer.
    """
    text = _joined_text(documents)
    lowered = text.lower()

    for marker in JS_SHELL_MARKERS:
        if marker in lowered:
            return (
                f"{origin} returned a JavaScript app shell, not page content "
                f"({len(text)} chars, matched {marker!r}). This fetcher does not run "
                "JavaScript. Save the page as a PDF and add the file, or paste the text "
                "via add_text_source. Pass force=true to index it anyway."
            )

    if not text:
        return (
            f"{origin} produced no text at all. Pass force=true to index it anyway."
        )

    if min_chars and len(text) < min_chars:
        return (
            f"{origin} produced only {len(text)} characters, below the "
            f"{min_chars}-character minimum, so it is unlikely to be usable "
            "content. Pass force=true to index it anyway."
        )

    return None


def detect_version(documents, *, fallback: str = "") -> str:
    """Best-effort product version stamped in the document text.

    Guidewire prints a release on nearly every page footer ("Guidewire ... 2026.07.0
    ... Application Guide"), which lets search results and dedupe distinguish two
    releases of the same guide. Returns the most frequent match, or ``fallback``.

    A release footer appears on a large share of a document's pages, so the winning
    match must clear ``_VERSION_PAGE_SHARE`` of the pages scanned. Without that
    threshold an incidental body-text mention wins on a document that has no footer
    at all: the ContactManager guide names ``2020.05`` four times across ~350 pages
    and would otherwise be stamped with it, outranking a correct filename fallback.
    """
    page_texts = [(getattr(doc, "content", "") or "") for doc in documents]
    if not any(text.strip() for text in page_texts):
        return fallback

    # Count pages containing each version rather than raw occurrences, so a single
    # page repeating a version many times cannot outvote a genuine footer.
    pages_scanned = 0
    counts: dict[str, int] = {}
    budget = 200_000
    for text in page_texts:
        if budget <= 0:
            break
        budget -= len(text)
        pages_scanned += 1
        for match in set(_VERSION_RE.findall(text)):
            counts[match] = counts.get(match, 0) + 1

    if not counts or not pages_scanned:
        return fallback

    version, pages_seen = max(counts.items(), key=lambda item: (item[1], item[0]))
    if pages_seen / pages_scanned < _VERSION_PAGE_SHARE:
        return fallback
    return version


def normalize_for_dedupe(text: str) -> str:
    """Collapse whitespace and case so identical passages compare equal.

    Deliberately conservative: only exact matches after normalization are treated
    as duplicates, so genuinely different passages are never suppressed.
    """
    return " ".join((text or "").split()).lower()
