import logging
from datetime import date
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from wikifin_rag.config import EMBED_MODEL, PROJECT_ROOT
from wikifin_rag.download import ensure_embedding_model

_DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / EMBED_MODEL

_logger = logging.getLogger(__name__)
try:
    _log_dir = PROJECT_ROOT / "logs" / "embedder"
    _log_dir.mkdir(parents=True, exist_ok=True)
    _fh = logging.FileHandler(_log_dir / f"{date.today().strftime('%d_%m_%y')}.log")
    _fh.setLevel(logging.WARNING)
    _fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    _logger.addHandler(_fh)
except OSError:
    _logger.addHandler(logging.NullHandler())


class Embedder:
    def __init__(self, path=_DEFAULT_MODEL_PATH):
        path = Path(path)
        if path == _DEFAULT_MODEL_PATH:
            path = ensure_embedding_model()

        self.tokenizer = Tokenizer.from_file(str(path / "tokenizer.json"))
        self.session = ort.InferenceSession(
            str(path / "model.onnx"), providers=["CPUExecutionProvider"]
        )
        self.input_names = {inp.name for inp in self.session.get_inputs()}
        self.logger = _logger

    def encode(self, text, normalize=True):
        return self.encode_batch([text], normalize=normalize)[0]

    def encode_batch(self, texts, normalize=True):
        try:
            self.tokenizer.enable_padding()
            encoded = self.tokenizer.encode_batch(texts)
            feed = {}
            if "input_ids" in self.input_names:
                feed["input_ids"] = np.array([e.ids for e in encoded], dtype=np.int64)
            if "attention_mask" in self.input_names:
                feed["attention_mask"] = np.array(
                    [e.attention_mask for e in encoded], dtype=np.int64
                )
            if "token_type_ids" in self.input_names:
                feed["token_type_ids"] = np.array(
                    [e.type_ids for e in encoded], dtype=np.int64
                )
            hidden = self.session.run(None, feed)[0]
            mask = feed["attention_mask"][..., None]
            pooled = (hidden * mask).sum(axis=1) / mask.sum(axis=1)
            if normalize:
                pooled = pooled / np.linalg.norm(pooled, axis=1, keepdims=True)
            return pooled.tolist()
        except Exception as e:
            self.logger.exception("Error embedding the data: %s", e)
            raise
