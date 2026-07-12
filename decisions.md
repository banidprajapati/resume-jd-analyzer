# Engineering Decisions

Each entry follows: "I considered [X] but chose [Y] because [Z]."

---

**1. Planner + Reflection merged into one call**
I considered making "plan" and "reflect" two separate LLM calls per loop iteration (textbook ReAct) but chose to merge them into a single JSON response, because the hard 10-call budget makes a strict two-calls-per-iteration pattern unworkable — merging roughly doubles how much real work the agent can do within the same budget, while still satisfying the requirement that progress is evaluated after every tool call.

---

**2. Code execution: templated operations vs. arbitrary code**
I considered letting the planner submit arbitrary Python code to the code execution tool but chose to constrain it to a whitelist of pre-templated operations (`score_from_matches`) invoked with JSON arguments, because a local, unsandboxed model has no safe way to guarantee arbitrary code won't touch the filesystem or network. The tool still satisfies "code execution" — it runs real deterministic logic with real timeouts — it just can't run anything outside the whitelist.

---

**3. Tavily for web search**
I considered using DuckDuckGo (free, no API key) but chose Tavily because it returns structured, high-quality results with a proper API, which makes the downstream `extract_requirements` LLM call more reliable. The trade-off is requiring an API key, but Tavily has a generous free tier that fits the assignment's budget constraint.

---

**4. LLM-based resume parsing (tool calls LLM internally)**
I considered using purely deterministic regex/keyword extraction for the resume parser but chose to use an LLM call inside the tool, because skills appear in varied formats across resumes (bullet points, inline mentions, project descriptions) and a keyword list is brittle. The trade-off is that resume_parser costs budget tokens — this is transparent and tracked by the budget enforcer, so the planner sees the true cost.

---

**5. JSON-based progress evaluation instead of separate reflection call**
I considered adding a dedicated LLM call after each tool to evaluate "am I making progress?" but chose to evaluate progress via JSON field inspection of the tool's own output (`resume_parsed: true/false`, score comparison, requirement extraction status), because a separate reflection call would double the LLM cost per iteration. Guards enforce the correct sequence (parse → search → score → finish) so the model's reflection is supplemented by deterministic rules.

---

**6. Confidence-weighted scoring**
I considered treating all skill matches equally but chose to weight by confidence (high=1.0, medium/default=0.5), because an exact keyword match ("Python" in resume, "Python" in JD) is meaningfully stronger than a semantic stretch ("fast learner" maps to "problem-solving skills"). The weighting produces a more nuanced score that reflects real hiring decisions.

---

**7. Timeout mechanism**
I considered using `signal.alarm` for enforcing tool timeouts but chose `concurrent.futures.ThreadPoolExecutor.result(timeout=...)` for the search and resume-parsing tools, because `signal.alarm` only works on the main thread on Unix and silently fails in multi-threaded or non-Unix environments — the executor approach is portable and gives a real, verifiable kill of the blocking call.
