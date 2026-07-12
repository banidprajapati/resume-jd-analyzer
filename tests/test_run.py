import sys
sys.path.insert(0, "D:\\Projects\\jobins")

from resume_agent.agents.llm_agent import run_agent
from resume_agent.budget.budget_enforcer import BudgetEnforcer

jd_text = open("data/sample_jd_full.txt", "r", encoding="utf-8").read()

budget = BudgetEnforcer()
result = run_agent(
    goal="Evaluate how well this resume matches the given job description.",
    resume_path="data/Banid Prajapati CV.pdf",
    jd_text=jd_text,
    budget=budget,
)

print("=" * 60)
print("RESUME MATCH REPORT")
print("=" * 60)
print(result["state"])
print()
b = result["budget"]
print(f"Calls: {b['calls_used']}/{b['max_calls']} | Cost: ${b['total_cost']:.4f}/{b['max_cost']} | Tokens: {b['total_tokens']}")
print()
print("Budget breakdown:")
for r in b["records"]:
    print(f"  {r['purpose']}: prompt={r['prompt_tokens']}, completion={r['completion_tokens']}, cost=${r['cost']:.4f}")
