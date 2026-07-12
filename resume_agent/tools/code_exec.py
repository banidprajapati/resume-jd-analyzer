"""
Tool #3: Code Execution

Deterministic operations over LLM-produced structured data.
The LLM does semantic matching; code_exec does arithmetic.
"""

from datetime import datetime


def _compute_score(
    matched: int, total: int, high_conf: int = 0, med_conf: int = 0
) -> int:
    """Confidence-weighted scoring: high=1.0, medium=0.5."""
    if total == 0:
        return 1
    weighted = high_conf * 1.0 + med_conf * 0.5
    ratio = weighted / total
    if ratio >= 0.85:
        return 10
    if ratio >= 0.70:
        return 9
    if ratio >= 0.60:
        return 8
    if ratio >= 0.50:
        return 7
    if ratio >= 0.40:
        return 6
    if ratio >= 0.30:
        return 5
    if ratio >= 0.20:
        return 4
    if ratio >= 0.10:
        return 3
    if ratio > 0:
        return 2
    return 1


def _score_from_matches(matches: list, unmatched_requirements: list) -> dict:
    """Deterministic scoring from LLM-produced structured verdict."""
    # Normalize: extract jd_requirement string from dicts if needed
    clean_unmatched = []
    for u in unmatched_requirements:
        if isinstance(u, dict):
            clean_unmatched.append(u.get("jd_requirement", str(u)))
        else:
            clean_unmatched.append(str(u))

    total = len(matches) + len(clean_unmatched)
    matched_count = len(matches)

    high_conf = sum(1 for m in matches if m.get("confidence") == "high")
    med_conf = sum(
        1 for m in matches if m.get("confidence") != "high"
    )  # default missing to medium
    weighted_ratio = (high_conf * 1.0 + med_conf * 0.5) / total if total else 0.0

    return {
        "score": _compute_score(matched_count, total, high_conf, med_conf),
        "match_score_pct": round(weighted_ratio * 100, 1),
        "matched_count": matched_count,
        "total_requirements": total,
        "high_confidence_matches": high_conf,
        "medium_confidence_matches": med_conf,
        "matched_skills": list(
            dict.fromkeys(
                skill.strip()
                for m in matches
                for skill in (m.get("resume_evidence", "").split(","))
                if skill.strip()
            )
        ),
        "unmatched_requirements": clean_unmatched,
        "matches": matches,
    }


def _word_stats(text: str) -> dict:
    """Compute word/section stats from raw text."""
    words = text.split()
    lines = text.split("\n")
    non_empty_lines = [l for l in lines if l.strip()]

    sections = 0
    for line in non_empty_lines:
        stripped = line.strip()
        if stripped.isupper() or (len(stripped) < 60 and stripped.endswith(":")):
            sections += 1

    return {
        "word_count": len(words),
        "line_count": len(non_empty_lines),
        "estimated_sections": sections,
    }


def _date_range_years(ranges: list) -> dict:
    """Compute total years from a list of {start, end} date ranges."""
    total_months = 0
    for r in ranges:
        start = r.get("start", "")
        end = r.get("end", "")
        if not start:
            continue

        try:
            s = datetime.strptime(start, "%Y-%m")
            e = datetime.strptime(end, "%Y-%m") if end else datetime.now()
            months = (e.year - s.year) * 12 + (e.month - s.month)
            total_months += max(0, months)
        except ValueError:
            continue

    years = total_months / 12
    return {
        "total_years": round(years, 1),
        "total_months": total_months,
        "range_count": len(ranges),
    }


OPERATIONS = {
    "score_from_matches": lambda args: _score_from_matches(
        args["matches"], args.get("unmatched_requirements", [])
    ),
    "word_stats": lambda args: _word_stats(args["text"]),
    "date_range_years": lambda args: _date_range_years(args["ranges"]),
}


def code_exec_tool(operation: str, args: dict) -> dict:
    """
    Execute a deterministic operation.

    Supported operations:
        score_from_matches: args={"matches": [...], "unmatched_requirements": [...]}
        word_stats: args={"text": "..."}
        date_range_years: args={"ranges": [{"start": "2020-01", "end": "2023-06"}, ...]}

    Returns:
        {"status": "ok", "result": {...}} or {"status": "error", "reason": "..."}
    """
    op_fn = OPERATIONS.get(operation)
    if not op_fn:
        return {"status": "error", "reason": f"unknown operation: {operation}"}

    try:
        result = op_fn(args)
        return {"status": "ok", "result": result}
    except KeyError as e:
        return {"status": "error", "reason": f"missing arg: {e}"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}
