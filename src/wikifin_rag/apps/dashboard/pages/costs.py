import streamlit as st
from wikifin_rag.apps.dashboard.queries import get_costs

try:
    df = get_costs(
        start_date=st.session_state.from_date,
        end_date=st.session_state.to_date
    )
except:
    st.error("There was an error retrieving the data. Please try again later.")
    st.stop()



with st.container(gap="medium"):
    st.header("Costs")

    if df.empty:
        st.warning('No data available for the given time range.')
        st.stop()


    total_cost = df.total_cost.sum()
    total_input_cost = df.input_cost.sum()
    total_output_cost = df.output_cost.sum()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.badge("Input Cost")
        st.text(f"${total_input_cost:.2f}")

    with col2:
        st.badge("Output Cost")
        st.text(f"${total_output_cost:.2f}")

    with col3:
        st.badge("Total Cost")
        st.text(f"${total_cost:.2f}")


    df_grouped = df.groupby(st.session_state.granularity, as_index=False)\
        [['total_cost', 'input_cost', 'output_cost']].sum()

    chart_tab, data_tab = st.tabs(["📈 Chart", "🗃 Data"])

    chart_tab.line_chart(
        df_grouped,
        x=st.session_state.granularity,
        y=["total_cost", "input_cost", "output_cost"],
        x_label=st.session_state.granularity.upper(),
        y_label="Costs ($)"
    )

    data_tab.write(df_grouped)