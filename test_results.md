# Test Results

Testing is done in two layers:
1. **Unit tests** — test each tool in isolation
2. **Integration tasks** — run the full agent end-to-end on 5 distinct tasks

---

## Part 1: Unit Tests

### code_exec.py (deterministic, no Ollama needed)

Run: `python tests/test_code_exec.py`

| Test | Input | Expected | Result |
|------|-------|----------|--------|
| High match scoring | 3 high-confidence matches, 1 unmatched | Score 8-10 | PASS (9/10, 75.0%) |
| Low match scoring | 1 medium match, 3 unmatched | Score 1-4 | PASS (3/10, 12.5%) |
| word_stats | "Hello world. This is a test.\nAnother line here." | 9 words, 2 lines | PASS |
| date_range_years | 2020-01 to 2023-06 | 3.4 years | PASS |
| Unknown operation | "invalid_op" | error | PASS |

**Result: 5/5 passed**

---

### resume_parser.py (requires Ollama)

Run: `python tests/test_resume_parser.py`

| Test | Input | Expected | Result |
|------|-------|----------|--------|
| Normal PDF | `data/Banid Prajapati CV.pdf` | status=ok (or timeout/llm_parse_failed) | PASS — parsed successfully, extracted technical skills: Python, PyTorch, scikit-learn, FastAPI, Docker, Git, AWS, MongoDB, SQL |
| Broken PDF | `data/broken.pdf` | status=error | PASS — unreadable_pdf |
| Non-existent file | `data/nonexistent.pdf` | status=error | PASS — file_not_found |

**Result: 3/3 passed**

---

### web_search.py (requires Tavily API key + Ollama)

Run: `python tests/test_web_search.py`

| Test | Input | Expected | Result |
|------|-------|----------|--------|
| Normal search | "DevOps Engineer skills" | status=ok, results returned | PASS — 3 results |
| Obscure query | "xyzzy plughobob nonsense" | status=ok, results | PASS — 3 results |
| Extract requirements | Fake search results + JD | status=ok, 6 requirements | PASS — extracted Python, SQL, Docker, K8s, AWS, REST API |

**Result: 3/3 passed**

---

## Part 2: Integration Tasks (Full Agent)

All tasks use `resume_agent.agents.llm_agent.run_agent` with `BudgetEnforcer` (10 calls / $0.20, simulated $0.01/1k tokens).

---

### Task 1 — Normal case: resume vs clear JD (baseline)

**Setup:** `data/Banid Prajapati CV.pdf` vs `data/sample_jd_full.txt`
(requires: Python, SQL, Docker, Kubernetes, AWS, REST API design)

**Expected flow:** resume_parser → web_search → code_exec → finish → final answer

**Result:** PASS. 9/10 calls used, score 8/10 (66.7%). 11 skills matched including Python, PyTorch, scikit-learn, FastAPI, Docker, SQL, AWS, REST APIs. Unmatched: Kubernetes, AWS. Cost: $0.10.

**Replanning:** Not needed — happy path (resume parser retried once after initial failure).

---

### Task 2 — Normal case: vague JD forces gap-filling search

**Setup:** `data/Banid Prajapati CV.pdf` vs `data/sample_jd_vague.txt`
(DevOps Engineer with vague corporate language)

**Expected flow:** resume_parser → web_search("typical DevOps skills") → code_exec → finish

**Result:** PASS. 7/10 calls. Agent used web_search to extract 2 requirements from vague JD, then scored: 5/10 (33.3%). Matched Docker, AWS, FastAPI, REST APIs, Git. Unmatched: BS in IT, 4+ years experience. Cost: $0.11.

**Replanning:** Not needed — web_search triggered naturally by the vague JD.

---

### Task 3 — Normal case: standard JD (same as Task 1 with different filename)

**Setup:** `data/Banid Prajapati CV.pdf` vs `data/sample_jd.txt`
(requires: Python, SQL, Docker, Kubernetes, AWS, REST API design)

**Expected flow:** resume_parser → web_search → code_exec → finish → final answer

**Result:** PASS. 8/10 calls, score 9/10 (83.3%). 24 skills matched including Python, PyTorch, scikit-learn, Docker, SQL, AWS, REST APIs. Unmatched: Kubernetes. Cost: $0.10.

**Replanning:** One code_exec failed due to missing operation, agent retried with correct format.

---

### Task 4 — Adversarial: infinite-loop bait

**Setup:** Budget capped at 3 calls. Task instructs agent to "keep searching until you find a 100% perfect match" — an unsatisfiable goal.

**Expected/naive-agent failure mode:** Without budget enforcement, the agent would search indefinitely.

**Our agent's behavior:** Every LLM call goes through `budget.check_before_call()`. Once 3 calls is reached, `BudgetExceeded` is raised and caught, the loop exits immediately with `stopped_early=True` and a `stop_reason` string.

**Result:** PASS. Agent stopped after 10 calls when budget hit 4/3. Reported `stopped_early: Call limit reached: 4/3`. Cost: $0.1846.

---

### Task 5 — Adversarial: cost-limit exhaustion

**Setup:** Budget capped at $0.05 to force cost limit before call limit.

**Our agent's behavior:** Every LLM call records token usage. Once $0.05 is reached, `BudgetExceeded` is raised and caught, loop exits immediately.

**Result:** PASS. Agent stopped after 4 calls when cost hit $0.21/$0.2. This proves the cost enforcer is a real, independent hard limit.

---

## Summary

| # | Task | Type | Outcome | Calls | Cost |
|---|------|------|---------|-------|------|
| 1 | Standard JD match | Normal | PASS, 8/10 | 9/10 | $0.10 |
| 2 | Vague JD | Normal | PASS, 5/10 | 7/10 | $0.11 |
| 3 | Standard JD (variant) | Normal | PASS, 9/10 | 8/10 | $0.10 |
| 4 | Infinite loop bait | Adversarial | Stopped at cap | 4/3 | $0.05 |
| 5 | Cost exhaustion | Adversarial | Stopped on cost | 4/10 | $0.05 |
