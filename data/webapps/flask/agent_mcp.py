#!/usr/bin/env python3
"""
Claude Code Agent MCP Server
Allows this agent to be used as an MCP tool by other Claude Code instances

This MCP server exposes the agent's capabilities for:
- Code generation and editing
- File operations
- Command execution
- Task management

Usage in Claude Code settings.json:
{
  "mcpServers": {
    "claude-agent": {
      "command": "python3",
      "args": ["/home/claude/webapps/flask/agent_mcp.py"],
      "env": {
        "AGENT_API_URL": "http://localhost:5001",
        "AGENT_API_TOKEN": "your-token-if-set"
      }
    }
  }
}
"""

import os
import sys
import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

# Configuration
AGENT_API_URL = os.environ.get("AGENT_API_URL", "http://localhost:5001")
AGENT_API_TOKEN = os.environ.get("AGENT_API_TOKEN", "")


def api_request(method: str, endpoint: str, data: Dict = None) -> Dict:
    """Make API request to agent server"""
    url = f"{AGENT_API_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    if AGENT_API_TOKEN:
        headers["Authorization"] = f"Bearer {AGENT_API_TOKEN}"

    try:
        if method == "GET":
            req = urllib.request.Request(url, headers=headers)
        else:
            body = json.dumps(data or {}).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers=headers, method=method)

        with urllib.request.urlopen(req, timeout=300) as response:
            return json.loads(response.read().decode())

    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def send_response(response: Dict):
    """Send JSON-RPC response"""
    output = json.dumps(response)
    sys.stdout.write(output + "\n")
    sys.stdout.flush()


def handle_initialize(params: Dict) -> Dict:
    """Handle initialize request"""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "claude-code-agent",
            "version": "1.0.0"
        }
    }


def handle_list_tools() -> Dict:
    """Return available tools"""
    return {
        "tools": [
            {
                "name": "agent_execute",
                "description": "Execute a coding task using Claude Code agent. Use for code generation, file operations, git operations, and general development tasks.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The task or prompt to execute"
                        },
                        "working_dir": {
                            "type": "string",
                            "description": "Working directory (optional)"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 300)"
                        }
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "agent_status",
                "description": "Get the current status of the Claude Code agent, including configuration and active tasks.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "agent_create_task",
                "description": "Create an async task that runs in the background. Returns a task ID for checking status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The task to execute"
                        },
                        "working_dir": {
                            "type": "string",
                            "description": "Working directory (optional)"
                        }
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "agent_get_task",
                "description": "Get the status and result of a previously created task.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The task ID to check"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "agent_configure",
                "description": "Configure the agent with LLM provider settings.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "description": "Provider ID (zai, openrouter, nvidia, ollama)"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "API key for the provider"
                        },
                        "base_url": {
                            "type": "string",
                            "description": "Base URL for the API"
                        },
                        "model": {
                            "type": "string",
                            "description": "Model to use"
                        }
                    },
                    "required": ["provider"]
                }
            }
        ]
    }


def handle_call_tool(name: str, arguments: Dict) -> Dict:
    """Handle tool execution"""

    if name == "agent_execute":
        result = api_request("POST", "/v1/agent/execute", {
            "prompt": arguments.get("prompt"),
            "working_dir": arguments.get("working_dir"),
            "timeout": arguments.get("timeout", 300)
        })

        if "error" in result:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error: {result['error']}"
                }],
                "isError": True
            }

        output = result.get("output", "")
        error = result.get("error", "")

        text = output
        if error and not result.get("success"):
            text = f"Error: {error}\n\nOutput:\n{output}"

        return {
            "content": [{
                "type": "text",
                "text": text
            }]
        }

    elif name == "agent_status":
        result = api_request("GET", "/v1/agent/status")
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, indent=2)
            }]
        }

    elif name == "agent_create_task":
        result = api_request("POST", "/v1/agent/task", {
            "prompt": arguments.get("prompt"),
            "options": {
                "working_dir": arguments.get("working_dir")
            }
        })
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, indent=2)
            }]
        }

    elif name == "agent_get_task":
        task_id = arguments.get("task_id")
        result = api_request("GET", f"/v1/agent/task/{task_id}")
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, indent=2)
            }]
        }

    elif name == "agent_configure":
        provider = arguments.get("provider")
        config = {
            "ANTHROPIC_API_KEY": arguments.get("api_key", ""),
            "ANTHROPIC_BASE_URL": arguments.get("base_url", ""),
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": arguments.get("model", ""),
            "ANTHROPIC_DEFAULT_SONNET_MODEL": arguments.get("model", ""),
            "ANTHROPIC_DEFAULT_OPUS_MODEL": arguments.get("model", "")
        }

        result = api_request("POST", "/v1/agent/configure", config)
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, indent=2)
            }]
        }

    else:
        return {
            "content": [{
                "type": "text",
                "text": f"Unknown tool: {name}"
            }],
            "isError": True
        }


def main():
    """Main MCP server loop"""
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            method = request.get("method", "")
            params = request.get("params", {})
            request_id = request.get("id")

            response = {"jsonrpc": "2.0", "id": request_id}

            if method == "initialize":
                response["result"] = handle_initialize(params)

            elif method == "tools/list":
                response["result"] = handle_list_tools()

            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})
                response["result"] = handle_call_tool(tool_name, tool_args)

            elif method == "notifications/initialized":
                continue  # No response needed

            else:
                response["error"] = {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }

            send_response(response)

        except json.JSONDecodeError:
            send_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            })
        except Exception as e:
            send_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            })


if __name__ == "__main__":
    main()
