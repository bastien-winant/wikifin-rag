import streamlit as st
from wikifin_rag.assistant import create_assistant, search_function
from wikifin_rag.db_client import ConversationsClient
from wikifin_rag.judge import evaluate_relevance

assistant = create_assistant()

db_client = ConversationsClient()
db_client.init_db()

st.title("Ask Wikifin")

user_input = st.text_input("Enter your question:")

if st.button("Ask"):
    with st.spinner("Processing..."):
        answer = assistant.rag(user_input, search_function=search_function)
        st.success("Completed!")
        st.write(answer)

        record = assistant.last_call
        st.write(f"Response time: {record.response_time:.2f}s")
        st.write(f"Prompt tokens: {record.prompt_tokens}")
        st.write(f"Completion tokens: {record.completion_tokens}")
        st.write(f"Cost: ${record.cost:.4f}")

        conversation_id = db_client.save_conversation(record=record, question=user_input)
        st.session_state.conversation_id = conversation_id

        relevance, explanation = evaluate_relevance(user_input, answer)
        db_client.save_feedback(conversation_id=conversation_id, source="judge",
                        relevance=relevance, explanation=explanation)
        st.write(f"Relevance: {relevance}")
        st.write(f"Explanation: {explanation}")



conversation_id = st.session_state.get("conversation_id")

if conversation_id is not None:
    col1, col2 = st.columns(2)

    with col1:
        if st.button("+1", key=f"feedback_up_{conversation_id}"):
            db_client.save_feedback(conversation_id=conversation_id, source="user", score=1)
            st.success("Thanks!")

    with col2:
        if st.button("-1", key=f"feedback_down_{conversation_id}"):
            db_client.save_feedback(conversation_id=conversation_id, source="user", score=-1)
            st.success("Thanks for the feedback!")