# Orchestrator utilities

This repository provides a lightweight Python package for orchestrating GPT-generated workflows. It includes activation node helpers, a minimal DAG representation, and an orchestrator that uses OpenAI GPT models to assemble executable Python code.

## Installation

Install dependencies for DAG image export:

```bash
pip install graphviz
```

You also need the OpenAI Python SDK configured with `OPENAI_API_KEY` to generate plans.

## Quick start

```python
from orchestrator import (
    LLMOrchestrator,
    WorkflowDAG,
    WorkflowNode,
    parse_workflow_code,
    send_message,
    send_email,
)

available_nodes = [
    "send_message(recipient, body)",
    "send_email(to, subject, body)",
    "make_call(phone_number, script)",
]

orchestrator = LLMOrchestrator(model="gpt-4o-mini")
plan = orchestrator.plan_workflow(
    "Follow up with the product team, summarize open issues, and email stakeholders.",
    available_nodes,
)

# Save or execute the generated Python code
orchestrator.save_plan(plan, "workflow_plan.py")
print(plan.rationale)

# Automatically materialize the DAG from the generated code *without executing it*
dag = orchestrator.materialize_dag(plan)
image_path = orchestrator.export_plan_dag(plan, "workflow")
print(f"DAG exported to {image_path}")

# Or statically parse a saved workflow file yourself
with open("workflow_plan.py", "r", encoding="utf-8") as fp:
    saved_code = fp.read()
dag = parse_workflow_code(saved_code)
print(f"Parsed nodes: {list(dag.nodes)}")

# Manually build a DAG

dag = WorkflowDAG()
dag.add_node(WorkflowNode("summarize", "generate_summary", {"text": "Open issues"}))
dag.add_node(WorkflowNode("notify", "send_message", {"recipient": "product-team", "body": "Summary ready"}))
dag.add_edge("summarize", "notify")
image_path = dag.export_image("workflow")
print(f"DAG exported to {image_path}")
```

The activation nodes in `orchestrator.nodes` expose clear parameters for non-technical users and can be combined in GPT-generated workflows or manually constructed DAGs.

## End-to-end workflow validation

The `orchestrator.workflow_builder` module offers a harness to mirror the integration steps described in testing scenarios: create a virtual environment, install dependencies, generate workflow queries, and validate that the resulting Python code compiles to a `WorkflowDAG`.

```python
from orchestrator import LLMOrchestrator, run_end_to_end

report = run_end_to_end(
    "Plan a morning status update",
    [
        "generate_summary(text)",
        "send_message(recipient, body)",
    ],
    env_dir=".venv",
    dependencies=["graphviz"],
    orchestrator=LLMOrchestrator(model="gpt-4o-mini"),
)

print(f"Success rate: {report.success_rate:.0%}")
for plan in report.plans:
    print(plan.query, plan.node_count, plan.compiled)
```
