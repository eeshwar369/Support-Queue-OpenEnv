"""FastAPI app entrypoint for local runs and Hugging Face Spaces."""

from __future__ import annotations

import os

from fastapi import FastAPI

try:
    from openenv.core.env_server import create_app
except Exception:  # pragma: no cover - compatibility fallback
    from support_queue_env.server.openenv_compat import create_app

from support_queue_env.models import SupportQueueAction, SupportQueueObservation
from support_queue_env.server.support_queue_environment import SupportQueueEnvironment

ENV_NAME = "support_queue_env"

app: FastAPI = create_app(
    SupportQueueEnvironment,
    SupportQueueAction,
    SupportQueueObservation,
    env_name=ENV_NAME,
    max_concurrent_envs=16,
)


@app.get("/")
def root() -> dict[str, object]:
    return {
        "name": ENV_NAME,
        "status": "ok",
        "message": "Support Queue OpenEnv is running.",
        "endpoints": ["/health", "/reset", "/step", "/state", "/tasks"],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks() -> dict[str, object]:
    return {"tasks": [task.model_dump() for task in SupportQueueEnvironment.available_tasks()]}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "support_queue_env.server.app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()
