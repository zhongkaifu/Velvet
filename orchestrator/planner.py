"""Orchestrator that uses GPT to assemble executable workflow code."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .workflow import WorkflowDAG, WorkflowNode, parse_workflow_code


DEFAULT_SYSTEM_PROMPT = """You are a workflow planner. Build Python code that wires activation
nodes into an executable DAG. Use the WorkflowDAG and nodes from the
`orchestrator` package. Always create named WorkflowNode instances and
connect them in execution order."""


@dataclass
class PlannedWorkflow:
    """Returned plan that contains generated code and a short rationale."""

    code: str
    rationale: str


class LLMOrchestrator:
    """Generate workflow code and DAGs using an OpenAI client."""

    def __init__(self, *, model: str = "gpt-4o-mini", client: Optional[object] = None) -> None:
        self.model = model
        if client is None:
            from openai import OpenAI  # type: ignore

            self.client = OpenAI()
        else:
            self.client = client

    def build_prompt(self, task: str, available_nodes: Iterable[str]) -> str:
        readable_nodes = "\n".join(f"- {name}" for name in available_nodes)
        return (
            f"Task: {task}\n"
            "You can use the following activation nodes:\n"
            f"{readable_nodes}\n"
            "Return valid Python that builds a WorkflowDAG named `dag` and populates it."
        )

    def plan_workflow(self, task: str, available_nodes: Iterable[str]) -> PlannedWorkflow:
        """Ask GPT to assemble Python code for a workflow DAG."""

        prompt = self.build_prompt(task, available_nodes)
        completion = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_output_tokens=800,
        )
        parsed = getattr(completion, "output_parsed", None)
        if isinstance(parsed, str):
            code = parsed
        elif parsed is not None:
            code = getattr(parsed, "content", "") or str(parsed)
        else:
            code = getattr(completion, "output_text", "")
        rationale = "Generated workflow using available activation nodes."
        return PlannedWorkflow(code=code, rationale=rationale)

    def materialize_dag(self, plan: PlannedWorkflow) -> WorkflowDAG:
        """Statically analyze plan code to produce a :class:`WorkflowDAG`."""

        if not plan.code.strip():
            raise ValueError("Plan code is empty; cannot build a DAG")

        return parse_workflow_code(plan.code)

    def export_plan_dag(self, plan: PlannedWorkflow, path: str, format: str = "png") -> str:
        """Materialize and export a DAG image from a generated workflow plan."""

        dag = self.materialize_dag(plan)
        return dag.export_image(path, format=format)

    def save_plan(self, plan: PlannedWorkflow, path: str) -> str:
        """Persist generated code to a file for execution or review."""

        with open(path, "w", encoding="utf-8") as fp:
            fp.write(plan.code)
        return path


__all__ = ["LLMOrchestrator", "PlannedWorkflow", "DEFAULT_SYSTEM_PROMPT"]
