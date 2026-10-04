"""Base domain error.

Every domain error is raised as `Sub(message, "CODE")`. main.py's exception handler turns the code into an
HTTP status via its _STATUS_BY_CODE table and falls back to `status_code` (400) for unmapped codes.
"""
from __future__ import annotations


class MupezeniError(Exception):
    status_code: int = 400

    def __init__(self, message: str, code: str = "MUPEZENI_ERROR", status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        if status_code is not None:
            self.status_code = status_code

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


__all__ = ["MupezeniError"]
