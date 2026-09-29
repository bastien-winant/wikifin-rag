run:
	uv run python ./src/wikifin_rag/assistant.py

chat:
	uv run streamlit run ./src/wikifin_rag/apps/chat/app.py

monitor:
	uv run streamlit run ./src/wikifin_rag/apps/dashboard/app.py