"""Agent loop helpers for tool-calling LLM responses."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from wikifin_rag.agent_config import TOOL_FUNCTIONS
from wikifin_rag.records import ExchangeRecord, ResponseRecord, ToolCallRecord

load_dotenv(override=True)

_client = OpenAI()


def _calculate_cost(usage, model: str) -> dict[str, float]:
    input_cost = 0.0
    output_cost = 0.0

    if "gpt-5.4-mini" in model:
        input_price_per_million = 0.75
        output_price_per_million = 4.50
        input_cost = (usage.input_tokens / 1_000_000) * input_price_per_million
        output_cost = (usage.output_tokens / 1_000_000) * output_price_per_million

    return {"input": input_cost, "output": output_cost}


def _get_llm_response(
    messages: list[dict[str, Any]] | str,
    instructions: str,
    model: str,
    tools: list[dict] | None = None,
):
    return _client.responses.create(
        model=model,
        instructions=instructions,
        input=messages,
        temperature=0.0,
        max_output_tokens=750,
        tools=tools,
    )


def _make_call(call) -> dict[str, Any]:
    name = call.name
    args = json.loads(call.arguments)

    if func := TOOL_FUNCTIONS.get(name):
        result = func(**args)
        return {
            "type": "function_call_output",
            "call_id": call.call_id,
            "output": json.dumps(result, indent=2),
        }

    raise ValueError(f"Unknown function: {name}")


def _parse_tool_arguments(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        return json.loads(raw)
    return {}


def run_agent_loop(
    question: str,
    instructions: str,
    model: str,
    tools: list[dict] | None = None,
):
    exchange_record = ExchangeRecord(
        model=model,
        instructions=instructions,
        query=question,
    )

    messages: list[Any] = [{"role": "user", "content": question}]
    response_records: list[ResponseRecord] = []
    tool_call_records: list[ToolCallRecord] = []
    last_answer = None

    while True:
        has_function_calls = False

        response = _get_llm_response(
            messages=messages,
            instructions=instructions,
            model=model,
            tools=tools,
        )
        messages.extend(response.output)

        cost = _calculate_cost(response.usage, model)
        response_records.append(
            ResponseRecord(
                id=response.id,
                exchange_id=exchange_record.id,
                created_at=datetime.fromtimestamp(response.created_at, UTC).isoformat(),
                completed_at=datetime.fromtimestamp(response.completed_at, UTC).isoformat(),
                model=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                input_cost=cost["input"],
                output_cost=cost["output"],
            )
        )

        for item in response.output:
            if item.type == "function_call":
                messages.append(_make_call(item))
                has_function_calls = True
                tool_call_records.append(
                    ToolCallRecord(
                        id=item.id,
                        call_id=item.call_id,
                        response_id=response.id,
                        name=item.name,
                        arguments=_parse_tool_arguments(item.arguments),
                    )
                )
            elif item.type == "message":
                last_answer = item.content[0].text

        if not has_function_calls:
            break

    exchange_record.response = last_answer
    exchange_record.end_datetime = datetime.now(UTC).isoformat()

    return exchange_record, response_records, tool_call_records
