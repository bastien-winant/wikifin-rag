from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INDEX_NAME = "wikifin-search"
EMBED_MODEL = "Xenova/multilingual-e5-small"
EMBED_DIM = 384
DEFAULT_LLM_MODEL = "gpt-5.4-mini"