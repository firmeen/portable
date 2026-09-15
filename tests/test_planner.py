from __future__ import annotations

import unittest

from portable_installer.core.planner import resolve_install_plan
from portable_installer.models import Priority, Program


def noop() -> str:
    return "ok"


def missing() -> bool:
    return False


class PlannerTests(unittest.TestCase):
    def test_dependency_is_inserted_before_requested_program(self) -> None:
        programs = {
            "node": Program("node", "Node", "", "JS", Priority.CORE, noop, missing),
            "codex": Program(
                "codex",
                "Codex",
                "",
                "AI",
                Priority.RECOMMENDED,
                noop,
                missing,
                dependencies=("node",),
            ),
        }
        plan, requested = resolve_install_plan(["codex"], programs)
        self.assertEqual(plan, ["node", "codex"])
        self.assertEqual(requested, {"codex"})

    def test_duplicate_dependency_only_appears_once(self) -> None:
        programs = {
            "node": Program("node", "Node", "", "JS", Priority.CORE, noop, missing),
            "a": Program("a", "A", "", "AI", Priority.RECOMMENDED, noop, missing, ("node",)),
            "b": Program("b", "B", "", "AI", Priority.RECOMMENDED, noop, missing, ("node",)),
        }
        plan, _ = resolve_install_plan(["a", "b"], programs)
        self.assertEqual(plan, ["node", "a", "b"])

    def test_cycle_is_rejected(self) -> None:
        programs = {
            "a": Program("a", "A", "", "X", Priority.CORE, noop, missing, ("b",)),
            "b": Program("b", "B", "", "X", Priority.CORE, noop, missing, ("a",)),
        }
        with self.assertRaises(RuntimeError):
            resolve_install_plan(["a"], programs)


if __name__ == "__main__":
    unittest.main()
