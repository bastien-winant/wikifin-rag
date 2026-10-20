# import sys
import threading
# from pathlib import Path

# # Community Cloud does not install the src-layout package editable; make it importable.
# _SRC = Path(__file__).resolve().parents[3]
# if str(_SRC) not in sys.path:
#     sys.path.insert(0, str(_SRC))

import streamlit as st

st.set_page_config(page_title="Wikifin AI", layout="centered")

from wikifin_rag.assistant import get_assistant_response
from wikifin_rag.utils import num_tokens_from_message
from wikifin_rag.queries import log_feedback
from wikifin_rag.judge import evaluate_anwer
from wikifin_rag.queries import log_turn

_MAX_INPUT_TOKENS = 2000
_LANGUAGES = ("NL", "FR", "EN")
_COPY = {
    "NL": {
        "title": "Vraag het aan Wikifin",
        "explainer": (
            "Stel vragen over persoonlijke financiën — budgetteren, verzekeringen, "
            "sparen en meer — en krijg antwoorden gebaseerd op de educatieve inhoud "
            "van Wikifin."
        ),
        "disclaimer": (
            "Antwoorden zijn gebaseerd op informatie gepubliceerd op "
            "[wikifin.be](https://www.wikifin.be). Dit is geen gepersonaliseerd "
            "financieel advies."
        ),
        "placeholder": "Stel een vraag over persoonlijke financiën...",
    },
    "FR": {
        "title": "Demandez à Wikifin",
        "explainer": (
            "Posez des questions sur les finances personnelles — budget, assurances, "
            "épargne et plus encore — et obtenez des réponses basées sur le contenu "
            "éducatif de Wikifin."
        ),
        "disclaimer": (
            "Les réponses sont basées sur les informations publiées sur "
            "[wikifin.be](https://www.wikifin.be). Il ne s'agit pas de conseils "
            "financiers personnalisés."
        ),
        "placeholder": "Posez une question sur les finances personnelles...",
    },
    "EN": {
        "title": "Ask Wikifin",
        "explainer": (
            "Ask questions about personal finance — budgeting, insurance, saving, "
            "and more — and get answers grounded in Wikifin’s educational content."
        ),
        "disclaimer": (
            "Answers are based on information published on "
            "[wikifin.be](https://www.wikifin.be). This is not personalized "
            "financial advice."
        ),
        "placeholder": "Ask a question about personal finance...",
    },
}


def save_user_feedback():
    if not st.session_state.get("turn_logged"):
        return

    exchange_id = st.session_state.get("exchange_id")
    score = st.session_state.get("user_feedback")

    if exchange_id is None or score is None:
        return

    log_feedback(exchange_id=exchange_id, source="user", score=score)


def save_llm_feedback(exchange_id, question, response):
    if exchange_id is None or response is None:
        return

    feedback = evaluate_anwer(question, response)
    if feedback is None:
        return

    relevance, reasoning = feedback
    log_feedback(
        exchange_id=exchange_id,
        source="judge",
        relevance=relevance,
        explanation=reasoning,
    )


def clear_session_state():
    language = st.session_state.get("language")
    st.session_state.clear()
    if language is not None:
        st.session_state.language = language


def set_response_status():
    st.session_state.prompt_responded = False
    st.session_state.user_feedback = None
    st.session_state.turn_logged = False


with st.sidebar:
    language = st.segmented_control(
        "Language",
        options=_LANGUAGES,
        default="NL",
        key="language",
        label_visibility="collapsed",
    ) or "NL"
    copy = _COPY[language]

    st.header(copy["title"])
    st.text(copy["explainer"])
    st.caption(copy["disclaimer"])

with st.container(gap="medium", horizontal_alignment="center"):
    st.title("Ask Wikifin", text_alignment="center")

    with st.form(key="prompt_form", clear_on_submit=True, border=False):
        with st.container(horizontal=True, gap="xsmall"):
            st.text_input(
                key="prompt",
                label="prompt",
                label_visibility="collapsed",
                placeholder=copy["placeholder"],
                required=True,
                persist_state="page"
            )

            st.form_submit_button(type="primary", on_click=set_response_status)

    if prompt := st.session_state.get("prompt"):
        num_prompt_tokens = num_tokens_from_message(prompt)

        if num_prompt_tokens > _MAX_INPUT_TOKENS:
            st.error("Your message exceeds the maximum length. Please shorten it and try again.")
            st.stop()

        st.divider(width="stretch")
        with st.container(height=300, gap="xsmall", autoscroll=False, border=False):
            st.chat_message("human").write(prompt)

            with st.chat_message("ai"):
                if not st.session_state.get("prompt_responded"):
                    with st.spinner():
                        exchange_record, response_records, tool_call_records = get_assistant_response(question=prompt)

                        st.session_state.response = exchange_record.response
                        st.session_state.exchange_id = exchange_record.id
                        st.session_state.prompt_responded = True

                    turn_logged = log_turn(exchange_record, response_records, tool_call_records)
                    st.session_state.turn_logged = turn_logged

                    if turn_logged:
                        threading.Thread(
                            target=save_llm_feedback,
                            args=(exchange_record.id, prompt, exchange_record.response),
                            daemon=True,
                        ).start()

                st.write(st.session_state.response)

                if st.session_state.get("prompt_responded") and not st.session_state.get("turn_logged"):
                    st.warning("Couldn't save this conversation. Feedback won't be recorded.")

                st.feedback(
                    "thumbs",
                    key="user_feedback",
                    on_change=save_user_feedback,
                    disabled=(
                        not st.session_state.get("turn_logged")
                        or st.session_state.get("user_feedback") is not None
                    ),
                )
                st.button("Clear", type="primary", key="clear", on_click=clear_session_state)
