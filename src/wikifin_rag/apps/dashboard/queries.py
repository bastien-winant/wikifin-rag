from wikifin_rag.db_client import MonitoringDBClient
from wikifin_rag.factories import record_factory, stats_factory


def get_exchanges(limit=10):
    db_client = MonitoringDBClient()

    try:
        with db_client.get_db_connection() as con:
            con.row_factory = record_factory

            cur = con.execute(
                f"""
                SELECT e.id, e.query, e.answer, c.model,
                    c.instructions, e.prompt,
                    e.prompt_tokens, e.completion_tokens, e.total_tokens,
                    e.response_time, e.input_cost, e.output_cost, e.total_cost, e.timestamp
                FROM {db_client.exchanges_table_identifier} e
                JOIN {db_client.conversations_table_identifier} c
                ON c.id = e.conversation_id
                ORDER BY e.timestamp DESC
                LIMIT ?;
                """,
                (limit,),
            )
            rows = cur.fetchall()
    except Exception as e:
        db_client.logger.error(f"Error retrieving the data: {e}")
        raise

    return rows


def get_conversation_stats():
    db_client = MonitoringDBClient()
    
    try:
        with db_client.get_db_connection() as con:
            cur = con.execute(f"""
                SELECT
                    c.id,
                    c.started_at,
                    COUNT(e.id) AS total_exchanges,
                    SUM(e.total_cost) AS total_cost,
                    SUM(e.total_tokens) AS total_tokens
                FROM {db_client.conversations_table_identifier} c
                JOIN {db_client.exchanges_table_identifier} e
                ON c.id = e.conversation_id
                GROUP BY 1, 2;
            """)
            rows = cur.fetchall()
    except Exception as e:
        db_client.logger.error(f"Error retrieving the data: {e}")
        raise

    return dict(rows)


def get_exchange_stats():
    db_client = MonitoringDBClient()

    try:
        with db_client.get_db_connection() as con:
            con.row_factory = stats_factory

            cur = con.execute(f"""
                SELECT
                    COUNT(*),
                    AVG(response_time),
                    SUM(total_cost),
                    AVG(total_tokens)
                FROM {db_client.exchanges_table_identifier};
            """)
            row = cur.fetchone()
    except Exception as e:
        db_client.logger.error(f"Error retrieving the data: {e}")
        raise

    return row


def get_relevance_stats():
    db_client = MonitoringDBClient()

    try:
        with db_client.get_db_connection() as con:
            cur = con.execute(f"""
                SELECT relevance, COUNT(*)
                FROM {db_client.feedback_table_identifier}
                WHERE source = 'judge'
                GROUP BY relevance;
            """)
            rows = cur.fetchall()
    except Exception as e:
        db_client.logger.error(f"Error retrieving the data: {e}")
        raise

    return dict(rows)


def get_user_feedback_stats():
    db_client = MonitoringDBClient()

    try:
        with db_client.get_db_connection() as con:
            cur = con.execute(f"""
                SELECT
                    SUM(CASE WHEN score > 0 THEN 1 ELSE 0 END),
                    SUM(CASE WHEN score = 0 THEN 1 ELSE 0 END)
                FROM {db_client.feedback_table_identifier}
                WHERE source = 'user';
            """)
            row = cur.fetchone()
    except Exception as e:
        db_client.logger.error(f"Error retrieving the data: {e}")
        raise

    return row