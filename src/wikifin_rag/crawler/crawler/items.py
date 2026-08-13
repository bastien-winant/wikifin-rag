from dataclasses import dataclass
from datetime import date as Date


@dataclass
class DocumentItem:
    source_url: str
    language: str | None = None
    title: str | None = None
    description: str | None = None
    date: Date | None = None
    html: str  | None = None
    related_links: str  | None = None