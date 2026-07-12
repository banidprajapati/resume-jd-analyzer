"""
Manual Unit Test: code_exec.py

Run: python tests/test_code_exec.py

Tests the code execution tool directly.
Does NOT require Ollama — pure deterministic logic.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resume_agent.tools.code_exec import code_exec_tool


def test_code_exec():
    print("=" * 60)
    print("UNIT TEST: code_exec.py")
    print("=" * 60)

    test_cases = [
        {
            "name": "Test 1: score_from_matches — high match",
            "operation": "score_from_matches",
            "args": {
                "matches": [
                    {"jd_requirement": "Python", "resume_evidence": "Python", "confidence": "high"},
                    {"jd_requirement": "SQL", "resume_evidence": "SQL", "confidence": "high"},
                    {"jd_requirement": "Docker", "resume_evidence": "Docker", "confidence": "high"},
                ],
                "unmatched_requirements": ["Kubernetes"],
            },
            "expect_status": "ok",
            "expect_score_range": (8, 10),
        },
        {
            "name": "Test 2: score_from_matches — low match",
            "operation": "score_from_matches",
            "args": {
                "matches": [
                    {"jd_requirement": "Photoshop", "resume_evidence": "some tool", "confidence": "medium"},
                ],
                "unmatched_requirements": ["Illustrator", "Figma", "InDesign"],
            },
            "expect_status": "ok",
            "expect_score_range": (1, 4),
        },
        {
            "name": "Test 3: word_stats",
            "operation": "word_stats",
            "args": {"text": "Hello world. This is a test.\nAnother line here."},
            "expect_status": "ok",
        },
        {
            "name": "Test 4: date_range_years",
            "operation": "date_range_years",
            "args": {"ranges": [{"start": "2020-01", "end": "2023-06"}]},
            "expect_status": "ok",
        },
        {
            "name": "Test 5: unknown operation",
            "operation": "invalid_op",
            "args": {},
            "expect_status": "error",
        },
    ]

    results = []

    for tc in test_cases:
        print(f"\n{tc['name']}")
        print("-" * 40)

        result = code_exec_tool(tc["operation"], tc["args"])
        status = result.get("status", "unknown")
        passed = status == tc["expect_status"]
        results.append({"test": tc["name"], "status": status, "passed": passed})

        if passed:
            print(f"  PASS: status={status}")
        else:
            print(f"  FAIL: expected {tc['expect_status']}, got {status}")

        if status == "ok":
            res = result.get("result", {})
            if "score" in res:
                score = res["score"]
                print(f"  Score: {score}/10 ({res.get('match_score_pct', 0)}%)")
                print(f"  Matched: {res.get('matched_skills', [])}")
                print(f"  Unmatched: {res.get('unmatched_requirements', [])}")
                if "expect_score_range" in tc:
                    low, high = tc["expect_score_range"]
                    if low <= score <= high:
                        print(f"  Score in expected range [{low}-{high}]: OK")
                    else:
                        print(f"  WARNING: Score {score} outside expected range [{low}-{high}]")
                        passed = False
            elif "word_count" in res:
                print(f"  Words: {res['word_count']}, Lines: {res['line_count']}")
            elif "total_years" in res:
                print(f"  Total years: {res['total_years']}")
        elif status == "error":
            print(f"  Reason: {result.get('reason', 'unknown')}")

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
    success = test_code_exec()
    sys.exit(0 if success else 1)
