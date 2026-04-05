#!/usr/bin/env bash
set -euo pipefail

PING_URL="${1:-http://127.0.0.1:8000}"
REPO_DIR="${2:-.}"
IMAGE_NAME="support-queue-openenv:local"

echo "[1/4] Checking repo files"
test -f "$REPO_DIR/openenv.yaml"
test -f "$REPO_DIR/Dockerfile"
test -f "$REPO_DIR/inference.py"

echo "[2/4] Building Docker image"
docker build -t "$IMAGE_NAME" "$REPO_DIR"

echo "[3/4] Starting container"
CID=$(docker run -d -p 8000:8000 "$IMAGE_NAME")
trap 'docker rm -f "$CID" >/dev/null 2>&1 || true' EXIT
sleep 5

echo "[4/4] Pinging environment"
curl -fsS "$PING_URL/health"
curl -fsS -X POST "$PING_URL/reset" -H 'Content-Type: application/json' -d '{}'

echo "Validation completed"
