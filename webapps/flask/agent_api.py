#!/usr/bin/env python3
"""
Claude Code Headless Agent API Server
Enables programmatic access to Claude Code for subagent usage

Usage:
    python3 agent_api.py --port 5001 --token your-secret-token

API Endpoints:
    POST /v1/chat/completions - OpenAI-compatible chat API
    POST /v1/agent/execute   - Execute Claude Code command
    POST /v1/agent/task      - Create and run a task
    GET  /v1/agent/status    - Get agent status
    WebSocket /ws            - Real-time streaming responses
"""

import os
import sys
import json
import uuid
import subprocess
import threading
import queue
import argparse
import time
import re
from datetime import datetime
from typing import Optional, Dict, List, Any, Generator
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import websocket

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configuration
API_TOKEN = os.environ.get("AGENT_API_TOKEN", "")
CLAUDE_CONFIG_DIR = os.path.expanduser("~/.claude")
PROJECTS_DIR = os.path.expanduser("~/projects")

# Task storage
tasks: Dict[str, Dict] = {}
task_queue = queue.Queue()
executor = ThreadPoolExecutor(max_workers=4)


def verify_token(req) -> bool:
    """Verify API token from request"""
    if not API_TOKEN:
        return True  # No token required if not set

    auth_header = req.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:] == API_TOKEN

    token = req.headers.get("X-API-Token", "")
    return token == API_TOKEN


def run_claude_command(
    prompt: str,
    working_dir: str = None,
    timeout: int = 300,
    stream: bool = False
) -> Dict:
    """Run Claude Code command and return result"""

    work_dir = working_dir or PROJECTS_DIR
    os.makedirs(work_dir, exist_ok=True)

    try:
        # Build command
        cmd = ["claude", "--print", prompt]

        env = os.environ.copy()
        env["HOME"] = os.path.expanduser("~")

        if stream:
            # Return generator for streaming
            return stream_claude_output(cmd, work_dir, env, timeout)
        else:
            # Run synchronously
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Command timed out after {timeout} seconds",
            "output": ""
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "output": ""
        }


def stream_claude_output(cmd, work_dir, env, timeout) -> Generator:
    """Stream Claude Code output"""
    process = subprocess.Popen(
        cmd,
        cwd=work_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )

    start_time = time.time()

    try:
        while True:
            if time.time() - start_time > timeout:
                process.kill()
                yield json.dumps({"error": "Timeout", "done": True}) + "\n"
                break

            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break

            if line:
                yield json.dumps({
                    "content": line,
                    "done": False
                }) + "\n"

        # Get any remaining output
        stdout, stderr = process.communicate()
        if stdout:
            yield json.dumps({"content": stdout, "done": False}) + "\n"

        yield json.dumps({
            "done": True,
            "success": process.returncode == 0,
            "return_code": process.returncode
        }) + "\n"

    except Exception as e:
        yield json.dumps({"error": str(e), "done": True}) + "\n"


def create_task(prompt: str, options: Dict = None) -> str:
    """Create a new task and return task ID"""
    task_id = str(uuid.uuid4())[:8]

    tasks[task_id] = {
        "id": task_id,
        "prompt": prompt,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "options": options or {},
        "result": None
    }

    # Submit to executor
    executor.submit(execute_task, task_id)

    return task_id


def execute_task(task_id: str):
    """Execute a task in background"""
    task = tasks.get(task_id)
    if not task:
        return

    task["status"] = "running"
    task["started_at"] = datetime.now().isoformat()

    result = run_claude_command(
        prompt=task["prompt"],
        working_dir=task["options"].get("working_dir"),
        timeout=task["options"].get("timeout", 300)
    )

    task["status"] = "completed" if result["success"] else "failed"
    task["completed_at"] = datetime.now().isoformat()
    task["result"] = result


# ============== OpenAI-Compatible API ==============

@app.route("/v1/models", methods=["GET"])
def list_models():
    """List available models (OpenAI-compatible)"""
    if not verify_token(request):
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify({
        "object": "list",
        "data": [
            {
                "id": "claude-code",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "claude-code-agent",
                "permission": [],
                "root": "claude-code",
                "parent": None,
            }
        ]
    })


@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    """OpenAI-compatible chat completions endpoint"""
    if not verify_token(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    messages = data.get("messages", [])
    stream = data.get("stream", False)
    timeout = data.get("timeout", 300)
    working_dir = data.get("working_dir")

    # Convert messages to prompt
    prompt_parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            prompt_parts.append(f"System: {content}")
        elif role == "user":
            prompt_parts.append(f"User: {content}")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {content}")

    prompt = "\n".join(prompt_parts)

    if not prompt:
        return jsonify({"error": "No messages provided"}), 400

    if stream:
        # Streaming response
        def generate():
            result_gen = run_claude_command(prompt, working_dir, timeout, stream=True)
            for chunk in result_gen:
                data = json.loads(chunk)
                if "content" in data:
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': data['content']}}]})}\n\n"
                if data.get("done"):
                    yield "data: [DONE]\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream"
        )
    else:
        # Non-streaming response
        result = run_claude_command(prompt, working_dir, timeout)

        return jsonify({
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "claude-code",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.get("output", "")
                },
                "finish_reason": "stop" if result["success"] else "error"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            },
            "error": result.get("error") if not result["success"] else None
        })


# ============== Agent-Specific API ==============

@app.route("/v1/agent/execute", methods=["POST"])
def execute_command():
    """Execute a direct Claude Code command"""
    if not verify_token(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    prompt = data.get("prompt", "")
    working_dir = data.get("working_dir")
    timeout = data.get("timeout", 300)
    stream = data.get("stream", False)

    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    if stream:
        def generate():
            result_gen = run_claude_command(prompt, working_dir, timeout, stream=True)
            for chunk in result_gen:
                yield chunk

        return Response(generate(), mimetype="application/x-ndjson")

    result = run_claude_command(prompt, working_dir, timeout)
    return jsonify(result)


@app.route("/v1/agent/task", methods=["POST"])
def create_task_endpoint():
    """Create and start a new async task"""
    if not verify_token(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    prompt = data.get("prompt", "")

    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    task_id = create_task(prompt, data.get("options", {}))

    return jsonify({
        "task_id": task_id,
        "status": "created",
        "status_url": f"/v1/agent/task/{task_id}"
    })


@app.route("/v1/agent/task/<task_id>", methods=["GET"])
def get_task(task_id: str):
    """Get task status and result"""
    if not verify_token(request):
        return jsonify({"error": "Unauthorized"}), 401

    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    return jsonify(task)


@app.route("/v1/agent/tasks", methods=["GET"])
def list_tasks():
    """List all tasks"""
    if not verify_token(request):
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify({
        "tasks": list(tasks.values())
    })


@app.route("/v1/agent/status", methods=["GET"])
def agent_status():
    """Get agent status and configuration"""
    if not verify_token(request):
        return jsonify({"error": "Unauthorized"}), 401

    # Check if Claude Code is configured
    config_file = os.path.join(CLAUDE_CONFIG_DIR, "settings.json")
    is_configured = os.path.exists(config_file)

    # Get provider info
    provider = None
    if is_configured:
        try:
            with open(config_file) as f:
                config = json.load(f)
                base_url = config.get("env", {}).get("ANTHROPIC_BASE_URL", "")
                if "z.ai" in base_url:
                    provider = "zai"
                elif "openrouter" in base_url:
                    provider = "openrouter"
                elif "nvidia" in base_url:
                    provider = "nvidia"
                elif "11434" in base_url:
                    provider = "ollama"
        except:
            pass

    return jsonify({
        "status": "ready" if is_configured else "not_configured",
        "configured": is_configured,
        "provider": provider,
        "projects_dir": PROJECTS_DIR,
        "config_dir": CLAUDE_CONFIG_DIR,
        "active_tasks": len([t for t in tasks.values() if t["status"] == "running"]),
        "total_tasks": len(tasks)
    })


@app.route("/v1/agent/configure", methods=["POST"])
def configure_agent():
    """Configure the agent with LLM provider settings"""
    if not verify_token(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    os.makedirs(CLAUDE_CONFIG_DIR, exist_ok=True)

    config = {"env": data}

    config_file = os.path.join(CLAUDE_CONFIG_DIR, "settings.json")
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    return jsonify({
        "success": True,
        "message": "Configuration saved"
    })


# ============== Health & Info ==============

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "claude-agent-api"})


@app.route("/")
def index():
    """API info endpoint"""
    return jsonify({
        "name": "Claude Code Agent API",
        "version": "1.0.0",
        "endpoints": {
            "openai_compatible": {
                "GET /v1/models": "List available models",
                "POST /v1/chat/completions": "Chat completions (OpenAI-compatible)"
            },
            "agent": {
                "POST /v1/agent/execute": "Execute Claude Code command",
                "POST /v1/agent/task": "Create async task",
                "GET /v1/agent/task/<id>": "Get task status",
                "GET /v1/agent/tasks": "List all tasks",
                "GET /v1/agent/status": "Get agent status",
                "POST /v1/agent/configure": "Configure LLM provider"
            }
        },
        "auth": "Bearer token in Authorization header or X-API-Token" if API_TOKEN else "No auth required"
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claude Code Headless Agent API")
    parser.add_argument("--port", type=int, default=int(os.environ.get("AGENT_PORT", 5001)), help="API port")
    parser.add_argument("--token", type=str, default="", help="API authentication token")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    args = parser.parse_args()

    if args.token:
        API_TOKEN = args.token

    print(f"Starting Claude Code Agent API on {args.host}:{args.port}")
    print(f"Authentication: {'Enabled' if API_TOKEN else 'Disabled'}")
    print(f"\nEndpoints:")
    print(f"  OpenAI Compatible: POST http://localhost:{args.port}/v1/chat/completions")
    print(f"  Agent Execute:     POST http://localhost:{args.port}/v1/agent/execute")
    print(f"  Agent Status:      GET  http://localhost:{args.port}/v1/agent/status")

    app.run(host=args.host, port=args.port, debug=False, threaded=True)
