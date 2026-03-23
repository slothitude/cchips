#!/usr/bin/env python3
"""
Multi-Agent Orchestration Engine
Enables parallel, sequential, and DAG-based agent workflows
Supports per-task provider configuration
"""

import os
import json
import uuid
import threading
import subprocess
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowMode(Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    DAG = "dag"


@dataclass
class Provider:
    type: str  # anthropic, zai, ollama, openrouter, etc.
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    default_model: Optional[str] = None

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Task:
    id: str
    prompt: str
    working_dir: str
    timeout: int = 300
    depends_on: List[str] = field(default_factory=list)
    context_from: List[str] = field(default_factory=list)
    provider: Optional[Provider] = None  # Per-task provider
    status: TaskStatus = TaskStatus.PENDING
    output: str = ""
    error: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    files_created: List[str] = field(default_factory=list)
    duration_seconds: Optional[float] = None

    def to_dict(self):
        result = {
            "id": self.id,
            "prompt": self.prompt,
            "working_dir": self.working_dir,
            "timeout": self.timeout,
            "depends_on": self.depends_on,
            "context_from": self.context_from,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "files_created": self.files_created,
            "duration_seconds": self.duration_seconds
        }
        if self.provider:
            result["provider"] = self.provider.to_dict()
        return result


@dataclass
class Workflow:
    id: str
    mode: WorkflowMode
    tasks: Dict[str, Task]
    options: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    workflow_id: Optional[str] = None  # User-provided workflow ID

    def to_dict(self):
        return {
            "id": self.id,
            "workflow_id": self.workflow_id or self.id,
            "mode": self.mode.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "options": self.options,
            "tasks": {k: v.to_dict() for k, v in self.tasks.items()}
        }


class Orchestrator:
    def __init__(self, agent_api_url: str = "http://localhost:5001"):
        self.agent_api_url = agent_api_url
        self.workflows: Dict[str, Workflow] = {}
        self.providers: Dict[str, Provider] = {}  # Provider registry
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._lock = threading.Lock()
        self._load_providers()

    def _load_providers(self):
        """Load registered providers from config"""
        config_file = os.path.expanduser("~/.claude/providers.json")
        if os.path.exists(config_file):
            try:
                with open(config_file) as f:
                    data = json.load(f)
                    for name, cfg in data.items():
                        self.providers[name] = Provider(**cfg)
            except Exception as e:
                print(f"Warning: Could not load providers: {e}")

    def _save_providers(self):
        """Persist providers to config file"""
        config_file = os.path.expanduser("~/.claude/providers.json")
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump({k: v.to_dict() for k, v in self.providers.items()}, f, indent=2)

    def register_provider(self, name: str, config: dict) -> Provider:
        """Register a new provider"""
        provider = Provider(**config)
        self.providers[name] = provider
        self._save_providers()
        return provider

    def get_provider(self, name: str) -> Optional[Provider]:
        """Get a registered provider by name"""
        return self.providers.get(name)

    def list_providers(self) -> Dict[str, dict]:
        """List all registered providers"""
        return {k: v.to_dict() for k, v in self.providers.items()}

    def delete_provider(self, name: str) -> bool:
        """Delete a registered provider"""
        if name in self.providers:
            del self.providers[name]
            self._save_providers()
            return True
        return False

    def _get_provider(self, provider_spec) -> Optional[Provider]:
        """Resolve provider spec to Provider object"""
        if provider_spec is None:
            return None

        if isinstance(provider_spec, str):
            # Reference to registered provider
            if provider_spec in self.providers:
                return self.providers[provider_spec]
            raise ValueError(f"Unknown provider: {provider_spec}")
        elif isinstance(provider_spec, dict):
            # Inline provider config
            return Provider(**provider_spec)
        return None

    def _execute_with_provider(self, task: Task, prompt: str) -> dict:
        """Execute task with specific provider using direct HTTP calls"""
        provider = task.provider

        if provider is None:
            # Use default agent API (current provider)
            try:
                response = requests.post(
                    f"{self.agent_api_url}/v1/agent/execute",
                    json={
                        "prompt": prompt,
                        "working_dir": task.working_dir,
                        "timeout": task.timeout
                    },
                    timeout=task.timeout + 30
                )
                return response.json()
            except requests.exceptions.RequestException as e:
                return {"success": False, "error": str(e), "output": ""}

        # Direct HTTP execution for each provider type
        if provider.type == "ollama":
            return self._execute_ollama(provider, prompt, task.timeout)
        elif provider.type == "anthropic":
            return self._execute_anthropic(provider, prompt, task.timeout)
        elif provider.type == "zai":
            return self._execute_zai(provider, prompt, task.timeout)
        elif provider.type == "openrouter":
            return self._execute_openrouter(provider, prompt, task.timeout)
        elif provider.type == "nvidia":
            return self._execute_nvidia(provider, prompt, task.timeout)
        else:
            return {"success": False, "error": f"Unsupported provider type: {provider.type}", "output": ""}

    def _execute_ollama(self, provider: Provider, prompt: str, timeout: int) -> dict:
        """Execute via Ollama API directly"""
        host = provider.host or "host.docker.internal"
        port = provider.port or 11434
        model = provider.default_model or "llama3"

        try:
            response = requests.post(
                f"http://{host}:{port}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                },
                timeout=timeout
            )
            if response.status_code == 200:
                data = response.json()
                output = data.get("message", {}).get("content", "")
                return {"success": True, "output": output, "error": ""}
            else:
                return {"success": False, "error": f"Ollama error: {response.status_code}", "output": ""}
        except Exception as e:
            return {"success": False, "error": str(e), "output": ""}

    def _execute_anthropic(self, provider: Provider, prompt: str, timeout: int) -> dict:
        """Execute via Anthropic API directly"""
        import urllib.request
        model = provider.default_model or "claude-sonnet-4-6-20250929"

        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": provider.api_key or "",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                data=json.dumps({
                    "model": model,
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}]
                }).encode()
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                output = data.get("content", [{}])[0].get("text", "")
                return {"success": True, "output": output, "error": ""}
        except Exception as e:
            return {"success": False, "error": str(e), "output": ""}

    def _execute_zai(self, provider: Provider, prompt: str, timeout: int) -> dict:
        """Execute via Z.AI API (Anthropic-compatible)"""
        import urllib.request
        model = provider.default_model or "glm-4.7"

        try:
            req = urllib.request.Request(
                "https://api.z.ai/api/anthropic/v1/messages",
                headers={
                    "x-api-key": provider.api_key or "",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                data=json.dumps({
                    "model": model,
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}]
                }).encode()
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                output = data.get("content", [{}])[0].get("text", "")
                return {"success": True, "output": output, "error": ""}
        except Exception as e:
            return {"success": False, "error": str(e), "output": ""}

    def _execute_openrouter(self, provider: Provider, prompt: str, timeout: int) -> dict:
        """Execute via OpenRouter API"""
        model = provider.default_model or "anthropic/claude-sonnet"

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {provider.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=timeout
            )
            if response.status_code == 200:
                data = response.json()
                output = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"success": True, "output": output, "error": ""}
            else:
                return {"success": False, "error": f"OpenRouter error: {response.status_code}", "output": ""}
        except Exception as e:
            return {"success": False, "error": str(e), "output": ""}

    def _execute_nvidia(self, provider: Provider, prompt: str, timeout: int) -> dict:
        """Execute via NVIDIA NIM API"""
        model = provider.default_model or "meta/llama-3.1-8b-instruct"

        try:
            response = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {provider.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0.7
                },
                timeout=timeout
            )
            if response.status_code == 200:
                data = response.json()
                output = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"success": True, "output": output, "error": ""}
            else:
                return {"success": False, "error": f"NVIDIA error: {response.status_code}", "output": ""}
        except Exception as e:
            return {"success": False, "error": str(e), "output": ""}

    def create_workflow(self, mode: str, tasks: List[dict], options: dict = None,
                        workflow_id: str = None) -> Workflow:
        """Create a new workflow"""
        wf_id = workflow_id or str(uuid.uuid4())[:8]
        task_dict = {}

        for t in tasks:
            # Resolve provider
            provider = None
            if "provider" in t:
                provider = self._get_provider(t["provider"])

            task = Task(
                id=t["id"],
                prompt=t["prompt"],
                working_dir=t.get("working_dir", "/home/claude/projects"),
                timeout=t.get("timeout", 300),
                depends_on=t.get("depends_on", []),
                context_from=t.get("context_from", []),
                provider=provider
            )
            task_dict[t["id"]] = task

        workflow = Workflow(
            id=wf_id,
            workflow_id=workflow_id,
            mode=WorkflowMode(mode),
            tasks=task_dict,
            options=options or {}
        )

        with self._lock:
            self.workflows[wf_id] = workflow

        return workflow

    def execute_workflow(self, workflow_id: str) -> None:
        """Execute a workflow"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return

        workflow.status = TaskStatus.RUNNING
        workflow.started_at = datetime.now().isoformat()

        if workflow.mode == WorkflowMode.PARALLEL:
            self._execute_parallel(workflow)
        elif workflow.mode == WorkflowMode.SEQUENTIAL:
            self._execute_sequential(workflow)
        elif workflow.mode == WorkflowMode.DAG:
            self._execute_dag(workflow)

        # Determine final status
        all_completed = all(t.status == TaskStatus.COMPLETED for t in workflow.tasks.values())
        any_failed = any(t.status == TaskStatus.FAILED for t in workflow.tasks.values())

        if all_completed:
            workflow.status = TaskStatus.COMPLETED
        elif any_failed:
            workflow.status = TaskStatus.FAILED
        else:
            workflow.status = TaskStatus.CANCELLED

        workflow.completed_at = datetime.now().isoformat()

    def _execute_task(self, workflow: Workflow, task: Task, context: dict = None) -> Task:
        """Execute a single task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        start_time = datetime.now()

        # Build prompt with context from previous tasks
        prompt = task.prompt
        if context:
            context_str = "\n\n".join([
                f"[{tid}]: {workflow.tasks[tid].output}"
                for tid in task.context_from
                if tid in workflow.tasks and workflow.tasks[tid].output
            ])
            if context_str:
                prompt = f"Context from previous tasks:\n{context_str}\n\nCurrent task: {task.prompt}"

        try:
            result = self._execute_with_provider(task, prompt)
            task.output = result.get("output", "")
            task.error = result.get("error", "")
            if result.get("files_created"):
                task.files_created = result["files_created"]
            task.status = TaskStatus.FAILED if task.error else TaskStatus.COMPLETED
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED

        task.completed_at = datetime.now().isoformat()
        task.duration_seconds = (datetime.now() - start_time).total_seconds()
        return task

    def _execute_parallel(self, workflow: Workflow) -> None:
        """Execute all tasks in parallel"""
        futures = {}
        for task_id, task in workflow.tasks.items():
            future = self.executor.submit(self._execute_task, workflow, task, {})
            futures[future] = task_id

        for future in as_completed(futures):
            task_id = futures[future]
            try:
                future.result()
            except Exception as e:
                workflow.tasks[task_id].error = str(e)
                workflow.tasks[task_id].status = TaskStatus.FAILED

    def _execute_sequential(self, workflow: Workflow) -> None:
        """Execute tasks sequentially"""
        context = {}
        for task_id, task in workflow.tasks.items():
            self._execute_task(workflow, task, context)
            context[task_id] = task.output
            if task.status == TaskStatus.FAILED and workflow.options.get("stop_on_failure", True):
                # Cancel remaining tasks
                for tid, t in workflow.tasks.items():
                    if t.status == TaskStatus.PENDING:
                        t.status = TaskStatus.CANCELLED
                break

    def _execute_dag(self, workflow: Workflow) -> None:
        """Execute tasks as a DAG based on dependencies"""
        completed = set()
        context = {}

        while len(completed) < len(workflow.tasks):
            # Find tasks ready to run (all dependencies satisfied)
            ready = [
                t for t in workflow.tasks.values()
                if t.status == TaskStatus.PENDING
                and all(d in completed for d in t.depends_on)
            ]

            if not ready:
                # Check for remaining pending tasks (dependency cycle or failed deps)
                pending = [t for t in workflow.tasks.values() if t.status == TaskStatus.PENDING]
                if pending:
                    for t in pending:
                        t.status = TaskStatus.CANCELLED
                        t.error = "Dependency failed or cycle detected"
                break

            max_parallel = workflow.options.get("max_parallel", 3)
            batch = ready[:max_parallel]

            futures = {}
            for task in batch:
                future = self.executor.submit(self._execute_task, workflow, task, context)
                futures[future] = task.id

            for future in as_completed(futures):
                task_id = futures[future]
                try:
                    future.result()
                    if workflow.tasks[task_id].status == TaskStatus.COMPLETED:
                        completed.add(task_id)
                        context[task_id] = workflow.tasks[task_id].output
                    else:
                        # Task failed
                        if workflow.options.get("stop_on_failure", True):
                            # Cancel remaining
                            for tid, t in workflow.tasks.items():
                                if t.status == TaskStatus.PENDING:
                                    t.status = TaskStatus.CANCELLED
                            return
                except Exception as e:
                    workflow.tasks[task_id].error = str(e)
                    workflow.tasks[task_id].status = TaskStatus.FAILED
                    if workflow.options.get("stop_on_failure", True):
                        return

    def get_workflow(self, workflow_id: str) -> Optional[dict]:
        """Get workflow by ID"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return None

        result = workflow.to_dict()

        # Add merged output for completed workflows
        if workflow.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            result["merged_output"] = self.get_merged_output(workflow_id)

        return result

    def list_workflows(self) -> List[dict]:
        """List all workflows"""
        return [w.to_dict() for w in self.workflows.values()]

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        workflow = self.workflows.get(workflow_id)
        if not workflow or workflow.status != TaskStatus.RUNNING:
            return False

        workflow.status = TaskStatus.CANCELLED
        for task in workflow.tasks.values():
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED

        return True

    def retry_task(self, workflow_id: str, task_id: str = None) -> Optional[dict]:
        """Retry failed task(s) in a workflow"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return None

        if task_id:
            # Retry specific task
            task = workflow.tasks.get(task_id)
            if task and task.status == TaskStatus.FAILED:
                task.status = TaskStatus.PENDING
                task.error = ""
                task.output = ""
                # Re-execute in thread
                self.executor.submit(self._execute_task, workflow, task, {})
                return task.to_dict()
        else:
            # Retry all failed tasks
            retried = []
            for tid, task in workflow.tasks.items():
                if task.status == TaskStatus.FAILED:
                    task.status = TaskStatus.PENDING
                    task.error = ""
                    task.output = ""
                    self.executor.submit(self._execute_task, workflow, task, {})
                    retried.append(tid)

            if retried:
                # Update workflow status if we retried
                if workflow.status == TaskStatus.FAILED:
                    workflow.status = TaskStatus.RUNNING
                return {"status": "retrying", "tasks": retried}

        return None

    def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow"""
        workflow = self.workflows.get(workflow_id)
        if not workflow or workflow.status != TaskStatus.RUNNING:
            return False

        # Mark workflow as pending (paused)
        workflow.status = TaskStatus.PENDING
        return True

    def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow"""
        workflow = self.workflows.get(workflow_id)
        if not workflow or workflow.status != TaskStatus.PENDING:
            return False

        # Check if there are pending tasks
        has_pending = any(t.status == TaskStatus.PENDING for t in workflow.tasks.values())
        if not has_pending:
            return False

        # Re-execute with remaining tasks
        thread = threading.Thread(target=self.execute_workflow, args=(workflow_id,))
        thread.daemon = True
        thread.start()
        return True

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow from history"""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            return True
        return False

    def get_merged_output(self, workflow_id: str) -> str:
        """Get merged output from all completed tasks"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return ""

        outputs = []
        for task_id, task in workflow.tasks.items():
            if task.status == TaskStatus.COMPLETED and task.output:
                outputs.append(f"=== {task_id} ===\n{task.output}")

        return "\n\n".join(outputs)

    def get_artifacts(self, workflow_id: str) -> dict:
        """Get all artifacts (files created/modified) from workflow"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {"files_created": [], "files_modified": []}

        files_created = []
        files_modified = []

        for task in workflow.tasks.values():
            if task.files_created:
                files_created.extend(task.files_created)

        return {
            "files_created": list(set(files_created)),
            "files_modified": list(set(files_modified))
        }


# Global orchestrator instance
orchestrator = Orchestrator()
