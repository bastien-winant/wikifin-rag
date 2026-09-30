import streamlit as st
from datetime import date
from dateutil.relativedelta import relativedelta


end_date = date.today()
start_date = end_date - relativedelta(months=3)


with st.sidebar:
    st.text("Search parameters")

    with st.container():
        with st.container(width="content", horizontal=True):
            from_date = st.date_input(label="from", value=start_date, max_value=end_date)
            to_date = st.date_input(label="to", max_value=end_date)

        granularity = st.selectbox(
            "Granularity",
            ("year", "month", "week", "day"),
            index=2
        )

st.session_state.from_date = from_date
st.session_state.to_date = to_date
st.session_state.granularity = granularity

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
        "pages/usage.py",
        title="Token Usage"
    )
])

st.set_page_config(
    layout="wide",
    page_icon=":material/edit:")

pg.run()