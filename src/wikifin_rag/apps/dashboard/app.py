import streamlit as st
from datetime import date
from dateutil.relativedelta import relativedelta

if "end_date" not in st.session_state:
    st.session_state.end_date = date.today()

if "start_date" not in st.session_state:
    start_date = st.session_state.end_date - relativedelta(months=3)
    st.session_state.start_date = start_date
    

pg = st.navigation([
    st.Page(
        "pages/llm_feedback.py",
        title="LLM Feedback"
    ),
    st.Page(
        "pages/user_feedback.py",
        title="User Feedback"
    )
])
st.set_page_config(page_title="Data manager", page_icon=":material/edit:")
pg.run()