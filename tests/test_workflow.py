import unittest

from orchestrator.workflow import parse_workflow_code


class TestWorkflowParsingDefaults(unittest.TestCase):
    def test_defaults_action_to_name_when_missing(self) -> None:
        code = """
from orchestrator.workflow import WorkflowDAG, WorkflowNode

dag = WorkflowDAG()
dag.add_node(WorkflowNode("greet"))
"""
        dag = parse_workflow_code(code)
        node = dag.nodes["greet"]
        self.assertEqual(node.action, "greet")
        self.assertEqual(node.params, {})

    def test_preserves_explicit_action(self) -> None:
        code = """
from orchestrator.workflow import WorkflowDAG, WorkflowNode

dag = WorkflowDAG()
dag.add_node(WorkflowNode("step", "explicit_action"))
"""
        dag = parse_workflow_code(code)
        node = dag.nodes["step"]
        self.assertEqual(node.action, "explicit_action")

    def test_defaults_action_for_named_reference(self) -> None:
        code = """
from orchestrator.workflow import WorkflowDAG, WorkflowNode

dag = WorkflowDAG()
intro = WorkflowNode(name="intro")
dag.add_node(intro)
"""
        dag = parse_workflow_code(code)
        node = dag.nodes["intro"]
        self.assertEqual(node.action, "intro")


if __name__ == "__main__":
    unittest.main()
