# =============================================================================
# backend/api.py
#
# The FastAPI web server. Three simple endpoints:
#
#   POST  /project/start            → start a new pipeline session
#   GET   /project/{id}/status      → poll for current state (called every 2s)
#   POST  /project/{id}/respond     → send approve/feedback/cancel
#
# The React frontend calls these three endpoints for everything.
# =============================================================================

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from executor import run_code_in_sandbox
from database import get_all_files

from pipeline import (
    sessions,
    create_session,
    start_pipeline_thread,
    respond_to_pipeline,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Developer AI Agent API",
    description="Multi-agent software development pipeline",
    version="1.0.0",
)

# =============================================================================
# CORS — allows your React frontend (on Vercel) to call this API.
# Without this, the browser blocks all cross-origin requests.
# =============================================================================
_allowed_origins = [
    "http://localhost:5173",            # Vite local dev server
    "http://localhost:4173",            # Vite preview
    os.getenv("FRONTEND_URL", ""),      # Your Vercel URL (set in Render env vars)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in _allowed_origins if o],   # Filter empty strings
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# =============================================================================
# REQUEST / RESPONSE MODELS
# Pydantic models validate the JSON body automatically.
# If a required field is missing, FastAPI returns a 422 error.
# =============================================================================

class StartRequest(BaseModel):
    """Body for POST /project/start"""
    project_description: str
    project_type: str = "python"        # python | web | ml | javascript
    project_name: str = "ai-generated-project"


class RespondRequest(BaseModel):
    """
    Body for POST /project/{id}/respond
    Mirrors the three choices in your original get_user_approval():
      - approved=True              → choice "1" (Approve)
      - approved=False + feedback  → choice "2" (Request Changes)
      - cancelled=True             → choice "3" (Cancel)
    """
    approved: bool
    feedback: str = ""
    cancelled: bool = False


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """
    Simple health check. Render pings this to know the server is alive.
    Also useful for you to test that the server started correctly.
    """
    return {"status": "ok", "active_sessions": len(sessions)}


@app.post("/project/start")
async def start_project(req: StartRequest):
    """
    Creates a new pipeline session and starts the pipeline in a background thread.

    The session starts immediately. The background thread begins with
    Phase 0 (GitHub repo creation) right away.

    Returns the session_id — the frontend stores this and uses it for
    all subsequent calls.
    """
    if not req.project_description.strip():
        raise HTTPException(status_code=400, detail="project_description cannot be empty")

    # Create the session dict in memory
    session_id = create_session(
        project_description=req.project_description.strip(),
        project_type=req.project_type.strip() or "python",
        project_name=req.project_name.strip() or "ai-generated-project",
    )

    # Launch the pipeline in a background thread
    # Returns immediately — the thread runs independently
    start_pipeline_thread(session_id)

    session = sessions[session_id]
    return {
        "session_id": session_id,
        "repo_name": session["repo_name"],
        "github_url": session["github_url"],
        "project_dir": session["project_dir"],
        "message": "Pipeline started! Poll /project/{id}/status to track progress.",
    }


@app.get("/project/{session_id}/status")
async def get_status(session_id: str):
    """
    Returns the current state of the pipeline.

    The React frontend calls this every 2 seconds to update the UI.
    The response contains everything the frontend needs to display:
      - status: the current machine state (planning, waiting_plan_approval, etc.)
      - phase_label: human-readable description of what's happening
      - current_plan: the plan text to show when waiting for approval
      - outputs: accumulated agent outputs (architecture, code, tests)
      - files_generated: list of created files
      - error: set if something crashed

    This is called "polling" — simpler than WebSockets for this use case.
    """
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    # Return only the fields the frontend needs.
    # We deliberately exclude threading primitives (_response_event, _response_data)
    # because they can't be serialized to JSON.
    return {
        "session_id": session_id,
        "status": session["status"],
        "phase_label": session["phase_label"],
        "phase_detail": session.get("phase_detail", ""),
        "error": session.get("error"),

        # Content for display
        "current_plan": session.get("current_plan", ""),
        "outputs": session.get("outputs", {}),
        "files_generated": session.get("files_generated", []),
        "iteration": session.get("iteration", 0),

        # Project metadata
        "repo_name": session["repo_name"],
        "github_url": session["github_url"],
        "project_dir": session["project_dir"],
        "github_username": session["github_username"],

        # Convenience flags the frontend can use directly
        "is_running": session["status"] not in {"complete", "error", "cancelled"},
        "is_waiting": session["status"] in {
            "waiting_plan_approval",
            "waiting_review",
            "waiting_improvement_approval",
        },
        "is_done": session["status"] in {"complete", "error", "cancelled"},
    }


@app.post("/project/{session_id}/respond")
async def respond(session_id: str, req: RespondRequest):
    """
    Sends the user's decision back to the waiting pipeline thread.

    This is called when the user clicks:
      - "Approve"         → approved=True
      - "Request Changes" → approved=False, feedback="..."
      - "Cancel"          → cancelled=True

    Internally this sets a threading.Event, which wakes up the
    background pipeline thread and lets it continue.
    """
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    # Validate: pipeline must be paused at a review point
    waiting_states = {"waiting_plan_approval", "waiting_review", "waiting_improvement_approval"}
    if session["status"] not in waiting_states:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Pipeline is not waiting for input. "
                f"Current status: '{session['status']}'. "
                f"You can only respond when status is one of: {waiting_states}"
            )
        )

    if not req.approved and not req.cancelled and not req.feedback.strip():
        raise HTTPException(
            status_code=400,
            detail="If not approving or cancelling, you must provide feedback."
        )

    # Wake up the pipeline thread with the user's response
    success = respond_to_pipeline(
        session_id=session_id,
        approved=req.approved,
        feedback=req.feedback,
        cancelled=req.cancelled,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send response to pipeline.")

    return {
        "ok": True,
        "message": (
            "Approved — pipeline resuming."   if req.approved  else
            "Cancelled."                      if req.cancelled else
            "Feedback received — pipeline resuming."
        ),
        "session_id": session_id,
    }


@app.get("/project/{session_id}/files")
async def list_files(session_id: str):
    """
    Returns the list of files generated in the project directory.
    The frontend can show this as a file tree.
    """
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    from pathlib import Path
    project_dir = Path(session["project_dir"])

    files = []
    for f in sorted(project_dir.rglob("*")):
        if f.is_file():
            files.append({
                "path": str(f.relative_to(project_dir)),
                "size_bytes": f.stat().st_size,
            })

    return {
        "session_id": session_id,
        "project_dir": session["project_dir"],
        "files": files,
        "total": len(files),
    }


@app.get("/sessions")
async def list_sessions():
    """
    Debug endpoint: lists all active sessions.
    Useful during development. You'd remove or protect this in production.
    """
    return {
        "sessions": [
            {
                "id": s["id"],
                "status": s["status"],
                "repo_name": s["repo_name"],
                "phase_label": s["phase_label"],
            }
            for s in sessions.values()
        ],
        "total": len(sessions),
    }

@app.post("/project/{session_id}/execute")
async def execute_code(session_id: str):
    """
    Runs the generated code in a sandbox and returns results.
    Called when user clicks "Run & Test" in the UI.
    """
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get all files from Supabase
    files = get_all_files(session_id)
    if not files:
        raise HTTPException(status_code=404, detail="No files found")

    # Run in sandbox (this takes 10-30 seconds)
    # We run it in a thread so it doesn't block the server
    from fastapi.concurrency import run_in_threadpool
    results = await run_in_threadpool(
        run_code_in_sandbox,
        files,
        session.get("project_type", "python")
    )

    return {
        "session_id": session_id,
        "success":      results["success"],
        "output":       results["output"],
        "error":        results["error"],
        "test_results": results["test_results"],
        "summary":      results["summary"],
        "files_run":    len(files),
    }
