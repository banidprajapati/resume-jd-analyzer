"""
The ReAct-style planning loop.

Each iteration = ONE LLM call that both decides the next action AND
evaluates progress on the previous one (merged planner+reflection - see
decisions.md for why). That call is billed against the budget before
any tool runs.

IMPORTANT: resume_parser now uses an LLM call internally to parse
the resume into structured JSON. This means resume_parser costs tokens
toward the budget. If it fails (llm_parse_failed), you may retry once.

Flow per iteration:
  1. budget.check_before_call()
  2. call_llm(planner_prompt(state)) -> decision JSON
  3. budget.record(...)  <- may raise BudgetExceeded, propagates up
  4. if decision.action == "finish": break
  5. run the chosen tool (resume_parser costs tokens; others are free)
  6. update state with the observation
  7. loop

If progress == false on the previous step, the SAME call is responsible
for replanning: the prompt explicitly forbids repeating the last action
unchanged when the previous reflection said no progress.
"""

import json

from resume_agent.agents.llm_calling import call_llm
from resume_agent.agents.prompt import FINAL_ANSWER_SYSTEM_PROMPT, PLANNER_SYSTEM_PROMPT
from resume_agent.agents.state import AgentState, ToolCallEntry
from resume_agent.budget.budget_enforcer import BudgetEnforcer, BudgetExceeded
from resume_agent.core.loggings import get_logger
from resume_agent.tools.code_exec import code_exec_tool
from resume_agent.tools.resume_parser import resume_parser_tool
from resume_agent.tools.web_search import extract_requirements, web_search_tool

log = get_logger(__name__)


def _dispatch_tool(action: str, action_input: dict) -> dict:
    if action == "resume_parser":
        return resume_parser_tool(action_input.get("filepath", ""))
    if action == "web_search":
        return web_search_tool(action_input.get("query", ""))
    if action == "code_exec":
        op = action_input.get("operation", "")
        if not op:
            return {"status": "error", "reason": "missing operation"}
        return code_exec_tool(op, action_input.get("args", {}))
    return {"status": "error", "reason": "unknown_action", "detail": action}


def run_agent(
    goal: str, resume_path: str, jd_text: str, budget: BudgetEnforcer | None = None
) -> dict:
    budget = budget or BudgetEnforcer()
    state = AgentState(goal=goal, resume_path=resume_path, jd_text=jd_text)

    try:
        step = 0
        while True:
            step += 1
            budget.check_before_call()

            user_prompt = (
                f"{state.context_summary()}\n\n"
                f"Job description:\n{jd_text}\n\n"
                f"Resume filepath: {resume_path}\n\n"
                "Decide the next single action as JSON."
            )
            result = call_llm(PLANNER_SYSTEM_PROMPT, user_prompt, force_json=True)
            budget.record(
                result.prompt_tokens,
                result.completion_tokens,
                purpose=f"plan_step_{step}",
            )

            decision = result.as_json()
            if "_parse_error" in decision:
                entry = ToolCallEntry(
                    step=step,
                    action="parse_error",
                    action_input="",
                    observation=decision,
                    reflection={
                        "progress": False,
                        "progress_reason": "invalid JSON from planner",
                    },
                )
                state.add_entry(entry)
                continue

            action = decision.get("action")
            action_input = decision.get("action_input", {})
            reasoning = decision.get("reasoning", "")

            # Enforce rules — no progress = no next step
            if not state.resume_data and action != "resume_parser":
                action = "resume_parser"
                action_input = {"filepath": resume_path}
            elif not state.requirements and action == "code_exec":
                action = "web_search"
                action_input = {"query": f"{jd_text[:80]} requirements"}
            elif state.match_result and action == "code_exec":
                action = "finish"
                action_input = {}
            elif action == "web_search" and state.web_search_count >= 3:
                if state.requirements:
                    action = "code_exec"
                    action_input = {
                        "operation": "score_from_matches",
                        "args": {"matches": [], "unmatched_requirements": []},
                    }
                else:
                    action = "finish"
                    action_input = {}

            # Check finish
            if action == "finish":
                state.finished = True
                break

            # Dispatch tool
            observation = _dispatch_tool(action, action_input)

            # Progress check
            progress = False
            progress_reason = ""

            if action == "resume_parser":
                progress = observation.get("resume_parsed", False)
                progress_reason = "Resume parsed" if progress else "Parse failed"
                if progress:
                    state.resume_data = observation
                state.resume_attempts += 1
                pt = observation.get("prompt_tokens", 0)
                ct = observation.get("completion_tokens", 0)
                if pt > 0 or ct > 0:
                    budget.record(pt, ct, purpose="resume_parse")

            elif action == "web_search":
                state.web_search_count += 1
                if observation.get("status") == "ok":
                    raw_results = observation.get("results", [])
                    extract_result = extract_requirements(raw_results, jd_text)
                    pt = extract_result.get("prompt_tokens", 0)
                    ct = extract_result.get("completion_tokens", 0)
                    if pt > 0 or ct > 0:
                        budget.record(pt, ct, purpose="extract_requirements")
                    if extract_result.get("status") == "ok":
                        state.requirements = extract_result["requirements"]
                        progress = True
                        progress_reason = (
                            f"Extracted {len(state.requirements)} requirements"
                        )
                    else:
                        progress_reason = (
                            f"Extraction failed: {extract_result.get('reason')}"
                        )
                else:
                    progress_reason = f"Search error: {observation.get('reason')}"

            elif action == "code_exec":
                if observation.get("status") == "ok":
                    state.match_result = observation["result"]
                    progress = True
                    progress_reason = f"Score: {state.match_result.get('score')}/10"
                else:
                    progress_reason = f"code_exec error: {observation.get('reason')}"

            # Log reasoning and action
            if reasoning:
                log.info("Reasoning: %s", reasoning)
            if action == "resume_parser":
                log.info("    Parsing resume PDF...")
            elif action == "web_search":
                if progress:
                    log.info(
                        "    Extracted %d job requirements", len(state.requirements)
                    )
                else:
                    log.info("    Failed to extract requirements")
            elif action == "code_exec":
                if progress:
                    log.info(
                        "    Computed score: %d/10", state.match_result.get("score", 0)
                    )
                else:
                    log.info("    Scoring failed")

            entry = ToolCallEntry(
                step=step,
                action=action,
                action_input=json.dumps(action_input),
                observation=observation,
                reflection={"progress": progress, "progress_reason": progress_reason},
                reasoning=reasoning,
            )
            state.add_entry(entry)

        if state.finished:
            budget.check_before_call()
            reasoning_summary = "\n".join(
                f"Step {e.step} ({e.action}): {e.reasoning}"
                for e in state.history
                if e.reasoning
            )
            final_prompt = (
                f"{state.context_summary()}\n\n"
                f"Agent reasoning at each step:\n{reasoning_summary}\n\n"
                f"Write the final report now."
            )
            result = call_llm(
                FINAL_ANSWER_SYSTEM_PROMPT, final_prompt, force_json=False
            )
            budget.record(
                result.prompt_tokens, result.completion_tokens, purpose="final_answer"
            )
            state.final_answer = result.raw_text

    except BudgetExceeded as e:
        state.stopped_early = True
        state.stop_reason = str(e)

    return {
        "state": state.partial_report(),
        "budget": budget.summary(),
    }
