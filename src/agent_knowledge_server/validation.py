"""Guards against silently indexing content that carries no information.

The motivating failure: ``load_url_documents`` fetches with ``urllib``, which does
not execute JavaScript. Pointed at a single-page-app documentation site it stores
the loading shell -- e.g. ``"Guidewire Documentation You need to enable JavaScript
to run this app."`` -- and the source is recorded as ``status="indexed"`` with no
error. The source then never matches a query, and nothing tells you why.
"""

from __future__ import annotations

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
    """
    text = _joined_text(documents)
    if not text:
        return fallback
    matches = _VERSION_RE.findall(text[:200_000])
    if not matches:
        return fallback
    counts: dict[str, int] = {}
    for match in matches:
        counts[match] = counts.get(match, 0) + 1
    return max(counts.items(), key=lambda item: (item[1], item[0]))[0]


def normalize_for_dedupe(text: str) -> str:
    """Collapse whitespace and case so identical passages compare equal.

    Deliberately conservative: only exact matches after normalization are treated
    as duplicates, so genuinely different passages are never suppressed.
    """
    return " ".join((text or "").split()).lower()
