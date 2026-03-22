# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
- `/` - Flask onboarding UI (port 5000)
- `/v1/` - Claude Code OpenAI Wrapper (port 8000)
- `/agent/` - Headless Agent API (port 5001)
- `/search/` - SearXNG (separate container, port 8888)
- `/ttyd/` - Web terminal with auto-login (port 7682)

### Key Components

**entrypoint.sh** - Starts all services in order:
1. SSH/Samba for file access
2. SearXNG search engine
3. Nginx reverse proxy
4. ttyd web terminal (auto-login via sshpass)
5. Claude Code OpenAI Wrapper (Poetry/uvicorn)
6. Flask onboarding wizard
7. Headless Agent API

**nginx-default.conf** - Routes requests to internal services. Long timeouts (600s) for `/v1/` due to LLM response times.

**Dockerfile** - Ubuntu 24.04 base with:
- Node.js 20 + Claude Code CLI
- Python 3 + MCP SDK
- Poetry for wrapper dependencies
- ttyd + sshpass for web terminal

### Configuration Files

- `~/.claude/settings.json` - Claude Code config (API keys, model defaults)
- `~/.claude/wrapper.env` - Environment for OpenAI wrapper
- `~/.claude/mcp-servers.json` - MCP server definitions

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

## Provider Configuration

Providers are configured via Flask UI or by setting environment variables in docker-compose.yml:
- `anthropic` - Direct Anthropic API
- `zai` - Z.AI/GLM Coding Plan
- `bedrock` - AWS Bedrock
- `vertex` - Google Vertex AI
- `openrouter` - OpenRouter
- `ollama` - Local Ollama

## MCP Servers

Pre-configured in mcp-servers.json:
- filesystem, github, sqlite, fetch, memory, brave-search
- searxng - Local search
- claude-agent-self - Recursive agent calls via MCP
