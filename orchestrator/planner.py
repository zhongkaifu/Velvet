"""Orchestrator that uses GPT to assemble executable workflow code."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from .workflow import WorkflowDAG, WorkflowNode, parse_workflow_code


logger = logging.getLogger(__name__)


DEFAULT_SYSTEM_PROMPT = """You are a workflow planner. Build Python code that wires activation
nodes into an executable DAG. Use the WorkflowDAG and nodes from the
`orchestrator` package. Always create named WorkflowNode instances and
connect them in execution order. Ensure the Python you return compiles
without syntax errors."""


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

    def build_prompt(self, task: str, available_nodes: Sequence[str]) -> str:
        readable_nodes = "\n".join(f"- {name}" for name in available_nodes)
        return (
            f"Task: {task}\n"
            "You can use the following activation nodes:\n"
            f"{readable_nodes}\n"
            "Return valid Python that builds a WorkflowDAG named `dag` and populates it."
        )

    def _response_text(self, completion: object) -> str:
        """Retrieve the raw text content from an LLM completion."""

        parsed = getattr(completion, "output_parsed", None)
        if isinstance(parsed, str):
            raw = parsed
        elif parsed is not None:
            raw = getattr(parsed, "content", "") or str(parsed)
        else:
            raw = getattr(completion, "output_text", "")

        return (raw if isinstance(raw, str) else str(raw)).strip()

    def _log_completion_output(self, completion: object, *, label: str) -> None:
        """Log the complete LLM response text for transparency."""

        raw_text = self._response_text(completion)
        if raw_text:
            logger.info("%s LLM output:\n%s", label, raw_text)
        else:
            logger.info("%s LLM output was empty", label)

    def _extract_code(self, completion: object) -> str:
        """Extract Python source from an OpenAI response payload."""

        code = self._response_text(completion)

        fenced_blocks = re.findall(r"```(?:python)?\n?(.*?)```", code, flags=re.DOTALL)
        if fenced_blocks:
            code = "\n\n".join(block.strip() for block in fenced_blocks if block.strip())

        logger.debug("Extracted workflow code with length %d characters", len(code))
        return code

    def plan_workflow(self, task: str, available_nodes: Iterable[str]) -> PlannedWorkflow:
        """Ask GPT to assemble Python code for a workflow DAG."""

        available_nodes_list = list(available_nodes)
        prompt = self.build_prompt(task, available_nodes_list)
        logger.info(
            "Requesting workflow plan for task '%s' using %d available nodes",
            task,
            len(available_nodes_list),
        )
        completion = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_output_tokens=800,
        )
        self._log_completion_output(completion, label="Initial workflow plan")
        code = self._extract_code(completion)
        rationale = "Generated workflow using available activation nodes."
        logger.debug("Generated workflow code preview: %s", code[:200])
        logger.info("Full generated workflow code for task '%s':\n%s", task, code)
        return PlannedWorkflow(code=code, rationale=rationale)

    def revise_workflow(
        self,
        task: str,
        available_nodes: Iterable[str],
        *,
        previous_code: str,
        error_message: str,
    ) -> PlannedWorkflow:
        """Request a corrected workflow plan when compilation fails."""

        available_nodes_list = list(available_nodes)
        prompt = self.build_prompt(task, available_nodes_list)
        messages = [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": previous_code},
            {
                "role": "user",
                "content": (
                    "The previous workflow code failed to compile. "
                    "Fix the syntax or structural issues so the code compiles and builds a valid WorkflowDAG.\n"
                    f"Compilation error: {error_message}\n"
                    "Please return the corrected Python workflow code."
                ),
            },
        ]

        completion = self.client.responses.create(
            model=self.model,
            input=messages,
            max_output_tokens=800,
        )
        self._log_completion_output(completion, label="Revised workflow plan")
        code = self._extract_code(completion)
        rationale = "Revised workflow after addressing compilation error."
        logger.info("Received revised workflow code for task '%s'", task)
        logger.info("Full revised workflow code for task '%s':\n%s", task, code)
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
