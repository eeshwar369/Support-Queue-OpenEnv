"""Environment implementation for SaaS support queue triage."""

from __future__ import annotations

from itertools import cycle
from threading import Lock
from typing import Any
from uuid import uuid4

try:
    from openenv.core.env_server import Environment
except Exception:  # pragma: no cover - compatibility fallback
    from support_queue_env.server.openenv_compat import Environment

from support_queue_env.grading import grade_ticket
from support_queue_env.models import TaskCard, TicketSnapshot, SupportQueueAction, SupportQueueObservation, SupportQueueState
from support_queue_env.tasks import TASK_INDEX, TASKS, TaskSpec


class SupportQueueEnvironment(Environment[SupportQueueAction, SupportQueueObservation, SupportQueueState]):
    SUPPORTS_CONCURRENT_SESSIONS = True
    _task_cycle = cycle(task.task_id for task in TASKS)
    _cycle_lock = Lock()

    def __init__(self) -> None:
        self.episode_id = ""
        self.task: TaskSpec = TASKS[0]
        self.current_index = 0
        self.cumulative_reward = 0.0
        self.ticket_scores = []
        self.action_history = []
        self.processed_tickets = []
        self.done = False

    @classmethod
    def available_tasks(cls) -> list[TaskCard]:
        return [
            TaskCard(
                task_id=task.task_id,
                title=task.title,
                difficulty=task.difficulty,
                description=task.description,
                ticket_count=len(task.tickets),
            )
            for task in TASKS
        ]

    @classmethod
    def next_default_task_id(cls) -> str:
        with cls._cycle_lock:
            return next(cls._task_cycle)

    def reset(self, task_id: str | None = None, **_: Any) -> SupportQueueObservation:
        selected_task_id = task_id or self.next_default_task_id()
        self.task = TASK_INDEX.get(selected_task_id, TASKS[0])
        self.episode_id = str(uuid4())
        self.current_index = 0
        self.cumulative_reward = 0.0
        self.ticket_scores = []
        self.action_history = []
        self.processed_tickets = []
        self.done = False
        return self._build_observation(reward=0.0, done=False, feedback=None)

    def step(self, action: SupportQueueAction) -> SupportQueueObservation:
        if self.done:
            return self._terminal_observation("Episode already finished. Call reset() to start a new task.")

        ticket = self.task.tickets[self.current_index]
        feedback = grade_ticket(ticket, action)

        self.action_history.append(action)
        self.ticket_scores.append(feedback)
        self.processed_tickets.append(ticket.ticket_id)
        self.cumulative_reward = round(self.cumulative_reward + feedback.breakdown.total, 4)
        self.current_index += 1
        self.done = self.current_index >= len(self.task.tickets)

        if self.done:
            return self._terminal_observation(feedback.feedback, reward=feedback.breakdown.total, feedback=feedback)

        return self._build_observation(reward=feedback.breakdown.total, done=False, feedback=feedback)

    def state(self) -> SupportQueueState:
        average_reward = self.cumulative_reward / len(self.ticket_scores) if self.ticket_scores else 0.0
        return SupportQueueState(
            episode_id=self.episode_id or "not-started",
            task=TaskCard(
                task_id=self.task.task_id,
                title=self.task.title,
                difficulty=self.task.difficulty,
                description=self.task.description,
                ticket_count=len(self.task.tickets),
            ),
            current_index=self.current_index,
            total_tickets=len(self.task.tickets),
            done=self.done,
            cumulative_reward=round(self.cumulative_reward, 4),
            average_reward=round(average_reward, 4),
            ticket_scores=self.ticket_scores,
            action_history=self.action_history,
            processed_tickets=self.processed_tickets,
        )

    def _current_ticket(self) -> TicketSnapshot:
        ticket = self.task.tickets[min(self.current_index, len(self.task.tickets) - 1)]
        return TicketSnapshot(
            ticket_id=ticket.ticket_id,
            subject=ticket.subject,
            body=ticket.body,
            customer_tier=ticket.customer_tier,
            product_area=ticket.product_area,
            sla_hours=ticket.sla_hours,
            recent_events=ticket.recent_events,
        )

    def _build_observation(self, reward: float, done: bool, feedback) -> SupportQueueObservation:
        average_reward = self.cumulative_reward / len(self.ticket_scores) if self.ticket_scores else 0.0
        return SupportQueueObservation(
            task_id=self.task.task_id,
            task_title=self.task.title,
            difficulty=self.task.difficulty,
            instructions=self.task.instructions,
            current_index=self.current_index + 1,
            total_tickets=len(self.task.tickets),
            ticket=self._current_ticket(),
            last_feedback=feedback,
            cumulative_reward=round(self.cumulative_reward, 4),
            reward=round(reward, 4),
            done=done,
            info={
                "episode_id": self.episode_id,
                "processed_tickets": list(self.processed_tickets),
                "average_reward": round(average_reward, 4),
            },
        )

    def _terminal_observation(self, message: str, reward: float = 0.0, feedback=None) -> SupportQueueObservation:
        placeholder_ticket = self._current_ticket()
        return SupportQueueObservation(
            task_id=self.task.task_id,
            task_title=self.task.title,
            difficulty=self.task.difficulty,
            instructions=f"{self.task.instructions} Episode complete.",
            current_index=len(self.task.tickets),
            total_tickets=len(self.task.tickets),
            ticket=placeholder_ticket,
            last_feedback=feedback,
            cumulative_reward=round(self.cumulative_reward, 4),
            reward=round(reward, 4),
            done=True,
            info={
                "episode_id": self.episode_id,
                "processed_tickets": list(self.processed_tickets),
                "message": message,
            },
        )
