from dataclasses import dataclass
from datetime import date as Date


@dataclass
class Document:
    id: str
    source_url: str
    language: str | None = None
    updated_on: Date | None = None
    title: str | None = None
    description: str | None = None
    section: str | None = None
    html: str | None = None
    content: str | None = None
    related_links: str | None = None


@dataclass
class Batch:
    documents: list[Document]
    size: int
    on_full_callback: function | None = None
    clear_on_full: bool | None = False

    def clear_documents(self):
        self.documents.clear()

    def add_document(self, data):
        self.documents.append(Document(**data))

        if self.is_full():
            if self.on_full_callback:
                self.on_full_callback(self.documents)

            if self.clear_on_full:
                self.clear_documents()

    def length(self):
        return len(self.documents)

    def is_full(self):
        return len(self.documents) >= self.size

    def is_empty(self):
        return len(self.documents) == 0