import unittest

from mini_alfworld_env import MiniALFWorldEnv


class MiniALFWorldEnvTests(unittest.TestCase):
    def test_put_apple_is_not_admissible_until_fridge_is_open(self):
        env = MiniALFWorldEnv()
        env.reset()
        env.step(["go to kitchen"])
        env.step(["take apple"])

        self.assertIn("open fridge", env._admissible_commands())
        self.assertNotIn("put apple in fridge", env._admissible_commands())

        env.step(["open fridge"])

        self.assertIn("put apple in fridge", env._admissible_commands())


if __name__ == "__main__":
    unittest.main()
