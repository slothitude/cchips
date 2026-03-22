# Quick Launch Script for Claude Code Containers (PowerShell)
# Single port deployment - all services via nginx
#
# Usage:
#   .\launch-claude.ps1                    # Default: zai on port 80
#   .\launch-claude.ps1 -Provider openrouter -Port 8002
#   .\launch-claude.ps1 -Port 9000 -Token "secret123"

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("zai", "openrouter", "nvidia", "ollama", "custom")]
    [string]$Provider = "zai",

    [Parameter(Mandatory=$false)]
    [int]$Port = 80,

    [Parameter(Mandatory=$false)]
    [string]$Token = "",

    [Parameter(Mandatory=$false)]
    [switch]$NoSSH
)

$ProjectName = "claude-$Provider-$(if($Port -eq 80){'default'}else{$Port})"

Write-Host "========================================"
Write-Host "Claude Code Agent Launcher"
Write-Host "========================================"
Write-Host "Provider:  $Provider"
Write-Host "Port:      $Port"
Write-Host "Project:   $ProjectName"
Write-Host "SSH:       $(if($NoSSH){'Disabled'}else{'Enabled'})"
Write-Host ""

# Build if needed
$imageExists = docker images -q claude-sshwifty 2>$null
if ([string]::IsNullOrEmpty($imageExists)) {
    Write-Host "Building Docker image..."
    docker-compose build
}

# Set environment
$env:PORT = $Port
$env:AGENT_API_TOKEN = $Token
if ($NoSSH) {
    $env:SSH_PORT = "0"
}

# Launch
Write-Host "Launching container..."
docker-compose -p $ProjectName up -d

Write-Host ""
Write-Host "========================================"
Write-Host "Access URLs (all on port $Port):"
Write-Host "========================================"
Write-Host ""
Write-Host "  Web UI:        http://localhost:$Port/"
Write-Host "  Agent API:     http://localhost:$Port/v1/"
Write-Host "  Search:        http://localhost:$Port/search/"
Write-Host "  SSHwifty:      http://localhost:$Port/ssh/"
Write-Host "  Health:        http://localhost:$Port/health"
Write-Host ""
Write-Host "API Endpoints:"
Write-Host "  POST /v1/chat/completions   - OpenAI-compatible chat"
Write-Host "  POST /agent/execute         - Execute task"
Write-Host "  GET  /agent/status          - Agent status"
Write-Host ""
Write-Host "Python Example:"
Write-Host "  from openai import OpenAI"
Write-Host "  client = OpenAI(base_url='http://localhost:$Port/v1', api_key='dummy')"
Write-Host ""

if (-not $NoSSH) {
    $sshPort = 2200 + ($Port - 80)
    Write-Host "SSH: ssh claude@localhost -p $sshPort"
    Write-Host ""
}

Write-Host "To stop: docker-compose -p $ProjectName down"
Write-Host "========================================"

# Open browser
Start-Process "http://localhost:$Port"
