from wikifin_rag.search import rff_search

_DESCRIPTION = (
    "Search the Dutch document database for entries matching the given query. "
    "Accepts queries in any language; full-text matching uses a Dutch translation internally."
)

search_tool = {
    "type": "function",
    "name": "search",
    "description": _DESCRIPTION,
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query text to look up in the document database."
            }
        },
        "required": ["query"],
        "additionalProperties": False
    }
}

TOOL_FUNCTIONS = {
    "search": rff_search,
}

__all__ = ["search_tool", "TOOL_FUNCTIONS"]
