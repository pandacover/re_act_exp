import unittest

from menu_policy import normalize_action, action_looks_valid, pick_fallback_action


class MenuPolicyTests(unittest.TestCase):
    def test_normalize_prefers_admissible_command_inside_messy_output(self):
        admissible = ["look", "inventory", "go to kitchen"]
        raw = "I should inspect first.\nAction: go to kitchen"
        self.assertEqual(normalize_action(raw, admissible), "go to kitchen")

    def test_invalid_action_is_rejected_when_menu_is_available(self):
        admissible = ["look", "inventory", "go to kitchen"]
        self.assertFalse(action_looks_valid("open fridge", admissible))

    def test_fallback_prefers_progress_over_look(self):
        admissible = ["look", "inventory", "go to kitchen"]
        self.assertEqual(pick_fallback_action(admissible), "go to kitchen")


if __name__ == "__main__":
    unittest.main()
