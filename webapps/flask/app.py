#!/usr/bin/env python3
"""
Claude Code LLM Onboarding Wizard - Flask Application
Auto-port detection for multiple container deployment
"""

from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
import os
import json
import subprocess
import urllib.request
import urllib.parse
import socket
import platform
import threading

# Import orchestrator
from orchestrator import orchestrator

app = Flask(__name__,
            template_folder='templates',
            static_folder='static',
            static_url_path='/static')

# Enable CORS for all routes
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
    }
})

# Configuration paths
CLAUDE_CONFIG_DIR = os.path.expanduser("~/.claude")
CLAUDE_SETTINGS_FILE = os.path.join(CLAUDE_CONFIG_DIR, "settings.json")
CLAUDE_MCP_FILE = os.path.join(CLAUDE_CONFIG_DIR, "mcp-servers.json")
WRAPPER_ENV_FILE = os.path.join(CLAUDE_CONFIG_DIR, "wrapper.env")
PROJECTS_DIR = os.path.expanduser("~/projects")

# Provider configurations - updated for Claude Code OpenAI Wrapper
PROVIDERS = {
    "anthropic": {
        "name": "Anthropic (Direct)",
        "description": "Official Anthropic API - Recommended for production",
        "api_key_url": "https://console.anthropic.com/settings/keys",
        "auth_method": "api_key",
        "env_key": "ANTHROPIC_API_KEY",
        "models": [
            {"id": "claude-opus-4-6-20250929", "name": "Claude Opus 4.6 (Most Capable)", "type": "opus"},
            {"id": "claude-sonnet-4-6-20250929", "name": "Claude Sonnet 4.6 (Recommended)", "type": "sonnet"},
            {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5 (Fast)", "type": "haiku"}
        ],
        "default_model": "claude-sonnet-4-6-20250929"
    },
    "zai": {
        "name": "Z.AI (GLM Coding Plan)",
        "description": "Recommended - GLM models optimized for coding",
        "api_key_url": "https://z.ai/manage-apikey/apikey-list",
        "base_url": "https://api.z.ai/api/anthropic",
        "auth_method": "api_key",
        "env_key": "ANTHROPIC_API_KEY",
        "models": [
            {"id": "glm-5", "name": "GLM-5 (Latest, Max users)", "type": "opus"},
            {"id": "glm-4.7", "name": "GLM-4.7 (Balanced)", "type": "sonnet"},
            {"id": "glm-4.5-air", "name": "GLM-4.5-Air (Fast, Efficient)", "type": "haiku"}
        ],
        "default_model": "glm-4.7"
    },
    "bedrock": {
        "name": "AWS Bedrock",
        "description": "Amazon Bedrock - Claude via AWS",
        "auth_method": "bedrock",
        "env_keys": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"],
        "models": [
            {"id": "anthropic.claude-3-5-sonnet-20241022-v2:0", "name": "Claude 3.5 Sonnet v2", "type": "sonnet"},
            {"id": "anthropic.claude-3-opus-20240229-v1:0", "name": "Claude 3 Opus", "type": "opus"},
            {"id": "anthropic.claude-3-haiku-20240307-v1:0", "name": "Claude 3 Haiku", "type": "haiku"}
        ],
        "default_model": "anthropic.claude-3-5-sonnet-20241022-v2:0"
    },
    "vertex": {
        "name": "Google Vertex AI",
        "description": "Claude via Google Cloud Vertex AI",
        "auth_method": "vertex",
        "env_keys": ["GOOGLE_APPLICATION_CREDENTIALS", "GCP_PROJECT", "GCP_REGION"],
        "models": [
            {"id": "claude-3-5-sonnet-v2@20241022", "name": "Claude 3.5 Sonnet v2", "type": "sonnet"},
            {"id": "claude-3-opus@20240229", "name": "Claude 3 Opus", "type": "opus"},
            {"id": "claude-3-haiku@20240307", "name": "Claude 3 Haiku", "type": "haiku"}
        ],
        "default_model": "claude-3-5-sonnet-v2@20241022"
    },
    "openrouter": {
        "name": "OpenRouter",
        "description": "Access multiple LLM providers with free tier options",
        "api_key_url": "https://openrouter.ai/keys",
        "base_url": "https://openrouter.ai/api/v1",
        "auth_method": "api_key",
        "env_key": "ANTHROPIC_API_KEY",
        "models_endpoint": "https://openrouter.ai/api/v1/models",
        "free_only": True
    },
    "nvidia": {
        "name": "NVIDIA NIM",
        "description": "NVIDIA's hosted AI models",
        "api_key_url": "https://build.nvidia.com/",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "auth_method": "api_key",
        "env_key": "ANTHROPIC_API_KEY",
        "models_endpoint": "https://integrate.api.nvidia.com/v1/models"
    },
    "ollama": {
        "name": "Ollama (Local)",
        "description": "Run models locally with Ollama",
        "base_url_template": "http://{host}:{port}/v1",
        "default_host": "host.docker.internal",
        "default_port": "11434",
        "auth_method": "api_key",
        "env_key": "ANTHROPIC_API_KEY",
        "local": True
    },
    "custom": {
        "name": "Custom Provider",
        "description": "Configure your own API endpoint",
        "custom": True,
        "auth_method": "api_key"
    }
}


def get_service_ports():
    """Detect running service ports"""
    ports = {
        "flask": int(os.environ.get("FLASK_PORT", 5000)),
        "nginx": 80,
        "ssh": 22,
        "samba": [139, 445],
        "sshwifty": 8182,
        "searxng": 8888
    }

    # Try to detect actual ports from environment
    for key, default in [("HTTP_PORT", 80), ("HTTPS_PORT", 443), ("FLASK_PORT", 5000)]:
        if key in os.environ:
            ports[key.lower()] = int(os.environ[key])

    return ports


def get_system_info():
    """Get system information"""
    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "ports": get_service_ports()
    }


def fetch_openrouter_models(api_key):
    """Fetch available models from OpenRouter"""
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            models = []
            for m in data.get("data", []):
                pricing = m.get("pricing", {})
                is_free = pricing.get("prompt", "1") == "0"
                models.append({
                    "id": m["id"],
                    "name": m.get("name", m["id"]),
                    "free": is_free,
                    "context_length": m.get("context_length", 0)
                })
            # Sort free models first
            models.sort(key=lambda x: (not x["free"], x["name"]))
            return models
    except Exception as e:
        return {"error": str(e)}


def fetch_nvidia_models(api_key):
    """Fetch available models from NVIDIA NIM"""
    try:
        req = urllib.request.Request(
            "https://integrate.api.nvidia.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return [{"id": m["id"], "name": m["id"]} for m in data.get("data", [])]
    except Exception as e:
        return {"error": str(e)}


def fetch_ollama_models(host="host.docker.internal", port=11434):
    """Fetch local Ollama models"""
    try:
        url = f"http://{host}:{port}/api/tags"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            return [{"id": m["name"], "name": m["name"]} for m in data.get("models", [])]
    except Exception as e:
        return {"error": str(e)}


def save_claude_config(config):
    """Save Claude Code configuration"""
    os.makedirs(CLAUDE_CONFIG_DIR, exist_ok=True)

    settings = {"env": config}

    with open(CLAUDE_SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

    # Also save API key separately for backup
    if "api_key" in config or "ANTHROPIC_API_KEY" in config:
        api_key = config.get("api_key") or config.get("ANTHROPIC_API_KEY") or config.get("ANTHROPIC_AUTH_TOKEN")
        if api_key:
            with open(os.path.join(CLAUDE_CONFIG_DIR, ".api_key"), 'w') as f:
                f.write(api_key)

    return True


def save_wrapper_env(provider_id, config):
    """Save wrapper environment configuration"""
    os.makedirs(CLAUDE_CONFIG_DIR, exist_ok=True)

    provider = PROVIDERS.get(provider_id, {})
    auth_method = provider.get("auth_method", "api_key")

    env_lines = [
        "# Claude Code OpenAI Wrapper Configuration",
        f"# Generated for provider: {provider.get('name', provider_id)}",
        "",
        f"CLAUDE_AUTH_METHOD={auth_method}",
        "",
        "# Server configuration",
        "PORT=8000",
        "MAX_TIMEOUT=600000",
        "",
        "# Working directory for Claude Code",
        "CLAUDE_CWD=/home/claude/projects",
        ""
    ]

    if auth_method == "api_key":
        api_key = config.get("api_key") or config.get("ANTHROPIC_API_KEY") or config.get("ANTHROPIC_AUTH_TOKEN")
        if api_key:
            env_lines.append(f"ANTHROPIC_API_KEY={api_key}")

        base_url = config.get("base_url") or provider.get("base_url")
        if base_url:
            env_lines.append(f"ANTHROPIC_BASE_URL={base_url}")

    elif auth_method == "bedrock":
        env_lines.extend([
            f"AWS_ACCESS_KEY_ID={config.get('aws_access_key_id', '')}",
            f"AWS_SECRET_ACCESS_KEY={config.get('aws_secret_access_key', '')}",
            f"AWS_REGION={config.get('aws_region', 'us-east-1')}"
        ])

    elif auth_method == "vertex":
        env_lines.extend([
            f"GOOGLE_APPLICATION_CREDENTIALS={config.get('google_credentials', '')}",
            f"GCP_PROJECT={config.get('gcp_project', '')}",
            f"GCP_REGION={config.get('gcp_region', 'us-central1')}"
        ])

    # Add model configuration
    if config.get("model"):
        env_lines.extend([
            "",
            "# Model configuration",
            f"DEFAULT_MODEL={config.get('model')}"
        ])

    with open(WRAPPER_ENV_FILE, 'w') as f:
        f.write('\n'.join(env_lines))

    return True


def load_claude_config():
    """Load existing Claude Code configuration"""
    if os.path.exists(CLAUDE_SETTINGS_FILE):
        with open(CLAUDE_SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return None


def get_current_provider():
    """Determine current provider from config"""
    config = load_claude_config()
    if not config:
        # Also check wrapper.env
        if os.path.exists(WRAPPER_ENV_FILE):
            with open(WRAPPER_ENV_FILE, 'r') as f:
                content = f.read()
                if "CLAUDE_AUTH_METHOD=bedrock" in content:
                    return "bedrock"
                elif "CLAUDE_AUTH_METHOD=vertex" in content:
                    return "vertex"
                elif "z.ai" in content:
                    return "zai"
                elif "openrouter" in content:
                    return "openrouter"
                elif "nvidia" in content:
                    return "nvidia"
                elif "CLAUDE_AUTH_METHOD=api_key" in content:
                    return "anthropic"
        return None

    base_url = config.get("env", {}).get("ANTHROPIC_BASE_URL", "")

    if "z.ai" in base_url:
        return "zai"
    elif "openrouter" in base_url:
        return "openrouter"
    elif "nvidia" in base_url:
        return "nvidia"
    elif "11434" in base_url or "ollama" in base_url:
        return "ollama"
    elif base_url:
        return "custom"
    elif config.get("env", {}).get("ANTHROPIC_API_KEY"):
        return "anthropic"

    return None


# ============== API Routes ==============

@app.route('/')
def index():
    """Main landing page"""
    return render_template('index.html',
                           providers=PROVIDERS,
                           system_info=get_system_info(),
                           current_provider=get_current_provider())


@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "claude-onboarding",
        "version": "1.0.0"
    })


@app.route('/api/system')
def system_info():
    """Get system information"""
    return jsonify(get_system_info())


@app.route('/api/ports')
def get_ports():
    """Get service ports"""
    return jsonify(get_service_ports())


@app.route('/api/providers')
def list_providers():
    """List all available providers"""
    return jsonify(PROVIDERS)


@app.route('/api/providers/<provider_id>')
def get_provider(provider_id):
    """Get specific provider info"""
    if provider_id in PROVIDERS:
        return jsonify(PROVIDERS[provider_id])
    return jsonify({"error": "Provider not found"}), 404


@app.route('/api/providers/<provider_id>/models', methods=['POST'])
def fetch_models(provider_id):
    """Fetch available models for a provider"""
    data = request.get_json() or {}

    if provider_id == "openrouter":
        api_key = data.get("api_key")
        if not api_key:
            return jsonify({"error": "API key required"}), 400
        models = fetch_openrouter_models(api_key)
        return jsonify({"models": models})

    elif provider_id == "nvidia":
        api_key = data.get("api_key")
        if not api_key:
            return jsonify({"error": "API key required"}), 400
        models = fetch_nvidia_models(api_key)
        return jsonify({"models": models})

    elif provider_id == "ollama":
        host = data.get("host", "host.docker.internal")
        port = data.get("port", 11434)
        models = fetch_ollama_models(host, port)
        return jsonify({"models": models})

    elif provider_id == "zai":
        return jsonify({"models": PROVIDERS["zai"]["models"]})

    return jsonify({"error": "Unknown provider"}), 400


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    config = load_claude_config()
    provider = get_current_provider()
    return jsonify({
        "config": config,
        "provider": provider
    })


@app.route('/api/config', methods=['POST'])
def save_config():
    """Save configuration"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    provider_id = data.get("provider")
    if not provider_id:
        return jsonify({"error": "Provider required"}), 400

    config = {}

    if provider_id == "anthropic":
        config = {
            "ANTHROPIC_API_KEY": data.get("api_key"),
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": data.get("haiku_model", "claude-haiku-4-5-20251001"),
            "ANTHROPIC_DEFAULT_SONNET_MODEL": data.get("sonnet_model", "claude-sonnet-4-6-20250929"),
            "ANTHROPIC_DEFAULT_OPUS_MODEL": data.get("opus_model", "claude-opus-4-6-20250929")
        }

    elif provider_id == "zai":
        config = {
            "api_key": data.get("api_key"),
            "base_url": "https://api.z.ai/api/anthropic",
            "ANTHROPIC_AUTH_TOKEN": data.get("api_key"),
            "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
            "API_TIMEOUT_MS": "3000000",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": data.get("haiku_model", "glm-4.5-air"),
            "ANTHROPIC_DEFAULT_SONNET_MODEL": data.get("sonnet_model", "glm-4.7"),
            "ANTHROPIC_DEFAULT_OPUS_MODEL": data.get("opus_model", "glm-4.7")
        }

    elif provider_id == "bedrock":
        config = {
            "aws_access_key_id": data.get("aws_access_key_id"),
            "aws_secret_access_key": data.get("aws_secret_access_key"),
            "aws_region": data.get("aws_region", "us-east-1"),
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": data.get("haiku_model"),
            "ANTHROPIC_DEFAULT_SONNET_MODEL": data.get("sonnet_model"),
            "ANTHROPIC_DEFAULT_OPUS_MODEL": data.get("opus_model")
        }

    elif provider_id == "vertex":
        config = {
            "google_credentials": data.get("google_credentials"),
            "gcp_project": data.get("gcp_project"),
            "gcp_region": data.get("gcp_region", "us-central1"),
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": data.get("haiku_model"),
            "ANTHROPIC_DEFAULT_SONNET_MODEL": data.get("sonnet_model"),
            "ANTHROPIC_DEFAULT_OPUS_MODEL": data.get("opus_model")
        }

    elif provider_id == "openrouter":
        config = {
            "api_key": data.get("api_key"),
            "base_url": "https://openrouter.ai/api/v1",
            "ANTHROPIC_API_KEY": data.get("api_key"),
            "ANTHROPIC_BASE_URL": "https://openrouter.ai/api/v1",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": data.get("model"),
            "ANTHROPIC_DEFAULT_SONNET_MODEL": data.get("model"),
            "ANTHROPIC_DEFAULT_OPUS_MODEL": data.get("model")
        }

    elif provider_id == "nvidia":
        config = {
            "api_key": data.get("api_key"),
            "base_url": "https://integrate.api.nvidia.com/v1",
            "ANTHROPIC_API_KEY": data.get("api_key"),
            "ANTHROPIC_BASE_URL": "https://integrate.api.nvidia.com/v1",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": data.get("model"),
            "ANTHROPIC_DEFAULT_SONNET_MODEL": data.get("model"),
            "ANTHROPIC_DEFAULT_OPUS_MODEL": data.get("model")
        }

    elif provider_id == "ollama":
        host = data.get("host", "host.docker.internal")
        port = data.get("port", 11434)
        config = {
            "api_key": "ollama",
            "base_url": f"http://{host}:{port}/v1",
            "ANTHROPIC_API_KEY": "ollama",
            "ANTHROPIC_BASE_URL": f"http://{host}:{port}/v1",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": data.get("model"),
            "ANTHROPIC_DEFAULT_SONNET_MODEL": data.get("model"),
            "ANTHROPIC_DEFAULT_OPUS_MODEL": data.get("model")
        }

    elif provider_id == "custom":
        config = {
            "api_key": data.get("api_key"),
            "base_url": data.get("base_url"),
            "ANTHROPIC_API_KEY": data.get("api_key"),
            "ANTHROPIC_BASE_URL": data.get("base_url"),
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": data.get("haiku_model"),
            "ANTHROPIC_DEFAULT_SONNET_MODEL": data.get("sonnet_model"),
            "ANTHROPIC_DEFAULT_OPUS_MODEL": data.get("opus_model")
        }

    # Save both Claude config and wrapper env
    save_claude_config(config)
    save_wrapper_env(provider_id, {**config, **data})

    return jsonify({
        "success": True,
        "message": f"{PROVIDERS[provider_id]['name']} configured successfully!",
        "provider": provider_id,
        "wrapper_env": WRAPPER_ENV_FILE
    })


@app.route('/api/search')
def search():
    """Proxy search to SearXNG"""
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Query required"})

    try:
        url = f"http://localhost:8888/search?q={urllib.parse.quote(query)}&format=json"
        with urllib.request.urlopen(url, timeout=10) as response:
            return jsonify(json.loads(response.read().decode()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/test', methods=['POST'])
def test_connection():
    """Test API connection"""
    data = request.get_json()
    provider = data.get("provider")

    # This would test the actual API connection
    # For now, just validate the config
    if provider == "ollama":
        host = data.get("host", "host.docker.internal")
        port = data.get("port", 11434)
        try:
            url = f"http://{host}:{port}/api/tags"
            with urllib.request.urlopen(url, timeout=5) as response:
                return jsonify({"success": True, "message": "Ollama connection successful"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    # For other providers, just check if API key is present
    if data.get("api_key"):
        return jsonify({"success": True, "message": "Configuration valid"})

    return jsonify({"success": False, "error": "API key required"})


@app.route('/api/wrapper/status')
def wrapper_status():
    """Check Claude Code OpenAI Wrapper status"""
    try:
        req = urllib.request.Request("http://localhost:8000/health")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            return jsonify({
                "status": "running",
                "wrapper": data
            })
    except Exception as e:
        return jsonify({
            "status": "not_running",
            "error": str(e)
        })


@app.route('/api/wrapper/models')
def wrapper_models():
    """Get available models from wrapper"""
    try:
        req = urllib.request.Request("http://localhost:8000/v1/models")
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/wrapper/restart', methods=['POST'])
def wrapper_restart():
    """Restart the wrapper service (requires config reload)"""
    # The wrapper will pick up new env vars on restart
    # This endpoint just signals that a restart is needed
    return jsonify({
        "success": True,
        "message": "Wrapper restart signal sent. Container restart required for full effect.",
        "note": "Run: docker-compose restart"
    })


# ============== File Upload & Project Management ==============

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload a file to projects directory"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    # Get target directory
    project = request.form.get('project', '')
    target_dir = os.path.join(PROJECTS_DIR, project) if project else PROJECTS_DIR
    os.makedirs(target_dir, exist_ok=True)

    # Save file
    filepath = os.path.join(target_dir, file.filename)
    file.save(filepath)

    return jsonify({
        "success": True,
        "filename": file.filename,
        "path": filepath,
        "size": os.path.getsize(filepath)
    })


@app.route('/api/upload-and-ask', methods=['POST'])
def upload_and_ask():
    """Upload file(s) and send to Claude"""
    import glob

    if 'files' not in request.files and 'file' not in request.files:
        return jsonify({"error": "No files provided"}), 400

    files = request.files.getlist('files') if 'files' in request.files else [request.files['file']]
    prompt = request.form.get('prompt', 'Analyze these files')
    project = request.form.get('project', '')

    # Create project directory
    target_dir = os.path.join(PROJECTS_DIR, project) if project else PROJECTS_DIR
    if project:
        os.makedirs(target_dir, exist_ok=True)

    uploaded = []
    for file in files:
        if file.filename:
            filepath = os.path.join(target_dir, file.filename)
            file.save(filepath)
            uploaded.append(filepath)

    # Build prompt with file context
    full_prompt = f"{prompt}\n\nFiles uploaded:\n"
    for f in uploaded:
        full_prompt += f"- {f}\n"

    # Send to Claude via Agent API
    try:
        req = urllib.request.Request(
            "http://localhost:5001/v1/agent/execute",
            data=json.dumps({
                "prompt": full_prompt,
                "working_dir": target_dir
            }).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode())

        return jsonify({
            "success": True,
            "files": uploaded,
            "project": project,
            "claude_response": result.get("output", ""),
            "error": result.get("error")
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "files": uploaded,
            "error": str(e)
        })


@app.route('/api/project/create', methods=['POST'])
def create_project():
    """Create a new project with optional template"""
    data = request.get_json()
    name = data.get('name', '')
    template = data.get('template', 'empty')
    description = data.get('description', '')

    if not name:
        return jsonify({"error": "Project name required"}), 400

    # Sanitize name
    safe_name = "".join(c if c.isalnum() or c in '-_' else '-' for c in name)
    project_dir = os.path.join(PROJECTS_DIR, safe_name)

    if os.path.exists(project_dir):
        return jsonify({"error": "Project already exists"}), 409

    os.makedirs(project_dir, exist_ok=True)

    # Create based on template
    if template == 'python':
        os.makedirs(os.path.join(project_dir, 'src'), exist_ok=True)
        with open(os.path.join(project_dir, 'README.md'), 'w') as f:
            f.write(f"# {name}\n\n{description}\n")
        with open(os.path.join(project_dir, 'requirements.txt'), 'w') as f:
            f.write("# Add dependencies here\n")
        with open(os.path.join(project_dir, 'src', 'main.py'), 'w') as f:
            f.write('#!/usr/bin/env python3\n\ndef main():\n    pass\n\nif __name__ == "__main__":\n    main()\n')

    elif template == 'node':
        os.makedirs(os.path.join(project_dir, 'src'), exist_ok=True)
        with open(os.path.join(project_dir, 'README.md'), 'w') as f:
            f.write(f"# {name}\n\n{description}\n")
        with open(os.path.join(project_dir, 'package.json'), 'w') as f:
            json.dump({
                "name": safe_name,
                "version": "1.0.0",
                "description": description,
                "main": "src/index.js",
                "scripts": {"start": "node src/index.js"}
            }, f, indent=2)
        with open(os.path.join(project_dir, 'src', 'index.js'), 'w') as f:
            f.write('console.log("Hello World");\n')

    elif template == 'web':
        for subdir in ['css', 'js', 'images']:
            os.makedirs(os.path.join(project_dir, subdir), exist_ok=True)
        with open(os.path.join(project_dir, 'index.html'), 'w') as f:
            f.write(f'<!DOCTYPE html>\n<html>\n<head>\n  <title>{name}</title>\n</head>\n<body>\n  <h1>{name}</h1>\n</body>\n</html>\n')

    else:  # empty
        with open(os.path.join(project_dir, 'README.md'), 'w') as f:
            f.write(f"# {name}\n\n{description}\n")

    return jsonify({
        "success": True,
        "name": safe_name,
        "path": project_dir,
        "template": template,
        "share_url": f"/projects/{safe_name}"
    })


@app.route('/api/projects', methods=['GET'])
def list_projects():
    """List all projects"""
    if not os.path.exists(PROJECTS_DIR):
        return jsonify({"projects": []})

    projects = []
    for name in os.listdir(PROJECTS_DIR):
        path = os.path.join(PROJECTS_DIR, name)
        if os.path.isdir(path):
            projects.append({
                "name": name,
                "path": path,
                "modified": os.path.getmtime(path),
                "file_count": sum(1 for _ in os.walk(path) for __ in _[2])
            })

    return jsonify({"projects": sorted(projects, key=lambda x: x['modified'], reverse=True)})


@app.route('/api/project/<name>', methods=['GET'])
def get_project(name):
    """Get project details"""
    project_dir = os.path.join(PROJECTS_DIR, name)
    if not os.path.exists(project_dir):
        return jsonify({"error": "Project not found"}), 404

    files = []
    for root, dirs, filenames in os.walk(project_dir):
        for f in filenames:
            filepath = os.path.join(root, f)
            relpath = os.path.relpath(filepath, project_dir)
            files.append({
                "name": f,
                "path": relpath,
                "size": os.path.getsize(filepath),
                "modified": os.path.getmtime(filepath)
            })

    return jsonify({
        "name": name,
        "path": project_dir,
        "files": files,
        "share_url": f"/projects/{name}"
    })


@app.route('/api/project/<name>/open', methods=['POST'])
def open_project_in_claude(name):
    """Send project to Claude for analysis/working"""
    project_dir = os.path.join(PROJECTS_DIR, name)
    if not os.path.exists(project_dir):
        return jsonify({"error": "Project not found"}), 404

    prompt = request.get_json().get('prompt', f'Open and analyze the project at {project_dir}')

    try:
        req = urllib.request.Request(
            "http://localhost:5001/v1/agent/execute",
            data=json.dumps({
                "prompt": prompt,
                "working_dir": project_dir
            }).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode())

        return jsonify({
            "success": True,
            "project": name,
            "path": project_dir,
            "claude_response": result.get("output", ""),
            "error": result.get("error")
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ============== Provider Registry API ==============

@app.route('/api/registry/providers', methods=['GET'])
def list_registered_providers():
    """List all registered providers"""
    return jsonify({
        "providers": orchestrator.list_providers()
    })


@app.route('/api/registry/providers', methods=['POST'])
def register_provider():
    """Register a new provider"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    name = data.get("name")
    if not name:
        return jsonify({"error": "Provider name required"}), 400

    # Remove name from config (it's the dict key)
    config = {k: v for k, v in data.items() if k != "name"}

    try:
        provider = orchestrator.register_provider(name, config)
        return jsonify({
            "success": True,
            "name": name,
            "provider": provider.to_dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/registry/providers/<name>', methods=['GET'])
def get_registered_provider(name):
    """Get a registered provider"""
    provider = orchestrator.get_provider(name)
    if provider:
        return jsonify({"name": name, "provider": provider.to_dict()})
    return jsonify({"error": "Provider not found"}), 404


@app.route('/api/registry/providers/<name>', methods=['DELETE'])
def delete_registered_provider(name):
    """Delete a registered provider"""
    if orchestrator.delete_provider(name):
        return jsonify({"success": True, "message": f"Provider '{name}' deleted"})
    return jsonify({"error": "Provider not found"}), 404


# ============== Orchestration API ==============

@app.route('/api/orchestrate', methods=['POST'])
def create_orchestration():
    """Create and start a multi-agent workflow"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    mode = data.get("mode", "parallel")
    tasks = data.get("tasks", [])
    options = data.get("options", {})
    workflow_id = data.get("workflow_id")

    if not tasks:
        return jsonify({"error": "No tasks provided"}), 400

    # Validate mode
    if mode not in ["parallel", "sequential", "dag"]:
        return jsonify({"error": f"Invalid mode: {mode}. Must be 'parallel', 'sequential', or 'dag'"}), 400

    # Validate tasks
    for i, task in enumerate(tasks):
        if "id" not in task:
            return jsonify({"error": f"Task {i} missing 'id'"}), 400
        if "prompt" not in task:
            return jsonify({"error": f"Task '{task.get('id', i)}' missing 'prompt'"}), 400

    try:
        workflow = orchestrator.create_workflow(
            mode=mode,
            tasks=tasks,
            options=options,
            workflow_id=workflow_id
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to create workflow: {str(e)}"}), 500

    # Execute in background thread
    thread = threading.Thread(
        target=orchestrator.execute_workflow,
        args=(workflow.id,)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        "workflow_id": workflow.id,
        "status": workflow.status.value,
        "created_at": workflow.created_at,
        "mode": mode,
        "task_count": len(tasks),
        "status_url": f"/api/orchestrate/{workflow.id}"
    })


@app.route('/api/orchestrate', methods=['GET'])
def list_orchestrations():
    """List all workflows"""
    workflows = orchestrator.list_workflows()
    # Sort by created_at descending
    workflows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({
        "count": len(workflows),
        "workflows": workflows
    })


@app.route('/api/orchestrate/<workflow_id>', methods=['GET'])
def get_orchestration(workflow_id):
    """Get workflow status and results"""
    workflow = orchestrator.get_workflow(workflow_id)
    if not workflow:
        return jsonify({"error": "Workflow not found"}), 404

    # Add merged output and artifacts for completed workflows
    if workflow.get("status") == "completed":
        workflow["merged_output"] = orchestrator.get_merged_output(workflow_id)
        workflow["artifacts"] = orchestrator.get_artifacts(workflow_id)

    return jsonify(workflow)


@app.route('/api/orchestrate/<workflow_id>', methods=['DELETE'])
def cancel_orchestration(workflow_id):
    """Cancel a running workflow"""
    if orchestrator.cancel_workflow(workflow_id):
        return jsonify({
            "success": True,
            "message": "Workflow cancelled",
            "workflow_id": workflow_id
        })
    return jsonify({
        "error": "Cannot cancel workflow. It may not exist or not be running."
    }), 400


@app.route('/api/orchestrate/<workflow_id>/output', methods=['GET'])
def get_orchestration_output(workflow_id):
    """Get merged output from a workflow"""
    workflow = orchestrator.get_workflow(workflow_id)
    if not workflow:
        return jsonify({"error": "Workflow not found"}), 404

    merged = orchestrator.get_merged_output(workflow_id)
    return jsonify({
        "workflow_id": workflow_id,
        "status": workflow.get("status"),
        "merged_output": merged
    })


@app.route('/api/orchestrate/<workflow_id>/artifacts', methods=['GET'])
def get_orchestration_artifacts(workflow_id):
    """Get artifacts from a workflow"""
    workflow = orchestrator.get_workflow(workflow_id)
    if not workflow:
        return jsonify({"error": "Workflow not found"}), 404

    artifacts = orchestrator.get_artifacts(workflow_id)
    return jsonify({
        "workflow_id": workflow_id,
        "artifacts": artifacts
    })


@app.route('/api/orchestrate/<workflow_id>', methods=['POST'])
def delete_completed_orchestration(workflow_id):
    """Delete a completed workflow from history"""
    workflow = orchestrator.get_workflow(workflow_id)
    if not workflow:
        return jsonify({"error": "Workflow not found"}), 404

    if workflow.get("status") in ["running", "pending"]:
        return jsonify({"error": "Cannot delete running or pending workflow"}), 400

    if orchestrator.delete_workflow(workflow_id):
        return jsonify({"success": True, "message": "Workflow deleted"})
    return jsonify({"error": "Failed to delete workflow"}), 500


# ============== Static Routes ==============

@app.route('/favicon.ico')
def favicon():
    return '', 204


if __name__ == '__main__':
    # Get port from environment or use default
    port = int(os.environ.get('FLASK_PORT', 5000))

    # Create directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('static/img', exist_ok=True)

    print(f"Starting Claude Onboarding Wizard on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
