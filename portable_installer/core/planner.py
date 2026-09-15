from __future__ import annotations

from ..models import Program


def resolve_install_plan(
    selected: list[str],
    program_by_id: dict[str, Program],
) -> tuple[list[str], set[str]]:
    requested = set(selected)
    plan: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(program_id: str) -> None:
        if program_id in visited:
            return
        if program_id in visiting:
            raise RuntimeError(f"Circular dependency detected: {program_id}")
        if program_id not in program_by_id:
            raise RuntimeError(f"Unknown program dependency: {program_id}")

        program = program_by_id[program_id]
        visiting.add(program_id)

        for dependency_id in program.dependencies:
            dependency = program_by_id[dependency_id]
            if dependency_id not in requested and dependency.installed():
                continue
            visit(dependency_id)

        visiting.remove(program_id)
        visited.add(program_id)
        plan.append(program_id)

    for program_id in selected:
        visit(program_id)

    return plan, requested
