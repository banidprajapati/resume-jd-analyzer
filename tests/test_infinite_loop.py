"""
Task 4: Infinite-loop bait
Budget capped at 3 calls. Task instructs agent to "keep searching until you find a 100% perfect match".

Run: python tests/test_task4.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resume_agent.agents.llm_agent import run_agent
from resume_agent.budget.budget_enforcer import BudgetEnforcer

tight = BudgetEnforcer(max_calls=10, max_cost=0.20)
result = run_agent(
    "Find a perfect 100% matching resume",
    "data/Banid Prajapati CV.pdf",
    "Keep searching until you find a 100% perfect match for this resume",
    tight,
)
print(result["state"])
print(result["budget"])
