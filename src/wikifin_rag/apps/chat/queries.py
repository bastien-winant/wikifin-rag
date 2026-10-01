from wikifin_rag.db_client import MonitoringDBClient
from datetime import datetime

def save_conversation(record):
    db_client = MonitoringDBClient()
    
    try:
        timestamp = datetime.now(db_client.DB_TIMEZONE).strftime(format='%Y-%m-%d %H:%M:%S.%f')
        
        with db_client.get_db_connection() as con:
            cur = con.execute(f"""
                INSERT INTO {db_client.conversations_table_identifier} (model, instructions, started_at)
                VALUES (?, ?, ?)
                RETURNING id;
                """,
                (record.model, record.instructions, timestamp)
            )
            conversation_id = cur.fetchone()[0]

            db_client.logger.info(f"Inserted new LLM conversation record.")
    except Exception as e:
        db_client.logger.error(f"Error writing conversation data: {e}")
        raise

    return conversation_id
    

def save_exchange(conversation_id, record, query):
    db_client = MonitoringDBClient()
    
    try:
        with db_client.get_db_connection() as con:
            cur = con.execute(f"""
                INSERT INTO {db_client.exchanges_table_identifier} (
                    conversation_id, query, answer, prompt,
                    prompt_tokens, completion_tokens, total_tokens,
                    response_time, input_cost, output_cost, total_cost, timestamp
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                RETURNING id;
                """,
                (
                    conversation_id,
                    query,
                    record.answer,
                    record.prompt,
                    record.prompt_tokens,
                    record.completion_tokens,
                    record.total_tokens,
                    record.response_time,
                    record.input_cost,
                    record.output_cost,
                    record.total_cost,
                    record.timestamp,
                ),
            )
            exchange_id = cur.fetchone()[0]

            db_client.logger.info(f"Inserted new LLM exchange record.")
    except Exception as e:
        db_client.logger.error(f"Error writing exchange data: {e}")
        raise

    return exchange_id


def save_feedback(exchange_id, source, relevance=None, explanation=None, score=None):
    db_client = MonitoringDBClient()
    
    timestamp = datetime.now(db_client.DB_TIMEZONE)

    try:
        with db_client.get_db_connection() as con:
            con.execute(
                f"""
                INSERT INTO {db_client.feedback_table_identifier} (
                    exchange_id, source, relevance,
                    explanation, score, timestamp
                ) VALUES (
                    ?, ?, ?, ?, ?, ?
                );
                """,
                (exchange_id, source, relevance,
                explanation, score, timestamp),
            )
    except Exception as e:
        db_client.logger.error(f"Error writing feedback data: {e}")
        raise