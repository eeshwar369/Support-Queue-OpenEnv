"""HTTP client for interacting with the support queue environment."""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import time
from typing import Any

import requests

from support_queue_env.models import TaskCard, SupportQueueAction, SupportQueueObservation, SupportQueueState

DEFAULT_ENV_BASE_URL = os.getenv("ENV_BASE_URL")
DEFAULT_IMAGE_CANDIDATES = [
    "support-queue-openenv:latest",
    "support-queue-openenv",
    "support_queue_env:latest",
    "support_queue_env",
]


class _Result:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.observation = SupportQueueObservation.model_validate(payload["observation"])
        self.reward = float(payload.get("reward") or 0.0)
        self.done = bool(payload.get("done"))


class SupportQueueEnv:
    def __init__(self, base_url: str, container_id: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.container_id = container_id

    @classmethod
    def from_base_url(cls, base_url: str) -> "SupportQueueEnv":
        return cls(base_url=base_url)

    @classmethod
    async def from_docker_image(cls, image_name: str | None = None) -> "SupportQueueEnv":
        if DEFAULT_ENV_BASE_URL:
            return cls(base_url=DEFAULT_ENV_BASE_URL)
        return await asyncio.to_thread(cls._spawn_local_container, image_name)

    @classmethod
    def _spawn_local_container(cls, image_name: str | None) -> "SupportQueueEnv":
        chosen_image = cls._resolve_image_name(image_name)
        port = cls._pick_free_port()
        container_id = cls._run(["docker", "run", "-d", "-p", f"{port}:8000", chosen_image]).strip()
        base_url = f"http://127.0.0.1:{port}"

        try:
            cls._wait_until_ready(base_url)
        except Exception:
            cls._safe_remove_container(container_id)
            raise

        return cls(base_url=base_url, container_id=container_id)

    @classmethod
    def _resolve_image_name(cls, image_name: str | None) -> str:
        candidates: list[str] = []
        if image_name:
            candidates.append(image_name)
        candidates.extend(DEFAULT_IMAGE_CANDIDATES)

        for candidate in candidates:
            if cls._image_exists(candidate):
                return candidate

        build_tag = image_name or "support-queue-openenv:local"
        cls._run(["docker", "build", "-t", build_tag, "."])
        return build_tag

    @staticmethod
    def _image_exists(image_name: str) -> bool:
        try:
            SupportQueueEnv._run(["docker", "image", "inspect", image_name])
            return True
        except RuntimeError:
            return False

    @staticmethod
    def _pick_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    @staticmethod
    def _wait_until_ready(base_url: str, timeout_seconds: int = 45) -> None:
        deadline = time.time() + timeout_seconds
        last_error = ""

        while time.time() < deadline:
            try:
                response = requests.get(f"{base_url}/health", timeout=3)
                if response.ok:
                    return
            except Exception as exc:
                last_error = str(exc)
            time.sleep(1)

        raise RuntimeError(f"Environment did not become ready at {base_url}: {last_error}")

    @staticmethod
    def _run(command: list[str]) -> str:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout).strip() or f"Command failed: {' '.join(command)}")
        return result.stdout

    @staticmethod
    def _safe_remove_container(container_id: str) -> None:
        subprocess.run(["docker", "rm", "-f", container_id], check=False, capture_output=True, text=True)

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
        if self.container_id:
            await asyncio.to_thread(self._safe_remove_container, self.container_id)
