---
title: Support Queue OpenEnv
emoji: 🎫
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
---

# Support Queue OpenEnv

Real-world OpenEnv benchmark for SaaS support triage.

## Quick Links

- Full project documentation: [PROJECT.md](./PROJECT.md)
- OpenEnv manifest: [openenv.yaml](./openenv.yaml)
- Baseline runner: [inference.py](./inference.py)
- Environment server: [support_queue_environment.py](./support_queue_env/server/support_queue_environment.py)

## Quick Start

```bash
docker build -t support-queue-openenv .
docker run --rm -p 8000:8000 support-queue-openenv
```

Then run:

```bash
python inference.py
```

## Notes

- This repository is configured for a Hugging Face Docker Space.
- The full environment description, tasks, reward design, and setup guide are in [PROJECT.md](./PROJECT.md).
