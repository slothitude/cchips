#!/usr/bin/env python3
"""
Skills and MCP Server Library for CChips
Manages installation, configuration, and updates
"""

import os
import json
import shutil
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

SKILLS_DIR = os.path.expanduser("~/.claude/skills")
MCP_CONFIG_FILE = os.path.expanduser("~/.claude/mcp-servers.json")
LIBRARY_CACHE_FILE = os.path.expanduser("~/.claude/library_cache.json")

# Remote catalog URL (can be customized)
CATALOG_URL = "https://raw.githubusercontent.com/anthropics/mcp-servers/main/catalog.json"


@dataclass
class SkillPackage:
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    installed: bool = False
    install_path: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class MCPServerPackage:
    id: str
    name: str
    description: str
    npm_package: str
    version: str = "latest"
    author: str = ""
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    config_template: Dict[str, Any] = field(default_factory=dict)
    installed: bool = False

    def to_dict(self):
        return asdict(self)


class LibraryRegistry:
    def __init__(self):
        os.makedirs(SKILLS_DIR, exist_ok=True)
        self.skills_catalog: List[SkillPackage] = []
        self.mcp_catalog: List[MCPServerPackage] = []
        self.installed_skills: Dict[str, SkillPackage] = {}
        self.mcp_config: Dict[str, Any] = {}
        self._load_installed_skills()
        self._load_mcp_config()

    def _load_installed_skills(self):
        """Load installed skills from disk"""
        if not os.path.exists(SKILLS_DIR):
            return

        for skill_id in os.listdir(SKILLS_DIR):
            skill_path = os.path.join(SKILLS_DIR, skill_id)
            if os.path.isdir(skill_path):
                meta_file = os.path.join(skill_path, "skill.json")
                if os.path.exists(meta_file):
                    try:
                        with open(meta_file) as f:
                            data = json.load(f)
                            data['installed'] = True
                            data['install_path'] = skill_path
                            self.installed_skills[skill_id] = SkillPackage(**data)
                    except Exception as e:
                        print(f"Error loading skill {skill_id}: {e}")

    def _load_mcp_config(self):
        """Load current MCP server configuration"""
        if os.path.exists(MCP_CONFIG_FILE):
            try:
                with open(MCP_CONFIG_FILE) as f:
                    self.mcp_config = json.load(f)
            except:
                self.mcp_config = {"mcpServers": {}}
        else:
            self.mcp_config = {"mcpServers": {}}

    def fetch_catalog(self) -> dict:
        """Fetch remote catalog of available skills and MCP servers"""
        try:
            req = urllib.request.Request(CATALOG_URL)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"Failed to fetch catalog: {e}")
            return self._get_builtin_catalog()

    def _get_builtin_catalog(self) -> dict:
        """Return built-in catalog as fallback"""
        return {
            "skills": self._get_builtin_skills(),
            "mcp_servers": self._get_builtin_mcp_servers()
        }

    def _get_builtin_skills(self) -> List[dict]:
        """Built-in skill packages"""
        return [
            {
                "id": "code-review",
                "name": "Code Review",
                "description": "Review code for bugs, security issues, and best practices",
                "category": "development",
                "tags": ["review", "quality", "security"],
                "skill_content": "# Code Review\n\nUse this skill when reviewing code.\n\n## Steps\n1. Analyze code structure\n2. Identify bugs and edge cases\n3. Check security vulnerabilities\n4. Suggest improvements\n5. Verify coding standards"
            },
            {
                "id": "security-analysis",
                "name": "Security Analysis",
                "description": "Analyze code for OWASP Top 10 vulnerabilities",
                "category": "security",
                "tags": ["security", "owasp", "vulnerability"],
                "skill_content": "# Security Analysis\n\nAnalyze for security vulnerabilities.\n\n## Checklist\n- Injection (SQL, Command, LDAP)\n- Broken Authentication\n- Sensitive Data Exposure\n- XML External Entities\n- Broken Access Control\n- Security Misconfiguration\n- Cross-Site Scripting (XSS)\n- Insecure Deserialization\n- Using Components with Known Vulnerabilities\n- Insufficient Logging & Monitoring"
            },
            {
                "id": "documentation",
                "name": "Documentation Generator",
                "description": "Generate comprehensive documentation from code",
                "category": "documentation",
                "tags": ["docs", "readme", "api"],
                "skill_content": "# Documentation Generator\n\nGenerate documentation from code.\n\n## Output Includes\n- Function/method descriptions\n- Parameter documentation\n- Return value documentation\n- Usage examples\n- Edge cases and error handling"
            },
            {
                "id": "testing",
                "name": "Test Generator",
                "description": "Generate unit tests and integration tests",
                "category": "testing",
                "tags": ["test", "unit-test", "coverage"],
                "skill_content": "# Test Generator\n\nGenerate comprehensive tests.\n\n## Test Types\n- Unit tests for functions/methods\n- Integration tests for workflows\n- Edge case coverage\n- Error handling tests\n- Mock data generation"
            },
            {
                "id": "refactoring",
                "name": "Code Refactoring",
                "description": "Suggest code improvements and optimizations",
                "category": "development",
                "tags": ["refactor", "optimize", "clean-code"],
                "skill_content": "# Code Refactoring\n\nSuggest code improvements.\n\n## Areas to Analyze\n- Code duplication\n- Naming conventions\n- Function length and complexity\n- Design patterns\n- Performance optimizations\n- Maintainability improvements"
            },
            {
                "id": "git-workflow",
                "name": "Git Workflow",
                "description": "Help with git operations and workflows",
                "category": "version-control",
                "tags": ["git", "branch", "merge", "commit"],
                "skill_content": "# Git Workflow\n\nHelp with git operations.\n\n## Capabilities\n- Commit message generation\n- Branch strategy advice\n- Merge conflict resolution\n- Rebase assistance\n- Git history analysis"
            }
        ]

    def _get_builtin_mcp_servers(self) -> List[dict]:
        """Built-in MCP server packages"""
        return [
            {
                "id": "filesystem",
                "name": "Filesystem",
                "description": "File system operations with read, write, search",
                "npm_package": "@modelcontextprotocol/server-filesystem",
                "category": "files",
                "tags": ["files", "read", "write"],
                "config_template": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/claude/projects"]
                }
            },
            {
                "id": "github",
                "name": "GitHub",
                "description": "GitHub API integration for repos, issues, PRs",
                "npm_package": "@modelcontextprotocol/server-github",
                "category": "integration",
                "tags": ["github", "api", "git"],
                "config_template": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_TOKEN": ""}
                }
            },
            {
                "id": "postgres",
                "name": "PostgreSQL",
                "description": "Query and manage PostgreSQL databases",
                "npm_package": "@modelcontextprotocol/server-postgres",
                "category": "database",
                "tags": ["postgres", "sql", "database"],
                "config_template": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-postgres"],
                    "env": {"DATABASE_URL": "postgresql://localhost/mydb"}
                }
            },
            {
                "id": "sqlite",
                "name": "SQLite",
                "description": "Query and manage SQLite databases",
                "npm_package": "@modelcontextprotocol/server-sqlite",
                "category": "database",
                "tags": ["sqlite", "sql", "database"],
                "config_template": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-sqlite", "--db-path", "/path/to/db.sqlite"]
                }
            },
            {
                "id": "brave-search",
                "name": "Brave Search",
                "description": "Web search using Brave Search API",
                "npm_package": "@modelcontextprotocol/server-brave-search",
                "category": "search",
                "tags": ["search", "web", "api"],
                "config_template": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                    "env": {"BRAVE_API_KEY": ""}
                }
            },
            {
                "id": "puppeteer",
                "name": "Puppeteer",
                "description": "Browser automation and web scraping",
                "npm_package": "@modelcontextprotocol/server-puppeteer",
                "category": "browser",
                "tags": ["browser", "scraping", "automation"],
                "config_template": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
                }
            },
            {
                "id": "slack",
                "name": "Slack",
                "description": "Slack workspace integration",
                "npm_package": "@modelcontextprotocol/server-slack",
                "category": "communication",
                "tags": ["slack", "messaging", "api"],
                "config_template": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-slack"],
                    "env": {"SLACK_BOT_TOKEN": "", "SLACK_TEAM_ID": ""}
                }
            },
            {
                "id": "memory",
                "name": "Memory",
                "description": "Persistent memory storage for context",
                "npm_package": "@modelcontextprotocol/server-memory",
                "category": "utilities",
                "tags": ["memory", "storage", "context"],
                "config_template": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-memory"]
                }
            }
        ]

    def list_available_skills(self) -> List[dict]:
        """List all available skills (built-in + remote)"""
        catalog = self.fetch_catalog()
        skills = catalog.get("skills", self._get_builtin_skills())

        # Mark installed skills
        for skill in skills:
            skill['installed'] = skill['id'] in self.installed_skills

        return skills

    def list_available_mcp_servers(self) -> List[dict]:
        """List all available MCP servers"""
        catalog = self.fetch_catalog()
        servers = catalog.get("mcp_servers", self._get_builtin_mcp_servers())

        # Mark installed servers
        for server in servers:
            server['installed'] = server['id'] in self.mcp_config.get("mcpServers", {})

        return servers

    def install_skill(self, skill_id: str) -> bool:
        """Install a skill from the catalog"""
        catalog = self.fetch_catalog()
        skills = catalog.get("skills", self._get_builtin_skills())

        skill = next((s for s in skills if s['id'] == skill_id), None)
        if not skill:
            return False

        skill_path = os.path.join(SKILLS_DIR, skill_id)
        os.makedirs(skill_path, exist_ok=True)

        # Create skill.json
        meta = {k: v for k, v in skill.items() if k != 'skill_content'}
        with open(os.path.join(skill_path, "skill.json"), 'w') as f:
            json.dump(meta, f, indent=2)

        # Create SKILL.md
        skill_content = skill.get('skill_content', f"# {skill['name']}\n\n{skill['description']}")
        with open(os.path.join(skill_path, "SKILL.md"), 'w') as f:
            f.write(skill_content)

        # Update installed skills
        skill['installed'] = True
        skill['install_path'] = skill_path
        # Filter out skill_content for SkillPackage
        skill_meta = {k: v for k, v in skill.items() if k != 'skill_content'}
        self.installed_skills[skill_id] = SkillPackage(**skill_meta)

        return True

    def uninstall_skill(self, skill_id: str) -> bool:
        """Uninstall a skill"""
        if skill_id not in self.installed_skills:
            return False

        skill_path = os.path.join(SKILLS_DIR, skill_id)
        if os.path.exists(skill_path):
            shutil.rmtree(skill_path)

        del self.installed_skills[skill_id]
        return True

    def install_mcp_server(self, server_id: str, config_override: dict = None) -> bool:
        """Install an MCP server"""
        catalog = self.fetch_catalog()
        servers = catalog.get("mcp_servers", self._get_builtin_mcp_servers())

        server = next((s for s in servers if s['id'] == server_id), None)
        if not server:
            return False

        # Get config template
        config = server.get('config_template', {})
        if config_override:
            # Deep merge config
            config = {**config, **config_override}
            if 'env' in config_override and 'env' in server.get('config_template', {}):
                config['env'] = {**server['config_template']['env'], **config_override['env']}

        # Add to MCP config
        self.mcp_config["mcpServers"][server_id] = config

        # Save config
        os.makedirs(os.path.dirname(MCP_CONFIG_FILE), exist_ok=True)
        with open(MCP_CONFIG_FILE, 'w') as f:
            json.dump(self.mcp_config, f, indent=2)

        return True

    def uninstall_mcp_server(self, server_id: str) -> bool:
        """Uninstall an MCP server"""
        if server_id not in self.mcp_config.get("mcpServers", {}):
            return False

        del self.mcp_config["mcpServers"][server_id]

        with open(MCP_CONFIG_FILE, 'w') as f:
            json.dump(self.mcp_config, f, indent=2)

        return True

    def update_mcp_server_config(self, server_id: str, config: dict) -> bool:
        """Update configuration for an installed MCP server"""
        if server_id not in self.mcp_config.get("mcpServers", {}):
            return False

        self.mcp_config["mcpServers"][server_id] = config

        with open(MCP_CONFIG_FILE, 'w') as f:
            json.dump(self.mcp_config, f, indent=2)

        return True

    def get_installed_skills(self) -> List[SkillPackage]:
        """Get list of installed skills"""
        return list(self.installed_skills.values())

    def get_installed_mcp_servers(self) -> List[dict]:
        """Get list of installed MCP servers with their configs"""
        servers = []
        for server_id, config in self.mcp_config.get("mcpServers", {}).items():
            servers.append({
                "id": server_id,
                "config": config,
                "installed": True
            })
        return servers


# Global registry instance
library_registry = LibraryRegistry()
