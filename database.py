# backend/database.py
#
# All Supabase database operations in one place.
# The rest of the code calls these functions —
# nothing else needs to know about Supabase directly.

import os
import re
import logging
from pathlib import Path
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ── Connect to Supabase ───────────────────────────────────────────────────────
# These come from environment variables — never hardcode them.
_url  = os.getenv("SUPABASE_URL")
_key  = os.getenv("SUPABASE_SERVICE_KEY")
_supabase: Client = create_client(_url, _key) if _url and _key else None


def _check():
    if not _supabase:
        raise RuntimeError(
            "Supabase not configured. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
        )


# ── WRITE ─────────────────────────────────────────────────────────────────────

def save_file(session_id: str, file_path: str, content: str) -> bool:
    """
    Save a single file to the database.
    Uses upsert so re-running the same session updates existing rows.
    """
    _check()
    try:
        _supabase.table("project_files").upsert({
            "session_id": session_id,
            "file_path":  file_path,
            "content":    content,
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to save file {file_path}: {e}")
        return False


def save_files_bulk(session_id: str, files: dict) -> int:
    """
    Save multiple files at once.
    files = { "src/main.py": "print('hello')", "README.md": "# My Project" }
    Returns number of files saved.
    """
    _check()
    rows = [
        {"session_id": session_id, "file_path": path, "content": content}
        for path, content in files.items()
    ]
    try:
        _supabase.table("project_files").upsert(rows).execute()
        return len(rows)
    except Exception as e:
        logger.error(f"Bulk save failed: {e}")
        return 0


# ── READ ──────────────────────────────────────────────────────────────────────

def get_all_files(session_id: str) -> dict:
    """
    Get all files for a session as a dict: { "filename": "content" }
    """
    _check()
    try:
        result = (
            _supabase.table("project_files")
            .select("file_path, content")
            .eq("session_id", session_id)
            .execute()
        )
        return {row["file_path"]: row["content"] for row in result.data}
    except Exception as e:
        logger.error(f"Failed to get files: {e}")
        return {}


def get_file(session_id: str, file_path: str):
    """Get a single file's content. Returns None if not found."""
    _check()
    try:
        result = (
            _supabase.table("project_files")
            .select("content")
            .eq("session_id", session_id)
            .eq("file_path", file_path)
            .single()
            .execute()
        )
        return result.data["content"] if result.data else None
    except Exception as e:
        logger.error(f"Failed to get file {file_path}: {e}")
        return None


def list_files(session_id: str) -> list:
    """Get just the file paths for a session."""
    _check()
    try:
        result = (
            _supabase.table("project_files")
            .select("file_path")
            .eq("session_id", session_id)
            .execute()
        )
        return [row["file_path"] for row in result.data]
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        return []


# ── PARSE AGENT OUTPUT ────────────────────────────────────────────────────────

def parse_and_save(session_id: str, agent_output: str) -> dict:
    """
    Parses agent output text, extracts all code blocks, saves to database.

    Handles two common formats agents use:

    Format 1 (most common):
        ### src/main.py
        ```python
        code here
        ```

    Format 2 (also seen):
        **filename.py**
        ```python
        code here
        ```

    Returns dict of { filename: content } that was saved.
    """
    files = {}

    # Pattern 1: ### filename or ## filename
    pattern1 = re.compile(
        r'#{1,3}\s+([\w./\-]+\.\w+)\s*\n'   # ### src/main.py
        r'```[\w]*\n'                          # ```python
        r'(.*?)'                               # code content
        r'```',                                # closing ```
        re.DOTALL
    )

    # Pattern 2: **filename.ext** or `filename.ext`
    pattern2 = re.compile(
        r'(?:\*\*|`)?([\w./\-]+\.\w+)(?:\*\*|`)?\s*\n'
        r'```[\w]*\n'
        r'(.*?)'
        r'```',
        re.DOTALL
    )

    for pattern in [pattern1, pattern2]:
        for match in pattern.finditer(agent_output):
            filename = match.group(1).strip()
            content  = match.group(2).strip()

            # Basic sanity checks — skip if it looks wrong
            if len(content) < 5:
                continue
            if filename in files:
                continue  # Already captured by pattern1

            files[filename] = content

    if files:
        saved = save_files_bulk(session_id, files)
        logger.info(f"[{session_id}] Saved {saved} files to database: {list(files.keys())}")

    return files


# ── WRITE TO DISK (temp, for GitHub commit) ───────────────────────────────────

def write_to_temp_dir(session_id: str, base_dir: Path) -> list:
    """
    Reads all files for this session from the database and writes them
    to the given directory on disk.

    Used by the GitHub agent right before committing — it needs real
    files on disk to run git commands. After the commit, the temp files
    can be left (Render will clean them up on next deploy).

    Returns list of file paths written.
    """
    files = get_all_files(session_id)
    written = []

    for file_path, content in files.items():
        full_path = base_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        written.append(file_path)

    logger.info(f"[{session_id}] Wrote {len(written)} files to {base_dir}")
    return written