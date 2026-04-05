# Support Queue OpenEnv

A real-world OpenEnv benchmark for **SaaS support triage**.

Agents must read incoming support tickets, assign the right priority, route the case to the correct internal queue, choose the next action, and draft a safe first reply. The benchmark is designed to feel like an actual support operations workflow rather than a toy task.

## Why This Environment

Real support teams repeatedly solve the same high-value triage problems:

- decide how urgent a ticket is
- route it to the right team
- avoid unsafe or misleading replies
- handle ambiguous requests without over-escalating

This makes support triage a strong RL and agent-evaluation environment because success is measurable, partial credit is meaningful, and mistakes are easy to interpret.

## What The Agent Does

For each ticket, the agent must produce a `SupportQueueAction` with:

- `priority`: `P1 | P2 | P3 | P4`
- `queue`: `billing | security | technical | success | trust_safety`
- `disposition`: `respond | request_info | escalate | close`
- `summary`: short internal triage note
- `response`: first customer-facing reply
- `confidence`: float in `[0.0, 1.0]`

## Observation Space

Each `reset()` and `step()` returns a typed `SupportQueueObservation` containing:

| Field | Meaning |
| --- | --- |
| `task_id`, `task_title`, `difficulty` | Active benchmark task metadata |
| `instructions` | Task-specific operating guidance |
| `current_index`, `total_tickets` | Episode progress |
| `ticket` | Current customer ticket payload |
| `allowed_priorities`, `allowed_queues`, `allowed_dispositions` | Valid discrete actions |
| `scoring_weights` | Reward decomposition |
| `last_feedback` | Previous grader output |
| `reward`, `cumulative_reward`, `done` | Episode feedback |
| `info` | Extra metadata such as `episode_id` |

The ticket payload includes:

- `ticket_id`
- `subject`
- `body`
- `customer_tier`
- `product_area`
- `sla_hours`
- `recent_events`

## State Space

`state()` returns a typed `SupportQueueState` with:

- active task card
- current cursor
- cumulative and average reward
- processed ticket ids
- full action history
- full per-ticket grading history

## Tasks

The benchmark includes three deterministic tasks with increasing difficulty.

| Task ID | Difficulty | Tickets | Description |
| --- | --- | ---: | --- |
| `easy_inbox_cleanup` | Easy | 2 | Straightforward access and billing tickets |
| `medium_sla_defense` | Medium | 3 | Mix of phishing escalation, webhook failure, and billing ambiguity |
| `hard_exec_escalations` | Hard | 4 | Executive-pressure tickets spanning production, security, commercial, and retention workflows |

## Reward Design

Each processed ticket gets a reward in `[0.0, 1.0]`.

Reward components:

| Component | Weight |
| --- | ---: |
| Priority accuracy | `0.30` |
| Queue accuracy | `0.25` |
| Disposition accuracy | `0.20` |
| Summary keyword coverage | `0.15` |
| Response keyword coverage | `0.10` |
| Unsafe reply penalty | `-0.10` |

This gives useful partial progress signals. An agent can still earn reward for a good route or good reply even if one part of the triage decision is wrong.

## API Surface

The environment server exposes:

- `POST /reset`
- `POST /step`
- `GET /state`
- `GET /tasks`
- `GET /health`
- `GET /`

Example reset payload:

```json
{
  "task_id": "easy_inbox_cleanup"
}
```

## Project Structure

```text
support_queue_env/
  client.py
  grading.py
  models.py
  tasks.py
  server/
    app.py
    openenv_compat.py
    support_queue_environment.py
Dockerfile
openenv.yaml
inference.py
```

## Running Locally

### Python

```bash
pip install -r requirements.txt
uvicorn support_queue_env.server.app:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker build -t support-queue-openenv .
docker run --rm -p 8000:8000 support-queue-openenv
```

## Baseline Inference

The required inference script is [inference.py](./inference.py).

It:

- uses the OpenAI Python client
- reads `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`, and optional `LOCAL_IMAGE_NAME`
- emits structured `[START]`, `[STEP]`, and `[END]` logs
- writes `inference_results.json`

Set environment variables:

```bash
API_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini
HF_TOKEN=your_token
LOCAL_IMAGE_NAME=
```

Then run:

```bash
python inference.py
```

## Baseline Scores

Expected deterministic baseline scores from the bundled heuristic policy:

| Task | Score |
| --- | ---: |
| `easy_inbox_cleanup` | `1.00` |
| `medium_sla_defense` | `0.98` |
| `hard_exec_escalations` | `0.97` |
| Average | `0.98` |

## Hugging Face Space

This repository is configured for a **Docker Space**.

- front matter in `README.md` sets `sdk: docker`
- app serves on port `8000`
- `GET /health` and `POST /reset` support deployment checks

## OpenEnv Files

Core submission files:

- [openenv.yaml](./openenv.yaml)
- [inference.py](./inference.py)
- [Dockerfile](./Dockerfile)
- [support_queue_env/models.py](./support_queue_env/models.py)
- [support_queue_env/server/support_queue_environment.py](./support_queue_env/server/support_queue_environment.py)

## Submission Checklist

- typed action, observation, and state models included
- `reset()`, `step()`, and `state()` implemented
- three graded tasks included
- reward bounded to `[0.0, 1.0]`
- Dockerfile included
- Hugging Face Docker Space compatible
- root `inference.py` included
