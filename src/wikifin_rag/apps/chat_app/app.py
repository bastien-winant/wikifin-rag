import threading
import streamlit as st
from wikifin_rag.assistant import get_assistant_response
from wikifin_rag.utils import num_tokens_from_message
from wikifin_rag.queries import log_feedback
from wikifin_rag.judge import evaluate_anwer
from wikifin_rag.queries import log_turn
from streamlit.runtime.scriptrunner import add_script_run_ctx


st.set_page_config(
	page_title="Chat with the Wikifin docs, powered by OpenAI",
	layout="centered",
	initial_sidebar_state="locked",
	menu_items=None
)

_MAX_INPUT_TOKENS = 2000
_LANGUAGES_OPTIONS = {
    "NL": {
        "label": "🇳🇱 NL",
        "title": "Vraag het aan Wikifin",
        "explainer": "Een betrouwbare chatbot voor vragen over sparen, leningen en belastingen in België.",
        "disclaimer": """
			Wikifin is uitsluitend bedoeld voor educatieve doeleinden en vervangt geen professioneel financieel advies.
			De antwoorden zijn uitsluitend gebaseerd op informatie van [wikifin.be](https://wikifin.be).
		""",
        "placeholder": "Stel een vraag...",
		"button_label": "Verzenden",
		"spinner_label": "Ik denk na..."
    },
    "FR": {
        "label": "🇫🇷 FR",
        "title": "Demandez à Wikifin",
        "explainer": "Un chatbot fiable pour vos questions sur l'épargne, les prêts et les impôts en Belgique.",
        "disclaimer": """
			Wikifin est uniquement destiné à des fins éducatives et ne remplace pas les conseils d'un professionnel de la finance.
			Les réponses sont basées exclusivement sur les informations de [wikifin.be](https://wikifin.be).
		""",
        "placeholder": "Posez une question...",
		"button_label": "Envoyer",
		"spinner_label": "Je réfléchis..."
    },
    "EN": {
		"label": "🇬🇧 EN",
        "title": "Ask Wikifin",
        "explainer": "A trustworthy chatbot for your questions about managing savings, loans, and taxes in Belgium.",
        "disclaimer": """
			Ask Wikifin is for educational purposes only and should not be used as a substitute for professional financial advice.
			Answers are based strictly on information from [wikifin.be](https://wikifin.be).
		""",
        "placeholder": "Ask a question...",
		"button_label": "Submit",
		"spinner_label": "Thinking..."
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


def save_llm_feedback():
    exchange_id = st.session_state.get("exchange_id")
    question = st.session_state.get("prompt")
    response = st.session_state.get("response")

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
    language = st.session_state.get("language", "NL")
    st.session_state.clear()
    st.session_state.language = language


def reset_response_status():
    st.session_state.prompt = None
    st.session_state.prompt_responded = False
    st.session_state.user_feedback = None
    st.session_state.turn_logged = False


with st.sidebar:
    language = st.segmented_control(
        label="language",
        options=_LANGUAGES_OPTIONS.keys(),
        format_func=lambda option: _LANGUAGES_OPTIONS[option]["label"],
        key="language",
        label_visibility="collapsed",
        default="NL",
        on_change=reset_response_status
    )

    container = st.container()
    container.space(size="medium")


    container.header(_LANGUAGES_OPTIONS[st.session_state.language]["title"])
    container.text(_LANGUAGES_OPTIONS[st.session_state.language]["explainer"])
    container.caption(_LANGUAGES_OPTIONS[st.session_state.language]["disclaimer"], unsafe_allow_html=True)


st.title("Ask Wikifin", text_alignment="center")

with st.form("query_form", clear_on_submit=True):
	st.text_area(
		label="User prompt",
		key="prompt",
		label_visibility="collapsed",
		placeholder=_LANGUAGES_OPTIONS[st.session_state.language]["placeholder"],
	)
	st.form_submit_button(
		_LANGUAGES_OPTIONS[st.session_state.language]["button_label"],
		width="stretch",
		key="submitted",
		type="primary",
	)


if prompt := st.session_state.prompt:    
    # limit the size of the input
    num_prompt_tokens = num_tokens_from_message(prompt)
    if num_prompt_tokens > _MAX_INPUT_TOKENS:
        st.error("Your message exceeds the maximum length. Please shorten it and try again.")
        st.stop()


    # write the user prompt to the screen
    st.chat_message("human").write(prompt)

    with st.chat_message("ai"):
        # check if the user query has been answered
        if not st.session_state.get("prompt_responded"):
            with st.spinner(_LANGUAGES_OPTIONS[st.session_state.language]["spinner_label"]):
                # get AI response to the prompt
                exchange_record, response_records, tool_call_records = get_assistant_response(question=prompt)

                # save conversation data in the session state
                st.session_state.response = exchange_record.response
                st.session_state.exchange_id = exchange_record.id
                st.session_state.prompt_responded = True

            # save telemetry data for the exchange
            turn_logged = log_turn(exchange_record, response_records, tool_call_records)
            st.session_state.turn_logged = turn_logged

            # collet and save LLM feedback
            if turn_logged:
                thread = threading.Thread(
                    target=save_llm_feedback,
                    daemon=True,
                )
                add_script_run_ctx(thread=thread)
                thread.start()

        st.write(st.session_state.response)
        st.feedback(
            "thumbs",
            key="user_feedback",
            on_change=save_user_feedback,
            disabled=(
                not st.session_state.get("turn_logged") # make sure the exchange ID exists in the DB
                or st.session_state.get("user_feedback") is not None # user can provide feedback only once
            ),
        )
        st.button("Clear chat", on_click=clear_session_state)