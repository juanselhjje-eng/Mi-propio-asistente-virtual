import unittest

from runtime import looks_like_programming, requests_implementation
from subagents import detect_specialists


class RuntimeRoutingTests(unittest.TestCase):
    def test_simple_greeting_is_general(self):
        self.assertFalse(looks_like_programming("hola", []))

    def test_general_question_is_general(self):
        self.assertFalse(looks_like_programming("qué es la fotosíntesis", []))

    def test_python_question_stays_general(self):
        self.assertFalse(looks_like_programming("qué es Python", []))

    def test_python_assistant_is_development(self):
        request = "créame un asistente IA con Python"
        self.assertTrue(looks_like_programming(request, []))
        self.assertTrue(requests_implementation(request))
        names = {agent.name for agent in detect_specialists([], request)}
        self.assertIn("python", names)
        self.assertNotIn("pygame", names)

    def test_racing_game_is_not_used_as_default_domain(self):
        request = "crea un juego de carreras"
        names = {agent.name for agent in detect_specialists([], request)}
        self.assertNotIn("python", names)
        self.assertNotIn("pygame", names)

    def test_new_request_does_not_inherit_old_game_domain(self):
        history = [{"role": "user", "content": "crea un juego de carreras"}]
        request = "crea un asistente IA con Python"
        names = {agent.name for agent in detect_specialists([], request)}
        self.assertTrue(looks_like_programming(request, history))
        self.assertIn("python", names)
        self.assertNotIn("pygame", names)


if __name__ == "__main__":
    unittest.main()
