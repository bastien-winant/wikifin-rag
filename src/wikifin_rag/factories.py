from wikifin_rag.items import LLMCallRecord, Stats

def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def record_factory(_, row):
    return LLMCallRecord(
        model=row[3],
        prompt=row[5],
        instructions=row[4],
        answer=row[2],
        prompt_tokens=row[6],
        completion_tokens=row[7],
        total_tokens=row[8],
        response_time=row[9],
        input_cost=row[10],
        output_cost=row[11],
        total_cost=row[12],
        timestamp=row[13],
    )

def stats_factory(_, row):
    return Stats(
        total=row[0],
        avg_response_time=row[1],
        total_cost=row[2],
        avg_tokens=row[3],
    )