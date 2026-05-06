#!/usr/bin/env bash
set -euo pipefail

COMPOSE_DIR="${HERMES_AGENT_DIR:-${HOME}/.hermes/hermes-agent}"

cd "$COMPOSE_DIR"

echo "Stopping AI Agent CLI Docker Compose stack..."
docker compose stop

echo
docker compose ps
