"""Validator-friendly root app entrypoint."""

from __future__ import annotations

import os

import uvicorn

from support_queue_env.server.app import app

__all__ = ["app", "main"]


def main() -> None:
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()
