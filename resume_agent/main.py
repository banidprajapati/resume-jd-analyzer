"""
Entry point. Run with:
    uv run python -m resume_agent.main --resume "data/Banid Prajapati CV.pdf" --jd "data/sample_jd.txt"
"""

import argparse

from resume_agent.agents.llm_agent import run_agent
from resume_agent.agents.llm_calling import init_client
from resume_agent.budget.budget_enforcer import BudgetEnforcer
from resume_agent.core.loggings import get_logger

log = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", required=True, help="path to resume PDF")
    parser.add_argument("--jd", required=True, help="path to a text file containing the JD")
    parser.add_argument("--max-calls", type=int, default=10)
    parser.add_argument("--max-cost", type=float, default=0.20)
    args = parser.parse_args()

    init_client()

    with open(args.jd, "r", encoding="utf-8") as f:
        jd_text = f.read()

    budget = BudgetEnforcer(max_calls=args.max_calls, max_cost=args.max_cost)
    result = run_agent(
        goal="Evaluate how well this resume matches the given job description.",
        resume_path=args.resume,
        jd_text=jd_text,
        budget=budget,
    )

    log.info("=" * 60)
    log.info("RESUME MATCH REPORT")
    log.info("=" * 60)
    log.info(result["state"])
    log.info("")
    b = result["budget"]
    log.info("Calls: %d/%d | Cost: $%.4f/%.2f | Tokens: %d", b['calls_used'], b['max_calls'], b['total_cost'], b['max_cost'], b['total_tokens'])


if __name__ == "__main__":
    main()
