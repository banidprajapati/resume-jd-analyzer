"""
Agent state tracking. Stores the full execution trace and computed
results so the planner prompt can reference everything seen so far.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCallEntry:
    step: int
    action: str
    action_input: str
    observation: dict
    reflection: dict
    reasoning: str = ""


@dataclass
class AgentState:
    goal: str
    resume_path: str
    jd_text: str

    resume_data: dict | None = None
    match_result: dict | None = None
    final_answer: str | None = None
    requirements: list[str] = field(default_factory=list)

    flagged_credentials: list[str] = field(default_factory=list)
    web_search_results: list[str] = field(default_factory=list)
    web_search_count: int = 0
    history: list[ToolCallEntry] = field(default_factory=list)
    resume_attempts: int = 0

    finished: bool = False
    stopped_early: bool = False
    stop_reason: str | None = None

    def add_entry(self, entry: ToolCallEntry):
        self.history.append(entry)

    def context_summary(self) -> str:
        """Build a compact string the planner can use for replanning."""
        lines = []

        if self.resume_data:
            resume_parsed = self.resume_data.get("resume_parsed", False)
            structured = self.resume_data.get("structured")
            if structured:
                skills = structured.get("skills") or {}
                all_skills = (skills.get("technical") or []) + (skills.get("tools") or [])
                exp = structured.get("experience") or []
                companies = [e.get("company", "") for e in exp if e.get("company")]
                lines.append(f"resume_parsed: true — DO NOT call resume_parser again")
                lines.append(f"Resume parsed: experience at {companies}")
                lines.append(f"All technical skills: {all_skills}")
            else:
                lines.append(f"resume_parsed: false — structured data unavailable")
        elif self.resume_attempts > 0:
            lines.append(f"resume_parsed: FAILED after {self.resume_attempts} attempt(s) — retry parsing")
        else:
            lines.append("resume_parsed: false — Call resume_parser(filepath) first.")

        if self.requirements:
            lines.append(f"requirements_extracted: true ({len(self.requirements)} requirements)")
            lines.append(f"JD Requirements: {', '.join(self.requirements)}")
        elif self.web_search_results:
            lines.append(f"web_search_done: true ({self.web_search_count}/3 searches used)")
            lines.append(f"Web search raw results available (not yet processed)")
        else:
            lines.append("requirements_extracted: false — No web search performed yet.")

        if self.match_result:
            score = self.match_result.get("score", "?")
            pct = self.match_result.get("match_score_pct", "?")
            matched = [s for s in self.match_result.get("matched_skills", []) if s.strip()]
            unmatched = [s for s in self.match_result.get("unmatched_requirements", []) if s.strip()]
            lines.append(f"Match Score: {score}/10 ({pct}%)")
            lines.append(f"Matched: {', '.join(str(s) for s in matched)}")
            lines.append(f"Unmatched: {', '.join(str(s) for s in unmatched)}")
        else:
            lines.append("Match score: not yet computed")

        if self.history:
            last = self.history[-1]
            progress = last.reflection.get("progress", "unknown")
            progress_reason = last.reflection.get("progress_reason", "")
            obs_status = last.observation.get("status", "unknown")
            lines.append(f"Last step ({last.step}): {last.action} -> progress={progress}")
            if progress_reason:
                lines.append(f"Progress reason: {progress_reason}")
            # Show observation details for reflection
            if last.action == "web_search":
                results = last.observation.get("results", [])
                lines.append(f"Observation: web_search returned {len(results)} results (status={obs_status})")
            elif last.action == "resume_parser":
                lines.append(f"Observation: resume_parser status={obs_status}")
            elif last.action == "code_exec":
                score = last.observation.get("result", {}).get("score", "?")
                lines.append(f"Observation: code_exec score={score}/10 (status={obs_status})")
            else:
                lines.append(f"Observation: {last.action} status={obs_status}")
        else:
            lines.append("No steps taken yet")

        return "\n".join(lines)

    def partial_report(self) -> str:
        """Return whatever we have if budget runs out early."""
        parts = []
        if self.match_result:
            score = self.match_result.get("score", "?")
            pct = self.match_result.get("match_score_pct", "?")
            matched = [s for s in self.match_result.get("matched_skills", []) if s.strip()]
            unmatched = [s for s in self.match_result.get("unmatched_requirements", []) if s.strip()]
            parts.append(f"Match Score: {score}/10 ({pct}%)")
            parts.append(f"Matched ({len(matched)}): {', '.join(str(s) for s in matched)}")
            if unmatched:
                parts.append(f"Unmatched ({len(unmatched)}): {', '.join(str(s) for s in unmatched)}")
        if self.final_answer:
            parts.append(f"\n{self.final_answer}")
        if self.stopped_early:
            parts.append(f"\nStopped early: {self.stop_reason}")
        return "\n".join(parts)
