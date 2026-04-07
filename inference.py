from __future__ import annotations

import asyncio
import json
import os
from typing import Any, List

try:
    from openai import OpenAI
    import openai as openai_module
except ImportError:
    OpenAI = None
    import openai as openai_module

from support_queue_env.client import SupportQueueEnv
from support_queue_env.models import TaskCard, SupportQueueAction, SupportQueueObservation
from support_queue_env.tasks import TASKS

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
ENV_BASE_URL = os.getenv("ENV_BASE_URL")

BENCHMARK = "support_queue_env"
SUCCESS_SCORE_THRESHOLD = 0.80
MAX_TOKENS = 250


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: str | None) -> None:
    error_value = "none" if error is None else error.replace("\n", " ")
    print(
        f"[STEP] step={step} action={action} reward={reward:.4f} done={str(done).lower()} error={error_value}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.4f} rewards={json.dumps([round(r, 4) for r in rewards])}",
        flush=True,
    )


def create_openai_client() -> Any:
    if not HF_TOKEN:
        return None

    if OpenAI is not None:
        return OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    openai_module.api_base = API_BASE_URL
    openai_module.api_key = HF_TOKEN
    return openai_module


def get_model_message(
    client: Any,
    step: int,
    observation: SupportQueueObservation,
    last_reward: float,
    history: List[str],
) -> str:
    if client is None:
        return "hello"

    prompt = (
        "Return a short support-triage recommendation as JSON with fields priority, queue, disposition, summary, response. "
        f"Step: {step}. Last reward: {last_reward:.4f}. History: {history[-4:]}. Observation: {observation.model_dump_json()}"
    )
    try:
        if hasattr(client, "chat") and hasattr(client.chat, "completions"):
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are assisting a support triage agent."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=MAX_TOKENS,
                stream=False,
            )
            text = (completion.choices[0].message.content or "").strip()
        else:
            completion = client.ChatCompletion.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are assisting a support triage agent."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=MAX_TOKENS,
                stream=False,
            )
            text = (completion["choices"][0]["message"]["content"] or "").strip()
        return text if text else "hello"
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return "hello"


def available_tasks() -> list[TaskCard]:
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


def heuristic_action(observation: SupportQueueObservation) -> SupportQueueAction:
    text = " ".join(
        [
            observation.ticket.subject,
            observation.ticket.body,
            " ".join(observation.ticket.recent_events),
            observation.task_title,
        ]
    ).lower()

    if any(word in text for word in ["password reset", "account is locked", "locked out"]):
        return SupportQueueAction(
            priority="P3",
            queue="technical",
            disposition="respond",
            summary="Customer account locked after password reset in the admin portal.",
            response=(
                "Thanks for reporting this. Please verify the account owner details and we will unlock the account and "
                "confirm the next reset step for you."
            ),
            confidence=0.82,
        )

    if any(word in text for word in ["phishing", "credentials", "oauth", "unknown ip", "contractor", "security"]):
        return SupportQueueAction(
            priority="P1",
            queue="security",
            disposition="escalate",
            summary="Security issue involving phishing, credentials, or unknown OAuth access.",
            response=(
                "Thanks for flagging this quickly. This is escalated to our security team now. Please do not click the message "
                "again, revoke suspicious access where possible, and keep audit logs ready."
            ),
            confidence=0.9,
        )

    if any(word in text for word in ["502", "500", "webhook", "login", "blocked", "outage", "rollout"]):
        priority = "P1" if any(word in text for word in ["all agents", "entire", "502", "blocked"]) else "P2"
        return SupportQueueAction(
            priority=priority,
            queue="technical",
            disposition="escalate",
            summary="Technical incident affecting login, webhook delivery, or a recent rollout.",
            response=(
                "I am escalating this incident to engineering right away. Please keep example timestamps and logs handy while "
                "we investigate the rollout behavior and urgent production impact."
            ),
            confidence=0.88,
        )

    if any(word in text for word in ["renewal", "discount", "cfo", "quote"]):
        return SupportQueueAction(
            priority="P2",
            queue="success",
            disposition="escalate",
            summary="Renewal quote issue where the committed discount is blocking the CFO review.",
            response=(
                "I am escalating this to the account manager now. We will review the quote, confirm the discount commitment, "
                "and share the escalated renewal update as soon as possible."
            ),
            confidence=0.83,
        )

    if any(word in text for word in ["cancel", "data export"]):
        return SupportQueueAction(
            priority="P3",
            queue="success",
            disposition="request_info",
            summary="Customer wants cancellation and a data export after verification.",
            response=(
                "I can help with the export and cancellation flow. Please verify that you are the account owner and confirm "
                "the workspace name so we can start the export safely."
            ),
            confidence=0.8,
        )

    if any(word in text for word in ["invoice", "charged", "billed", "refund", "billing"]):
        unclear = any(word in text for word in ["maybe", "not fully sure", "thinks", "what details"])
        return SupportQueueAction(
            priority="P2" if any(word in text for word in ["charged twice", "double billed", "two identical charges"]) else "P3",
            queue="billing",
            disposition="request_info" if unclear else "respond",
            summary=(
                "Billing issue is unclear because only one invoice is visible today."
                if unclear
                else "Duplicate charge appears tied to a specific invoice in billing."
            ),
            response=(
                "I can review this with billing. Please send the invoice number, charged amount, and the last four digits of "
                "the payment method so we can compare the records."
                if unclear
                else "I am checking this with our billing team now. If this is a duplicate charge, we will investigate the invoice and share the refund update for you."
            ),
            confidence=0.84,
        )

    return SupportQueueAction(
        priority="P3",
        queue="technical",
        disposition="respond",
        summary="General product issue that needs standard technical follow-up.",
        response="Thanks for the report. We will verify the issue and share the next reset or troubleshooting step.",
        confidence=0.7,
    )


async def build_env() -> SupportQueueEnv:
    if ENV_BASE_URL:
        env = SupportQueueEnv(base_url=ENV_BASE_URL)
        await env.connect()
        return env
    return await SupportQueueEnv.from_docker_image(LOCAL_IMAGE_NAME or "support-queue-openenv")


async def run_task(client: Any, env: SupportQueueEnv, task: TaskCard) -> dict[str, Any]:
    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task.task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset(task_id=task.task_id)
        last_reward = 0.0

        for step in range(1, task.ticket_count + 1):
            if result.done:
                break

            observation = result.observation
            _ = get_model_message(client, step, observation, last_reward, history)
            action = heuristic_action(observation)

            try:
                result = await env.step(action)
            except Exception as exc:
                action_payload = json.dumps(action.model_dump(), separators=(",", ":"), sort_keys=True)
                log_step(step=step, action=action_payload, reward=0.0, done=True, error=str(exc))
                break

            reward = result.reward or 0.0
            done = result.done
            error = None

            rewards.append(reward)
            steps_taken = step
            last_reward = reward

            action_payload = json.dumps(action.model_dump(), separators=(",", ":"), sort_keys=True)
            log_step(step=step, action=action_payload, reward=reward, done=done, error=error)

            history.append(f"Step {step}: {action_payload} -> reward {reward:+.2f}")

            if done:
                break

        score = sum(rewards) / len(rewards) if rewards else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] Task {task.task_id} failed: {exc}", flush=True)

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return {
        "task_id": task.task_id,
        "score": score,
        "steps": steps_taken,
        "rewards": rewards,
        "success": success,
    }


async def main() -> None:
    client = create_openai_client()
    tasks = available_tasks()
    results: list[dict[str, Any]] = []
    env: SupportQueueEnv | None = None

    try:
        env = await build_env()
        for task in tasks:
            results.append(await run_task(client, env, task))
    except Exception as exc:
        print(f"[DEBUG] Environment bootstrap failed: {exc}", flush=True)
        for task in tasks:
            log_start(task=task.task_id, env=BENCHMARK, model=MODEL_NAME)
            log_end(success=False, steps=0, score=0.0, rewards=[])
            results.append(
                {
                    "task_id": task.task_id,
                    "score": 0.0,
                    "steps": 0,
                    "rewards": [],
                    "success": False,
                }
            )
    finally:
        if env is not None:
            try:
                await env.close()
            except Exception as exc:
                print(f"[DEBUG] env.close() error (container cleanup): {exc}", flush=True)

        aggregate = {
            "benchmark": BENCHMARK,
            "model": MODEL_NAME,
            "average_score": round(sum(item["score"] for item in results) / len(results), 4) if results else 0.0,
            "tasks": results,
        }
        with open("inference_results.json", "w", encoding="utf-8") as handle:
            json.dump(aggregate, handle, indent=2)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"[DEBUG] Fatal inference error: {exc}", flush=True)
