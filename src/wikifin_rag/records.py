"""Persistence records for logged chat turns."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from wikifin_rag.config import DEFAULT_LLM_MODEL


@dataclass
class ExchangeRecord:
    instructions: str
    query: str
    id: str = field(default_factory=lambda: str(uuid4()))
    model: str = DEFAULT_LLM_MODEL
    response: str | None = None
    start_datetime: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    end_datetime: str | None = None


@dataclass
class ResponseRecord:
    id: str
    exchange_id: str
    created_at: str
    completed_at: str
    model: str = DEFAULT_LLM_MODEL
    input_tokens: int = 0
    output_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0


@dataclass
class ToolCallRecord:
    id: str
    call_id: str
    response_id: str
    name: str
    arguments: dict = field(default_factory=dict)
