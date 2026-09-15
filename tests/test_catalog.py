from __future__ import annotations

import unittest
from pathlib import PureWindowsPath

from portable_installer.catalog import ECOSYSTEM_ORDER, PROGRAMS, PROGRAM_BY_ID


NEW_TOOL_IDS = {
    "jq",
    "ripgrep",
    "sqlite",
    "fzf",
    "duckdb",
    "powershell",
    "terraform",
    "kubectl",
    "helm",
    "rclone",
}


class CatalogTests(unittest.TestCase):
    def test_program_ids_are_unique(self) -> None:
        self.assertEqual(len(PROGRAMS), len(PROGRAM_BY_ID))

    def test_new_tooling_is_registered(self) -> None:
        self.assertTrue(NEW_TOOL_IDS.issubset(PROGRAM_BY_ID))

    def test_every_program_declares_permanent_user_path(self) -> None:
        missing = [program.id for program in PROGRAMS if not program.path_entries]
        self.assertEqual(missing, [])

    def test_path_entries_are_safe_relative_paths(self) -> None:
        invalid: list[str] = []
        for program in PROGRAMS:
            for entry in program.path_entries:
                path = PureWindowsPath(entry)
                if path.is_absolute() or ".." in path.parts:
                    invalid.append(f"{program.id}:{entry}")
        self.assertEqual(invalid, [])

    def test_every_ecosystem_is_renderable(self) -> None:
        ecosystems = {program.ecosystem for program in PROGRAMS}
        self.assertTrue(ecosystems.issubset(set(ECOSYSTEM_ORDER)))


if __name__ == "__main__":
    unittest.main()
