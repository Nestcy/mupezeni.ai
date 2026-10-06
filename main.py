"""Mupezeni API — root entry point.

Render start command (web service):
    uvicorn main:app --host 0.0.0.0 --port $PORT

This module is intentionally thin: it re-exports the FastAPI application
that lives in apps/api/app/main.py so that:
  • Render's start command has a stable, single entry point at the repo root.
  • All route logic, middleware, and service wiring lives in apps/api/app/main.py only.

NEVER add routes or middleware here — use apps/api/app/main.py.
"""
import sys
from pathlib import Path

# Ensure apps/api is on the Python path so `from app.xxx import ...` works
# whether uvicorn is invoked from the repo root or from apps/api/.
_api_root = Path(__file__).parent / "apps" / "api"
if str(_api_root) not in sys.path:
    sys.path.insert(0, str(_api_root))

from app.main import app  # noqa: E402, F401  — re-export for uvicorn

__all__ = ["app"]
