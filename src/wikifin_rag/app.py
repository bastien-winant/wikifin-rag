import streamlit as st
from wikifin_rag.assistant import create_assistant
from wikifin_rag.db_client import MonitoringDBClient

assistant = create_assistant()

db_client = MonitoringDBClient()
db_client.init_db(drop=False)

st.title("Course Assistant")

user_input = st.text_input("Enter your question:")

if st.button("Ask"):
    with st.spinner("Processing..."):
        answer = assistant.rag(user_input)
        st.success("Completed!")
        st.write(answer)

        record = assistant.last_call
        conversation_id = db_client.save_conversation(record, user_input)
        st.session_state.conversation_id = conversation_id
