FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV SEARXNG_BASE_URL=http://localhost:8888/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    openssh-server \
    sudo \
    ca-certificates \
    wget \
    samba \
    samba-common-bin \
    dialog \
    jq \
    python3 \
    python3-pip \
    python3-venv \
    python3-requests \
    python3-flask \
    python3-gunicorn \
    build-essential \
    libxslt-dev \
    libxml2-dev \
    libffi-dev \
    nginx \
    nginx-common \
    supervisor \
    ttyd \
    sshpass \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

# Install Node.js 20 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Install Claude Code globally
RUN npm install -g @anthropic-ai/claude-code

# Install MCP servers for Claude Code (only packages that exist)
RUN npm install -g \
    @modelcontextprotocol/server-filesystem \
    @modelcontextprotocol/server-github \
    @modelcontextprotocol/server-brave-search || true

# MCP servers can also be configured at runtime via mcp-servers.json

# Install Python MCP SDK and common MCP tools
RUN pip3 install --break-system-packages \
    mcp \
    fastmcp \
    flask-cors \
    flask-socketio \
    gunicorn \
    uvicorn \
    websocket-client

# Install Poetry for claude-code-openai-wrapper
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Clone and install claude-code-openai-wrapper
RUN cd /opt && \
    git clone https://github.com/RichardAtCT/claude-code-openai-wrapper && \
    cd claude-code-openai-wrapper && \
    poetry install --no-interaction

# Create wrapper config directory
RUN mkdir -p /home/claude/.claude-wrapper

# Configure SSH server (enables SFTP by default)
RUN mkdir -p /var/run/sshd \
    && sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Create claude user with sudo access
RUN useradd -m -s /bin/bash claude \
    && echo "claude:claude" | chpasswd \
    && adduser claude sudo

# Configure Samba user (same password as SSH)
RUN (echo "claude"; echo "claude") | smbpasswd -s -a claude

# Download SSHwifty prebuilt binary (latest release)
RUN wget -q https://github.com/nirui/sshwifty/releases/download/0.4.5-beta-release-prebuild/sshwifty_0.4.5-beta-release_linux_amd64.tar.gz \
    && tar -xzf sshwifty_0.4.5-beta-release_linux_amd64.tar.gz \
    && find . -maxdepth 1 -type f -name "sshwifty*" -executable -exec mv {} /usr/local/bin/sshwifty \; \
    && chmod +x /usr/local/bin/sshwifty \
    && rm -f sshwifty_0.4.5-beta-release_linux_amd64.tar.gz

# Install SearXNG
RUN useradd -m -s /bin/bash searxng \
    && mkdir -p /etc/searxng /var/log/searxng /var/cache/searxng \
    && chown -R searxng:searxng /etc/searxng /var/log/searxng /var/cache/searxng

# Install SearXNG via pip in virtual environment
RUN python3 -m venv /opt/searxng \
    && /opt/searxng/bin/pip install --upgrade pip \
    && /opt/searxng/bin/pip install searxng

# Setup nginx directories and config
RUN mkdir -p /var/log/nginx /var/lib/nginx/body /var/cache/nginx \
    && chown -R www-data:www-data /var/log/nginx /var/lib/nginx /var/cache/nginx

# Setup Flask app directory
RUN mkdir -p /home/claude/webapps/flask/templates \
    && mkdir -p /home/claude/webapps/flask/static/css \
    && mkdir -p /home/claude/webapps/flask/static/js \
    && mkdir -p /home/claude/webapps/static \
    && mkdir -p /home/claude/projects

# Setup MCP directory
RUN mkdir -p /home/claude/mcp-servers

# Copy configuration files
COPY sshwifty.conf.json /etc/sshwifty.conf.json
COPY smb.conf /etc/samba/smb.conf
COPY claude-setup.sh /usr/local/bin/claude-setup.sh
COPY searxng/settings.yml /etc/searxng/settings.yml
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx-default.conf /etc/nginx/sites-available/default
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY mcp-servers.json /opt/claude-config/mcp-servers.json
COPY entrypoint.sh /entrypoint.sh

# Copy Flask webapp files to /opt (will be copied to /home/claude at runtime if volume mount)
COPY webapps/flask/app.py /opt/webapps/flask/app.py
COPY webapps/flask/agent_api.py /opt/webapps/flask/agent_api.py
COPY webapps/flask/agent_mcp.py /opt/webapps/flask/agent_mcp.py
COPY webapps/flask/orchestrator.py /opt/webapps/flask/orchestrator.py
COPY webapps/flask/subagent_config.json /opt/webapps/flask/subagent_config.json
COPY webapps/flask/templates/index.html /opt/webapps/flask/templates/index.html
COPY webapps/flask/static/css/style.css /opt/webapps/flask/static/css/style.css

RUN chmod +x /entrypoint.sh /usr/local/bin/claude-setup.sh \
    && chmod +x /opt/webapps/flask/app.py \
    && chmod +x /opt/webapps/flask/agent_api.py \
    && chmod +x /opt/webapps/flask/agent_mcp.py \
    && chmod +x /opt/webapps/flask/orchestrator.py

# Create default Claude config directory
RUN mkdir -p /home/claude/.claude \
    && chown -R claude:claude /home/claude/.claude \
    && chown -R claude:claude /home/claude/webapps \
    && chown -R claude:claude /home/claude/mcp-servers \
    && chown -R claude:claude /home/claude/projects

# Environment variables for agent
ENV AGENT_PORT=5001
ENV FLASK_PORT=5000

# Create projects directory for Samba
RUN mkdir -p /home/claude/projects \
    && chown -R claude:claude /home/claude/projects

# Expose single port (nginx proxy) + SSH
# All services accessible via port 80:
#   /           - Flask UI
#   /v1/        - Claude Code OpenAI Wrapper (OpenAI/Anthropic compatible)
#   /wrapper/   - Wrapper landing page
#   /agent/     - Agent endpoints
#   /search/    - SearXNG
#   /ssh/       - SSHwifty
#   /health     - Health check
EXPOSE 80 22

WORKDIR /home/claude

CMD ["/entrypoint.sh"]
