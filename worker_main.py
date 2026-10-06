"""Render Background Worker entry point.

Render start command (background worker service):
    python worker_main.py

This module starts the durable-job poll loop. It is separate from the
web service (main.py / uvicorn) so the two processes can scale independently
and the web process is never blocked by long-running AI/channel work.

Environment variables (same .env as the web service):
    WORKER_ID           unique string identifying this process (default: hostname)
    WORKER_POLL_INTERVAL_S  seconds between claim cycles (default: 2)
    WORKER_JOB_TYPES    comma-separated list of job types to claim (default: all)
    WORKER_CONCURRENCY  max concurrent jobs (default: 4)
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys
from pathlib import Path

# Ensure apps/api is on the Python path (same logic as main.py)
_api_root = Path(__file__).parent / "apps" / "api"
if str(_api_root) not in sys.path:
    sys.path.insert(0, str(_api_root))

logging.basicConfig(
    stream=sys.stdout,
    format='%(asctime)s %(levelname)-8s %(name)s %(message)s',
    level=logging.DEBUG if os.getenv("DEBUG", "").lower() in {"1", "true"} else logging.INFO,
)
logger = logging.getLogger("mupezeni.worker")

WORKER_ID = os.getenv("WORKER_ID", socket.gethostname())
POLL_INTERVAL = float(os.getenv("WORKER_POLL_INTERVAL_S", "2"))
JOB_TYPES_ENV = os.getenv("WORKER_JOB_TYPES", "")
JOB_TYPES: list[str] | None = [t.strip() for t in JOB_TYPES_ENV.split(",") if t.strip()] or None
CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "4"))


async def main() -> None:
    # Import here so the path manipulation above takes effect first
    from app.jobs.worker import run_loop  # noqa: PLC0415

    logger.info(
        "Worker starting  id=%s  poll_interval=%.1fs  job_types=%s  concurrency=%d",
        WORKER_ID, POLL_INTERVAL, JOB_TYPES or "all", CONCURRENCY,
    )
    await run_loop(
        worker_id=WORKER_ID,
        poll_interval=POLL_INTERVAL,
        job_types=JOB_TYPES,
        concurrency=CONCURRENCY,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by keyboard interrupt")
