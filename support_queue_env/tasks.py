"""Deterministic task catalog for the support triage environment."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from support_queue_env.models import Difficulty, Disposition, Priority, QueueName


class TicketSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str
    subject: str
    body: str
    customer_tier: str
    product_area: str
    sla_hours: int
    recent_events: list[str] = Field(default_factory=list)
    expected_priority: Priority
    expected_queue: QueueName
    expected_disposition: Disposition
    acceptable_queues: list[QueueName] = Field(default_factory=list)
    acceptable_dispositions: list[Disposition] = Field(default_factory=list)
    summary_keywords: list[str] = Field(default_factory=list)
    response_keywords: list[str] = Field(default_factory=list)
    disallowed_keywords: list[str] = Field(default_factory=list)


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    difficulty: Difficulty
    description: str
    instructions: str
    tickets: list[TicketSpec]


TASKS: list[TaskSpec] = [
    TaskSpec(
        task_id="easy_inbox_cleanup",
        title="Inbox Cleanup",
        difficulty="easy",
        description="Two straightforward tickets covering access and billing triage.",
        instructions=(
            "You are a SaaS support triage agent. For each ticket, choose priority, routing queue, "
            "and the next best disposition. Write a short internal summary plus the first reply you "
            "would send to the customer."
        ),
        tickets=[
            TicketSpec(
                ticket_id="E-101",
                subject="Locked out after password reset",
                body=(
                    "I reset my password this morning and now the admin portal says my account is locked. "
                    "We need to finish payroll before noon."
                ),
                customer_tier="starter",
                product_area="auth",
                sla_hours=24,
                recent_events=["Password reset completed 2 hours ago", "No prior incidents on status page"],
                expected_priority="P3",
                expected_queue="technical",
                expected_disposition="respond",
                summary_keywords=["account", "locked", "password"],
                response_keywords=["verify", "unlock", "reset"],
                disallowed_keywords=["refund", "breach"],
            ),
            TicketSpec(
                ticket_id="E-102",
                subject="We were charged twice for March",
                body=(
                    "Our card shows two identical charges from your company for invoice INV-4481. "
                    "Please confirm whether one of them will be refunded."
                ),
                customer_tier="growth",
                product_area="billing",
                sla_hours=8,
                recent_events=["Invoice INV-4481 marked paid yesterday"],
                expected_priority="P2",
                expected_queue="billing",
                expected_disposition="respond",
                summary_keywords=["duplicate", "charge", "invoice"],
                response_keywords=["refund", "investigate", "billing"],
                disallowed_keywords=["ignore", "security incident"],
            ),
        ],
    ),
    TaskSpec(
        task_id="medium_sla_defense",
        title="SLA Defense",
        difficulty="medium",
        description="Three tickets that mix urgent escalation with an ambiguity check.",
        instructions=(
            "Prioritize by customer impact and risk. Security events and broad service degradation should "
            "be escalated immediately. If the customer has not given enough evidence to act safely, ask for "
            "the minimum details needed to proceed."
        ),
        tickets=[
            TicketSpec(
                ticket_id="M-201",
                subject="Suspicious email asking admins to re-enter credentials",
                body=(
                    "Several admins received an email that looks like your login page and asks us to "
                    "re-authenticate. One teammate clicked it but says they closed the tab before typing anything."
                ),
                customer_tier="enterprise",
                product_area="security",
                sla_hours=1,
                recent_events=["Customer SSO is enabled", "No status page incident posted"],
                expected_priority="P1",
                expected_queue="security",
                expected_disposition="escalate",
                summary_keywords=["phishing", "credentials", "admins"],
                response_keywords=["security", "escalated", "do not click"],
                disallowed_keywords=["send password", "share secrets"],
            ),
            TicketSpec(
                ticket_id="M-202",
                subject="Webhook deliveries are failing after yesterday's rollout",
                body=(
                    "Every webhook call since 06:15 UTC has returned HTTP 500. This is blocking our downstream "
                    "fulfillment pipeline. Can you investigate urgently?"
                ),
                customer_tier="growth",
                product_area="integrations",
                sla_hours=4,
                recent_events=["Customer is on API version 2025-11", "Platform release went out last night"],
                expected_priority="P2",
                expected_queue="technical",
                expected_disposition="escalate",
                acceptable_queues=["success"],
                summary_keywords=["webhook", "500", "rollout"],
                response_keywords=["engineering", "logs", "investigate"],
                disallowed_keywords=["duplicate charge", "unsubscribe"],
            ),
            TicketSpec(
                ticket_id="M-203",
                subject="Maybe double charged? Not fully sure",
                body=(
                    "My finance teammate thinks we were double billed, but I can only find one invoice in the portal. "
                    "Could you explain what happened and what details you need from me?"
                ),
                customer_tier="growth",
                product_area="billing",
                sla_hours=12,
                recent_events=["One paid invoice visible in portal", "No payment failures recorded"],
                expected_priority="P3",
                expected_queue="billing",
                expected_disposition="request_info",
                acceptable_dispositions=["respond"],
                summary_keywords=["billing", "unclear", "invoice"],
                response_keywords=["invoice", "last four", "amount"],
                disallowed_keywords=["breach", "status page"],
            ),
        ],
    ),
    TaskSpec(
        task_id="hard_exec_escalations",
        title="Executive Escalations",
        difficulty="hard",
        description="Four high-stakes tickets that require precise triage under pressure.",
        instructions=(
            "You are covering an executive escalation queue during a busy incident window. Optimize for "
            "business continuity, account safety, and clean handoffs. Use P1 only for severe production or "
            "security impact. Ask for more detail only when it materially changes the next safe action."
        ),
        tickets=[
            TicketSpec(
                ticket_id="H-301",
                subject="All agents see 502 during login",
                body=(
                    "Our entire support floor is blocked from logging in. Every browser gets a 502 after "
                    "submitting the sign-in form. The public status page still says operational."
                ),
                customer_tier="enterprise",
                product_area="auth",
                sla_hours=1,
                recent_events=["50+ seats on account", "Issue started 18 minutes ago"],
                expected_priority="P1",
                expected_queue="technical",
                expected_disposition="escalate",
                summary_keywords=["login", "502", "all agents"],
                response_keywords=["incident", "engineering", "urgent"],
                disallowed_keywords=["refund only", "close ticket"],
            ),
            TicketSpec(
                ticket_id="H-302",
                subject="Unknown OAuth app connected after employee departure",
                body=(
                    "An OAuth app named 'SyncFast' appeared in our workspace this morning from an IP we don't recognize. "
                    "The only recent account change is that one contractor left yesterday."
                ),
                customer_tier="enterprise",
                product_area="security",
                sla_hours=1,
                recent_events=["Customer has audit logs enabled", "Former contractor account was deactivated yesterday"],
                expected_priority="P1",
                expected_queue="security",
                expected_disposition="escalate",
                summary_keywords=["oauth", "unknown", "contractor"],
                response_keywords=["security", "revoke", "escalated"],
                disallowed_keywords=["share api key", "ignore"],
            ),
            TicketSpec(
                ticket_id="H-303",
                subject="Renewal quote lost our committed discount",
                body=(
                    "Our renewal quote is missing the 18% discount your sales team committed in writing. "
                    "Our CFO will freeze procurement tomorrow if this isn't corrected."
                ),
                customer_tier="enterprise",
                product_area="commercial",
                sla_hours=6,
                recent_events=["Renewal date in 2 days", "Account owner is on PTO"],
                expected_priority="P2",
                expected_queue="success",
                expected_disposition="escalate",
                acceptable_queues=["billing"],
                summary_keywords=["renewal", "discount", "cfo"],
                response_keywords=["account manager", "quote", "escalated"],
                disallowed_keywords=["security breach", "reset password"],
            ),
            TicketSpec(
                ticket_id="H-304",
                subject="Need cancellation plus data export",
                body=(
                    "We're planning to cancel next month for budget reasons, but first I need a data export for "
                    "our records. Please tell me exactly what you need from me to start."
                ),
                customer_tier="starter",
                product_area="retention",
                sla_hours=24,
                recent_events=["No open invoices", "Account is owner-managed"],
                expected_priority="P3",
                expected_queue="success",
                expected_disposition="request_info",
                acceptable_queues=["billing"],
                summary_keywords=["cancel", "data export", "verification"],
                response_keywords=["verify", "export", "owner"],
                disallowed_keywords=["breach", "status page"],
            ),
        ],
    ),
]

TASK_INDEX = {task.task_id: task for task in TASKS}
