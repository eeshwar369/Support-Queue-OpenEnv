"""OpenEnv client for interacting with the support queue environment."""

from __future__ import annotations

from typing import Any, Dict

import requests

from support_queue_env.models import TaskCard, SupportQueueAction, SupportQueueObservation, SupportQueueState

try:
    from openenv.core.client_types import StepResult
    from openenv.core.env_client import EnvClient as OpenEnvClient
except Exception:  # pragma: no cover - fallback for environments without openenv-core
    OpenEnvClient = None
    StepResult = None


if OpenEnvClient is not None:

    class SupportQueueEnv(OpenEnvClient[SupportQueueAction, SupportQueueObservation, SupportQueueState]):
        def __init__(self, base_url: str, **kwargs: Any) -> None:
            super().__init__(base_url=base_url, **kwargs)
            self.base_url = base_url.rstrip("/")

        def _step_payload(self, action: SupportQueueAction) -> Dict[str, Any]:
            return action.model_dump()

        def _parse_result(self, payload: Dict[str, Any]) -> StepResult[SupportQueueObservation]:
            observation = SupportQueueObservation.model_validate(payload.get("observation", {}))
            return StepResult(
                observation=observation,
                reward=payload.get("reward"),
                done=payload.get("done", False),
            )

        def _parse_state(self, payload: Dict[str, Any]) -> SupportQueueState:
            return SupportQueueState.model_validate(payload)

        def list_tasks(self) -> list[TaskCard]:
            response = requests.get(f"{self.base_url.rstrip('/')}/tasks", timeout=30)
            response.raise_for_status()
            payload = response.json()
            return [TaskCard.model_validate(item) for item in payload["tasks"]]

else:

    class _Result:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.observation = SupportQueueObservation.model_validate(payload["observation"])
            self.reward = float(payload.get("reward") or 0.0)
            self.done = bool(payload.get("done"))


    class SupportQueueEnv:
        def __init__(self, base_url: str, **_: Any) -> None:
            self.base_url = base_url.rstrip("/")

        @classmethod
        async def from_docker_image(cls, image_name: str | None = None) -> "SupportQueueEnv":
            _ = image_name
            return cls(base_url="http://127.0.0.1:8000")

        def list_tasks(self) -> list[TaskCard]:
            response = requests.get(f"{self.base_url}/tasks", timeout=30)
            response.raise_for_status()
            payload = response.json()
            return [TaskCard.model_validate(item) for item in payload["tasks"]]

        async def reset(self, **kwargs: Any) -> _Result:
            response = requests.post(f"{self.base_url}/reset", json=kwargs or {}, timeout=30)
            response.raise_for_status()
            return _Result(response.json())

        async def step(self, action: SupportQueueAction) -> _Result:
            response = requests.post(
                f"{self.base_url}/step",
                json={"action": action.model_dump()},
                timeout=30,
            )
            response.raise_for_status()
            return _Result(response.json())

        async def state(self) -> SupportQueueState:
            response = requests.get(f"{self.base_url}/state", timeout=30)
            response.raise_for_status()
            return SupportQueueState.model_validate(response.json())

        async def close(self) -> None:
            return None
