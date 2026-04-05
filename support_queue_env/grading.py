"""Deterministic reward shaping and grading utilities."""

from __future__ import annotations

import re

from support_queue_env.models import GradingBreakdown, SupportQueueAction, TicketFeedback
from support_queue_env.tasks import TicketSpec

PRIORITY_ORDER = ["P1", "P2", "P3", "P4"]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _contains_keywords(text: str, keywords: list[str]) -> int:
    normalized = _normalize(text)
    return sum(1 for keyword in keywords if keyword.lower() in normalized)


def _priority_score(expected: str, predicted: str) -> float:
    if expected == predicted:
        return 0.30
    try:
        distance = abs(PRIORITY_ORDER.index(expected) - PRIORITY_ORDER.index(predicted))
    except ValueError:
        return 0.0
    if distance == 1:
        return 0.15
    return 0.0


def _queue_score(ticket: TicketSpec, predicted: str) -> float:
    if predicted == ticket.expected_queue:
        return 0.25
    if predicted in ticket.acceptable_queues:
        return 0.15
    return 0.0


def _disposition_score(ticket: TicketSpec, predicted: str) -> float:
    if predicted == ticket.expected_disposition:
        return 0.20
    if predicted in ticket.acceptable_dispositions:
        return 0.10
    return 0.0


def grade_ticket(ticket: TicketSpec, action: SupportQueueAction) -> TicketFeedback:
    summary_hits = _contains_keywords(action.summary, ticket.summary_keywords)
    response_hits = _contains_keywords(action.response, ticket.response_keywords)
    penalty_hits = _contains_keywords(action.response, ticket.disallowed_keywords)

    summary_score = 0.15 * (summary_hits / len(ticket.summary_keywords)) if ticket.summary_keywords else 0.15
    response_score = 0.10 * (response_hits / len(ticket.response_keywords)) if ticket.response_keywords else 0.10
    penalty = -0.10 if penalty_hits else 0.0

    breakdown = GradingBreakdown(
        priority_score=_priority_score(ticket.expected_priority, action.priority),
        queue_score=_queue_score(ticket, action.queue),
        disposition_score=_disposition_score(ticket, action.disposition),
        summary_score=round(summary_score, 4),
        response_score=round(response_score, 4),
        penalty=penalty,
    )
    total = (
        breakdown.priority_score
        + breakdown.queue_score
        + breakdown.disposition_score
        + breakdown.summary_score
        + breakdown.response_score
        + breakdown.penalty
    )
    breakdown.total = round(max(0.0, min(1.0, total)), 4)

    matched_summary = summary_hits if ticket.summary_keywords else 0
    matched_response = response_hits if ticket.response_keywords else 0
    feedback = (
        f"priority={action.priority} target={ticket.expected_priority}; "
        f"queue={action.queue} target={ticket.expected_queue}; "
        f"disposition={action.disposition} target={ticket.expected_disposition}; "
        f"summary_keywords={matched_summary}/{len(ticket.summary_keywords)}; "
        f"response_keywords={matched_response}/{len(ticket.response_keywords)}"
    )

    return TicketFeedback(
        ticket_id=ticket.ticket_id,
        expected_priority=ticket.expected_priority,
        expected_queue=ticket.expected_queue,
        expected_disposition=ticket.expected_disposition,
        breakdown=breakdown,
        feedback=feedback,
    )
