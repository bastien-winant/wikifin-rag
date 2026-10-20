from dataclasses import dataclass, field
from datetime import date as Date


@dataclass
class Document:
    id: str
    title: str
    description: str
    section: str
    html: str
    content: str
    source_url: str
    language: str
    updated_on: Date | None = None
    related_links: str | None = None


@dataclass
class Batch:
    documents: list[Document]
    size: int
    on_full_callback: function | None = None
    clear_on_full: bool | None = False
    _document_ids: set[str] = field(default_factory=set, init=False, repr=False)

    def clear_documents(self):
        self.documents.clear()
        self._document_ids.clear()

    def add_document(self, data):
        document_id = data.get("id")

        if document_id is None or document_id in self._document_ids:
            return

        if data.get("title") is None:
            data["title"] = ""

        if data.get("description") is None:
            data["description"] = ""

        if data.get("section") is None:
            data["section"] = ""

        if data.get("content") is None:
            return

        document = Document(**data)
        self.documents.append(document)
        self._document_ids.add(document_id)

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