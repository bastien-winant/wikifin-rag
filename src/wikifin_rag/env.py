"""Runtime environment helpers for local and Streamlit Community Cloud."""

from __future__ import annotations

import os


def bootstrap_runtime() -> None:
    """Load `.env`, then mirror Streamlit secrets into ``os.environ``.

    OpenAI, Pinecone, and Supabase clients read credentials from the
    environment. Locally those come from `.env` / `.streamlit/secrets.toml`;
    on Community Cloud they are injected via ``st.secrets``.
    """
    from dotenv import load_dotenv

    load_dotenv(override=True)

    try:
        import streamlit as st

        for key, value in st.secrets.items():
            if isinstance(value, (str, int, float, bool)):
                os.environ[key] = str(value)
    except Exception:
        pass
