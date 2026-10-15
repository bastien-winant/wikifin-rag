import pandas as pd
from supabase import create_client
import os
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(override=True)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
_supabase = create_client(url, key)


def get_judge_feedback(start_date, end_date):
    response = (_supabase
                .table('exchanges')
                .select('start_datetime, feedback(relevance)')
                .gte('start_datetime', start_date)
                .lte('start_datetime', end_date)
                .eq("feedback.source", "judge")
                .execute()
    )

    raw_data = response.data

    rows = []
    for entry in raw_data:
        dt = datetime.fromisoformat(entry["start_datetime"])
        for feedback in entry["feedback"]:
            rows.append({
                "relevance": feedback['relevance'],
                "date": dt.date(),
                "day": dt.strftime('%F'),
                "week": dt.strftime('%Y-%W'),
                "month": dt.strftime('%Y-%m'),
                "year": dt.strftime('%Y')
            })

    return pd.DataFrame(rows)


def get_user_feedback(start_date, end_date):
    response = (_supabase
                .table('exchanges')
                .select('start_datetime, feedback(source, score)')
                .gte('start_datetime', start_date)
                .lte('start_datetime', end_date)
                .or_("source.eq.user,source.is.null", reference_table="feedback")
                .execute()
    )

    raw_data = response.data

    rows = []
    for entry in raw_data:
        dt = datetime.fromisoformat(entry["start_datetime"])
        feedback_rows = entry["feedback"]

        if feedback_rows == []:
            rows.append({
                "score": 'UNSCORED',
                "date": dt.date(),
                "day": dt.strftime('%F'),
                "week": dt.strftime('%Y-%W'),
                "month": dt.strftime('%Y-%m'),
                "year": dt.strftime('%Y')
            })
            continue

        for feedback in entry["feedback"]:
            score = 'POSITIVE' if feedback["score"] == '1' else 'NEGATIVE'

            rows.append({
                "score": score,
                "date": dt.date(),
                "day": dt.strftime('%F'),
                "week": dt.strftime('%Y-%W'),
                "month": dt.strftime('%Y-%m'),
                "year": dt.strftime('%Y')
            })

    return pd.DataFrame(rows)


def get_tokens(start_date, end_date):
    response = (_supabase
                .table('responses')
                .select("""
                    id,
                    input_tokens,
                    output_tokens,
                    created_at
                """)
                .gte('created_at', start_date)
                .lte('created_at', end_date)
                .execute()
    )

    raw_data = response.data

    rows = []
    for entry in raw_data:
        dt = datetime.fromisoformat(entry["created_at"])
        rows.append({
            "id": entry["id"],
            "input_tokens": entry["input_tokens"],
            "output_tokens": entry["output_tokens"],
            "date": dt.date(),
            "day": dt.strftime('%F'),
            "week": dt.strftime('%Y-%W'),
            "month": dt.strftime('%Y-%m'),
            "year": dt.strftime('%Y')
        })

    df = pd.DataFrame(rows)

    df["total_tokens"] = df.input_tokens + df.output_tokens

    return df


def get_costs(start_date, end_date):
    response = (_supabase
                .table('responses')
                .select("""
                    id,
                    input_cost,
                    output_cost,
                    created_at
                """)
                .gte('created_at', start_date)
                .lte('created_at', end_date)
                .execute()
    )

    raw_data = response.data

    rows = []
    for entry in raw_data:
        dt = datetime.fromisoformat(entry["created_at"])
        rows.append({
            "id": entry["id"],
            "input_cost": entry["input_cost"],
            "output_cost": entry["output_cost"],
            "date": dt.date(),
            "day": dt.strftime('%F'),
            "week": dt.strftime('%Y-%W'),
            "month": dt.strftime('%Y-%m'),
            "year": dt.strftime('%Y')
        })

    df = pd.DataFrame(rows)

    df["total_cost"] = df.input_cost + df.output_cost

    return df