<div align="center">

# 📦 CChips

**Self-hosted Claude Code Agent with OpenAI-compatible API**

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## What is CChips?

CChips is a Docker container deployment that provides Claude Code CLI with an OpenAI-compatible API wrapper, web terminal access, file sharing, and multiple MCP servers. Access everything through a single port.

## ✨ Features

- 🔌 **OpenAI-Compatible API** - Use Claude Code through any OpenAI SDK
- 🖥️ **Web Terminal** - ttyd with auto-login, no authentication required
- 📁 **File Access** - SSH, SFTP, and Samba/SMB sharing
- 🔍 **Search Engine** - Built-in SearXNG for web search
- 🔌 **MCP Servers** - Pre-configured Model Context Protocol servers
- 🎛️ **Onboarding UI** - Flask wizard for provider configuration
- 📦 **Single Port** - All services proxied through nginx

## 🚀 Quick Start

```bash
# Clone and start
git clone https://github.com/slothitude/cchips.git
cd cchips
docker-compose up -d

# Access at http://localhost
```

First launch opens the onboarding wizard to configure your LLM provider.

## 🌐 Services

| Path | Service | Port | Description |
|------|---------|------|-------------|
| `/` | Flask UI | 5000 | Onboarding wizard |
| `/v1/` | Wrapper API | 8000 | OpenAI-compatible API |
| `/agent/` | Agent API | 5001 | Headless agent endpoints |
| `/search/` | SearXNG | 8888 | Web search engine |
| `/ttyd/` | ttyd | 7682 | Web terminal (auto-login) |
| `/health` | Health | - | Health check endpoint |

**External Ports:**
- `80` - HTTP (nginx proxy)
- `22` - SSH/SFTP

## 📖 API Reference

### Project Management (`/api/`)

```bash
# Create new project
curl -X POST http://localhost/api/project/create \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app", "template": "python"}'

# Upload files
curl -X POST http://localhost/api/upload \
  -F "file=@app.py" -F "project=my-app"

# Upload and ask Claude
curl -X POST http://localhost/api/upload-and-ask \
  -F "files=@main.py" -F "prompt=Review for bugs"

# List projects
curl http://localhost/api/projects

# Open project in Claude
curl -X POST http://localhost/api/project/my-app/open \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Analyze this project"}'
```

**Templates:** `empty`, `python`, `node`, `web`

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

# Create async task
curl -X POST http://localhost/agent/v1/agent/task \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Build a REST API", "options": {"timeout": 600}}'
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

## 🔧 Configuration

### Supported Providers

| Provider | Auth Method | Description |
|----------|-------------|-------------|
| `anthropic` | API Key | Direct Anthropic API |
| `zai` | API Key | Z.AI/GLM Coding Plan |
| `bedrock` | AWS Credentials | AWS Bedrock |
| `vertex` | GCP Credentials | Google Vertex AI |
| `openrouter` | API Key | OpenRouter aggregator |
| `nvidia` | API Key | NVIDIA NIM |
| `ollama` | None | Local Ollama |
| `custom` | API Key | Custom endpoint |

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

## 🔌 MCP Servers

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

## 📦 Multi-Instance Deployment

Run multiple instances with different providers:

```bash
# Instance 1: Z.AI on port 8001
PORT=8001 docker-compose -p cchips-zai up -d

# Instance 2: OpenRouter on port 8002
PORT=8002 docker-compose -p cchips-openrouter up -d

# Instance 3: Ollama on port 8003
PORT=8003 docker-compose -p cchips-ollama up -d
```

Or use `docker-compose.multi.yml` for predefined instances.

## 🔐 Security

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

> ⚠️ Change default passwords in production

## 📁 File Access

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

## 🔧 Troubleshooting

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
- Check provider configuration in onboarding UI
- Verify API key is valid
- Check wrapper logs: `docker logs cchips-agent | grep wrapper`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**[⬆ Back to Top](#-cchips)**

</div>
