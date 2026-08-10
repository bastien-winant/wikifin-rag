from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
FAQ_DATA_PATH = ROOT_DIR / "data" / "faq_corpus.jsonl"
TIP_DATA_PATH = ROOT_DIR / "data" / "tip_corpus.jsonl"