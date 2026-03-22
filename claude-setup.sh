#!/bin/bash
# Claude Code LLM Provider Setup
# Automatically fetches available FREE models from providers

CONFIG_FILE="$HOME/.claude/settings.json"

# Colors for better UI
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

show_banner() {
    clear
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                           ║${NC}"
    echo -e "${BLUE}║        ${YELLOW}Claude Code - LLM Provider Setup${BLUE}                  ║${NC}"
    echo -e "${BLUE}║                                                           ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Local SearXNG Search: http://localhost:8888${NC}"
    echo -e "${CYAN}JSON API: curl 'http://localhost:8888/search?q=test&format=json'${NC}"
    echo ""
}

show_menu() {
    echo -e "${GREEN}Select your LLM Provider:${NC}"
    echo ""
    echo "  1) Z.AI (GLM Coding Plan - Recommended)"
    echo "  2) OpenRouter (Fetch FREE models)"
    echo "  3) NVIDIA NIM (Fetch available models)"
    echo "  4) Ollama (Local models)"
    echo "  5) Custom (Enter your own API settings)"
    echo "  6) Show Current Configuration"
    echo "  7) Test SearXNG Search"
    echo "  8) Exit"
    echo ""
    echo -n "Enter choice [1-8]: "
}

# Z.AI Static Model List (GLM Coding Plan)
get_zai_models() {
    echo "glm-4.5-air|GLM-4.5-Air (Fast, Efficient)"
    echo "glm-4.7|GLM-4.7 (Balanced)"
    echo "glm-5|GLM-5 (Latest, Max users)"
}

# Fetch OpenRouter FREE models
fetch_openrouter_free_models() {
    local API_KEY="$1"
    echo -e "${YELLOW}Fetching FREE models from OpenRouter...${NC}"
    echo ""

    response=$(curl -s -H "Authorization: Bearer $API_KEY" \
        "https://openrouter.ai/api/v1/models" 2>/dev/null)

    if [ $? -eq 0 ] && [ -n "$response" ]; then
        # Filter FREE models (pricing.prompt == "0")
        echo "$response" | jq -r '
            .data[] |
            select(.pricing.prompt == "0") |
            "\(.id)|\(.name) [FREE]"
        ' 2>/dev/null | sort
    fi
}

# Fetch NVIDIA NIM models
fetch_nvidia_models() {
    local API_KEY="$1"
    echo -e "${YELLOW}Fetching available models from NVIDIA NIM...${NC}"
    echo ""

    response=$(curl -s -H "Authorization: Bearer $API_KEY" \
        "https://integrate.api.nvidia.com/v1/models" 2>/dev/null)

    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo "$response" | jq -r '.data[] | "\(.id)|\(.id)"' 2>/dev/null | sort
    fi
}

# Fetch Ollama local models
fetch_ollama_models() {
    local HOST="$1"
    local PORT="$2"
    echo -e "${YELLOW}Fetching local Ollama models from ${HOST}:${PORT}...${NC}"
    echo ""

    response=$(curl -s "http://${HOST}:${PORT}/api/tags" 2>/dev/null)

    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo "$response" | jq -r '.models[] | "\(.name)|\(.name) (Local)"' 2>/dev/null
    fi
}

# Display model selection menu
select_model() {
    local models="$1"
    local title="$2"

    echo ""
    echo -e "${CYAN}=== $title ===${NC}"
    echo ""

    # Number the models
    local i=1
    declare -A model_map

    while IFS='|' read -r model_id model_name; do
        if [ -n "$model_id" ]; then
            printf "  %2d) %s\n" "$i" "$model_name"
            model_map[$i]="$model_id"
            ((i++))
        fi
    done <<< "$models"

    echo ""
    echo -n "Select model [1-$((i-1))]: "
    read selection

    if [ -n "${model_map[$selection]}" ]; then
        echo "${model_map[$selection]}"
    else
        echo ""
    fi
}

configure_zai() {
    echo ""
    echo -e "${YELLOW}Configuring Z.AI (GLM Coding Plan)...${NC}"
    echo ""
    echo -e "${CYAN}Get your API Key from: https://z.ai/manage-apikey/apikey-list${NC}"
    echo ""
    echo -n "Enter your Z.AI API Key: "
    read -s API_KEY
    echo ""

    # Show available models
    models=$(get_zai_models)
    MODEL=$(select_model "$models" "Z.AI GLM Models")

    if [ -z "$MODEL" ]; then
        MODEL="glm-4.7"
    fi

    # Set model variants based on selection
    case "$MODEL" in
        glm-5)
            HAIKU_MODEL="glm-5"
            SONNET_MODEL="glm-5"
            OPUS_MODEL="glm-5"
            ;;
        glm-4.5-air)
            HAIKU_MODEL="glm-4.5-air"
            SONNET_MODEL="glm-4.7"
            OPUS_MODEL="glm-4.7"
            ;;
        *)
            HAIKU_MODEL="glm-4.5-air"
            SONNET_MODEL="glm-4.7"
            OPUS_MODEL="glm-4.7"
            ;;
    esac

    mkdir -p "$HOME/.claude"

    cat > "$CONFIG_FILE" << EOF
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "$API_KEY",
    "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
    "API_TIMEOUT_MS": "3000000",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "$HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "$SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "$OPUS_MODEL"
  }
}
EOF

    echo "$API_KEY" > "$HOME/.claude/.api_key"

    echo -e "${GREEN}✓ Z.AI configured successfully!${NC}"
    echo -e "  Base URL: https://api.z.ai/api/anthropic"
    echo -e "  Models: $HAIKU_MODEL (Haiku), $SONNET_MODEL (Sonnet/Opus)"
    echo ""
    echo -e "Run ${YELLOW}claude${NC} to start using Claude Code with Z.AI."
}

configure_openrouter() {
    echo ""
    echo -e "${YELLOW}Configuring OpenRouter...${NC}"
    echo ""
    echo -e "${CYAN}Get your API Key from: https://openrouter.ai/keys${NC}"
    echo ""
    echo -n "Enter your OpenRouter API Key: "
    read -s API_KEY
    echo ""

    # Fetch FREE models
    models=$(fetch_openrouter_free_models "$API_KEY")

    if [ -z "$models" ]; then
        echo -e "${RED}Could not fetch models. Using known free models.${NC}"
        models="meta-llama/llama-3.2-3b-instruct:free|Llama 3.2 3B [FREE]
meta-llama/llama-3.2-1b-instruct:free|Llama 3.2 1B [FREE]
mistralai/mistral-7b-instruct:free|Mistral 7B [FREE]
google/gemma-2-9b-it:free|Gemma 2 9B [FREE]
qwen/qwen-2-7b-instruct:free|Qwen 2 7B [FREE]
huggingfaceh4/zephyr-7b-beta:free|Zephyr 7B [FREE]
openchat/openchat-7b:free|OpenChat 7B [FREE]"
    fi

    MODEL=$(select_model "$models" "OpenRouter FREE Models")

    if [ -z "$MODEL" ]; then
        MODEL="meta-llama/llama-3.2-3b-instruct:free"
    fi

    mkdir -p "$HOME/.claude"

    cat > "$CONFIG_FILE" << EOF
{
  "env": {
    "ANTHROPIC_API_KEY": "$API_KEY",
    "ANTHROPIC_BASE_URL": "https://openrouter.ai/api/v1",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "$MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "$MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "$MODEL"
  }
}
EOF

    echo "$API_KEY" > "$HOME/.claude/.api_key"

    echo -e "${GREEN}✓ OpenRouter configured successfully!${NC}"
    echo -e "  Model: $MODEL"
    echo ""
    echo -e "Run ${YELLOW}claude${NC} to start using Claude Code with OpenRouter."
}

configure_nvidia() {
    echo ""
    echo -e "${YELLOW}Configuring NVIDIA NIM...${NC}"
    echo ""
    echo -e "${CYAN}Get your API Key from: https://build.nvidia.com/${NC}"
    echo ""
    echo -n "Enter your NVIDIA API Key: "
    read -s API_KEY
    echo ""

    # Fetch available models
    models=$(fetch_nvidia_models "$API_KEY")

    if [ -z "$models" ]; then
        echo -e "${RED}Could not fetch models. Using defaults.${NC}"
        models="meta/llama-3.1-405b-instruct|Llama 3.1 405B
meta/llama-3.1-70b-instruct|Llama 3.1 70B
meta/llama-3.1-8b-instruct|Llama 3.1 8B
mistralai/mixtral-8x7b-instruct-v0.1|Mixtral 8x7B
moonshotai/kimi-k2.5|Kimi K2.5
google/gemma-2-9b-it|Gemma 2 9B
microsoft/phi-3-mini-128k-instruct|Phi-3 Mini"
    fi

    MODEL=$(select_model "$models" "NVIDIA NIM Available Models")

    if [ -z "$MODEL" ]; then
        MODEL="meta/llama-3.1-70b-instruct"
    fi

    mkdir -p "$HOME/.claude"

    cat > "$CONFIG_FILE" << EOF
{
  "env": {
    "ANTHROPIC_API_KEY": "$API_KEY",
    "ANTHROPIC_BASE_URL": "https://integrate.api.nvidia.com/v1",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "$MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "$MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "$MODEL"
  }
}
EOF

    echo "$API_KEY" > "$HOME/.claude/.api_key"

    echo -e "${GREEN}✓ NVIDIA NIM configured successfully!${NC}"
    echo -e "  Model: $MODEL"
    echo ""
    echo -e "Run ${YELLOW}claude${NC} to start using Claude Code with NVIDIA."
}

configure_ollama() {
    echo ""
    echo -e "${YELLOW}Configuring Ollama (Local)...${NC}"
    echo ""

    echo -n "Enter Ollama host (default: host.docker.internal): "
    read OLLAMA_HOST
    OLLAMA_HOST=${OLLAMA_HOST:-host.docker.internal}

    echo -n "Enter Ollama port (default: 11434): "
    read OLLAMA_PORT
    OLLAMA_PORT=${OLLAMA_PORT:-11434}

    # Fetch local models
    models=$(fetch_ollama_models "$OLLAMA_HOST" "$OLLAMA_PORT")

    if [ -z "$models" ]; then
        echo -e "${RED}Could not fetch models. Make sure Ollama is running.${NC}"
        echo ""
        echo -n "Enter model name manually (e.g., llama3.1, codellama): "
        read MODEL
    else
        MODEL=$(select_model "$models" "Ollama Local Models")
    fi

    MODEL=${MODEL:-llama3.1}

    mkdir -p "$HOME/.claude"

    cat > "$CONFIG_FILE" << EOF
{
  "env": {
    "ANTHROPIC_API_KEY": "ollama",
    "ANTHROPIC_BASE_URL": "http://${OLLAMA_HOST}:${OLLAMA_PORT}/v1",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "$MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "$MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "$MODEL"
  }
}
EOF

    echo "ollama" > "$HOME/.claude/.api_key"

    echo -e "${GREEN}✓ Ollama configured successfully!${NC}"
    echo -e "  Host: ${OLLAMA_HOST}:${OLLAMA_PORT}"
    echo -e "  Model: $MODEL"
    echo ""
    echo -e "Run ${YELLOW}claude${NC} to start using Claude Code with Ollama."
}

configure_custom() {
    echo ""
    echo -e "${YELLOW}Custom Configuration...${NC}"
    echo ""
    echo -n "Enter API Key: "
    read -s API_KEY
    echo ""
    echo -n "Enter API Base URL: "
    read BASE_URL
    echo -n "Enter Haiku model name: "
    read HAIKU_MODEL
    echo -n "Enter Sonnet model name: "
    read SONNET_MODEL
    echo -n "Enter Opus model name: "
    read OPUS_MODEL

    mkdir -p "$HOME/.claude"

    cat > "$CONFIG_FILE" << EOF
{
  "env": {
    "ANTHROPIC_API_KEY": "$API_KEY",
    "ANTHROPIC_BASE_URL": "$BASE_URL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "$HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "$SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "$OPUS_MODEL"
  }
}
EOF

    echo "$API_KEY" > "$HOME/.claude/.api_key"

    echo -e "${GREEN}✓ Custom configuration saved!${NC}"
}

show_current_config() {
    echo ""
    echo -e "${YELLOW}Current Configuration:${NC}"
    echo ""

    if [ -f "$CONFIG_FILE" ]; then
        echo "Config file: $CONFIG_FILE"
        echo ""
        cat "$CONFIG_FILE" | jq . 2>/dev/null || cat "$CONFIG_FILE"
        echo ""

        # Show which provider based on base URL
        BASE_URL=$(cat "$CONFIG_FILE" | jq -r '.env.ANTHROPIC_BASE_URL' 2>/dev/null)
        case "$BASE_URL" in
            *z.ai*) echo -e "Provider: ${GREEN}Z.AI${NC}" ;;
            *openrouter*) echo -e "Provider: ${GREEN}OpenRouter${NC}" ;;
            *nvidia*) echo -e "Provider: ${GREEN}NVIDIA NIM${NC}" ;;
            *11434*|*ollama*) echo -e "Provider: ${GREEN}Ollama (Local)${NC}" ;;
            *) echo -e "Provider: ${GREEN}Custom${NC}" ;;
        esac
    else
        echo -e "${RED}No configuration found. Run setup first.${NC}"
    fi
    echo ""
}

test_searxng() {
    echo ""
    echo -e "${YELLOW}Testing SearXNG Search...${NC}"
    echo ""

    echo -n "Enter search query: "
    read query

    if [ -z "$query" ]; then
        query="claude code ai"
    fi

    echo ""
    echo -e "${CYAN}Searching for: $query${NC}"
    echo ""

    # Test JSON API
    result=$(curl -s "http://localhost:8888/search?q=$(echo "$query" | sed 's/ /+/g')&format=json" 2>/dev/null)

    if [ $? -eq 0 ] && [ -n "$result" ]; then
        echo -e "${GREEN}✓ SearXNG is working!${NC}"
        echo ""
        echo "Results (first 3):"
        echo "$result" | jq -r '.results[:3][] | "  • \(.title)\n    \(.url)\n"' 2>/dev/null || echo "$result"
    else
        echo -e "${RED}✗ SearXNG is not responding.${NC}"
        echo "  Make sure SearXNG is running on port 8888"
    fi
    echo ""
}

# Main loop
while true; do
    show_banner
    show_menu
    read choice

    case $choice in
        1) configure_zai ;;
        2) configure_openrouter ;;
        3) configure_nvidia ;;
        4) configure_ollama ;;
        5) configure_custom ;;
        6) show_current_config ;;
        7) test_searxng ;;
        8)
            echo ""
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option. Please try again.${NC}"
            ;;
    esac

    echo ""
    echo -n "Press Enter to continue..."
    read
done
