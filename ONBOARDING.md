# CChips Claude Code Onboarding Guide

This document teaches Claude Code how to use every capability of CChips.

---

## 🎯 What is CChips?

CChips is YOUR environment. You are running inside a Docker container that provides you with:
- Web search via SearXNG
- File access via SSH/Samba
- Web terminal via ttyd
- Self-referential API calls
- Multiple MCP servers

---

## 🔍 How to Search the Web

### Method 1: SearXNG API (Recommended)

```bash
# JSON API
curl "http://localhost:8888/search?q=python+tutorial&format=json"

# Through nginx proxy
curl "http://localhost/search/?q=python+tutorial&format=json"
```

### Method 2: SearXNG MCP Server

You have a local SearXNG MCP server configured. Use it through MCP tools:

```
Use the searxng MCP server to search for "latest Python features"
```

### Method 3: Python Script

```python
import urllib.request
import json

query = "python best practices"
url = f"http://localhost:8888/search?q={query}&format=json"

with urllib.request.urlopen(url) as response:
    results = json.loads(response.read().decode())
    for result in results.get("results", [])[:5]:
        print(f"- {result['title']}: {result['url']}")
```

### Method 4: Brave Search MCP (Requires API Key)

If `BRAVE_API_KEY` is set, you can use Brave Search:

```
Use the brave-search MCP server to search for "docker best practices"
```

---

## 📁 How to Access Files

### Inside Container (Your Home)

Your working directory is `/home/claude`. Projects are in `/home/claude/projects`.

```bash
# List projects
ls ~/projects

# Create new project
mkdir ~/projects/my-app
cd ~/projects/my-app
```

### From Host Machine (SSH/SFTP)

```bash
# SSH
ssh claude@localhost -p 22
# Password: claude

# SFTP
sftp claude@localhost
```

### From Host Machine (Samba/SMB)

Windows:
```
\\localhost\projects
```

macOS/Linux:
```
smb://localhost/projects
```

### Filesystem MCP Server

You have direct filesystem access through MCP:

```
Use the filesystem MCP server to read files in /home/claude/projects
```

---

## 🖥️ Web Terminal Access

The ttyd web terminal is available for browser-based access:

- **URL**: `http://localhost/ttyd/`
- **Auto-login**: Yes (no password required)
- **User**: `claude`

This is useful for users who want terminal access without SSH.

---

## 🔌 MCP Servers Available

You have these MCP servers pre-configured:

| Server | Capability | How to Use |
|--------|------------|------------|
| `filesystem` | Read/write files | "Use filesystem MCP to read ~/projects/app.py" |
| `github` | GitHub API | "Use github MCP to create a repo" |
| `sqlite` | Database ops | "Use sqlite MCP to query data.db" |
| `fetch` | Web fetching | "Use fetch MCP to get content from URL" |
| `memory` | Persistent memory | "Store this in memory for later" |
| `brave-search` | Brave search | "Search for X using brave-search" |
| `searxng` | Local search | "Search for X using searxng" |
| `claude-agent-self` | Recursive calls | "Use claude-agent-self to delegate task" |

### Using MCP Servers

Just ask naturally:
- "Search the web for Python tutorials"
- "Read the file ~/projects/main.py"
- "Create a GitHub issue for this bug"
- "Store this decision in memory"

---

## 🤖 Self-Referential Agent Calls

You can call yourself as a sub-agent through the MCP server:

### When to Use Self-Calls

1. **Parallel tasks** - Run multiple independent tasks simultaneously
2. **Delegation** - Let a sub-agent handle a subtask while you focus on the main task
3. **Isolation** - Run potentially risky operations in isolation
4. **Different context** - Start fresh without current context

### How to Use

```
Use the claude-agent-self MCP server to:
- Analyze the codebase structure
- Write unit tests for the API
- Review the security of authentication
```

### Direct API Call Alternative

```python
import requests

response = requests.post(
    "http://localhost:5001/v1/agent/execute",
    json={
        "prompt": "Create a Python file that implements a REST API",
        "working_dir": "/home/claude/projects",
        "timeout": 300
    }
)
print(response.json()["output"])
```

---

## 🌐 API Endpoints Reference

### OpenAI-Compatible API (`/v1/`)

For external tools that expect OpenAI format:

```bash
# Chat completion
curl -X POST http://localhost/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'

# Stream response
curl -X POST http://localhost/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Write code"}], "stream": true}'

# List models
curl http://localhost/v1/models
```

### Agent API (`/agent/`)

For programmatic control:

```bash
# Execute synchronously
curl -X POST http://localhost/agent/v1/agent/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a file", "timeout": 300}'

# Create async task
curl -X POST http://localhost/agent/v1/agent/task \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Long running task", "options": {"timeout": 600}}'

# Check task status
curl http://localhost/agent/v1/agent/task/TASK_ID

# List all tasks
curl http://localhost/agent/v1/agent/tasks

# Get agent status
curl http://localhost/agent/v1/agent/status
```

---

## 🔧 Provider Configuration

### Check Current Provider

```bash
curl http://localhost/agent/v1/agent/status
```

### Configure Provider

Use the Flask UI at `http://localhost/` or:

```bash
curl -X POST http://localhost:5000/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "api_key": "your-api-key"
  }'
```

### Available Providers

| Provider | Required Config |
|----------|-----------------|
| `anthropic` | `api_key` |
| `zai` | `api_key` |
| `bedrock` | `aws_access_key_id`, `aws_secret_access_key`, `aws_region` |
| `vertex` | `google_credentials`, `gcp_project`, `gcp_region` |
| `openrouter` | `api_key` |
| `nvidia` | `api_key` |
| `ollama` | `host`, `port` |
| `custom` | `api_key`, `base_url` |

---

## 📋 Common Workflows

### Research and Implement

1. Search for information:
```
Search for "FastAPI best practices 2024" using searxng
```

2. Create the project:
```
Create a new FastAPI project in ~/projects/my-api
```

3. Implement based on research:
```
Implement the API following best practices found
```

### Parallel Sub-Agent Tasks

```
Use claude-agent-self to run these tasks in parallel:
1. Analyze ~/project/src for security issues
2. Write unit tests for ~/project/tests
3. Generate API documentation
```

### File Analysis Pipeline

```
1. Use filesystem MCP to read all Python files in ~/projects
2. Use searxng to find best practices for each pattern found
3. Create a report with recommendations
```

---

## 🚨 Troubleshooting

### Search Not Working

```bash
# Check SearXNG status
curl http://localhost:8888/

# Check through nginx
curl http://localhost/search/
```

### MCP Server Not Responding

```bash
# Check MCP server logs
docker logs cchips-agent 2>&1 | grep mcp

# Restart container
docker restart cchips-agent
```

### API Returns Errors

```bash
# Check agent status
curl http://localhost/agent/v1/agent/status

# Check wrapper health
curl http://localhost/health
```

---

## 🎓 Best Practices

1. **Use MCP servers** - They're optimized for specific tasks
2. **Use searxng for web search** - Fast, local, no API limits
3. **Use self-calls for parallel work** - Delegate independent tasks
4. **Store important info in memory MCP** - Persist across sessions
5. **Check agent status before long tasks** - Ensure provider is configured

---

## 📚 Quick Reference

| Want to... | Use this... |
|------------|-------------|
| Search the web | `searxng` MCP or `http://localhost:8888/search?q=...&format=json` |
| Read/write files | `filesystem` MCP or direct file access |
| Access GitHub | `github` MCP (set `GITHUB_TOKEN` first) |
| Store memories | `memory` MCP |
| Call yourself | `claude-agent-self` MCP |
| External API access | `http://localhost/v1/chat/completions` |
| Programmatic control | `http://localhost:5001/v1/agent/execute` |
| Web terminal | `http://localhost/ttyd/` |
| File sharing | SSH (port 22) or SMB (`\\localhost\projects`) |

---

*This document should give Claude Code everything needed to utilize CChips effectively.*
