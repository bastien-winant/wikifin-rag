from dataclasses import dataclass
from datetime import date as Date


@dataclass
class DocumentItem:
    document_id: str
    chunk_id: str
    source_url: str
    language: str | None = None
    date: Date | None = None
    category: str | None = None
    description: str | None = None
    title: str | None = None
    html: str | None = None
    content: str | None = None
    related_links: str | None = None