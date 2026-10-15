from supabase import create_client
import os
from dataclasses import asdict

from dotenv import load_dotenv
load_dotenv(override=True)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
_supabase = create_client(url, key)


def log_exchange(record):
    try:
        _supabase.table("exchanges").insert(asdict(record)).execute()
    except Exception as e:
        print("Error saving the exchange: ", e)
        return


def log_response(record):
    try:
        _supabase.table("responses").insert(asdict(record)).execute()
    except:
        return


def log_tool_call(record):
    try:
        _supabase.table("tool_calls").insert(asdict(record)).execute()
    except Exception as e:
        print(e)
        return


def log_turn(exchange, responses, tool_calls):
    """Insert exchange, then all responses, then tool calls (FK order).

    Returns True on success, False if any insert fails.
    """
    try:
        _supabase.table("exchanges").insert(asdict(exchange)).execute()
        if responses:
            _supabase.table("responses").insert([asdict(r) for r in responses]).execute()
        if tool_calls:
            _supabase.table("tool_calls").insert([asdict(t) for t in tool_calls]).execute()
    except Exception as e:
        print("Error saving the turn: ", e)
        return False

    return True


def log_feedback(exchange_id, source, relevance=None, explanation=None, score=None):
    try:
        response = _supabase.table("feedback")\
            .insert({
                "exchange_id": exchange_id,
                "source": source,
                "relevance": relevance,
                "explanation": explanation,
                "score": score
            })\
            .select("id")\
            .execute()

        feedback_id = response.data[0]["id"]
    except Exception as e:
        print(f"Error logging the {source} feedback for {exchange_id}: {e}")
        return

    return feedback_id


