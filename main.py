# =============================================================================
# main.py  (project root — this REPLACES your original main.py)
#
# This is now the entry point for the FastAPI server.
# Your original main() logic has moved to backend/pipeline.py.
#
# To run locally:
#   uvicorn main:app --reload --port 8000
#
# To run on Render:
#   uvicorn main:app --host 0.0.0.0 --port 10000
# =============================================================================

from api import app   # noqa: F401 — Uvicorn imports "app" from here

# If you ever want to run this file directly (python main.py),
# this block starts the server. During normal development you use
# "uvicorn main:app --reload" instead.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)