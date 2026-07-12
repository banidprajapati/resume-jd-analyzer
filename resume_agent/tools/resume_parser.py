"""
Custom tool #1: Resume Parser

Extracts raw text from PDF via PyMuPDF, then uses the LLM to parse it
into structured JSON. The LLM identifies sections, skills, education,
experience, and contact info — no hardcoded keyword lists.

Timeout is enforced with ThreadPoolExecutor, same as every other tool.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

import fitz  # PyMuPDF

from resume_agent.agents.llm_calling import call_llm

PARSE_SYSTEM_PROMPT = """Parse this resume into JSON. Return ONLY valid JSON, no other text.

Schema:
{
  "contact_info": {"name": "", "email": "", "phone": "", "location": "", "linkedin": ""},
  "skills": {
    "technical": [],
    "soft": [],
    "tools": [],
    "languages": []
  },
  "experience": [{"company": "", "title": "", "dates": "", "highlights": []}],
  "education": [{"institution": "", "degree": "", "field": "", "dates": "", "gpa": ""}],
  "certifications": [],
  "summary": ""
}

Skill extraction rules:
- Scan the ENTIRE resume: skills section, experience highlights, project descriptions, education
- "technical": programming languages, frameworks, libraries (Python, PyTorch, React, FastAPI, etc.)
- "tools": platforms, databases, cloud, DevOps, version control (Docker, Git, AWS, MongoDB, etc.)
- "soft": interpersonal skills (leadership, communication, teamwork, etc.)
- "languages": spoken languages only (English, Nepali, Spanish) — NOT programming languages
- Each skill appears ONCE in its correct category

Experience rules:
- Include ALL roles: work, internship, volunteer, community — in one "experience" array
- Each highlight is a single bullet point describing what was done

General rules:
- Use "" for missing strings, [] for missing lists, null for missing nested objects
- Extract skills mentioned ANYWHERE in the resume, not just a dedicated skills section"""


def _extract_raw_text(filepath: str) -> str:
    try:
        doc = fitz.open(filepath)
    except (fitz.FileDataError, RuntimeError) as e:
        raise ValueError(f"File is corrupted or not a valid PDF: {e}") from e

    try:
        if doc.is_closed:
            raise ValueError("PDF failed to open (encrypted or corrupted)")

        text_parts = []
        for page in doc:
            text = page.get_text()
            text_parts.append(text)
    finally:
        doc.close()

    return "\n".join(text_parts)


def _parse_with_llm(raw_text: str) -> dict:
    """LLM call to parse raw text into structured JSON."""
    result = call_llm(
        PARSE_SYSTEM_PROMPT, f"Parse this resume:\n\n{raw_text}", force_json=True
    )
    parsed = result.as_json()
    return {
        "parsed": parsed,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
    }


def _parse_pdf(filepath: str) -> dict:
    if not os.path.exists(filepath):
        return {"status": "error", "resume_parsed": False, "reason": "file_not_found"}

    if os.path.getsize(filepath) == 0:
        return {"status": "error", "resume_parsed": False, "reason": "empty_file"}

    try:
        raw_text = _extract_raw_text(filepath)
    except ValueError as e:
        return {"status": "error", "resume_parsed": False, "reason": "unreadable_pdf", "detail": str(e)}

    if not raw_text.strip():
        return {
            "status": "error",
            "resume_parsed": False,
            "reason": "no_extractable_text",
            "detail": "PDF likely scanned/image-only",
        }

    llm_result = _parse_with_llm(raw_text)

    if "_parse_error" in llm_result["parsed"]:
        return {
            "status": "error",
            "resume_parsed": False,
            "reason": "llm_parse_failed",
            "detail": llm_result["parsed"]["_parse_error"],
            "prompt_tokens": llm_result["prompt_tokens"],
            "completion_tokens": llm_result["completion_tokens"],
        }

    return {
        "status": "ok",
        "resume_parsed": True,
        "structured": llm_result["parsed"],
        "prompt_tokens": llm_result["prompt_tokens"],
        "completion_tokens": llm_result["completion_tokens"],
    }


def resume_parser_tool(filepath: str, timeout: int = 30) -> dict:
    """Public entry point. Increased timeout to account for LLM call."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_parse_pdf, filepath)
        try:
            return future.result(timeout=timeout)
        except FutureTimeout:
            return {
                "status": "error",
                "reason": "timeout",
                "detail": f"parsing exceeded {timeout}s",
            }
        except Exception as e:
            return {"status": "error", "reason": "unexpected_error", "detail": str(e)}


if __name__ == "__main__":
    import json
    import sys

    filepath = (
        sys.argv[1]
        if len(sys.argv) > 1
        else r"D:\Projects\jobins\resume_agent\data\Banid Prajapati CV.pdf"
    )

    print(f"Parsing: {filepath}")
    result = resume_parser_tool(filepath, timeout=60)

    print(f"\nStatus: {result['status']}")
    if result["status"] == "error":
        print(f"Reason: {result['reason']}")
        if "detail" in result:
            print(f"Detail: {result['detail']}")
    else:
        if result.get("structured"):
            print(f"\nStructured output:\n{json.dumps(result['structured'], indent=2)}")
