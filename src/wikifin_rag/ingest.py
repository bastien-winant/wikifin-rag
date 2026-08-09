import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "faq_corpus.jsonl"

def load_faq_data():
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return [json.loads(line.strip()) for line in f if line.strip()]