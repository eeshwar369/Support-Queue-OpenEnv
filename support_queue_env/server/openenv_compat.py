"""Small FastAPI compatibility layer used when openenv-core is unavailable."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from fastapi import Body, FastAPI
from pydantic import BaseModel

ActT = TypeVar("ActT", bound=BaseModel)
ObsT = TypeVar("ObsT", bound=BaseModel)
StateT = TypeVar("StateT", bound=BaseModel)


class Environment(Generic[ActT, ObsT, StateT]):
    SUPPORTS_CONCURRENT_SESSIONS = False

    def reset(self, **kwargs: Any) -> ObsT:
        raise NotImplementedError

    def step(self, action: ActT) -> ObsT:
        raise NotImplementedError

    def state(self) -> StateT:
        raise NotImplementedError


def create_app(
    environment_cls: type[Environment[ActT, ObsT, StateT]],
    action_model: type[ActT],
    observation_model: type[ObsT],
    env_name: str,
    **_: Any,
) -> FastAPI:
    app = FastAPI(title=env_name)
    app.state.environment = environment_cls()

    @app.get("/")
    def root() -> dict[str, Any]:
        return {
            "name": env_name,
            "status": "ok",
            "endpoints": ["/health", "/reset", "/step", "/state", "/tasks", "/metadata", "/schema"],
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metadata")
    def metadata() -> dict[str, Any]:
        return {
            "name": env_name,
            "supports_state": True,
            "supports_tasks": True,
            "transport": "http",
        }

    @app.get("/schema")
    def schema() -> dict[str, Any]:
        return {
            "action": action_model.model_json_schema(),
            "observation": observation_model.model_json_schema(),
        }

    @app.post("/reset")
    def reset(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        observation = app.state.environment.reset(**(payload or {}))
        data = observation.model_dump()
        return {
            "observation": data,
            "reward": float(data.get("reward") or 0.0),
            "done": bool(data.get("done", False)),
        }

    @app.post("/step")
    def step(payload: dict[str, Any]) -> dict[str, Any]:
        action = action_model.model_validate(payload)
        observation = app.state.environment.step(action)
        data = observation.model_dump()
        return {
            "observation": data,
            "reward": float(data.get("reward") or 0.0),
            "done": bool(data.get("done", False)),
        }

    @app.get("/state")
    def state() -> dict[str, Any]:
        return app.state.environment.state().model_dump()

    return app
