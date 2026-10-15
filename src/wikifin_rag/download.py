import logging
import os
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download, list_repo_files

from wikifin_rag.config import EMBED_MODEL, PROJECT_ROOT

os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

_ONNX_CANDIDATES = [
    "onnx/model.onnx",
    "onnx/encoder_model.onnx",
    "model.onnx",
]


def _model_ready(model_dir: Path) -> bool:
    return (model_dir / "tokenizer.json").exists() and (model_dir / "model.onnx").exists()


def download(repo, dest=PROJECT_ROOT / "models"):
    dest = Path(dest) / repo
    dest.mkdir(parents=True, exist_ok=True)

    files = list_repo_files(repo_id=repo)
    onnx_file = next((c for c in _ONNX_CANDIDATES if c in files), None)
    if not onnx_file:
        raise FileNotFoundError(f"No ONNX model found in {repo}")

    for remote, local in [
        ("tokenizer.json", "tokenizer.json"),
        (onnx_file, "model.onnx"),
    ]:
        src = hf_hub_download(repo_id=repo, filename=remote)
        dst = dest / local
        if not dst.exists():
            shutil.copy2(src, dst)
            print(f"  saved {dst}")
        else:
            print(f"  exists {dst}")

    onnx_ext = onnx_file + "_data"
    if onnx_ext in files:
        src = hf_hub_download(repo_id=repo, filename=onnx_ext)
        dst = dest / "model.onnx_data"
        if not dst.exists():
            shutil.copy2(src, dst)
            print(f"  saved {dst}")
        else:
            print(f"  exists {dst}")

    return dest


def ensure_embedding_model(repo=EMBED_MODEL, dest=PROJECT_ROOT / "models") -> Path:
    """Return the local model directory, downloading from Hugging Face if needed."""
    model_dir = Path(dest) / repo
    if _model_ready(model_dir):
        return model_dir
    return download(repo, dest=dest)


if __name__ == "__main__":
    ensure_embedding_model()
