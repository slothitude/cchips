#!/bin/bash

# Create necessary directories (in case volume mount overwrites them)
mkdir -p /home/claude/.claude
mkdir -p /home/claude/projects
mkdir -p /home/claude/webapps/flask/templates
mkdir -p /home/claude/webapps/flask/static/css
mkdir -p /home/claude/webapps/flask/static/js
mkdir -p /home/claude/mcp-servers

# Copy webapp files from /opt if they don't exist (volume mount workaround)
if [ ! -f /home/claude/webapps/flask/app.py ]; then
    cp -r /opt/webapps/flask/* /home/claude/webapps/flask/
fi

# Always copy updated Flask files (app.py, orchestrator.py, templates, static)
cp /opt/webapps/flask/app.py /home/claude/webapps/flask/ 2>/dev/null || true
cp /opt/webapps/flask/orchestrator.py /home/claude/webapps/flask/ 2>/dev/null || true
cp /opt/webapps/flask/templates/index.html /home/claude/webapps/flask/templates/ 2>/dev/null || true
cp /opt/webapps/flask/static/css/style.css /home/claude/webapps/flask/static/css/ 2>/dev/null || true

# Copy mcp-servers.json if it doesn't exist
if [ ! -f /home/claude/.claude/mcp-servers.json ]; then
    cp /opt/claude-config/mcp-servers.json /home/claude/.claude/ 2>/dev/null || true
fi

# Ensure ownership
chown -R claude:claude /home/claude/.claude 2>/dev/null || true
chown -R claude:claude /home/claude/webapps 2>/dev/null || true
chown -R claude:claude /home/claude/projects 2>/dev/null || true
chown -R claude:claude /home/claude/mcp-servers 2>/dev/null || true

# Generate SSH host keys if missing
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    ssh-keygen -A
fi

# Start SSH daemon (also provides SFTP)
/usr/sbin/sshd

# Start Samba services
/usr/sbin/smbd
/usr/sbin/nmbd

# Start SearXNG
sudo -u searxng /opt/searxng/bin/searxng &

# Start Nginx
/usr/sbin/nginx

# Start ttyd - Web terminal with auto-login
ttyd -p 7682 -W -t fontSize=12 sshpass -p claude ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null claude@localhost &

# Start Claude Code OpenAI Wrapper (port 8000)
cd /opt/claude-code-openai-wrapper

# Configure from saved settings
if [ -f /home/claude/.claude/wrapper.env ]; then
    echo "Loading wrapper configuration..."
    # Export each line from wrapper.env
    set -a
    source /home/claude/.claude/wrapper.env
    set +a
fi

# Set default working directory for Claude Code
export CLAUDE_CWD=${CLAUDE_CWD:-/home/claude/projects}

# Start wrapper in background
echo "Starting Claude Code OpenAI Wrapper on port 8000..."
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# Wait for wrapper to start
sleep 3

cd /home/claude

# Start Flask Onboarding Wizard (port 5000)
cd /home/claude/webapps/flask
python3 app.py &
cd /home/claude

# Start Headless Agent API (port 5001)
python3 /home/claude/webapps/flask/agent_api.py &

# Run Claude setup on first launch if no config exists
if [ ! -f /home/claude/.claude/settings.json ] && [ ! -f /home/claude/.claude/wrapper.env ]; then
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║     Welcome! First time setup required.                   ║"
    echo "║     Access the onboarding wizard to configure providers.  ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Available Services:"
    echo "  - Onboarding:  http://localhost:5000"
    echo "  - Wrapper API: http://localhost:8000 (OpenAI/Anthropic compatible)"
    echo "  - Agent API:   http://localhost:5001"
    echo "  - ttyd:        http://localhost/ttyd/ (Web terminal with auto-login)"
    echo "  - SSHwifty:    http://localhost:8182"
    echo "  - SearXNG:     http://localhost:8888"
    echo "  - Nginx:       http://localhost:80"
    echo ""
    echo "API Endpoints (via Wrapper on port 8000):"
    echo "  POST /v1/chat/completions  - OpenAI-compatible chat"
    echo "  POST /v1/messages          - Anthropic-compatible messages"
    echo "  GET  /v1/models            - List available models"
    echo ""
    echo "Agent API (for subagents on port 5001):"
    echo "  POST /v1/chat/completions"
    echo "  POST /v1/agent/execute"
    echo ""
    echo "MCP Servers available in ~/.claude/mcp-servers.json"
    echo ""
fi

# Start SSHwifty
/usr/local/bin/sshwifty --config /etc/sshwifty.conf.json

# Keep container running (fallback)
tail -f /dev/null
