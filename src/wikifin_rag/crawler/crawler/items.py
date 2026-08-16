from dataclasses import dataclass
from datetime import date as Date


@dataclass
class Chunk:
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


@dataclass
class Batch:
    chunks: list[Chunk]

    def clear_items(self):
        self.chunks.clear()

    def add_item(self, data):
        self.chunks.append(Chunk(**data))

    def length(self):
        return len(self.chunks)