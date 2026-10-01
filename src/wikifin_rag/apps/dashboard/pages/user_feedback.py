import streamlit as st
from wikifin_rag.apps.dashboard.queries import get_user_feedback

try:
    df = get_user_feedback(
        start_date=st.session_state.from_date,
        end_date=st.session_state.to_date
    )
except:
    st.error("There was an error retrieving the data. Please try again later.")
    st.stop()

with st.container(gap="medium"):
    st.header("User Feedback")

    if df.empty:
        st.warning('No data available for the given time range.')
        st.stop()

    count_positives = int((df.score == 'POSITIVE').sum())
    count_negatives = int((df.score == 'NEGATIVE').sum())
    count_unscored = int((df.score == 'UNSCORED').sum())
    count_scored = int((df.score != 'UNSCORED').sum())

    col1, col2, col3 = st.columns(3)

    with col1:
        st.badge("Positive scores", color="green")

        with st.container(horizontal=True, vertical_alignment="bottom", gap="xsmall"):
            st.text(f"{count_positives}")
            st.caption(f"{(100 * count_positives / count_scored):.2f}%")

    with col2:
        st.badge("Negative scores", color="red")

        with st.container(horizontal=True, vertical_alignment="bottom", gap="xsmall"):
            st.text(f"{count_negatives}")
            st.caption(f"{(100 * count_negatives / count_scored):.2f}%")

    with col3:
        st.badge("No feedback", color="yellow")

        with st.container(horizontal=True, vertical_alignment="bottom", gap="xsmall"):
            st.text(f"{count_unscored}")
            st.caption(f"{(100 * count_unscored / df.shape[0]):.2f}%")

    df_grouped = df.groupby([st.session_state.granularity, 'score'], as_index=False).size()

    chart_tab, data_tab = st.tabs(["📈 Chart", "🗃 Data"])
    
    chart_tab.bar_chart(
        df_grouped,
        x=st.session_state.granularity,
        y="size",
        color="score",
        stack="normalize",
        x_label=st.session_state.granularity.upper(),
        y_label="Percentage",
    )

    data_tab.write(df_grouped)