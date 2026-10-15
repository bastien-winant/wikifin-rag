"""Translate search queries to Dutch for full-text search over Dutch documents."""

from dotenv import load_dotenv
from openai import OpenAI

from wikifin_rag.config import DEFAULT_LLM_MODEL

load_dotenv(override=True)

_client = OpenAI()
_TRANSLATE_MODEL = DEFAULT_LLM_MODEL

_SYSTEM = ("""
    You translate search queries into Dutch for retrieval over a Dutch document corpus.
    If the query is already Dutch, return it unchanged.
    Preserve named entities, product names, numbers, and acronyms.
    Return only the query text, with no quotes or explanation.
""").strip()


def to_dutch_query(query: str) -> str | None:
    """Return a Dutch version of ``query`` for FTS, or ``None`` on failure."""
    query = (query or "").strip()
    if not query:
        return None

    try:
        response = _client.responses.create(
            model=_TRANSLATE_MODEL,
            instructions=_SYSTEM,
            input=query,
            temperature=0.0,
            max_output_tokens=200,
        )
        translated = (response.output_text or "").strip()
        return translated or None
    except Exception:
        return None
