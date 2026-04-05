"""Typed models for the SaaS support triage benchmark."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

try:
    from openenv.core.env_server.types import Action as OpenEnvAction
    from openenv.core.env_server.types import Observation as OpenEnvObservation
except Exception:  # pragma: no cover - compatibility fallback
    OpenEnvAction = BaseModel
    OpenEnvObservation = BaseModel


Priority = Literal["P1", "P2", "P3", "P4"]
QueueName = Literal["billing", "security", "technical", "success", "trust_safety"]
Disposition = Literal["respond", "request_info", "escalate", "close"]
Difficulty = Literal["easy", "medium", "hard"]
CustomerTier = Literal["starter", "growth", "enterprise"]


class TaskCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    difficulty: Difficulty
    description: str
    ticket_count: int


class TicketSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str
    subject: str
    body: str
    customer_tier: CustomerTier
    product_area: str
    sla_hours: int
    recent_events: list[str] = Field(default_factory=list)


class SupportQueueAction(OpenEnvAction):
    model_config = ConfigDict(extra="forbid")

    priority: Priority
    queue: QueueName
    disposition: Disposition
    summary: str = Field(..., min_length=8, max_length=280)
    response: str = Field(..., min_length=16, max_length=1200)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class GradingBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority_score: float = 0.0
    queue_score: float = 0.0
    disposition_score: float = 0.0
    summary_score: float = 0.0
    response_score: float = 0.0
    penalty: float = 0.0
    total: float = 0.0


class TicketFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str
    expected_priority: Priority
    expected_queue: QueueName
    expected_disposition: Disposition
    breakdown: GradingBreakdown
    feedback: str


class SupportQueueObservation(OpenEnvObservation):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    task_title: str
    difficulty: Difficulty
    instructions: str
    current_index: int
    total_tickets: int
    ticket: TicketSnapshot
    allowed_priorities: list[Priority] = Field(default_factory=lambda: ["P1", "P2", "P3", "P4"])
    allowed_queues: list[QueueName] = Field(
        default_factory=lambda: ["billing", "security", "technical", "success", "trust_safety"]
    )
    allowed_dispositions: list[Disposition] = Field(
        default_factory=lambda: ["respond", "request_info", "escalate", "close"]
    )
    scoring_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "priority": 0.30,
            "queue": 0.25,
            "disposition": 0.20,
            "summary": 0.15,
            "response": 0.10,
        }
    )
    last_feedback: TicketFeedback | None = None
    cumulative_reward: float = 0.0
    reward: float = 0.0
    done: bool = False
    info: dict[str, Any] = Field(default_factory=dict)


class SupportQueueState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str
    task: TaskCard
    current_index: int
    total_tickets: int
    done: bool
    cumulative_reward: float
    average_reward: float
    ticket_scores: list[TicketFeedback] = Field(default_factory=list)
    action_history: list[SupportQueueAction] = Field(default_factory=list)
    processed_tickets: list[str] = Field(default_factory=list)
