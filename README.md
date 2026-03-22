<div align="center">

# CChips

**Multi-Agent AI Orchestration Platform**

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

*Self-hosted Claude Code Agent with OpenAI-compatible API, multi-agent workflows, and premium dashboard*

</div>

---

## What is CChips?

CChips is a Docker container deployment that provides Claude Code CLI with an OpenAI-compatible API wrapper, multi-agent orchestration, web terminal access, file sharing, and MCP servers. Run parallel AI workflows with different providers through a beautiful dark-themed dashboard.

## Features

- **Multi-Agent Orchestration** - Run parallel, sequential, or DAG-based AI workflows
- **Per-Task Providers** - Assign different LLM providers to each task in a workflow
- **Premium Dashboard** - Dark theme with glassmorphism, real-time SSE updates
- **OpenAI-Compatible API** - Use Claude Code through any OpenAI SDK
- **Web Terminal** - ttyd with auto-login, no authentication required
- **File Access** - SSH, SFTP, and Samba/SMB sharing
- **Search Engine** - Built-in SearXNG for web search
- **MCP Servers** - Pre-configured Model Context Protocol servers
- **Single Port** - All services proxied through nginx

## Quick Start

```bash
# Clone and start
git clone https://github.com/slothitude/cchips.git
cd cchips
docker-compose up -d

# Access dashboard at http://localhost
```

First launch opens the onboarding wizard to configure your LLM provider.

## Services

| Path | Service | Port | Description |
|------|---------|------|-------------|
| `/` | Dashboard | 5000 | Multi-agent control center |
| `/v1/` | Wrapper API | 8000 | OpenAI-compatible API |
| `/agent/` | Agent API | 5001 | Headless agent endpoints |
| `/search/` | SearXNG | 8888 | Web search engine |
| `/ttyd/` | ttyd | 7682 | Web terminal (auto-login) |
| `/health` | Health | - | Health check endpoint |

**External Ports:**
- `80` - HTTP (nginx proxy)
- `22` - SSH/SFTP

## Multi-Agent Orchestration

### Workflow Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `parallel` | Execute all tasks simultaneously | Independent tasks, maximum speed |
| `sequential` | Execute tasks one by one | Tasks that build on each other |
| `dag` | Execute based on dependencies | Complex workflows with dependencies |

### Create Workflow via API

```bash
# Parallel workflow with multiple providers
curl -X POST http://localhost/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "parallel",
    "tasks": [
      {"id": "research", "prompt": "Research topic A", "provider": "anthropic"},
      {"id": "code", "prompt": "Write code for B", "provider": "ollama"},
      {"id": "review", "prompt": "Review results", "provider": "zai"}
    ],
    "options": {"max_parallel": 3}
  }'

# DAG workflow with dependencies
curl -X POST http://localhost/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "dag",
    "tasks": [
      {"id": "research", "prompt": "Research the topic"},
      {"id": "design", "prompt": "Design the architecture", "depends_on": ["research"]},
      {"id": "implement", "prompt": "Implement the design", "depends_on": ["design"]},
      {"id": "test", "prompt": "Test the implementation", "depends_on": ["implement"]},
      {"id": "review", "prompt": "Review everything", "context_from": ["research", "implement"]}
    ]
  }'
```

### Monitor Workflows

```bash
# Get workflow status
curl http://localhost/api/orchestrate/<workflow_id>

# Real-time updates (SSE)
curl http://localhost/api/orchestrate/<workflow_id>/stream

# List all workflows
curl http://localhost/api/orchestrate

# Retry failed tasks
curl -X POST http://localhost/api/orchestrate/<workflow_id>/retry
```

### Workflow Management

```bash
# Pause running workflow
curl -X POST http://localhost/api/orchestrate/<workflow_id>/pause

# Resume paused workflow
curl -X POST http://localhost/api/orchestrate/<workflow_id>/resume

# Delete workflow
curl -X DELETE http://localhost/api/orchestrate/<workflow_id>
```

## Provider Registry

### Register Providers

```bash
# Register Ollama (local)
curl -X POST http://localhost/api/registry/providers \
  -H "Content-Type: application/json" \
  -d '{"name": "ollama", "type": "ollama", "host": "host.docker.internal", "port": 11434, "default_model": "llama3.2"}'

# Register Anthropic
curl -X POST http://localhost/api/registry/providers \
  -H "Content-Type: application/json" \
  -d '{"name": "claude", "type": "anthropic", "api_key": "sk-ant-...", "default_model": "claude-sonnet-4-6-20250929"}'

# Register Z.AI
curl -X POST http://localhost/api/registry/providers \
  -H "Content-Type: application/json" \
  -d '{"name": "zai", "type": "zai", "api_key": "...", "default_model": "glm-4.7"}'

# Register OpenRouter
curl -X POST http://localhost/api/registry/providers \
  -H "Content-Type: application/json" \
  -d '{"name": "openrouter", "type": "openrouter", "api_key": "sk-or-...", "default_model": "anthropic/claude-sonnet"}'
```

### Validate & Discover

```bash
# Validate provider credentials
curl -X POST http://localhost/api/registry/providers/validate \
  -H "Content-Type: application/json" \
  -d '{"type": "anthropic", "api_key": "sk-ant-..."}'

# Get available models
curl http://localhost/api/registry/providers/<name>/models

# List all providers
curl http://localhost/api/registry/providers

# Delete provider
curl -X DELETE http://localhost/api/registry/providers/<name>
```

### Supported Providers

| Provider | Auth Method | Description |
|----------|-------------|-------------|
| `anthropic` | API Key | Direct Anthropic API |
| `zai` | API Key | Z.AI/GLM Coding Plan |
| `ollama` | None | Local Ollama |
| `openrouter` | API Key | OpenRouter aggregator |
| `nvidia` | API Key | NVIDIA NIM |
| `custom` | API Key | Custom endpoint |

## API Reference

### OpenAI-Compatible (`/v1/`)

```bash
# Chat completions
curl -X POST http://localhost/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'

# List models
curl http://localhost/v1/models

# Streaming
curl -X POST http://localhost/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Write code"}], "stream": true}'
```

### Agent API (`/agent/`)

```bash
# Execute command
curl -X POST http://localhost/agent/v1/agent/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a Python file"}'

# Check status
curl http://localhost/agent/v1/agent/status
```

### Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost/v1",
    api_key="dummy"
)

response = client.chat.completions.create(
    model="claude-code",
    messages=[{"role": "user", "content": "Create a REST API"}]
)
print(response.choices[0].message.content)
```

### LangChain

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost/v1",
    api_key="dummy",
    model="claude-code"
)

response = llm.invoke("Write a function")
```

## Configuration

### Environment Variables

Set in `docker-compose.yml` or `.env`:

```yaml
environment:
  - ANTHROPIC_API_KEY=your-key
  - ANTHROPIC_BASE_URL=https://api.anthropic.com  # optional
  - AGENT_API_TOKEN=your-secret-token  # optional auth
  - CLAUDE_AUTH_METHOD=api_key
```

### Configuration Files

| File | Purpose |
|------|---------|
| `~/.claude/settings.json` | Claude Code config |
| `~/.claude/wrapper.env` | Wrapper environment |
| `~/.claude/mcp-servers.json` | MCP server definitions |
| `~/.claude/providers.json` | Provider registry |

## MCP Servers

Pre-configured in `mcp-servers.json`:

| Server | Description |
|--------|-------------|
| `filesystem` | File system access to projects |
| `github` | GitHub API (set `GITHUB_TOKEN`) |
| `sqlite` | SQLite database operations |
| `fetch` | Web fetching capabilities |
| `memory` | Persistent conversation memory |
| `brave-search` | Brave search (set `BRAVE_API_KEY`) |
| `searxng` | Local SearXNG search |
| `claude-agent-self` | Recursive agent calls via MCP |

## Multi-Instance Deployment

Run multiple instances with different providers:

```bash
# Instance 1: Z.AI on port 8001
PORT=8001 docker-compose -p cchips-zai up -d

# Instance 2: OpenRouter on port 8002
PORT=8002 docker-compose -p cchips-openrouter up -d

# Instance 3: Ollama on port 8003
PORT=8003 docker-compose -p cchips-ollama up -d
```

## Security

### Optional API Token

```bash
# Set token when launching
AGENT_API_TOKEN=mysecret docker-compose up -d

# Include in requests
curl -H "Authorization: Bearer mysecret" http://localhost/agent/v1/agent/status
```

### Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| SSH/SFTP | `claude` | `claude` |
| Samba/SMB | `claude` | `claude` |
| Web Terminal | Auto-login | - |

> **Warning**: Change default passwords in production

## File Access

### SSH/SFTP
```bash
sftp claude@localhost
# Password: claude
```

### Samba/SMB
```
\\localhost\projects
```

### Volume Mount
```yaml
volumes:
  - ./data:/home/claude  # Persists all user data
```

## Troubleshooting

### Container won't start
```bash
docker logs cchips-agent
```

### Rebuild after config changes
```bash
docker-compose build --no-cache && docker-compose up -d
```

### Check service status
```bash
docker exec cchips-agent ps aux
```

### API returns 500
- Check provider configuration in dashboard
- Verify API key is valid
- Check wrapper logs: `docker logs cchips-agent | grep wrapper`

### Workflow fails
- Check provider is registered: `curl http://localhost/api/registry/providers`
- Verify provider works: `curl -X POST http://localhost/api/registry/providers/validate ...`
- Check workflow status: `curl http://localhost/api/orchestrate/<id>`

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │           Nginx (port 80)           │
                    └───────────────┬─────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│  Flask UI     │         │  Wrapper API  │         │   SearXNG     │
│  (port 5000)  │         │  (port 8000)  │         │  (port 8888)  │
│               │         │               │         │               │
│ - Dashboard   │         │ - /v1/chat    │         │ - Web Search  │
│ - Providers   │         │ - /v1/models  │         │               │
│ - Workflows   │         │ - /v1/messages│         │               │
│ - Orchestrate │         │               │         │               │
└───────────────┘         └───────────────┘         └───────────────┘
        │
        ▼
┌───────────────┐
│ Orchestrator  │
│               │
│ - Parallel    │──────► Ollama API
│ - Sequential  │──────► Anthropic API
│ - DAG         │──────► Z.AI API
│               │──────► OpenRouter API
└───────────────┘
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**[Back to Top](#cchips)**

</div>
