import time
from tqdm.auto import tqdm
import random
import json
from functools import reduce
import pandas as pd

from pydantic import BaseModel

from pinecone import Pinecone
from wikifin_rag.config import INDEX_NAME

from concurrent.futures import ThreadPoolExecutor
from wikifin_rag.config import DEFAULT_LLM_MODEL

from dotenv import load_dotenv
load_dotenv(override=True)

from openai import OpenAI

_pc = Pinecone(source_tag="pinecone:wikifin_search")
_index = _pc.index(name=INDEX_NAME)
_client = OpenAI()


_QUERY_GEN_INSTRUCTIONS = """
You create evaluation cases for a Belgian personal-finance RAG assistant grounded in Wikifin.

Given one document chunk, produce natural user questions/search queries in each requested language
that this chunk should retrieve as a relevant result.

Rules:
- Produce one query per requested language.
- Prefer realistic user questions over keyword dumps.
- The questions must be answerable from the chunk alone.
- Keep the same information need across languages (parallel translations of intent).
- Do not mention document IDs or that this is an evaluation.
- Do not quote the chunk verbatim at length; paraphrase the information need.
""".strip()

QUERY_LANGUAGES = ["nl", "en", "fr"]


class Query(BaseModel):
    text: str
    language: str

class Queries(BaseModel):
    queries: list[Query]


def calc_price(usage):
    input_price_per_million = 0.75
    output_price_per_million = 4.50

    input_cost = (usage.input_tokens / 1_000_000) * input_price_per_million
    output_cost = (usage.output_tokens / 1_000_000) * output_price_per_million
    total_cost = input_cost + output_cost

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
    }


def calc_total_price(usages):
    total_cost = 0.0

    for usage in usages:
        cost = calc_price(usage)
        total_cost = total_cost + cost["total_cost"]

    return total_cost


def llm_structured(client, instructions, user_prompt, output_type, model="gpt-5.4-mini"):
    response = client.responses.parse(
        model=model,
        instructions=instructions,
        input=user_prompt,
        text_format=output_type
    )

    return response.output_parsed, response.usage


def llm_structured_retry(
    client,
    instructions,
    user_prompt,
    output_type,
    model="gpt-5.4-mini",
    max_retries=3,
):
    for attempt in range(max_retries):
        try:
            return llm_structured(
                client,
                instructions,
                user_prompt,
                output_type,
                model=model,
            )
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)


def map_progress(pool, seq, f):
    results = []

    with tqdm(total=len(seq)) as progress:
        futures = []

        for el in seq:
            future = pool.submit(f, el)
            future.add_done_callback(lambda p: progress.update())
            futures.append(future)

        for future in futures:
            result = future.result()
            results.append(result)

    return results


def _list_document_ids(namespace: str = "__default__", limit: int | None = None) -> list[str]:
    ids: list[str] = []
    for entry in _index.documents.list(namespace=namespace):
        ids.append(entry.id)
        if limit is not None and len(ids) >= limit:
            break
    return ids


def _fetch_documents(ids: list[str], include_fields: list[str], namespace: str = "__default__") -> list[dict]:
    docs: list[dict] = []
    batch_size = 50
    for start in range(0, len(ids), batch_size):
        batch_ids = ids[start : start + batch_size]
        response = _index.documents.fetch(
            namespace=namespace,
            ids=batch_ids,
            include_fields=include_fields,
        )
        for doc_id in batch_ids:
            doc = response.documents.get(doc_id)
            if doc is None:
                continue
            payload = doc.to_dict()
            if payload.get("language") and payload["language"] != "nl":
                continue
            if not payload.get("text"):
                continue
            docs.append(payload)
    return docs


def sample_documents(include_fields: list, n: int = 20, oversample_factor: int = 4) -> list[dict]:
    """List a capped ID pool, shuffle, and fetch until we have n usable docs."""
    candidate_ids = _list_document_ids(limit=max(n * oversample_factor, n))
    random.shuffle(candidate_ids)
    selected: list[dict] = []
    batch_size = 50
    for start in range(0, len(candidate_ids), batch_size):
        batch = _fetch_documents(candidate_ids[start : start + batch_size], include_fields=include_fields)
        for doc in batch:
            selected.append(doc)
            if len(selected) >= n:
                return selected
    return selected


def _generate_document_queries(doc: dict) -> list[dict]:
    excerpt = (doc.get("text") or "")[:1200]
    user_payload = {
        "title": doc.get("title", ""),
        "section": doc.get("section", ""),
        "text": excerpt,
        "languages": QUERY_LANGUAGES,
    }
    try:
        data, usage = llm_structured_retry(
            client=_client,
            instructions=_QUERY_GEN_INSTRUCTIONS,
            user_prompt=json.dumps(user_payload, ensure_ascii=False),
            output_type=Queries,
            model=DEFAULT_LLM_MODEL
        )
        queries = data.queries

        results = [
            {
                "query": query.text,
                "query_language": query.language,
                "relevant_id": doc["_id"],
                "title": doc.get("title", ""),
                "section": doc.get("section", ""),
                "text": doc.get("text", "")
            } for query in queries
        ]

        return results, usage
    except Exception as exc:
        print(f"Query generation failed for {doc.get('_id')}: {exc}")
        return


def generate_corpus_queries(docs, file_path: str | None = None):
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = map_progress(pool, docs, _generate_document_queries)

    ground_truth: list[dict] = []
    usages: list = []

    for result in results:
        if result:
            records, usage = result
            ground_truth.extend(records)
            usages.append(usage)


    total_cost = reduce(lambda x, y: x + calc_price(y)["total_cost"], usages, 0.0)

    if file_path:
        df_ground_truth = pd.DataFrame(ground_truth)
        df_ground_truth.to_csv(file_path, index=False)

    return ground_truth, total_cost