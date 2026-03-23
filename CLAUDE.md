# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **📖 Read ONBOARDING.md for full capability documentation**

## Project Overview

CChips - Docker container deployment for Claude Code Agent. A self-contained environment that provides Claude Code CLI with OpenAI-compatible API wrapper, web terminal access, and multiple MCP servers.

## Commands

```bash
# Build and start
docker-compose up -d

# Rebuild after Dockerfile changes
docker-compose build --no-cache && docker-compose up -d

# View logs
docker logs claude-agent

# Execute commands inside container
docker exec -it claude-agent bash

# Multi-instance deployment (different ports)
PORT=8001 docker-compose -p claude1 up -d
PORT=8002 docker-compose -p claude2 up -d
```

## Architecture

### Single Port Design
All services are proxied through nginx on port 80:
- `/` - Flask dashboard UI (port 5000)
- `/v1/` - Claude Code OpenAI Wrapper (port 8000)
- `/agent/` - Headless Agent API (port 5001)
- `/search/` - SearXNG (separate container, port 8888)
- `/ttyd/` - Web terminal with auto-login (port 7682)

### Flask Application Structure (`webapps/flask/`)

| File | Purpose |
|------|---------|
| `app.py` | Main Flask app - Dashboard UI, providers, workflows, agent builder, library APIs |
| `agent_api.py` | Headless Agent API - `/v1/agent/execute`, task management |
| `orchestrator.py` | Multi-agent workflow engine - parallel, sequential, DAG execution |
| `agents.py` | Agent registry - CRUD for custom agents with skills |
| `library.py` | Skills/MCP library - install/uninstall skills and MCP servers |
| `telegram_bot.py` | Optional Telegram bot integration |

### Key Components

**entrypoint.sh** - Starts all services in order:
1. SSH/Samba for file access
2. SearXNG search engine
3. Nginx reverse proxy
4. ttyd web terminal (auto-login via sshpass)
5. Claude Code OpenAI Wrapper (Poetry/uvicorn)
6. Flask dashboard
7. Headless Agent API
8. Telegram bot (if configured)

**nginx-default.conf** - Routes requests to internal services. Long timeouts (600s) for `/v1/` due to LLM response times.

### Configuration Files

- `~/.claude/settings.json` - Claude Code config (API keys, model defaults)
- `~/.claude/wrapper.env` - Environment for OpenAI wrapper
- `~/.claude/mcp-servers.json` - MCP server definitions
- `~/.claude/agents/` - Custom agent configurations
- `~/.claude/skills/` - Installed skill packages
- `~/.claude/providers.json` - Provider registry

### Volume Mounts

- `./data:/home/claude` - Persists user data, projects, and Claude config

## APIs

### OpenAI-Compatible (`/v1/`)
```bash
curl -X POST http://localhost/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'
```

### Agent API (`/agent/`)
- `POST /v1/agent/execute` - Run Claude Code command
- `GET /v1/agent/status` - Check configuration status

### Orchestration API (`/api/orchestrate`)
- `POST /api/orchestrate` - Create workflow (parallel/sequential/dag)
- `GET /api/orchestrate/<id>` - Get workflow status
- `GET /api/orchestrate/<id>/stream` - SSE real-time updates

### Agent Builder API (`/api/agents`)
- `GET/POST /api/agents` - List/create agents
- `GET/PUT/DELETE /api/agents/<id>` - Agent CRUD
- `POST /api/agents/<id>/execute` - Execute agent task

### Library API (`/api/library`)
- `GET /api/library/skills` - List available skills
- `POST /api/library/skills/<id>/install` - Install skill
- `GET /api/library/mcp` - List available MCP servers
- `POST /api/library/mcp/<id>/install` - Install MCP server

## MCP Servers

Pre-configured in mcp-servers.json:
- filesystem, github, sqlite, fetch, memory, brave-search
- searxng - Local search
- claude-agent-self - Recursive agent calls via MCP
