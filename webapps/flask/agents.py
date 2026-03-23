#!/usr/bin/env python3
"""
Agent Registry for CChips
Manages custom agent configurations with skills
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

AGENTS_DIR = os.path.expanduser("~/.claude/agents")
SKILLS_DIR = os.path.expanduser("~/.claude/skills")


@dataclass
class Skill:
    id: str
    name: str
    description: str
    instructions: str
    triggers: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class Agent:
    id: str
    name: str
    description: str
    system_prompt: str
    version: str = "1.0.0"
    provider: Optional[str] = None
    model: Optional[str] = None
    tools: List[str] = field(default_factory=lambda: ["read", "write", "bash"])
    skills: List[str] = field(default_factory=list)
    workflow_template: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self):
        return asdict(self)


class AgentRegistry:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.skills: Dict[str, Skill] = {}
        os.makedirs(AGENTS_DIR, exist_ok=True)
        os.makedirs(SKILLS_DIR, exist_ok=True)
        self._load_all()

    def _load_all(self):
        """Load all agents and skills from disk"""
        # Load agents
        if os.path.exists(AGENTS_DIR):
            for filename in os.listdir(AGENTS_DIR):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(AGENTS_DIR, filename)) as f:
                            data = json.load(f)
                            self.agents[data['id']] = Agent(**data)
                    except Exception as e:
                        print(f"Error loading agent {filename}: {e}")

        # Load skills
        if os.path.exists(SKILLS_DIR):
            for filename in os.listdir(SKILLS_DIR):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(SKILLS_DIR, filename)) as f:
                            data = json.load(f)
                            self.skills[data['id']] = Skill(**data)
                    except Exception as e:
                        print(f"Error loading skill {filename}: {e}")

    def create_agent(self, config: dict) -> Agent:
        """Create a new agent"""
        agent_id = config.get('id') or str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        agent = Agent(
            id=agent_id,
            name=config.get('name', 'New Agent'),
            description=config.get('description', ''),
            system_prompt=config.get('system_prompt', ''),
            version=config.get('version', '1.0.0'),
            provider=config.get('provider'),
            model=config.get('model'),
            tools=config.get('tools', ['read', 'write', 'bash']),
            skills=config.get('skills', []),
            workflow_template=config.get('workflow_template', {}),
            created_at=config.get('created_at', now),
            updated_at=now
        )

        self.agents[agent_id] = agent
        self._save_agent(agent)
        return agent

    def update_agent(self, agent_id: str, config: dict) -> Optional[Agent]:
        """Update an existing agent"""
        if agent_id not in self.agents:
            return None

        agent = self.agents[agent_id]
        for key, value in config.items():
            if hasattr(agent, key) and key not in ['id', 'created_at']:
                setattr(agent, key, value)
        agent.updated_at = datetime.now().isoformat()

        self._save_agent(agent)
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent"""
        if agent_id not in self.agents:
            return False

        del self.agents[agent_id]
        filepath = os.path.join(AGENTS_DIR, f"{agent_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
        return True

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID"""
        return self.agents.get(agent_id)

    def list_agents(self) -> List[Agent]:
        """List all agents"""
        return list(self.agents.values())

    def _save_agent(self, agent: Agent):
        """Save agent to disk"""
        filepath = os.path.join(AGENTS_DIR, f"{agent.id}.json")
        with open(filepath, 'w') as f:
            json.dump(agent.to_dict(), f, indent=2)

    # Skill management
    def create_skill(self, config: dict) -> Skill:
        """Create a new skill"""
        skill_id = config.get('id') or str(uuid.uuid4())[:8]
        skill = Skill(
            id=skill_id,
            name=config.get('name', 'New Skill'),
            description=config.get('description', ''),
            instructions=config.get('instructions', ''),
            triggers=config.get('triggers', [])
        )
        self.skills[skill_id] = skill
        self._save_skill(skill)
        return skill

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID"""
        return self.skills.get(skill_id)

    def list_skills(self) -> List[Skill]:
        """List all skills"""
        return list(self.skills.values())

    def delete_skill(self, skill_id: str) -> bool:
        """Delete a skill"""
        if skill_id not in self.skills:
            return False
        del self.skills[skill_id]
        filepath = os.path.join(SKILLS_DIR, f"{skill_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
        return True

    def _save_skill(self, skill: Skill):
        """Save skill to disk"""
        filepath = os.path.join(SKILLS_DIR, f"{skill.id}.json")
        with open(filepath, 'w') as f:
            json.dump(skill.to_dict(), f, indent=2)

    def get_builtin_skills(self) -> List[dict]:
        """Get built-in skill templates"""
        return [
            {
                "id": "code-review",
                "name": "Code Review",
                "description": "Review code for quality and issues",
                "instructions": "Review the code for bugs, security issues, and best practices. Provide actionable feedback.",
                "triggers": ["review", "check code", "analyze"]
            },
            {
                "id": "security-analysis",
                "name": "Security Analysis",
                "description": "Analyze for security vulnerabilities",
                "instructions": "Check for OWASP Top 10 vulnerabilities including injection, XSS, CSRF, and authentication issues.",
                "triggers": ["security", "vulnerability", "cve", "exploit"]
            },
            {
                "id": "documentation",
                "name": "Documentation Generator",
                "description": "Generate documentation from code",
                "instructions": "Analyze code and generate comprehensive documentation including function descriptions, parameters, and examples.",
                "triggers": ["document", "docs", "readme"]
            },
            {
                "id": "testing",
                "name": "Test Generator",
                "description": "Generate unit tests for code",
                "instructions": "Analyze code and generate comprehensive unit tests covering edge cases and normal operation.",
                "triggers": ["test", "unit test", "coverage"]
            },
            {
                "id": "refactoring",
                "name": "Code Refactoring",
                "description": "Suggest code improvements",
                "instructions": "Analyze code structure and suggest improvements for readability, maintainability, and performance.",
                "triggers": ["refactor", "improve", "clean", "optimize"]
            }
        ]

    def get_builtin_agents(self) -> List[dict]:
        """Get built-in agent templates"""
        return [
            {
                "id": "general-assistant",
                "name": "General Assistant",
                "description": "A versatile AI assistant for general tasks",
                "system_prompt": "You are a helpful AI assistant. Provide clear, accurate, and helpful responses.",
                "tools": ["read", "write", "bash"],
                "skills": []
            },
            {
                "id": "code-reviewer",
                "name": "Code Reviewer",
                "description": "Expert code reviewer focusing on quality and security",
                "system_prompt": "You are an expert code reviewer. Analyze code for bugs, security issues, performance problems, and violations of best practices. Provide specific, actionable feedback.",
                "tools": ["read", "bash"],
                "skills": ["code-review", "security-analysis"]
            },
            {
                "id": "developer",
                "name": "Developer Agent",
                "description": "Full-stack developer for implementing features",
                "system_prompt": "You are an expert software developer. Write clean, efficient, well-documented code following best practices and design patterns.",
                "tools": ["read", "write", "edit", "bash"],
                "skills": ["testing", "documentation"]
            },
            {
                "id": "architect",
                "name": "Solution Architect",
                "description": "Design system architecture and patterns",
                "system_prompt": "You are a solution architect. Design scalable, maintainable system architectures. Consider trade-offs, patterns, and best practices.",
                "tools": ["read", "write"],
                "skills": ["documentation"]
            }
        ]


# Global registry instance
agent_registry = AgentRegistry()
