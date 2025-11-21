"""Workflow DAG utilities for orchestrating activation nodes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

import ast


@dataclass
class WorkflowNode:
    """A node in the workflow graph representing an executable step."""

    name: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)

    def describe(self) -> str:
        """Human-readable description of the node."""
        args = ", ".join(f"{key}={value!r}" for key, value in self.params.items())
        return f"{self.action}({args})"


class WorkflowDAG:
    """Minimal DAG to store workflow nodes and edges."""

    def __init__(self) -> None:
        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: Dict[str, Set[str]] = {}

    def add_node(self, node: WorkflowNode) -> None:
        if node.name in self.nodes:
            raise ValueError(f"Node with name '{node.name}' already exists")
        self.nodes[node.name] = node
        self.edges[node.name] = set()

    def add_edge(self, source: str, target: str) -> None:
        if source not in self.nodes or target not in self.nodes:
            raise KeyError("Both source and target must be added before connecting")
        self.edges[source].add(target)

    def topological_order(self) -> List[WorkflowNode]:
        visited: Set[str] = set()
        temp: Set[str] = set()
        order: List[str] = []

        def visit(node_name: str) -> None:
            if node_name in temp:
                raise ValueError("Cycle detected in workflow")
            if node_name in visited:
                return
            temp.add(node_name)
            for neighbor in self.edges[node_name]:
                visit(neighbor)
            temp.remove(node_name)
            visited.add(node_name)
            order.append(node_name)

        for name in self.nodes:
            if name not in visited:
                visit(name)

        return [self.nodes[name] for name in reversed(order)]

    def to_dot(self) -> str:
        """Create a Graphviz DOT representation of the DAG."""

        lines = ["digraph workflow {"]
        for name, node in self.nodes.items():
            lines.append(f'    "{name}" [label="{node.describe()}"];')
        for source, targets in self.edges.items():
            for target in targets:
                lines.append(f'    "{source}" -> "{target}";')
        lines.append("}")
        return "\n".join(lines)

    def export_image(self, path: str, format: str = "png") -> str:
        """Export the DAG to an image using graphviz if available.

        Args:
            path: Base filename (without extension) or full path where the image should be written.
            format: Graphviz output format such as "png" or "pdf".

        Returns:
            The fully qualified path to the rendered image.
        """

        try:
            from graphviz import Source
        except ModuleNotFoundError as exc:  # pragma: no cover - clear error for users
            raise ModuleNotFoundError(
                "The 'graphviz' package is required for image export. Install with `pip install graphviz` "
                "and ensure Graphviz binaries are available."
            ) from exc

        dot = self.to_dot()
        graph = Source(dot, format=format)
        output_path = graph.render(filename=path, cleanup=True)
        return output_path

    def execute(self, runner: Callable[[WorkflowNode], Any]) -> List[Any]:
        """Execute the workflow nodes in topological order using a runner callable."""

        results: List[Any] = []
        for node in self.topological_order():
            results.append(runner(node))
        return results


def _literal_eval_node(node: ast.AST, *, label: str) -> Any:
    """Safely evaluate AST literals with friendlier error messages."""

    try:
        return ast.literal_eval(node)
    except Exception as exc:  # pragma: no cover - defensive error path
        raise ValueError(f"Unable to evaluate {label} from workflow code") from exc


def _is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _is_dag_method_call(call: ast.Call, dag_names: Set[str], method: str) -> bool:
    if not isinstance(call.func, ast.Attribute):
        return False
    if not isinstance(call.func.value, ast.Name):
        return False
    return call.func.value.id in dag_names and call.func.attr == method


def _parse_workflow_node_call(call: ast.Call, *, default_name: str | None = None) -> WorkflowNode:
    if not _is_name(call.func, "WorkflowNode"):
        raise ValueError("add_node must wrap a WorkflowNode construction")

    name: Any = None
    action: Any = None
    params: Dict[str, Any] = {}

    if call.args:
        if len(call.args) >= 1:
            name = _literal_eval_node(call.args[0], label="node name")
        if len(call.args) >= 2:
            action = _literal_eval_node(call.args[1], label="node action")
        if len(call.args) >= 3:
            params = _literal_eval_node(call.args[2], label="node params")
    for kw in call.keywords:
        if kw.arg == "name":
            name = _literal_eval_node(kw.value, label="node name")
        elif kw.arg == "action":
            action = _literal_eval_node(kw.value, label="node action")
        elif kw.arg == "params":
            params = _literal_eval_node(kw.value, label="node params")

    if name is None:
        name = default_name

    # Default the action to the node name when not explicitly provided. This
    # makes the parser tolerant of minimal WorkflowNode declarations where only
    # a name is supplied.
    if action is None and name is not None:
        action = name

    missing = [
        field
        for field, value in (("name", name), ("action", action))
        if value is None
    ]
    if missing:
        missing_fields = ", ".join(missing)
        raise ValueError(f"WorkflowNode requires values for: {missing_fields}")
    if not isinstance(params, dict):
        raise ValueError("WorkflowNode params must be a dictionary")

    return WorkflowNode(name=str(name), action=str(action), params=params)


def parse_workflow_code(code: str) -> WorkflowDAG:
    """Statically analyze workflow Python code and build an equivalent DAG.

    The parser looks for ``WorkflowDAG`` instantiations assigned to variables
    and then captures ``add_node`` and ``add_edge`` method calls to reconstruct
    the graph without executing the user-provided code.
    """

    module = ast.parse(code)

    dag_names: Set[str] = set()
    named_nodes: Dict[str, WorkflowNode] = {}
    for stmt in module.body:
        if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
            if _is_name(stmt.value.func, "WorkflowDAG"):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        dag_names.add(target.id)
            elif _is_name(stmt.value.func, "WorkflowNode"):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        named_nodes[target.id] = _parse_workflow_node_call(
                            stmt.value, default_name=target.id
                        )

    if not dag_names:
        raise ValueError("No WorkflowDAG instance found in the provided code")

    dag = WorkflowDAG()
    edges: List[tuple[str, str]] = []

    for stmt in module.body:
        call: Optional[ast.Call] = None
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
        elif isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
            call = stmt.value

        if call is None:
            continue

        if _is_dag_method_call(call, dag_names, "add_node"):
            if not call.args:
                raise ValueError("add_node must receive a WorkflowNode instance")
            node_ref = call.args[0]
            if isinstance(node_ref, ast.Call):
                node = _parse_workflow_node_call(node_ref)
            elif isinstance(node_ref, ast.Name) and node_ref.id in named_nodes:
                node = named_nodes[node_ref.id]
            else:
                raise ValueError(
                    "add_node expects a WorkflowNode constructor call or named instance"
                )
            dag.add_node(node)
        elif _is_dag_method_call(call, dag_names, "add_edge"):
            if len(call.args) < 2:
                raise ValueError("add_edge requires source and target node names")
            source = _literal_eval_node(call.args[0], label="edge source")
            target = _literal_eval_node(call.args[1], label="edge target")
            edges.append((str(source), str(target)))

    for source, target in edges:
        dag.add_edge(source, target)

    return dag
