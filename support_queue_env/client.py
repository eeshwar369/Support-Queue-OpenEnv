"""HTTP client for interacting with the support queue environment."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import requests

from support_queue_env.models import TaskCard, SupportQueueAction, SupportQueueObservation, SupportQueueState

DEFAULT_ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://127.0.0.1:8000")


class _Result:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.observation = SupportQueueObservation.model_validate(payload["observation"])
        self.reward = float(payload.get("reward") or 0.0)
        self.done = bool(payload.get("done"))


class SupportQueueEnv:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    @classmethod
    def from_base_url(cls, base_url: str) -> "SupportQueueEnv":
        return cls(base_url=base_url)

    @classmethod
    async def from_docker_image(cls, image_name: str | None = None) -> "SupportQueueEnv":
        _ = image_name
        return cls(base_url=DEFAULT_ENV_BASE_URL)

    def list_tasks(self) -> list[TaskCard]:
        response = requests.get(f"{self.base_url}/tasks", timeout=30)
        response.raise_for_status()
        payload = response.json()
        return [TaskCard.model_validate(item) for item in payload["tasks"]]

    async def alist_tasks(self) -> list[TaskCard]:
        return await asyncio.to_thread(self.list_tasks)

    def reset_sync(self, **kwargs: Any) -> _Result:
        response = requests.post(f"{self.base_url}/reset", json=kwargs or {}, timeout=30)
        response.raise_for_status()
        return _Result(response.json())

    async def reset(self, **kwargs: Any) -> _Result:
        return await asyncio.to_thread(self.reset_sync, **kwargs)

    def step_sync(self, action: SupportQueueAction) -> _Result:
        response = requests.post(f"{self.base_url}/step", json=action.model_dump(), timeout=30)
        response.raise_for_status()
        return _Result(response.json())

    async def step(self, action: SupportQueueAction) -> _Result:
        return await asyncio.to_thread(self.step_sync, action)

    def state_sync(self) -> SupportQueueState:
        response = requests.get(f"{self.base_url}/state", timeout=30)
        response.raise_for_status()
        return SupportQueueState.model_validate(response.json())

    async def state(self) -> SupportQueueState:
        return await asyncio.to_thread(self.state_sync)

    async def close(self) -> None:
        return None
