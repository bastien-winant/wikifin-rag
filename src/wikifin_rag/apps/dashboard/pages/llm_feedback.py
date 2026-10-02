import streamlit as st
from wikifin_rag.apps.dashboard.queries import get_judge_feedback
import pandas as pd

try:
    df = get_judge_feedback(
        start_date=st.session_state.from_date,
        end_date=st.session_state.to_date
    )
except:
    st.error("There was an error retrieving the data. Please try again later.")
    st.stop()

with st.container(gap="medium"):
    st.header("Judge Feedback")

    if df.empty:
        st.warning('No data available for the given time range.')
        st.stop()

    count_relevant = (df.relevance == 'RELEVANT').sum()
    count_irrelevant = (df.relevance == 'IRRELEVANT').sum()
    count_partly_relevant = (df.relevance == 'PARTLY_RELEVANT').sum()
    count_scored = df.shape[0]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.badge("Positive scores", color="green")

        with st.container(horizontal=True, vertical_alignment="bottom", gap="xsmall"):
            st.text(count_relevant)
            st.caption(f"{(100 * count_relevant / count_scored):.2f}%")

    with col2:
        st.badge("Negative scores", color="red")

        with st.container(horizontal=True, vertical_alignment="bottom", gap="xsmall"):
            st.text(count_irrelevant)
            st.caption(f"{(100 * count_irrelevant / count_scored):.2f}%")

    with col3:
        st.badge("No feedback", color="yellow")

        with st.container(horizontal=True, vertical_alignment="bottom", gap="xsmall"):
            st.text(count_partly_relevant)
            st.caption(f"{(100 * count_partly_relevant / df.shape[0]):.2f}%")


    score_values = ['RELEVANT', 'IRRELEVANT', 'PARTLY_RELEVANT']
    df.relevance = pd.Categorical(df.relevance, score_values)
    df_formatted = df.pivot_table(
        index=st.session_state.granularity,
        columns="relevance",
        aggfunc="size",
        fill_value=0,
        observed=False
    ).reset_index()

    st.bar_chart(
        df_formatted,
        x=st.session_state.granularity,
        y=score_values,
        color=["green", "red", "yellow"]
    )