import sys
from wikifin_rag.rag_utils import run_agent_loop
from wikifin_rag.agent_config import INSTRUCTIONS, OPENAI_MODEL, search_tool

def get_assistant_response(question):
    return run_agent_loop(
        question=question,
        instructions=INSTRUCTIONS,
        model=OPENAI_MODEL,
        tools=[search_tool]
    )


if __name__ == "__main__":
    query = "Welke verschilpunten noemt de tekst tussen een jonge en een ervaren bestuurder bij een BA Auto-verzekering?"
    if len(sys.argv) > 1:
        query = sys.argv[1]

    exchange_record, *_ = get_assistant_response(query)
    print(exchange_record.response)