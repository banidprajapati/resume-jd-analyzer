"""
Manual Test: Full Agent on 5 Tasks

Run: python tests/test_data.py

Runs the resume-matching agent on 5 different task configurations
and documents the results.

Requires:
  - Ollama running with gemma4:e2b model
  - TAVILY_API_KEY in .env
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resume_agent.agents.llm_agent import run_agent
from resume_agent.budget.budget_enforcer import BudgetEnforcer

RESUME = "data/Banid Prajapati CV.pdf"
RESULTS_LOG = "tests/manual_test_results.json"


def run_task(task_name, goal, resume_path, jd_text, budget=None):
    """Run one task and return the result."""
    print(f"\n{'=' * 60}")
    print(f"TASK: {task_name}")
    print(f"{'=' * 60}")
    print(f"Goal: {goal}")
    print(f"Resume: {resume_path}")
    print(f"JD (first 100 chars): {jd_text[:100]}...")

    result = run_agent(goal, resume_path, jd_text, budget)

    state = result["state"]
    budget_info = result["budget"]

    print(f"\nResult:")
    print(f"  State: {state[:200]}...")
    print(f"  Calls used: {budget_info['calls_used']}/{budget_info['max_calls']}")
    print(f"  Total cost: ${budget_info['total_cost']:.4f}/${budget_info['max_cost']:.2f}")

    return {
        "task": task_name,
        "state": state,
        "calls_used": budget_info["calls_used"],
        "max_calls": budget_info["max_calls"],
        "total_cost": budget_info["total_cost"],
        "max_cost": budget_info["max_cost"],
    }


def load_jd(filepath):
    """Load a JD from file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def main():
    print("MANUAL TEST: Full Agent on 5 Tasks")
    print("Requires Ollama running with gemma4:e2b")

    all_results = []

    # Task 1: Standard JD
    jd_full = load_jd("data/sample_jd_full.txt")
    r1 = run_task(
        "Task 1: Standard JD match",
        "Match resume to job description",
        RESUME,
        jd_full,
    )
    all_results.append(r1)

    # Task 2: Vague JD
    jd_vague = load_jd("data/sample_jd_vague.txt")
    r2 = run_task(
        "Task 2: Vague JD",
        "Match resume to job description",
        RESUME,
        jd_vague,
    )
    all_results.append(r2)

    # Task 3: Minimal JD
    jd_minimal = "Looking for a Python developer."
    r3 = run_task(
        "Task 3: Minimal JD",
        "Match resume to job description",
        RESUME,
        jd_minimal,
    )
    all_results.append(r3)

    # Task 4: Wrong domain JD
    jd_wrong = "We need a Graphic Designer with Photoshop, Illustrator, and Figma experience. Must have a strong portfolio."
    r4 = run_task(
        "Task 4: Wrong domain (low match expected)",
        "Match resume to job description",
        RESUME,
        jd_wrong,
    )
    all_results.append(r4)

    # Task 5: Tight budget (infinite loop bait simulation)
    tight_budget = BudgetEnforcer(max_calls=3, max_cost=0.20)
    r5 = run_task(
        "Task 5: Tight budget (stops early)",
        "Keep searching until you find a 100% perfect match for this resume",
        RESUME,
        jd_full,
        budget=tight_budget,
    )
    all_results.append(r5)

    # Summary
    print("\n" + "=" * 60)
    print("ALL RESULTS")
    print("=" * 60)
    print(f"{'Task':<35} {'Calls':<10} {'Cost':<12} {'Status'}")
    print("-" * 60)
    for r in all_results:
        calls = f"{r['calls_used']}/{r['max_calls']}"
        cost = f"${r['total_cost']:.4f}"
        status = "STOPPED EARLY" if "STOPPED" in r["state"].upper() or r["calls_used"] >= r["max_calls"] else "OK"
        print(f"{r['task']:<35} {calls:<10} {cost:<12} {status}")

    # Save results
    with open(RESULTS_LOG, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {RESULTS_LOG}")

    return all_results


if __name__ == "__main__":
    main()
