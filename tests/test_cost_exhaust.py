"""
Task 5: Cost-limit exhaustion
Budget capped at $0.05 to force cost limit before call limit.

Run: python tests/test_task5.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resume_agent.agents.llm_agent import run_agent
from resume_agent.agents.llm_calling import init_client
from resume_agent.budget.budget_enforcer import BudgetEnforcer

init_client()
cheap = BudgetEnforcer(max_calls=10, max_cost=0.2)
result = run_agent(
    "Cost test",
    "data/Banid Prajapati CV.pdf",
    "Match resume to job description",
    cheap
)
print(result["state"])
print(result["budget"])
