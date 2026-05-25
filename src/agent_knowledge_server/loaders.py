from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from html.parser import HTMLParser
from pathlib import Path
import re
import urllib.request

import fitz


@dataclass
class NormalizedDocument:
    document_id: str
    title: str
    content: str
    content_type: str
    metadata: dict


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if tag in {"p", "div", "h1", "h2", "h3", "li", "br"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self.in_title:
            self.title_parts.append(text)
        self.text_parts.append(text)

    @property
    def title(self) -> str:
        return " ".join(self.title_parts).strip()

    @property
    def text(self) -> str:
        return " ".join(part for part in self.text_parts if part).strip()


def _fingerprint(text: str) -> str:
    return sha1(text.encode("utf-8")).hexdigest()


def _markdown_to_text(raw: str) -> tuple[str, str]:
    heading = ""
    for line in raw.splitlines():
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            break
    cleaned = re.sub(r"[`*_>#-]", " ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, heading


def _html_to_text(raw: str) -> tuple[str, str]:
    parser = _HTMLTextParser()
    parser.feed(raw)
    text = re.sub(r"\s+", " ", parser.text).strip()
    return text, parser.title


def _infer_file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix == ".txt":
        return "text"
    raise ValueError(f"Unsupported file type: {path.suffix or '<none>'}")


def load_file_documents(path: Path) -> tuple[list[NormalizedDocument], dict]:
    path = path.expanduser().resolve()
    content_type = _infer_file_type(path)
    if content_type == "pdf":
        documents: list[NormalizedDocument] = []
        with fitz.open(str(path)) as doc:
            for page_num in range(len(doc)):
                text = doc[page_num].get_text().strip()
                if not text:
                    continue
                documents.append(
                    NormalizedDocument(
                        document_id=f"{path.name}::p{page_num}",
                        title=path.name,
                        content=text,
                        content_type="pdf",
                        metadata={"page": page_num + 1},
                    )
                )
        return documents, {"content_type": "pdf", "title": path.name}

    raw = path.read_text(encoding="utf-8")
    if content_type == "markdown":
        text, title = _markdown_to_text(raw)
    elif content_type == "html":
        text, title = _html_to_text(raw)
    else:
        text, title = raw.strip(), path.stem

    document = NormalizedDocument(
        document_id=f"{path.name}::root",
        title=title or path.name,
        content=text,
        content_type=content_type,
        metadata={},
    )
    return [document], {"content_type": content_type, "title": title or path.name}


def load_url_documents(url: str, source_dir: Path) -> tuple[list[NormalizedDocument], dict]:
    source_dir.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "agent-knowledge-server"})
    with urllib.request.urlopen(request, timeout=20) as response:
        raw_bytes = response.read()
        charset = "utf-8"
        if hasattr(response.headers, "get_content_charset"):
            charset = response.headers.get_content_charset() or "utf-8"
        raw = raw_bytes.decode(charset, errors="replace")

    snapshot_path = source_dir / "snapshot.html"
    snapshot_path.write_text(raw, encoding="utf-8")
    text, title = _html_to_text(raw)
    document = NormalizedDocument(
        document_id=f"url::{_fingerprint(url)}",
        title=title or url,
        content=text,
        content_type="html",
        metadata={"url": url},
    )
    return [document], {
        "content_type": "html",
        "title": title or url,
        "snapshot_path": str(snapshot_path),
        "fingerprint": _fingerprint(text),
    }
