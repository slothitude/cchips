#!/bin/bash
# Quick Launch Script for Claude Code Containers
# Single port deployment - all services via nginx
#
# Usage:
#   ./launch-claude.sh                     # Default: zai on port 80
#   ./launch-claude.sh openrouter 8002     # OpenRouter on port 8002
#   PORT=9000 TOKEN=secret ./launch-claude.sh

set -e

PROVIDER=${1:-zai}
PORT=${PORT:-80}
TOKEN=${TOKEN:-}
NO_SSH=${NO_SSH:-false}

PROJECT_NAME="claude-$PROVIDER-$( [ "$PORT" = "80" ] && echo "default" || echo "$PORT" )"

echo "========================================"
echo "Claude Code Agent Launcher"
echo "========================================"
echo "Provider:  $PROVIDER"
echo "Port:      $PORT"
echo "Project:   $PROJECT_NAME"
echo "SSH:       $([ "$NO_SSH" = "true" ] && echo "Disabled" || echo "Enabled")"
echo ""

# Build if needed
if [ -z "$(docker images -q claude-sshwifty 2>/dev/null)" ]; then
    echo "Building Docker image..."
    docker-compose build
fi

# Launch
echo "Launching container..."
export PORT=$PORT
export AGENT_API_TOKEN=$TOKEN
[ "$NO_SSH" = "true" ] && export SSH_PORT=0

docker-compose -p "$PROJECT_NAME" up -d

echo ""
echo "========================================"
echo "Access URLs (all on port $PORT):"
echo "========================================"
echo ""
echo "  Web UI:        http://localhost:$PORT/"
echo "  Agent API:     http://localhost:$PORT/v1/"
echo "  Search:        http://localhost:$PORT/search/"
echo "  SSHwifty:      http://localhost:$PORT/ssh/"
echo "  Health:        http://localhost:$PORT/health"
echo ""
echo "API Endpoints:"
echo "  POST /v1/chat/completions   - OpenAI-compatible chat"
echo "  POST /agent/execute         - Execute task"
echo "  GET  /agent/status          - Agent status"
echo ""
echo "Python Example:"
echo "  from openai import OpenAI"
echo "  client = OpenAI(base_url='http://localhost:$PORT/v1', api_key='dummy')"
echo ""

if [ "$NO_SSH" != "true" ]; then
    SSH_PORT=$((2200 + PORT - 80))
    echo "SSH: ssh claude@localhost -p $SSH_PORT"
    echo ""
fi

echo "To stop: docker-compose -p $PROJECT_NAME down"
echo "========================================"

# Open browser (macOS/Linux)
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:$PORT"
elif command -v open &> /dev/null; then
    open "http://localhost:$PORT"
fi
