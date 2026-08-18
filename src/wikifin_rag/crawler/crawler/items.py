from dataclasses import dataclass
from datetime import date as Date


@dataclass
class Chunk:
    chunk_id: str
    source_url: str
    language: str | None = None
    updated_on: Date | None = None
    category: str | None = None
    description: str | None = None
    title: str | None = None
    html: str | None = None
    content: str | None = None
    related_links: str | None = None


@dataclass
class Batch:
    chunks: list[Chunk]
    size: int
    on_full_callback: function | None = None
    clear_on_full: bool | None = False

    def clear_chunks(self):
        self.chunks.clear()

    def add_chunk(self, data):
        self.chunks.append(Chunk(**data))

        if self.is_full():
            if self.on_full_callback:
                self.on_full_callback(self.chunks)

            if self.clear_on_full:
                self.clear_chunks()

    def length(self):
        return len(self.chunks)

    def is_full(self):
        return len(self.chunks) >= self.size

    def is_empty(self):
        return len(self.chunks) == 0