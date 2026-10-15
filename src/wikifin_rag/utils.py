import tiktoken

from wikifin_rag.config import DEFAULT_LLM_MODEL


def num_tokens_from_message(message, model=DEFAULT_LLM_MODEL):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("o200k_base")

    return len(encoding.encode(message))
