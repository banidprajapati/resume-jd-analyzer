"""
Budget enforcement. Tracks LLM call count and simulated cost,
raising BudgetExceeded when either limit is hit.

Cost model: $0.01 per 1000 tokens (qwen2.5:3b-instruct pricing).
"""

from dataclasses import dataclass, field

COST_PER_1K_TOKENS = 0.01


class BudgetExceeded(Exception):
    """Raised when call count or cost limit is exceeded."""

    def __init__(
        self, message: str, limit_type: str = "", current: float = 0, limit: float = 0
    ):
        super().__init__(message)
        self.limit_type = limit_type  # "calls" or "cost"
        self.current = current
        self.limit = limit


@dataclass
class BudgetEnforcer:
    max_calls: int = 10
    max_cost: float = 0.20

    call_count: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    records: list[dict] = field(default_factory=list)

    def check_before_call(self):
        """Call before every LLM invocation. Raises if budget is exhausted."""
        if self.call_count >= self.max_calls:
            raise BudgetExceeded(
                f"Call limit reached: {self.call_count}/{self.max_calls}",
                limit_type="calls",
                current=self.call_count,
                limit=self.max_calls,
            )
        if self.total_cost >= self.max_cost:
            raise BudgetExceeded(
                f"Cost limit reached: ${self.total_cost:.4f}/${self.max_cost:.2f}",
                limit_type="cost",
                current=self.total_cost,
                limit=self.max_cost,
            )

    def record(self, prompt_tokens: int, completion_tokens: int, purpose: str = ""):
        """Record usage after a successful LLM call."""
        self.call_count += 1
        self.total_tokens += prompt_tokens + completion_tokens
        cost = ((prompt_tokens + completion_tokens) / 1000) * COST_PER_1K_TOKENS
        self.total_cost += cost
        self.records.append(
            {
                "call": self.call_count,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost": round(cost, 4),
                "purpose": purpose,
            }
        )

    def summary(self) -> dict:
        return {
            "calls_used": self.call_count,
            "max_calls": self.max_calls,
            "total_cost": round(self.total_cost, 4),
            "max_cost": self.max_cost,
            "total_tokens": self.total_tokens,
            "remaining_calls": self.max_calls - self.call_count,
            "remaining_budget": round(self.max_cost - self.total_cost, 4),
            "records": self.records,
        }
