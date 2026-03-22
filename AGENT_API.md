# Claude Code Agent - Single Port Deployment

All services accessible through **one port** via nginx reverse proxy.

## Quick Start

```bash
# Build and launch
docker-compose up -d

# Access everything at http://localhost
```

## URL Paths

| Path | Service | Description |
|------|---------|-------------|
| `/` | Flask UI | Web onboarding wizard |
| `/api/` | Flask API | Configuration API |
| `/v1/` | Agent API | OpenAI-compatible API |
| `/agent/` | Agent API | Agent-specific endpoints |
| `/search/` | SearXNG | Search engine |
| `/ssh/` | SSHwifty | Web terminal |
| `/health` | Health | Health check |

## API Usage (OpenAI-Compatible)

```python
from openai import OpenAI

# Single endpoint for everything
client = OpenAI(
    base_url="http://localhost/v1",
    api_key="dummy"
)

# Chat
response = client.chat.completions.create(
    model="claude-code",
    messages=[{"role": "user", "content": "Create a REST API"}]
)

# Streaming
stream = client.chat.completions.create(
    model="claude-code",
    messages=[{"role": "user", "content": "Write code"}],
    stream=True
)
for chunk in stream:
    print(chunk.choices[0].delta.content, end="")
```

## cURL Examples

```bash
# Chat completion
curl -X POST http://localhost/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Execute task
curl -X POST http://localhost/agent/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a Python file"}'

# Agent status
curl http://localhost/agent/status

# Search
curl "http://localhost/search/?q=python&format=json"
```

## Multi-Instance Deployment

```bash
# Instance 1: Z.AI on port 8001
PORT=8001 docker-compose -p claude-zai up -d

# Instance 2: OpenRouter on port 8002
PORT=8002 docker-compose -p claude-openrouter up -d

# Or use multi-compose file
docker-compose -f docker-compose.multi.yml up -d
```

| Instance | Port | Access URL |
|----------|------|------------|
| Z.AI | 8001 | http://localhost:8001 |
| OpenRouter | 8002 | http://localhost:8002 |
| NVIDIA | 8003 | http://localhost:8003 |
| Ollama | 8004 | http://localhost:8004 |

## Authentication

Set token when launching:

```bash
# With authentication
PORT=80 TOKEN=mysecret docker-compose up -d

# Then include in requests
curl -H "Authorization: Bearer mysecret" http://localhost/agent/status
```

## LangChain Integration

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost/v1",
    api_key="dummy",
    model="claude-code"
)

response = llm.invoke("Write a function")
```

## Subagent MCP Usage

Add to your Claude Code settings:

```json
{
  "mcpServers": {
    "remote-agent": {
      "command": "python3",
      "args": ["/path/to/agent_mcp.py"],
      "env": {
        "AGENT_API_URL": "http://localhost:8001"
      }
    }
  }
}
```

## Health Check

```bash
curl http://localhost/health
# {"status": "healthy", "service": "claude-agent-api"}
```
