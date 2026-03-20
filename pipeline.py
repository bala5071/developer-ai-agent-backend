# =============================================================================
# backend/pipeline.py
#
# This is your original main.py logic — refactored for a web API.
#
# THE CORE PROBLEM WE'RE SOLVING:
#   Your original code used input() to pause and wait for the user.
#   In a web API, there's no terminal. We can't call input().
#   Instead, we use threading.Event — a "flag" that the background thread
#   waits on. When the user clicks "Approve" in the React frontend, the API
#   sets the flag, and the pipeline thread wakes up and continues.
#
# HOW SESSIONS WORK:
#   Each project run gets a unique session_id (like a12b3c4d).
#   The session dict stores everything: current status, outputs, plan text,
#   and the Event objects used for pausing/resuming.
#   The React frontend polls GET /project/{id}/status every 2 seconds
#   to see updates, and calls POST /project/{id}/respond to send approval
#   or feedback.
# =============================================================================

import threading
import traceback
import re
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from crewai import Crew, Process
from flask import session

# Import your existing agents
from agents.manager import create_manager_agent
from agents.developer import create_developer_agent
from agents.tester import create_tester_agent
from agents.github import create_github_agent

# Import your existing tasks
from tasks.manager_tasks import create_planning_task, create_improvement_planning_task_inline
from tasks.developer_tasks import create_development_task
from tasks.tester_tasks import create_testing_task
from tasks.github_tasks import create_github_deployment_task, create_github_repository_task

# Import your existing config
from config import OUTPUT_DIR, GITHUB_USERNAME

from tools.file_operations import set_current_session
from database import parse_and_save, write_to_temp_dir

logger = logging.getLogger(__name__)

# =============================================================================
# SESSION STORE
# A simple in-memory dictionary that maps session_id → session state.
# In production you'd use Redis or a database, but for a portfolio project
# this is perfectly fine — it resets when the server restarts.
# =============================================================================
sessions: dict[str, dict] = {}


def sanitize_repo_name(name: str) -> str:
    """Identical to your original — converts any string to a valid GitHub repo name."""
    name = re.sub(r'[^a-zA-Z0-9\s-]', '', name)
    name = name.lower().strip().replace(' ', '-')
    name = re.sub(r'-+', '-', name)
    return name


def create_session(project_description: str, project_type: str, project_name: str) -> str:
    """
    Create a new pipeline session and return its ID.
    Called by POST /project/start.
    """
    session_id = str(uuid.uuid4())[:8]   # Short, readable ID like "a1b2c3d4"
    repo_name = sanitize_repo_name(project_name or "ai-generated-project")
    project_dir = OUTPUT_DIR / repo_name
    project_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # The session dict is the "memory" of this pipeline run.
    # The frontend reads most of these fields via GET /project/{id}/status.
    # -------------------------------------------------------------------------
    sessions[session_id] = {
        # ── Identity ──────────────────────────────────────────────────────────
        "id": session_id,
        "project_description": project_description,
        "project_type": project_type,
        "project_name": project_name,
        "repo_name": repo_name,
        "github_username": GITHUB_USERNAME,
        "project_dir": str(project_dir),
        "github_url": f"https://github.com/{GITHUB_USERNAME}/{repo_name}",

        # ── Status ────────────────────────────────────────────────────────────
        # "status" is what the frontend shows the user.
        # Possible values: starting | creating_repo | planning | waiting_plan_approval
        #                  developing | testing | deploying | waiting_review
        #                  processing_feedback | waiting_improvement_approval
        #                  implementing | validating | deploying_changes | complete | error
        "status": "starting",
        "phase_label": "Initializing…",       # Human-readable current phase
        "phase_detail": "",                    # More detail (e.g. "Iteration 2/5")
        "error": None,                         # Set if something crashes

        # ── Content for the frontend to display ───────────────────────────────
        # These are the big text outputs the user needs to review.
        "current_plan": "",                    # Plan text shown to user for approval
        "outputs": {                           # Accumulated agent outputs
            "architecture": "",
            "code": "",
            "tests": "",
            "improvement_plan": "",
        },
        "files_generated": [],                 # List of file paths created
        "execution_result": None,
        "iteration": 0,                        # Current feedback iteration number

        # ── Threading primitives (NEVER sent to frontend) ────────────────────
        # _response_event: the background thread waits on this.
        #   When the user clicks Approve/Reject in the UI, the API calls
        #   _response_event.set(), which wakes the thread up.
        # _response_data: the API puts the user's answer here before setting the event,
        #   so the thread can read it.
        "_response_event": threading.Event(),
        "_response_data": None,               # {"approved": bool, "feedback": str}
    }
    return session_id


def _wait_for_user(session: dict, waiting_status: str) -> dict:
    """
    REPLACES input() in the original code.

    Sets the session status so the frontend knows to show the approval UI,
    then blocks the background thread until the user responds.

    Returns the response dict: {"approved": True/False, "feedback": "..."}
    """
    # Tell the frontend "I'm paused, waiting for you"
    session["status"] = waiting_status
    session["_response_event"].clear()         # Reset the flag to "not set"

    logger.info(f"[{session['id']}] Paused — waiting for user response ({waiting_status})")

    # Block here indefinitely until API sets the event
    # (threading.Event.wait() with no timeout = wait forever)
    session["_response_event"].wait()

    response = session["_response_data"]
    session["_response_data"] = None           # Clear for next use
    logger.info(f"[{session['id']}] Resumed — approved={response.get('approved')}")
    return response


def _run_crew(agents: list, tasks: list, verbose: bool = True):
    """Helper that creates and runs a Crew. Mirrors your original pattern."""
    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=verbose,
    )
    return crew.kickoff()


def _save_file(project_dir: Path, filename: str, content: str) -> Path:
    """Save a file and return its path."""
    file_path = project_dir / filename
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _list_project_files(project_dir: Path) -> list[str]:
    """Return relative paths of all files in the project directory."""
    return [
        str(f.relative_to(project_dir))
        for f in sorted(project_dir.rglob("*"))
        if f.is_file()
    ]


# =============================================================================
# MAIN PIPELINE FUNCTION
# This is run in a background thread (not in the API's async loop).
# It mirrors your original main() function exactly — just with
# input() replaced by _wait_for_user().
# =============================================================================
def run_pipeline(session_id: str) -> None:
    """
    The full pipeline, run in a background thread.
    Mirrors main() from your original main.py exactly,
    with input() replaced by _wait_for_user().
    """
    session = sessions[session_id]
    project_dir = Path(session["project_dir"])
    project_description = session["project_description"]
    project_type = session["project_type"]
    repo_name = session["repo_name"]
    github_username = session["github_username"]

    try:
        # ── Create agents once (same as your original) ────────────────────────
        session["phase_label"] = "Initializing AI agents…"
        manager        = create_manager_agent()
        developer      = create_developer_agent()
        tester         = create_tester_agent()
        github_manager = create_github_agent()

        set_current_session(session_id)

        # =====================================================================
        # PHASE 0: GITHUB REPOSITORY CREATION
        # Identical logic to your original Phase 0.
        # =====================================================================
        session["status"] = "creating_repo"
        session["phase_label"] = "Creating GitHub repository…"
        logger.info(f"[{session_id}] Phase 0: Creating repo '{repo_name}'")

        repo_task = create_github_repository_task(
            github_manager,
            repo_name,
            project_description,
            github_username,
            str(project_dir),
            visibility="public",
            license_type="MIT",
        )
        _run_crew([github_manager], [repo_task])
        session["phase_label"] = f"Repository created → {session['github_url']}"

        # =====================================================================
        # PHASE 1: PLANNING WITH APPROVAL LOOP
        # Original had a while loop with input(). We replace input() with
        # _wait_for_user(), which blocks until the frontend sends a response.
        # =====================================================================
        plan_approved = False
        planning_iteration = 0
        max_planning_iterations = 5
        current_description = project_description
        planning_task = None

        while not plan_approved and planning_iteration < max_planning_iterations:
            planning_iteration += 1
            session["status"] = "planning"
            session["phase_label"] = f"Manager creating technical plan…"
            session["phase_detail"] = f"Iteration {planning_iteration}/{max_planning_iterations}"
            logger.info(f"[{session_id}] Planning iteration {planning_iteration}")

            planning_task = create_planning_task(
                manager,
                str(project_dir),
                current_description,
                project_type,
            )
            plan_result = _run_crew([manager], [planning_task])
            plan_text = str(plan_result)

            # Save plan to disk (same as original)
            _save_file(project_dir, "TECHNICAL_PLAN.md", plan_text)

            # Store plan text so the frontend can display it
            session["current_plan"] = plan_text
            session["outputs"]["architecture"] = plan_text

            # ── PAUSE 1: Show plan to user, wait for approval ──────────────
            response = _wait_for_user(session, "waiting_plan_approval")

            if response.get("cancelled"):
                session["status"] = "cancelled"
                session["phase_label"] = "Cancelled by user."
                return

            if response.get("approved"):
                plan_approved = True
            else:
                # User wants changes — append their feedback to the description
                feedback = response.get("feedback", "")
                current_description = (
                    f"{current_description}\n\n"
                    f"ADDITIONAL REQUIREMENTS (Iteration {planning_iteration}):\n"
                    f"{feedback}\n\n"
                    f"Update the technical plan to incorporate these requirements."
                )

        if not plan_approved:
            session["status"] = "error"
            session["error"] = f"Max planning iterations ({max_planning_iterations}) reached without approval."
            return

        # =====================================================================
        # PHASE 2: CODE IMPLEMENTATION
        # =====================================================================
        session["status"] = "developing"
        session["phase_label"] = "Developer writing code…"
        session["phase_detail"] = "This may take several minutes"
        logger.info(f"[{session_id}] Phase 2: Development")

        development_task = create_development_task(
            developer,
            str(project_dir),
            str(project_type),
            context_tasks=[planning_task],
        )
        dev_result = _run_crew([developer], [development_task])
        session["outputs"]["code"] = str(dev_result)
        files_saved = parse_and_save(session_id, str(dev_result))
        session["files_generated"] = list(files_saved.keys())

        # =====================================================================
        # PHASE 3: TESTING
        # =====================================================================
        session["status"] = "testing"
        session["phase_label"] = "Tester running quality checks…"
        logger.info(f"[{session_id}] Phase 3: Testing")

        testing_task = create_testing_task(
            tester,
            str(project_dir),
            str(project_type),
            context_tasks=[planning_task, development_task],
        )
        test_result = _run_crew([tester], [testing_task])
        session["outputs"]["tests"] = str(test_result)
        parse_and_save(session_id, str(test_result))

        # =====================================================================
        # PHASE 4: INITIAL GITHUB DEPLOYMENT
        # =====================================================================
        session["status"] = "deploying"
        session["phase_label"] = "Deploying to GitHub…"
        logger.info(f"[{session_id}] Phase 4: Initial GitHub deploy")

        session["phase_label"] = "Restoring files for GitHub commit…"
        write_to_temp_dir(session_id, project_dir)

        github_task = create_github_deployment_task(
            agent=github_manager,
            project_dir=str(project_dir),
            repo_name=repo_name,
            github_username=github_username,
            context_tasks=[planning_task, development_task, testing_task],
        )
        _run_crew([github_manager], [github_task])
        session["files_generated"] = _list_project_files(project_dir)

        session["status"] = "executing"
        session["phase_label"] = "Running your code in sandbox…"
        try:
            from backend.executor import run_code_in_sandbox
            from backend.database import get_all_files

            db_files = get_all_files(session_id)
            if db_files:
                execution = run_code_in_sandbox(db_files, project_type)
            else:
                # Fallback: read from disk if DB has nothing yet
                disk_files = {}
                for f in project_dir.rglob("*"):
                    if f.is_file() and not f.suffix in {'.pyc', '.db'}:
                        try:
                            disk_files[str(f.relative_to(project_dir))] = f.read_text(encoding="utf-8")
                        except Exception:
                            pass
                execution = run_code_in_sandbox(disk_files, project_type)

            session["execution_result"] = execution
            session["phase_label"] = "Code tested — waiting for your review…"
        except Exception as e:
            logger.warning(f"[{session_id}] E2B execution failed: {e}")
            session["execution_result"] = None
            session["phase_label"] = "Waiting for your review…"
        # ← END BLOCK

        # Now pause for user review (they can see execution results)
        session["status"] = "waiting_review"

        # =====================================================================
        # PHASE 5: ITERATIVE FEEDBACK LOOP
        # Original had while True with input(). Same here — we just pause
        # with _wait_for_user() instead.
        # =====================================================================
        feedback_iteration = 0
        project_approved = False
        session["iteration"] = 0

        while not project_approved:
            feedback_iteration += 1
            session["iteration"] = feedback_iteration

            # ── PAUSE 2: Show project to user, wait for review ─────────────
            session["status"] = "waiting_review"
            session["phase_label"] = "Waiting for your review…"
            session["files_generated"] = _list_project_files(project_dir)
            logger.info(f"[{session_id}] Waiting for review (iteration {feedback_iteration})")

            response = _wait_for_user(session, "waiting_review")

            if response.get("cancelled"):
                session["status"] = "complete"
                session["phase_label"] = "Saved locally and on GitHub."
                break

            if response.get("approved"):
                project_approved = True
                break

            # User wants changes — go through Manager → Developer → Tester → GitHub
            user_feedback = response.get("feedback", "")

            # Save user feedback file (same as original)
            feedback_file = f"USER_FEEDBACK_{feedback_iteration}.md"
            _save_file(project_dir, feedback_file, (
                f"# User Feedback — Iteration {feedback_iteration}\n\n"
                f"## Requested Changes:\n{user_feedback}\n\n"
                f"## Status: Processing…\n"
            ))

            # ── STEP 1: Manager creates improvement plan ──────────────────────
            improvement_plan_approved = False
            improvement_plan_iteration = 0
            max_improvement_iterations = 2
            current_feedback = user_feedback
            improvement_plan_task = None

            while not improvement_plan_approved and improvement_plan_iteration < max_improvement_iterations:
                improvement_plan_iteration += 1
                session["status"] = "processing_feedback"
                session["phase_label"] = "Manager analyzing your feedback…"
                session["phase_detail"] = f"Improvement iteration {feedback_iteration}"
                logger.info(f"[{session_id}] Manager creating improvement plan (attempt {improvement_plan_iteration})")

                improvement_plan_task = create_improvement_planning_task_inline(
                    manager,
                    str(project_dir),
                    project_type,
                    current_feedback,
                    feedback_iteration,
                    context_tasks=[planning_task, development_task, testing_task],
                )
                improvement_result = _run_crew([manager], [improvement_plan_task])
                improvement_text = str(improvement_result)

                plan_file = f"IMPROVEMENT_PLAN_{feedback_iteration}.md"
                _save_file(project_dir, plan_file, improvement_text)

                # Store for frontend display
                session["current_plan"] = improvement_text
                session["outputs"]["improvement_plan"] = improvement_text

                # ── PAUSE 3: Show improvement plan, wait for approval ─────
                response = _wait_for_user(session, "waiting_improvement_approval")

                if response.get("cancelled"):
                    session["status"] = "complete"
                    session["phase_label"] = "Saved. You can continue manually."
                    return

                if response.get("approved"):
                    improvement_plan_approved = True
                else:
                    plan_feedback = response.get("feedback", "")
                    current_feedback = (
                        f"{user_feedback}\n\n"
                        f"ADDITIONAL FEEDBACK ON IMPROVEMENT PLAN:\n{plan_feedback}\n\n"
                        f"Please update the improvement plan based on this additional feedback."
                    )

            if not improvement_plan_approved:
                # Skip this iteration if plan couldn't be finalized
                logger.warning(f"[{session_id}] Could not finalize improvement plan — skipping iteration")
                continue

            # ── STEP 2: Developer implements ─────────────────────────────────
            session["status"] = "implementing"
            session["phase_label"] = "Developer implementing your changes…"
            logger.info(f"[{session_id}] Developer implementing changes")

            development_task = create_development_task(
                developer,
                str(project_dir),
                str(project_type),
                context_tasks=[planning_task, improvement_plan_task],
            )
            dev_result = _run_crew([developer], [development_task])
            session["outputs"]["code"] = str(dev_result)
            files_saved = parse_and_save(session_id, str(dev_result))
            session["files_generated"] = list(files_saved.keys())

            # ── STEP 3: Tester validates ──────────────────────────────────────
            session["status"] = "validating"
            session["phase_label"] = "Tester validating changes…"
            logger.info(f"[{session_id}] Tester validating changes")

            testing_task = create_testing_task(
                tester,
                str(project_dir),
                str(project_type),
                context_tasks=[planning_task, improvement_plan_task, development_task],
            )
            test_result = _run_crew([tester], [testing_task])
            session["outputs"]["tests"] = str(test_result)
            parse_and_save(session_id, str(test_result))

            # ── STEP 4: GitHub deploys ────────────────────────────────────────
            session["status"] = "deploying_changes"
            session["phase_label"] = "Deploying updates to GitHub…"
            logger.info(f"[{session_id}] Deploying changes to GitHub")

            write_to_temp_dir(session_id, project_dir)

            github_task = create_github_deployment_task(
                agent=github_manager,
                project_dir=str(project_dir),
                repo_name=repo_name,
                github_username=github_username,
                context_tasks=[planning_task, improvement_plan_task, development_task, testing_task],
            )
            _run_crew([github_manager], [github_task])

            session["files_generated"] = _list_project_files(project_dir)

            # Update feedback file with completion (same as original)
            _save_file(project_dir, f"USER_FEEDBACK_{feedback_iteration}.md", (
                f"# User Feedback — Iteration {feedback_iteration}\n\n"
                f"## Requested Changes:\n{user_feedback}\n\n"
                f"## Status: ✅ Implemented and Deployed\n\n"
                f"View at: {session['github_url']}\n"
            ))

        # ── COMPLETE ──────────────────────────────────────────────────────────
        session["status"] = "complete"
        session["phase_label"] = "Project complete! 🎉"
        session["phase_detail"] = f"Feedback iterations: {feedback_iteration} | Files: {len(session['files_generated'])}"
        session["files_generated"] = _list_project_files(project_dir)
        logger.info(f"[{session_id}] Pipeline complete!")

    except Exception as e:
        # Catch-all: if anything crashes, store the error and show it in the UI
        logger.error(f"[{session_id}] Pipeline error: {e}\n{traceback.format_exc()}")
        session["status"] = "error"
        session["error"] = str(e)
        session["phase_label"] = f"Error: {e}"


def start_pipeline_thread(session_id: str) -> None:
    """
    Launches run_pipeline() in a background daemon thread.
    Called by POST /project/start after creating the session.

    Why a thread and not asyncio?
    CrewAI's kickoff() is SYNCHRONOUS — it blocks until the AI responds.
    We can't await it directly in FastAPI's async event loop because that
    would freeze the entire server (no other requests could be handled).
    Running it in a daemon thread lets the API continue serving other
    requests while the pipeline works in the background.
    """
    thread = threading.Thread(
        target=run_pipeline,
        args=(session_id,),
        daemon=True,   # Daemon = thread dies when main process exits (no orphaned threads)
        name=f"pipeline-{session_id}",
    )
    thread.start()
    logger.info(f"Started pipeline thread for session {session_id}")


def respond_to_pipeline(session_id: str, approved: bool, feedback: str = "", cancelled: bool = False) -> bool:
    """
    Called by POST /project/{id}/respond.
    Stores the user's response in the session, then sets the Event to
    wake up the waiting pipeline thread.

    Returns False if the session doesn't exist or isn't waiting.
    """
    session = sessions.get(session_id)
    if not session:
        return False

    # The pipeline must currently be paused at one of the three pause points
    waiting_states = {"waiting_plan_approval", "waiting_review", "waiting_improvement_approval"}
    if session["status"] not in waiting_states:
        return False

    # Store the response data BEFORE setting the event
    # (the thread reads _response_data immediately after waking up)
    session["_response_data"] = {
        "approved": approved,
        "feedback": feedback,
        "cancelled": cancelled,
    }

    # Wake up the waiting pipeline thread
    session["_response_event"].set()
    return True