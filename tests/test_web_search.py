"""
Manual Unit Test: web_search.py

Run: python tests/test_web_search.py

Tests web search and requirement extraction directly.
Requires TAVILY_API_KEY in .env and Ollama running.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resume_agent.tools.web_search import extract_requirements, web_search_tool


def test_web_search():
    print("=" * 60)
    print("UNIT TEST: web_search.py")
    print("=" * 60)

    test_cases = [
        {
            "name": "Test 1: Search for DevOps Engineer requirements",
            "query": "DevOps Engineer skills and requirements 2024",
            "expect_status": "ok",
        },
        {
            "name": "Test 2: Search for something obscure (fewer results)",
            "query": "xyzzy plughobob nonsense keyword 12345",
            "expect_status": "ok",  # returns empty results, still ok
        },
    ]

    results = []

    for tc in test_cases:
        print(f"\n{tc['name']}")
        print("-" * 40)

        result = web_search_tool(tc["query"])
        status = result.get("status", "unknown")
        passed = status == tc["expect_status"]
        results.append({"test": tc["name"], "status": status, "passed": passed})

        if passed:
            print(f"  PASS: status={status}")
        else:
            print(f"  FAIL: expected {tc['expect_status']}, got {status}")

        if status == "ok":
            items = result.get("results", [])
            print(f"  Results: {len(items)}")
            for i, item in enumerate(items[:2]):
                print(f"    [{i + 1}] {item.get('title', 'no title')[:50]}")
        elif status == "error":
            print(f"  Reason: {result.get('reason', 'unknown')}")

    print("\n" + "=" * 60)
    print("TEST: extract_requirements()")
    print("=" * 60)

    # Use fake search results to test extraction without hitting Tavily
    fake_results = [
        {
            "title": "Backend Skills",
            "url": "https://example.com",
            "content": "Python, SQL, Docker, Kubernetes, AWS, REST API design",
        },
        {
            "title": "Job Requirements",
            "url": "https://example.com/2",
            "content": "3+ years experience, strong communication skills",
        },
    ]
    jd_text = "We are hiring a Backend Engineer. Requirements: Python, SQL, Docker, Kubernetes, AWS."

    print("\nTest 3: Extract requirements from fake search results")
    print("-" * 40)

    extract_result = extract_requirements(fake_results, jd_text)
    status = extract_result.get("status", "unknown")
    passed = status == "ok"
    results.append(
        {"test": "Test 3: Extract requirements", "status": status, "passed": passed}
    )

    if passed:
        print(f"  PASS: status={status}")
        reqs = extract_result.get("requirements", [])
        print(f"  Requirements: {reqs}")
        print(
            f"  Tokens: {extract_result.get('prompt_tokens', 0)} + {extract_result.get('completion_tokens', 0)}"
        )
    else:
        print(
            f"  FAIL: status={status}, reason={extract_result.get('reason', 'unknown')}"
        )

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in results:
        status_icon = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status_icon}] {r['test']} -> {r['status']}")

    passed_count = sum(1 for r in results if r["passed"])
    print(f"\n  Total: {passed_count}/{len(results)} passed")
    return passed_count == len(results)


if __name__ == "__main__":
    success = test_web_search()
    sys.exit(0 if success else 1)
