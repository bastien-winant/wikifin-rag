from pydantic import BaseModel
from typing import Literal
from wikifin_rag.evaluation_utils import llm_structured_retry
from wikifin_rag.config import DEFAULT_LLM_MODEL
import json

from dotenv import load_dotenv
load_dotenv(override=True)

from openai import OpenAI

_client = OpenAI()


class AnswerEvaluation(BaseModel):
    relevance: Literal["IRRELEVANT", "PARTLY_RELEVANT", "RELEVANT"]
    reasoning: str


_JUDGE_INSTRUCTIONS = """
You are an impartial judge for a Wikifin personal-finance RAG assistant.

You receive:
- the user question
- the assistant's AI answer

Your task is to assess the relevance of the AI answer to the given question:
- RELEVANT: the answer addresses the question
- PARTLY_RELEVANT: the answer partially addresses the question
- IRRELEVANT: the answer is incorrect or does not address the question

Rules:
- The AI answer should NOT quote the document word-for-word
- Extra detail is fine as long as the core answer is correct
- If the assistant correctly refuses personalized advice or reports insufficient
  information, mark it as "RELEVANT"

Be fair and focus on relevance and correctness, not style.
Always provide your reasoning in English.
""".strip()


def evaluate_anwer(query: str, response: str) -> dict | None:
    payload = {
        "query": query,
        "assistant_answer": response,
    }
    
    try:
        response, _ = llm_structured_retry(
            client=_client,
            instructions=_JUDGE_INSTRUCTIONS,
            user_prompt=json.dumps(payload, ensure_ascii=False),
            output_type=AnswerEvaluation,
            model=DEFAULT_LLM_MODEL,
        )

        relevance = response.relevance
        reasoning = response.reasoning

        return relevance, reasoning
    except Exception as exc:
        print(f"Judge failed: {exc}")
        return None