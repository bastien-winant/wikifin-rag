import streamlit as st
from datetime import date
from dateutil.relativedelta import relativedelta
from wikifin_rag.apps.dashboard.queries import get_db_client


# Ensure the monitoring DB client (and schema) are ready before pages run.
get_db_client()

end_date = date.today()
start_date = end_date - relativedelta(months=3)


def update_to_date():
    st.session_state.to_date = max(st.session_state.to_date, st.session_state.from_date)

def update_from_date():
    st.session_state.from_date = min(st.session_state.from_date, st.session_state.to_date)

with st.sidebar:
    st.text("Search parameters")

    with st.container():
        with st.container(width="content", horizontal=True):
            st.date_input(
                label="from",
                value=start_date,
                max_value=end_date,
                key="from_date",
                on_change=update_to_date
            )

            st.date_input(
                label="to",
                max_value=end_date,
                key="to_date",
                on_change=update_from_date
            )

        granularity = st.selectbox(
            "Granularity",
            ("year", "month", "week", "day"),
            index=2,
            key="granularity"
        )

        if st.button("Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()


pg = st.navigation([
    st.Page(
        "pages/llm_feedback.py",
        title="LLM Feedback"
    ),
    st.Page(
        "pages/user_feedback.py",
        title="User Feedback"
    ),
    st.Page(
        "pages/costs.py",
        title="Costs"
    ),
    st.Page(
        "pages/tokens.py",
        title="Token Usage"
    )
])

st.set_page_config(
    layout="wide",
    page_icon=":material/edit:")

pg.run()