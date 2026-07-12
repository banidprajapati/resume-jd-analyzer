"""
FastAPI backend for the Resume-Matching Agent.

Run:
    uv run uvicorn resume_agent.api:app --reload
    uv run uvicorn resume_agent.api:app --host 0.0.0.0 --port 8000
"""

import os
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from resume_agent.agents.llm_agent import run_agent
from resume_agent.agents.llm_calling import init_client
from resume_agent.budget.budget_enforcer import BudgetEnforcer


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_client()
    yield


app = FastAPI(
    title="Jobins — Resume Matching Agent",
    description="Match resumes against job descriptions using an LLM agent",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/match")
def match_resume(
    resume: UploadFile = File(...),
    jd: str = Form(...),
):
    """
    Match a resume (PDF) against a job description.

    - **resume**: PDF file of the resume
    - **jd**: Job description text
    """
    resume_bytes = resume.file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(resume_bytes)
        tmp_path = tmp.name

    try:
        budget = BudgetEnforcer(max_calls=10, max_cost=0.20)
        result = run_agent(
            "Match resume to job description",
            tmp_path,
            jd,
            budget,
        )
        return JSONResponse(content={
            "report": result["state"],
            "budget": result["budget"],
        })
    finally:
        os.unlink(tmp_path)
