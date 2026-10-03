from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Mupezeni API")


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}


__all__ = ["app"]
