from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LLMCallRecord:
    model: str
    prompt: str
    instructions: str
    answer: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    response_time: float
    input_cost: float
    output_cost: float
    total_cost: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Stats:
    total: int
    avg_response_time: float
    total_cost: float
    avg_tokens: float