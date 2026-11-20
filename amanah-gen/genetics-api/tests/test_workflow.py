import unittest

from workflow import STATES, TERMINAL_STATES, is_valid_transition, workflow_definition


class ScreeningWorkflowTests(unittest.TestCase):
    def test_workflow_has_expected_lifecycle_states(self):
        self.assertEqual(
            STATES,
            (
                "requested",
                "sample_collected",
                "lab_received",
                "processing",
                "result_received",
                "clinical_review",
                "clinically_reviewed",
                "follow_up_required",
                "completed",
                "cancelled",
            ),
        )

    def test_happy_path_transitions_are_allowed(self):
        path = [
            ("requested", "sample_collected"),
            ("sample_collected", "lab_received"),
            ("lab_received", "processing"),
            ("processing", "result_received"),
            ("result_received", "clinical_review"),
            ("clinical_review", "clinically_reviewed"),
            ("clinically_reviewed", "follow_up_required"),
            ("follow_up_required", "completed"),
        ]
        for current, following in path:
            with self.subTest(current=current, following=following):
                self.assertTrue(is_valid_transition(current, following))

    def test_skipping_clinical_review_is_rejected(self):
        self.assertFalse(is_valid_transition("result_received", "completed"))
        self.assertFalse(is_valid_transition("result_received", "follow_up_required"))

    def test_terminal_states_cannot_transition(self):
        for state in TERMINAL_STATES:
            self.assertFalse(is_valid_transition(state, "requested"))
            self.assertFalse(is_valid_transition(state, "completed"))

    def test_unknown_states_are_rejected(self):
        self.assertFalse(is_valid_transition("unknown", "requested"))
        self.assertFalse(is_valid_transition("requested", "unknown"))

    def test_definition_documents_consent_and_release_gates(self):
        definition = workflow_definition()
        self.assertIn("consent", definition["creation_rule"].lower())
        self.assertIn("clinical review", definition["release_rule"].lower())


if __name__ == "__main__":
    unittest.main()
