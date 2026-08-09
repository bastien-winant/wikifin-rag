import json
from pathlib import Path
import tqdm

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT_DIR / "data" / "faq_corpus.jsonl"

def load_faq_data():
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return [json.loads(line.strip()) for line in f if line.strip()]


def embed_texts(texts):
    batch_size = 50
    vectors = []

    for i in tqdm(range(0, len(texts), batch_size)):
        batch = texts[i:i + batch_size]
        batch_vectors = model.encode(batch)
        vectors.extend(batch_vectors)