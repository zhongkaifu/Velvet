import unittest

from orchestrator.nodes import (
    conditional_check,
    loop_check,
    time_based_trigger,
    user_approval_check,
)


class TestActivationNodes(unittest.TestCase):
    def test_conditional_check_includes_optional_details(self) -> None:
        payload = conditional_check("x > 5", expected=False, details="guard clause")
        self.assertEqual(
            payload,
            {
                "type": "conditional_check",
                "condition": "x > 5",
                "expected": False,
                "details": "guard clause",
            },
        )

    def test_loop_check_sets_status(self) -> None:
        continue_payload = loop_check("retry", iteration=1, limit=3)
        stop_payload = loop_check("retry", iteration=3, limit=3)
        self.assertEqual(continue_payload["status"], "continue")
        self.assertEqual(stop_payload["status"], "stop")

    def test_user_approval_check(self) -> None:
        payload = user_approval_check(
            "publish_report", approver="manager@example.com", message="Review draft"
        )
        self.assertEqual(
            payload,
            {
                "type": "user_approval_check",
                "step": "publish_report",
                "approver": "manager@example.com",
                "message": "Review draft",
            },
        )

    def test_time_based_trigger_defaults_timezone(self) -> None:
        payload = time_based_trigger("2024-06-01T12:00:00")
        self.assertEqual(payload["timezone"], "UTC")
        self.assertIn("window_minutes", payload)


if __name__ == "__main__":
    unittest.main()
