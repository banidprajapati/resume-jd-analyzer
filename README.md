# Jobins — Resume-Matching Agent

A ReAct-style LLM agent that parses resumes, matches skills against job descriptions, and produces match reports under a hard budget of 10 LLM calls and $0.20.

## Architecture Overview

Three layers: a **planner** (LLM decides next action), **tools** (resume_parser, web_search, code_exec), and a **budget enforcer** (hard stop on calls/cost). State flows through an `AgentState` dataclass — the planner sees a compact `context_summary()` string on every call.

## Planning Loop

We use a **ReAct** loop where each iteration makes one LLM call that acts as both planner and reflector. The model receives current state, decides the next tool call as JSON, and the tool result is folded back into state.

**Biggest weakness:** The planner is a small local model (~2B params) that sometimes returns invalid JSON or ignores the workflow. Guards enforce the correct sequence (parse → search → score → finish), so the model's reasoning is partially overridden by hard-coded rules rather than being fully autonomous.

## Schema Design

`AgentState` fields: `resume_data` (parsed resume), `requirements` (extracted JD requirements), `match_result` (score, matched/unmatched skills), `history` (full trace with observation, progress, reasoning). Every tool returns `{"status": "ok"|"error"}`. The planner receives a `context_summary()` string plus raw JD text and resume filepath.

## Prompt Strategy

Prompts centralized in `agents/prompt.py`:
- **Planner** — lists tools with JSON schemas, states workflow order, enforces that `resume_evidence` comes from parsed resume only.
- **Extract** — extracts 5-10 concrete JD requirements from raw search results.
- **Parse** — parses resume text into structured JSON (skills, experience, education).
- **Final answer** — generates human-readable report from computed match data.

Progress is checked via JSON field inspection of tool output (not a separate LLM call), saving budget for actual work: `resume_parser` returns `resume_parsed: true/false`, `web_search` feeds through `extract_requirements()`, `code_exec` returns the score.

## Failure Modes

**Resume parser returns invalid JSON.** The model sometimes returns malformed JSON. System retries automatically — `resume_attempts` tracks failures, context summary tells planner to retry. 1-3 retries are common.

**Planner skips web_search.** Without guards, the planner jumps from parsing to code_exec without JD requirements. Guard forces web_search first.

## Future Work

- **Separate reflection model.** Merged planner+reflector saves budget but progress evaluation is unreliable. A dedicated reflection call would help.
- **Larger model.** 7B+ params would reduce parse errors and improve match quality.
- **Playwright for JD extraction.** Current web_search returns snippets, missing requirements for vague JDs. Playwright could extract full page content.

## Running

### Local (CLI)
```bash
ollama pull gemma4:e2b
uv run python -m resume_agent.main --resume "data/Banid Prajapati CV.pdf" --jd "data/sample_jd_full.txt"
```

### Local (API)
```bash
uv run uvicorn resume_agent.api:app --reload --port 8000
curl -X POST http://localhost:8000/match -F "resume=@data/Banid Prajapati CV.pdf" -F "jd=$(cat data/sample_jd_full.txt)"
```

### Docker
```bash
cp .env.example .env  # fill in keys; set LLM_BASE_URL=http://host.docker.internal:11434/v1 for Docker
docker build -t jobins .
docker run --env-file .env -p 8000:8000 --add-host=host.docker.internal:host-gateway jobins
```

### Tests
```bash
uv run python tests/test_code_exec.py
uv run python tests/test_resume_parser.py
uv run python tests/test_web_search.py
uv run python tests/test_infinite_loop.py
uv run python tests/test_cost_exhaust.py
```

## Files

```
resume_agent/
  agents/
    llm_agent.py      — Main ReAct loop
    llm_calling.py     — OpenAI-compatible API wrapper (Ollama)
    prompt.py          — All system prompts
    state.py           — AgentState dataclass + context_summary
  tools/
    resume_parser.py   — PDF extraction + LLM parsing
    web_search.py      — Tavily search + requirement extraction
    code_exec.py       — Deterministic scoring
  budget/
    budget_enforcer.py — Hard call/cost limits
  core/
    config.py          — Pydantic settings (.env)
    loggings.py        — Logger setup
  main.py             — CLI entry point
  api.py              — FastAPI backend
tests/
  test_code_exec.py      — Unit tests for code execution
  test_resume_parser.py  — Unit tests for resume parsing
  test_web_search.py     — Unit tests for web search
  test_data.py           — Sample resumes and JDs for testing
  test_run.py            — Full agent run tests
  test_infinite_loop.py  — Adversarial: infinite loop bait
  test_cost_exhaust.py   — Adversarial: cost exhaustion
data/                  — Resumes and job descriptions
```
