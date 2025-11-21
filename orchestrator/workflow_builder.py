"""Utilities to build and validate workflow plans end to end.

This module provides a small harness that mirrors the steps outlined in
integration-style tests:

1. Create a Python virtual environment and install dependencies.
2. Generate one or more task queries and produce Python workflow code for each.
3. Validate that the generated workflow code compiles and can be parsed into a
   :class:`~orchestrator.workflow.WorkflowDAG`.

The helpers lean on :class:`~orchestrator.planner.LLMOrchestrator` to produce
plans and validate they can be compiled into a workflow DAG.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from .planner import LLMOrchestrator, PlannedWorkflow
from .workflow import WorkflowDAG, WorkflowNode, parse_workflow_code


@dataclass
class WorkflowPlanResult:
    """Outcome of compiling and parsing a workflow plan."""

    query: str
    code: str
    compiled: bool
    dag: Optional[WorkflowDAG]
    error: Optional[str] = None

    @property
    def node_count(self) -> int:
        return len(self.dag.nodes) if self.dag else 0


@dataclass
class WorkflowBuildReport:
    """Summary of an end-to-end workflow build run."""

    environment: Path
    installed: Sequence[str]
    plans: List[WorkflowPlanResult]

    @property
    def success_rate(self) -> float:
        if not self.plans:
            return 0.0
        successes = sum(1 for plan in self.plans if plan.compiled and plan.dag)
        return successes / len(self.plans)


def create_virtualenv(path: Path | str) -> Path:
    """Create a Python virtual environment at ``path``.

    Args:
        path: Destination for the virtual environment.

    Returns:
        Path to the created environment directory.
    """

    env_path = Path(path)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "venv", str(env_path)], check=True)
    return env_path


def install_dependencies(env_path: Path, dependencies: Sequence[str]) -> None:
    """Install dependencies into the provided virtual environment."""

    if not dependencies:
        return

    pip_dir = "Scripts" if sys.platform.startswith("win") else "bin"
    pip_executable = env_path / pip_dir / "pip"
    subprocess.run([str(pip_executable), "install", *dependencies], check=True)


def generate_workflow_queries(task: str, *, variations: int = 3) -> List[str]:
    """Create simple query variants for workflow planning."""

    base = task.strip()
    if not base:
        raise ValueError("Task description must be non-empty")

    queries = [base]
    for idx in range(1, variations):
        queries.append(f"{base} (variation {idx})")
    return queries


def build_workflow_plan(
    query: str, available_nodes: Iterable[str], *, orchestrator: LLMOrchestrator
) -> PlannedWorkflow:
    """Create workflow code for a single query using an LLM orchestrator."""

    return orchestrator.plan_workflow(query, available_nodes)


def validate_workflow_plan(plan: PlannedWorkflow, query: str) -> WorkflowPlanResult:
    """Compile and parse a generated workflow plan."""

    try:
        compile(plan.code, "<workflow_plan>", "exec")
        dag = parse_workflow_code(plan.code)
        return WorkflowPlanResult(query=query, code=plan.code, compiled=True, dag=dag)
    except Exception as exc:
        return WorkflowPlanResult(
            query=query, code=plan.code, compiled=False, dag=None, error=str(exc)
        )


def run_end_to_end(
    task: str,
    available_nodes: Iterable[str],
    *,
    env_dir: str | Path = ".venv",
    dependencies: Sequence[str] = (),
    orchestrator: LLMOrchestrator,
) -> WorkflowBuildReport:
    """Execute the full build pipeline used by integration tests."""

    env_path = create_virtualenv(Path(env_dir))
    install_dependencies(env_path, dependencies)

    plans: List[WorkflowPlanResult] = []
    for query in generate_workflow_queries(task):
        plan = build_workflow_plan(query, available_nodes, orchestrator=orchestrator)
        plans.append(validate_workflow_plan(plan, query))

    return WorkflowBuildReport(environment=env_path, installed=list(dependencies), plans=plans)


__all__ = [
    "WorkflowPlanResult",
    "WorkflowBuildReport",
    "build_workflow_plan",
    "create_virtualenv",
    "generate_workflow_queries",
    "install_dependencies",
    "run_end_to_end",
    "validate_workflow_plan",
]
